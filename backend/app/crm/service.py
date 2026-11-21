import logging
import threading
import time
import zoneinfo
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from fastapi import Request
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, or_, and_
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.dependencies import CurrentUser
from app.core.exceptions import (
    PermissionDeniedError,
    ValidationError,
    NotFoundError,
    ConflictError
)
from app.users.model import User
from app.crm.permissions import is_crm_admin_or_manager
from app.crm.catalogue_model import OpportunityQuotationItem
from app.modules.model import Module, ModuleRole, UserModuleMembership
from app.crm.model import (
    Account,
    Contact,
    Lead,
    LeadRequirementType,
    LeadContactMethod,
    Opportunity,
    LeadCommunicationHistory,
    CrmSequence,
    ConsultingEngagement,
    SampleSubmission,
    SampleTestRequest,
    TestingChargeRecord,
    ProductTransaction,
    Milestone,
    OpportunityQuotation,
    OpportunityStageHistory,
    CrmIdempotencyRecord
)
from app.crm.invoice_model import ProformaInvoice
from app.files.model import FileMetadata
from app.crm.schema import (
    AccountCreate,
    AccountUpdate,
    ContactCreate,
    ContactUpdate,
    LeadCreate,
    LeadUpdate,
    CommunicationCreate,
    OpportunityCreate,
    OpportunityUpdate,
    LeadQualifyRequest,
    ConsultingEngagementCreate,
    SampleSubmissionCreate,
    ProductTransactionCreate,
    OpportunityStageTransitionRequest,
    OpportunityUpdateRequest,
    PipelineStageMetrics,
    OpportunityPipelineSummaryResponse,
    WorkstreamItem,
    OpportunityWorkstreamsResponse,
    RequirementRouteRequest,
    RequirementRouteResponse,
    MilestoneCreate,
    MilestoneUpdate,
    MilestoneStatusTransitionRequest,
    MilestoneItem,
    MilestoneListResponse,
    MilestoneDetailResponse,
    OpportunityQuotationCreate,
    OpportunityQuotationUpdate,
    OpportunityQuotationApprovalRequest,
    OpportunityQuotationShareRequest,
    OpportunityReopenRequest,
    APPROVED_CURRENCIES,
    OPPORTUNITY_STAGES,
    ALLOWED_BUSINESS_AREAS,
    ALLOWED_REQUIREMENT_TYPES,
    ALLOWED_LEAD_SOURCES,
    ALLOWED_LIFECYCLE_STATUSES,
    normalize_and_validate_req_types
)
from app.roles.assignment_service import RoleAssignmentService
from app.audit.service import AuditService

logger = logging.getLogger("revy.crm.service")


def normalize_text(val: Optional[str]) -> str:
    """Normalizes text by trimming, lowercasing, and collapsing multiple whitespace."""
    if not val:
        return ""
    return " ".join(val.strip().lower().split())


def _iso_utc(dt: Any) -> Optional[str]:
    """
    Formats a datetime or date into an unambiguous ISO-8601 string with explicit UTC offset (+00:00).
    If dt is a date-only object, returns YYYY-MM-DD.
    """
    if not dt:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    if isinstance(dt, date):
        return dt.isoformat()
    return str(dt)


_sequence_lock = threading.Lock()
_sqlite_write_lock = threading.Lock()


def get_next_sequence_id(db: Session, entity_name: str, prefix: str, padding: int = 5, commit: bool = True) -> str:
    """
    Concurrency-safe sequence generator using CrmSequence with thread locking and row locking.
    Generates IDs like LEAD-00001, ACC-00001, CON-00001, COM-00001, ENG-00001, SMP-00001, TST-00001, CHG-00001, PRD-00001.
    If commit=False, flushes instead of committing to preserve outer transaction atomicity.
    Includes concurrency lock retries for SQLite test environments.
    """
    entity_key = entity_name.strip().upper()
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with _sequence_lock:
                seq = db.query(CrmSequence).filter(CrmSequence.entity_name == entity_key).with_for_update().first()
                if not seq:
                    try:
                        seq = CrmSequence(entity_name=entity_key, current_value=1)
                        db.add(seq)
                        if commit:
                            db.commit()
                        else:
                            db.flush()
                        return f"{prefix}-{1:0{padding}d}"
                    except IntegrityError:
                        db.rollback()
                        seq = db.query(CrmSequence).filter(CrmSequence.entity_name == entity_key).with_for_update().first()

                seq.current_value += 1
                if commit:
                    db.commit()
                else:
                    db.flush()
                return f"{prefix}-{seq.current_value:0{padding}d}"
        except (OperationalError, Exception) as e:
            try:
                db.rollback()
            except Exception:
                pass
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(0.05 * (attempt + 1))
                continue
            raise


def record_opportunity_stage_transition(
    db: Session,
    opp: Opportunity,
    new_stage: str,
    triggering_event: str,
    actor: Any = None,
    remarks: Optional[str] = None,
    commit: bool = False
) -> OpportunityStageHistory:
    """
    Centralized stage transition service for CRM Opportunities.
    Enforces automated business transitions, updates opportunity.stage,
    and records an immutable stage history entry.
    """
    old_stage = opp.stage or "Enquiry"

    history_entry = OpportunityStageHistory(
        opportunity_id=opp.id,
        previous_stage=old_stage,
        new_stage=new_stage,
        triggering_event=triggering_event,
        triggering_user_id=str(actor.id) if actor and getattr(actor, "id", None) else None,
        triggering_user_name=getattr(actor, "name", None) or getattr(actor, "username", "System"),
        remarks=remarks,
        created_at=datetime.now(timezone.utc)
    )
    db.add(history_entry)

    opp.stage = new_stage
    opp.updated_at = datetime.now(timezone.utc)
    if actor and getattr(actor, "id", None):
        opp.updated_by_id = str(actor.id)

    if commit:
        db.commit()
        db.refresh(opp)
    else:
        db.flush()

    return history_entry


INTERNAL_EVENT_KEYWORDS = [
    "internal", "colleague", "note", "internal note",
    "internal discussion", "discussion with revy colleague",
    "revy team", "team discussion", "requirement analysis"
]


def is_qualifying_client_interaction(event_type: str) -> bool:
    """
    Returns True if an event qualifies as a client-facing interaction
    that updates the Lead's last_connected_date.
    Internal notes and colleague discussions return False.
    """
    clean = (event_type or "").strip().lower()
    for kw in INTERNAL_EVENT_KEYWORDS:
        if kw in clean:
            return False
    return True


class CrmService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def _get_crm_module(self) -> Module:
        crm_mod = self.db.query(Module).filter(Module.code == "CRM").first()
        if not crm_mod:
            raise NotFoundError("CRM module is not registered in the system.")
        return crm_mod

    # =========================================================================
    # 1. CRM USER HUB SERVICES
    # =========================================================================

    def list_crm_users(
        self,
        actor: CurrentUser,
        search: Optional[str] = None,
        crm_access: Optional[bool] = None,
        role_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        crm_mod = self._get_crm_module()

        # Hybrid User Management: Only list users who have explicit CRM module membership
        query = (
            self.db.query(UserModuleMembership)
            .join(User, UserModuleMembership.user_id == User.id)
            .options(
                joinedload(UserModuleMembership.user).joinedload(User.employee),
                joinedload(UserModuleMembership.role)
            )
            .filter(
                UserModuleMembership.module_id == crm_mod.id,
                User.is_hard_deleted == False
            )
        )

        if crm_access is not None:
            query = query.filter(UserModuleMembership.is_active == crm_access)

        if search:
            s = f"%{search.strip().lower()}%"
            query = query.filter(
                (func.lower(User.name).like(s)) |
                (func.lower(User.username).like(s)) |
                (func.lower(User.email).like(s))
            )

        memberships = query.all()

        lead_counts_query = self.db.query(
            Lead.assigned_to_user_id,
            func.count(Lead.id)
        ).filter(
            Lead.assigned_to_user_id.isnot(None)
        ).group_by(
            Lead.assigned_to_user_id
        ).all()
        lead_counts = {u_id: count for u_id, count in lead_counts_query if u_id}

        result = []
        for mem in memberships:
            u = mem.user
            if not u:
                continue
            r_code = mem.role.code if (mem.role and mem.is_active) else None
            r_name = mem.role.name if (mem.role and mem.is_active) else None

            if role_code and (not r_code or r_code.upper() != role_code.strip().upper()):
                continue

            result.append({
                "userId": u.id,
                "username": u.username,
                "name": u.name or u.username,
                "email": u.email,
                "phone": u.phone or "",
                "designation": u.employee.designation if getattr(u, "employee", None) else "",
                "department": u.employee.department if getattr(u, "employee", None) else "",
                "status": u.status,
                "crmAccess": bool(mem.is_active),
                "crmRoleCode": r_code,
                "crmRoleName": r_name,
                "assignedLeadCount": lead_counts.get(u.id, 0),
                "createdAt": u.created_at.isoformat() if u.created_at else None
            })

        return sorted(result, key=lambda x: x["name"])

    def list_available_central_users(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns active Central Users who do not currently have an active CRM membership.
        """
        crm_mod = self._get_crm_module()
        active_crm_mems = self.db.query(UserModuleMembership.user_id).filter(
            UserModuleMembership.module_id == crm_mod.id,
            UserModuleMembership.is_active == True
        ).all()
        crm_user_ids = {m[0] for m in active_crm_mems}

        query = self.db.query(User).options(joinedload(User.employee)).filter(
            User.is_hard_deleted == False,
            User.status == "active"
        )
        if crm_user_ids:
            query = query.filter(User.id.notin_(crm_user_ids))

        if search:
            s = f"%{search.strip().lower()}%"
            query = query.filter(
                (func.lower(User.name).like(s)) |
                (func.lower(User.username).like(s)) |
                (func.lower(User.email).like(s)) |
                (func.lower(User.phone).like(s))
            )

        users = query.order_by(User.name.asc(), User.username.asc()).all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "name": u.name or u.username,
                "email": u.email,
                "phone": u.phone or "",
                "status": u.status,
                "designation": u.employee.designation if getattr(u, "employee", None) else "",
                "department": u.employee.department if getattr(u, "employee", None) else ""
            }
            for u in users
        ]

    def assign_user_to_crm(
        self,
        actor: CurrentUser,
        user_id: str,
        role_code: str,
        is_active: bool = True,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """
        Assigns an existing Central User to CRM with an authorized CRM role.
        Central identity is reused without duplication.
        """
        crm_mod = self._get_crm_module()
        user = self.db.query(User).filter(User.id == user_id, User.is_hard_deleted == False).first()
        if not user:
            raise NotFoundError("The specified Central User does not exist.")
        if user.status != "active":
            raise ValidationError("Cannot assign an inactive Central User to CRM. Activate user in Central User Management first.")

        target_role_code = role_code.strip().upper()
        RoleAssignmentService.validate_role_assignment(
            actor=actor,
            target_module_code="CRM",
            target_role_code=target_role_code,
            target_user_id=user.id,
            db=self.db
        )

        role = self.db.query(ModuleRole).filter(
            ModuleRole.module_id == crm_mod.id,
            ModuleRole.code == target_role_code,
            ModuleRole.is_active == True
        ).first()
        if not role:
            raise ValidationError(f"Role '{target_role_code}' does not exist or is inactive in CRM.")

        mem = self.db.query(UserModuleMembership).filter(
            UserModuleMembership.user_id == user.id,
            UserModuleMembership.module_id == crm_mod.id
        ).first()

        if mem:
            mem.is_active = is_active
            mem.role_id = role.id
        else:
            mem = UserModuleMembership(
                user_id=user.id,
                module_id=crm_mod.id,
                role_id=role.id,
                is_active=is_active
            )
            self.db.add(mem)

        self.db.commit()
        self.db.refresh(mem)

        self.audit_service.log(
            action="CRM_USER_ASSIGNED_TO_MODULE",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=actor.active_role,
            target_info={
                "userId": user.id,
                "username": user.username,
                "roleCode": role.code,
                "isActive": is_active,
                "details": f"Assigned Central User '{user.username}' to CRM with role '{role.name}' (Active: {is_active})."
            }
        )

        return self.get_crm_user_details(user.id)

    def remove_crm_membership(
        self,
        actor: CurrentUser,
        user_id: str,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """
        Removes CRM module membership for a user without deleting their central identity.
        """
        crm_mod = self._get_crm_module()
        user = self.db.query(User).filter(User.id == user_id, User.is_hard_deleted == False).first()
        if not user:
            raise NotFoundError(f"User with ID '{user_id}' not found.")

        is_global = actor.is_global_admin or "*" in (actor.permissions or []) or any(r in (actor.roles or []) for r in ["IT_ADMIN", "DIRECTOR"])
        if str(actor.id) == str(user.id) and not is_global:
            raise PermissionDeniedError("Users cannot remove their own CRM access.")

        mem = self.db.query(UserModuleMembership).filter(
            UserModuleMembership.user_id == user.id,
            UserModuleMembership.module_id == crm_mod.id
        ).first()

        if mem:
            self.db.delete(mem)
            self.db.commit()

        self.audit_service.log(
            action="CRM_USER_MEMBERSHIP_REMOVED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=actor.active_role,
            target_info={
                "userId": user.id,
                "username": user.username,
                "details": f"Removed CRM module membership for user '{user.username}'."
            }
        )

        return {
            "success": True,
            "userId": user.id,
            "username": user.username,
            "message": f"User '{user.username}' removed from CRM module."
        }

    def get_crm_user_details(self, user_id: str) -> Dict[str, Any]:
        """
        Returns read-only central profile info and CRM-specific role and membership status.
        """
        crm_mod = self._get_crm_module()
        user = (
            self.db.query(User)
            .options(joinedload(User.employee))
            .filter(User.id == user_id, User.is_hard_deleted == False)
            .first()
        )
        if not user:
            raise NotFoundError(f"User with ID '{user_id}' not found.")

        mem = self.db.query(UserModuleMembership).options(joinedload(UserModuleMembership.role)).filter(
            UserModuleMembership.user_id == user.id,
            UserModuleMembership.module_id == crm_mod.id
        ).first()

        lead_count = self.db.query(func.count(Lead.id)).filter(
            Lead.assigned_to_user_id == user.id
        ).scalar() or 0

        return {
            "userId": user.id,
            "username": user.username,
            "name": user.name or user.username,
            "email": user.email,
            "phone": user.phone or "",
            "designation": user.employee.designation if getattr(user, "employee", None) else "",
            "department": user.employee.department if getattr(user, "employee", None) else "",
            "status": user.status,
            "crmAccess": bool(mem and mem.is_active),
            "crmRoleCode": mem.role.code if (mem and mem.role and mem.is_active) else None,
            "crmRoleName": mem.role.name if (mem and mem.role and mem.is_active) else None,
            "assignedLeadCount": lead_count,
            "createdAt": user.created_at.isoformat() if user.created_at else None
        }

    def set_crm_access(
        self,
        actor: CurrentUser,
        user_id: str,
        enabled: bool,
        initial_role_code: Optional[str] = None,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        crm_mod = self._get_crm_module()

        user = self.db.query(User).filter(User.id == user_id, User.is_hard_deleted == False).first()
        if not user:
            raise NotFoundError(f"User with ID '{user_id}' not found.")

        is_global = actor.is_global_admin or "*" in (actor.permissions or []) or any(r in (actor.roles or []) for r in ["IT_ADMIN", "DIRECTOR"])
        if str(actor.id) == str(user.id) and not is_global:
            raise PermissionDeniedError("Users cannot modify their own CRM access or role.")

        mem = self.db.query(UserModuleMembership).filter(
            UserModuleMembership.user_id == user.id,
            UserModuleMembership.module_id == crm_mod.id
        ).first()

        before_state = {
            "userId": user.id,
            "username": user.username,
            "crmAccess": bool(mem and mem.is_active),
            "crmRole": mem.role.code if (mem and mem.role) else None
        }

        if enabled:
            target_role_code = (initial_role_code or "").strip().upper()
            if not target_role_code:
                if mem and mem.role:
                    target_role_code = mem.role.code
                else:
                    target_role_code = "CRM_SALES_EXECUTIVE"

            RoleAssignmentService.validate_role_assignment(
                actor=actor,
                target_module_code="CRM",
                target_role_code=target_role_code,
                target_user_id=user.id,
                db=self.db
            )

            role = self.db.query(ModuleRole).filter(
                ModuleRole.module_id == crm_mod.id,
                ModuleRole.code == target_role_code,
                ModuleRole.is_active == True
            ).first()
            if not role:
                raise ValidationError(f"Role '{target_role_code}' does not exist or is inactive in CRM.")

            if mem:
                mem.is_active = True
                mem.role_id = role.id
            else:
                mem = UserModuleMembership(
                    user_id=user.id,
                    module_id=crm_mod.id,
                    role_id=role.id,
                    is_active=True
                )
                self.db.add(mem)

            action = "CRM_USER_ACCESS_GRANTED"
        else:
            if mem:
                mem.is_active = False
            action = "CRM_USER_ACCESS_REVOKED"

        self.db.commit()
        if mem:
            self.db.refresh(mem)

        after_state = {
            "userId": user.id,
            "username": user.username,
            "crmAccess": bool(mem and mem.is_active),
            "crmRole": mem.role.code if (mem and mem.role and mem.is_active) else None
        }

        self.audit_service.log(
            action=action,
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=actor.active_role,
            target_info={
                "recordId": user.id,
                "targetUserId": user.id,
                "targetEmployeeId": user.id,
                "targetUsername": user.username,
                "targetEmployeeName": user.name or user.username,
                "crmRole": after_state["crmRole"],
                "details": f"{'Granted' if enabled else 'Revoked'} CRM access for user '{user.username}' with role '{after_state['crmRole']}'."
            },
            before_state=before_state,
            after_state=after_state
        )

        lead_count = self.db.query(func.count(Lead.id)).filter(Lead.assigned_to_user_id == user.id).scalar() or 0

        return {
            "userId": user.id,
            "username": user.username,
            "name": user.name or user.username,
            "email": user.email,
            "status": user.status,
            "crmAccess": after_state["crmAccess"],
            "crmRoleCode": after_state["crmRole"],
            "crmRoleName": mem.role.name if (mem and mem.role and mem.is_active) else None,
            "assignedLeadCount": lead_count
        }

    def set_crm_role(
        self,
        actor: CurrentUser,
        user_id: str,
        role_code: str,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        crm_mod = self._get_crm_module()

        user = self.db.query(User).filter(User.id == user_id, User.is_hard_deleted == False).first()
        if not user:
            raise NotFoundError(f"User with ID '{user_id}' not found.")

        is_global = actor.is_global_admin or "*" in (actor.permissions or []) or any(r in (actor.roles or []) for r in ["IT_ADMIN", "DIRECTOR"])
        if str(actor.id) == str(user.id) and not is_global:
            raise PermissionDeniedError("Users cannot modify or escalate their own roles.")

        clean_role_code = role_code.strip().upper()

        RoleAssignmentService.validate_role_assignment(
            actor=actor,
            target_module_code="CRM",
            target_role_code=clean_role_code,
            target_user_id=user.id,
            db=self.db
        )

        role = self.db.query(ModuleRole).filter(
            ModuleRole.module_id == crm_mod.id,
            ModuleRole.code == clean_role_code,
            ModuleRole.is_active == True
        ).first()
        if not role:
            raise ValidationError(f"Role '{role_code}' does not exist or is inactive in CRM.")

        mem = self.db.query(UserModuleMembership).filter(
            UserModuleMembership.user_id == user.id,
            UserModuleMembership.module_id == crm_mod.id
        ).first()

        if not mem:
            mem = UserModuleMembership(
                user_id=user.id,
                module_id=crm_mod.id,
                role_id=role.id,
                is_active=True
            )
            self.db.add(mem)
        else:
            mem.role_id = role.id
            mem.is_active = True

        self.db.commit()
        self.db.refresh(mem)

        self.audit_service.log(
            action="CRM_USER_ROLE_CHANGED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=actor.active_role,
            target_info={
                "recordId": user.id,
                "targetUserId": user.id,
                "targetEmployeeId": user.id,
                "targetUsername": user.username,
                "targetEmployeeName": user.name or user.username,
                "newCrmRole": role.code,
                "details": f"Changed CRM role of user '{user.username}' to '{role.name}' ({role.code})."
            },
            before_state={"userId": user.id, "crmRole": mem.role.code if mem.role else None},
            after_state={"userId": user.id, "crmRole": role.code}
        )

        lead_count = self.db.query(func.count(Lead.id)).filter(Lead.assigned_to_user_id == user.id).scalar() or 0

        return {
            "userId": user.id,
            "username": user.username,
            "name": user.name or user.username,
            "email": user.email,
            "status": user.status,
            "crmAccess": mem.is_active,
            "crmRoleCode": role.code,
            "crmRoleName": role.name,
            "assignedLeadCount": lead_count
        }

    def get_crm_assignable_roles(self, actor: CurrentUser) -> List[Dict[str, Any]]:
        return RoleAssignmentService.get_assignable_roles_for_module(actor, "CRM", self.db)

    # =========================================================================
    # 2. ACCOUNT MANAGEMENT SERVICES
    # =========================================================================

    def list_accounts(
        self,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        query = self.db.query(Account)
        if search:
            s = f"%{search.strip().lower()}%"
            query = query.filter(
                (func.lower(Account.name).like(s)) |
                (func.lower(Account.site_name).like(s)) |
                (func.lower(Account.account_id).like(s)) |
                (func.lower(Account.industry).like(s)) |
                (func.lower(Account.website).like(s)) |
                (func.lower(Account.phone).like(s)) |
                (func.lower(Account.email).like(s))
            )

        total = query.count()
        accounts = query.order_by(Account.name.asc()).offset(offset).limit(limit).all()

        acc_ids = [a.id for a in accounts]
        contact_counts = dict(
            self.db.query(Contact.account_id, func.count(Contact.id))
            .filter(Contact.account_id.in_(acc_ids), Contact.is_active == True)
            .group_by(Contact.account_id)
            .all()
        )
        lead_counts = dict(
            self.db.query(Lead.account_id, func.count(Lead.id))
            .filter(Lead.account_id.in_(acc_ids))
            .group_by(Lead.account_id)
            .all()
        )
        opp_counts = dict(
            self.db.query(Opportunity.account_id, func.count(Opportunity.id))
            .filter(Opportunity.account_id.in_(acc_ids))
            .group_by(Opportunity.account_id)
            .all()
        )

        formatted = [
            {
                "id": a.id,
                "accountId": a.account_id,
                "name": a.name,
                "siteName": a.site_name,
                "industry": a.industry,
                "website": a.website,
                "phone": a.phone,
                "email": a.email,
                "address": a.address,
                "businessArea": a.business_area,
                "country": a.country,
                "state": a.state,
                "city": a.city,
                "billingAddress": a.billing_address,
                "shippingAddress": a.shipping_address,
                "gstNumber": a.gst_number,
                "panNumber": a.pan_number,
                "parentAccountId": a.parent_account_id,
                "createdById": a.created_by_id,
                "updatedById": a.updated_by_id,
                "isActive": a.is_active,
                "contactCount": contact_counts.get(a.id, 0),
                "leadCount": lead_counts.get(a.id, 0),
                "opportunityCount": opp_counts.get(a.id, 0),
                "createdAt": a.created_at.isoformat() if a.created_at else None,
                "updatedAt": a.updated_at.isoformat() if a.updated_at else None
            }
            for a in accounts
        ]
        return formatted, total

    def get_account(self, account_id: str) -> Dict[str, Any]:
        acc = self.db.query(Account).filter(
            or_(Account.id == account_id, Account.account_id == account_id)
        ).first()
        if not acc:
            raise NotFoundError(f"Account '{account_id}' not found.")

        contacts = self.db.query(Contact).filter(
            Contact.account_id == acc.id,
            Contact.is_active == True
        ).order_by(Contact.name.asc()).all()

        leads = self.db.query(Lead).filter(
            Lead.account_id == acc.id
        ).order_by(Lead.created_at.desc()).all()

        opportunities = self.db.query(Opportunity).filter(
            Opportunity.account_id == acc.id
        ).order_by(Opportunity.created_at.desc()).all()

        contacts_list = [
            {
                "id": c.id,
                "contactId": c.contact_id,
                "name": c.name,
                "email": c.email,
                "mobileNumber": c.mobile_number,
                "designation": c.designation
            }
            for c in contacts
        ]
        leads_list = [
            {
                "id": l.id,
                "leadId": l.lead_id,
                "leadName": l.lead_name or l.lead_id,
                "businessArea": l.business_area,
                "lifecycleStatus": l.lifecycle_status,
                "requestedProductService": l.requested_product_service
            }
            for l in leads
        ]
        opportunities_list = [
            {
                "id": o.id,
                "opportunityId": o.opportunity_id,
                "name": o.name,
                "status": o.status,
                "currency": o.currency,
                "estimatedValue": float(o.estimated_value) if o.estimated_value is not None else None,
                "createdAt": o.created_at.isoformat() if o.created_at else None
            }
            for o in opportunities
        ]

        return {
            "account": {
                "id": acc.id,
                "accountId": acc.account_id,
                "name": acc.name,
                "siteName": acc.site_name,
                "industry": acc.industry,
                "website": acc.website,
                "phone": acc.phone,
                "email": acc.email,
                "address": acc.address,
                "businessArea": acc.business_area,
                "country": acc.country,
                "state": acc.state,
                "city": acc.city,
                "billingAddress": acc.billing_address,
                "shippingAddress": acc.shipping_address,
                "gstNumber": acc.gst_number,
                "panNumber": acc.pan_number,
                "parentAccountId": acc.parent_account_id,
                "parentAccount": {
                    "id": acc.parent_account.id,
                    "accountId": acc.parent_account.account_id,
                    "name": acc.parent_account.name
                } if getattr(acc, "parent_account", None) else None,
                "subAccounts": [
                    {"id": sa.id, "accountId": sa.account_id, "name": sa.name}
                    for sa in getattr(acc, "sub_accounts", [])
                ],
                "createdById": acc.created_by_id,
                "updatedById": acc.updated_by_id,
                "isActive": acc.is_active,
                "contactCount": len(contacts),
                "leadCount": len(leads),
                "opportunityCount": len(opportunities),
                "contacts": contacts_list,
                "leads": leads_list,
                "opportunities": opportunities_list,
                "createdAt": acc.created_at.isoformat() if acc.created_at else None,
                "updatedAt": acc.updated_at.isoformat() if acc.updated_at else None
            },
            "contacts": contacts_list,
            "leads": leads_list,
            "opportunities": opportunities_list
        }

    def search_account_matches(
        self,
        name: Optional[str] = None,
        website: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        exclude_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Sensible, transparent duplicate and similarity matching for Accounts.
        Matches by normalized name, domain/website, email, and phone.
        """
        acc_filters = []
        norm_name = normalize_text(name) if name else ""
        if norm_name and len(norm_name) >= 2:
            acc_filters.append(func.lower(func.trim(Account.name)) == norm_name)
            if len(norm_name) >= 3:
                acc_filters.append(func.lower(Account.name).like(f"%{norm_name}%"))

        clean_web = website.strip().lower() if website else ""
        clean_domain = ""
        if clean_web:
            clean_domain = clean_web.replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0].split(":")[0]
            if clean_domain and len(clean_domain) >= 3:
                acc_filters.append(func.lower(Account.website).like(f"%{clean_domain}%"))

        clean_email = email.strip().lower() if email else ""
        if clean_email:
            acc_filters.append(func.lower(Account.email) == clean_email)
            if "@" in clean_email:
                email_domain = clean_email.split("@")[-1]
                if email_domain not in ("gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com") and len(email_domain) >= 4:
                    acc_filters.append(func.lower(Account.website).like(f"%{email_domain}%"))

        clean_phone = phone.strip() if phone else ""
        phone_digits = "".join(filter(str.isdigit, clean_phone)) if clean_phone else ""
        if len(phone_digits) >= 6:
            acc_filters.append(func.lower(Account.phone).like(f"%{phone_digits[-10:]}%"))

        if not acc_filters:
            return []

        query = self.db.query(Account).filter(
            Account.is_active == True,
            or_(*acc_filters)
        )
        if exclude_id:
            query = query.filter(Account.id != exclude_id, Account.account_id != exclude_id)

        accounts = query.limit(limit).all()
        if not accounts:
            return []

        acc_ids = [a.id for a in accounts]
        contact_counts = dict(
            self.db.query(Contact.account_id, func.count(Contact.id))
            .filter(Contact.account_id.in_(acc_ids), Contact.is_active == True)
            .group_by(Contact.account_id)
            .all()
        )
        lead_counts = dict(
            self.db.query(Lead.account_id, func.count(Lead.id))
            .filter(Lead.account_id.in_(acc_ids))
            .group_by(Lead.account_id)
            .all()
        )
        opp_counts = dict(
            self.db.query(Opportunity.account_id, func.count(Opportunity.id))
            .filter(Opportunity.account_id.in_(acc_ids))
            .group_by(Opportunity.account_id)
            .all()
        )

        results = []
        for a in accounts:
            reasons = []
            a_name_norm = normalize_text(a.name)
            if norm_name and a_name_norm == norm_name:
                reasons.append("Exact company name match")
            elif norm_name and (norm_name in a_name_norm or a_name_norm in norm_name):
                reasons.append("Partial company name match")

            if clean_domain and a.website and clean_domain in a.website.lower():
                reasons.append("Website domain match")
            elif clean_web and a.website and clean_web == a.website.lower():
                reasons.append("Exact website match")

            if clean_email and a.email and clean_email == a.email.lower():
                reasons.append("Exact company email match")

            if phone_digits and a.phone:
                a_phone_digits = "".join(filter(str.isdigit, a.phone))
                if phone_digits[-10:] in a_phone_digits or a_phone_digits[-10:] in phone_digits:
                    reasons.append("Company phone number match")

            results.append({
                "id": a.id,
                "accountId": a.account_id,
                "name": a.name,
                "siteName": a.site_name,
                "industry": a.industry,
                "website": a.website,
                "phone": a.phone,
                "email": a.email,
                "address": a.address,
                "matchReasons": reasons or ["Potential duplicate match"],
                "contactCount": contact_counts.get(a.id, 0),
                "leadCount": lead_counts.get(a.id, 0),
                "opportunityCount": opp_counts.get(a.id, 0)
            })

        results.sort(key=lambda r: (0 if "Exact company name match" in r["matchReasons"] else 1))
        return results

    def create_account(
        self,
        actor: CurrentUser,
        payload: AccountCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        norm_name = normalize_text(payload.name)
        if not norm_name:
            raise ValidationError("Account name cannot be empty.")

        # Duplicate check on normalized name
        existing = self.db.query(Account).filter(
            func.lower(func.trim(Account.name)) == norm_name,
            Account.is_active == True
        ).first()
        if existing and not payload.confirmDuplicate:
            matches = self.search_account_matches(
                name=payload.name,
                website=payload.website,
                email=payload.email,
                phone=payload.phone
            )
            raise ConflictError(
                message=f"An active account with name '{existing.name}' already exists ({existing.account_id}).",
                details={
                    "existingAccountId": existing.id,
                    "existingAccountNumber": existing.account_id,
                    "matches": matches
                }
            )

        account_code = get_next_sequence_id(self.db, "ACCOUNT", "ACC")

        final_address = payload.address.strip() if payload.address else None
        if payload.location and payload.location.strip():
            loc = payload.location.strip()
            if final_address:
                if loc.lower() not in final_address.lower():
                    final_address = f"{final_address}, {loc}"
            else:
                final_address = loc

        parent_acc = None
        if payload.parentAccountId:
            parent_acc = self.db.query(Account).filter(
                or_(Account.id == payload.parentAccountId, Account.account_id == payload.parentAccountId),
                Account.is_active == True
            ).first()
            if not parent_acc:
                raise NotFoundError(f"Parent account '{payload.parentAccountId}' not found.")

        account = Account(
            account_id=account_code,
            name=payload.name.strip(),
            site_name=payload.siteName.strip() if payload.siteName else None,
            industry=payload.industry.strip() if payload.industry else None,
            website=payload.website.strip() if payload.website else None,
            phone=payload.phone.strip() if payload.phone else None,
            email=payload.email.strip().lower() if payload.email else None,
            address=final_address,
            business_area=payload.businessArea,
            country=payload.country.strip() if payload.country else None,
            state=payload.state.strip() if payload.state else None,
            city=payload.city.strip() if payload.city else None,
            billing_address=payload.billingAddress.strip() if payload.billingAddress else None,
            shipping_address=payload.shippingAddress.strip() if payload.shippingAddress else None,
            gst_number=payload.gstNumber.strip() if payload.gstNumber else None,
            pan_number=payload.panNumber.strip() if payload.panNumber else None,
            parent_account_id=parent_acc.id if parent_acc else None,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None,
            is_active=True
        )

        try:
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
        except IntegrityError:
            self.db.rollback()
            collision = self.db.query(Account).filter(func.lower(func.trim(Account.name)) == norm_name).first()
            if collision and not payload.confirmDuplicate:
                raise ConflictError(
                    message=f"An active account with name '{collision.name}' already exists ({collision.account_id}).",
                    details={"existingAccountId": collision.id, "existingAccountNumber": collision.account_id}
                )
            raise ValidationError("Could not save account due to a database integrity constraint.")

        try:
            self.audit_service.log(
                action="CRM_ACCOUNT_CREATED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "recordId": account.id,
                    "accountCode": account.account_id,
                    "accountName": account.name,
                    "details": f"Created CRM Account '{account.name}' ({account.account_id})."
                }
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for account {account.account_id}: {audit_err}")

        return {
            "id": account.id,
            "accountId": account.account_id,
            "name": account.name,
            "siteName": account.site_name,
            "industry": account.industry,
            "website": account.website,
            "phone": account.phone,
            "email": account.email,
            "address": account.address,
            "businessArea": account.business_area,
            "country": account.country,
            "state": account.state,
            "city": account.city,
            "billingAddress": account.billing_address,
            "shippingAddress": account.shipping_address,
            "gstNumber": account.gst_number,
            "panNumber": account.pan_number,
            "parentAccountId": account.parent_account_id,
            "createdById": account.created_by_id,
            "updatedById": account.updated_by_id,
            "isActive": account.is_active,
            "contactCount": 0,
            "leadCount": 0,
            "opportunityCount": 0,
            "createdAt": account.created_at.isoformat() if account.created_at else None,
            "updatedAt": account.updated_at.isoformat() if account.updated_at else None
        }

    def update_account(
        self,
        actor: CurrentUser,
        account_id: str,
        payload: AccountUpdate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        acc = self.db.query(Account).filter(
            or_(Account.id == account_id, Account.account_id == account_id)
        ).first()
        if not acc:
            raise NotFoundError(f"Account '{account_id}' not found.")

        before_state = {
            "name": acc.name,
            "siteName": acc.site_name,
            "industry": acc.industry,
            "website": acc.website,
            "phone": acc.phone,
            "email": acc.email,
            "address": acc.address,
            "isActive": acc.is_active
        }

        if payload.name is not None:
            clean_name = payload.name.strip()
            if not clean_name:
                raise ValidationError("Account name cannot be empty.")
            norm_name = normalize_text(clean_name)
            conflict = self.db.query(Account).filter(
                func.lower(func.trim(Account.name)) == norm_name,
                Account.id != acc.id,
                Account.is_active == True
            ).first()
            if conflict and not payload.confirmDuplicate:
                matches = self.search_account_matches(name=clean_name, exclude_id=acc.id)
                raise ConflictError(
                    message=f"Another active account with name '{conflict.name}' already exists ({conflict.account_id}).",
                    details={"existingAccountId": conflict.id, "existingAccountNumber": conflict.account_id, "matches": matches}
                )
            acc.name = clean_name

        if payload.siteName is not None:
            acc.site_name = payload.siteName.strip() if payload.siteName else None
        if payload.industry is not None:
            acc.industry = payload.industry.strip() if payload.industry else None
        if payload.website is not None:
            acc.website = payload.website.strip() if payload.website else None
        if payload.phone is not None:
            acc.phone = payload.phone.strip() if payload.phone else None
        if payload.email is not None:
            acc.email = payload.email.strip().lower() if payload.email else None
        if payload.businessArea is not None:
            acc.business_area = payload.businessArea
        if payload.country is not None:
            acc.country = payload.country.strip() if payload.country else None
        if payload.state is not None:
            acc.state = payload.state.strip() if payload.state else None
        if payload.city is not None:
            acc.city = payload.city.strip() if payload.city else None
        if payload.billingAddress is not None:
            acc.billing_address = payload.billingAddress.strip() if payload.billingAddress else None
        if payload.shippingAddress is not None:
            acc.shipping_address = payload.shippingAddress.strip() if payload.shippingAddress else None
        if payload.gstNumber is not None:
            acc.gst_number = payload.gstNumber.strip() if payload.gstNumber else None
        if payload.panNumber is not None:
            acc.pan_number = payload.panNumber.strip() if payload.panNumber else None
        if payload.parentAccountId is not None:
            if payload.parentAccountId == "":
                acc.parent_account_id = None
            else:
                if payload.parentAccountId == acc.id or payload.parentAccountId == acc.account_id:
                    raise ValidationError("An account cannot be its own parent.")
                parent_acc = self.db.query(Account).filter(
                    or_(Account.id == payload.parentAccountId, Account.account_id == payload.parentAccountId),
                    Account.is_active == True
                ).first()
                if not parent_acc:
                    raise NotFoundError(f"Parent account '{payload.parentAccountId}' not found.")
                if parent_acc.id == acc.id:
                    raise ValidationError("An account cannot be its own parent.")

                # Circular parent-account check
                curr_ancestor_id = parent_acc.parent_account_id
                visited = {acc.id, parent_acc.id}
                while curr_ancestor_id:
                    if curr_ancestor_id == acc.id:
                        raise ValidationError("Circular parent-account relationship detected.")
                    if curr_ancestor_id in visited:
                        break
                    visited.add(curr_ancestor_id)
                    anc_row = self.db.query(Account.parent_account_id).filter(Account.id == curr_ancestor_id).first()
                    curr_ancestor_id = anc_row[0] if anc_row else None

                acc.parent_account_id = parent_acc.id

        acc.updated_by_id = str(actor.id) if actor.id else None

        if payload.address is not None:
            acc.address = payload.address.strip() if payload.address else None
        if payload.location is not None and payload.location.strip():
            loc = payload.location.strip()
            if acc.address:
                if loc.lower() not in acc.address.lower():
                    acc.address = f"{acc.address}, {loc}"
            else:
                acc.address = loc
        if payload.isActive is not None:
            acc.is_active = payload.isActive

        self.db.commit()
        self.db.refresh(acc)

        after_state = {
            "name": acc.name,
            "siteName": acc.site_name,
            "industry": acc.industry,
            "website": acc.website,
            "phone": acc.phone,
            "email": acc.email,
            "address": acc.address,
            "isActive": acc.is_active
        }

        try:
            self.audit_service.log(
                action="CRM_ACCOUNT_UPDATED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "recordId": acc.id,
                    "accountCode": acc.account_id,
                    "accountName": acc.name,
                    "details": f"Updated CRM Account '{acc.name}' ({acc.account_id})."
                },
                before_state=before_state,
                after_state=after_state
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for account update {acc.account_id}: {audit_err}")

        return self.get_account(acc.id)["account"]

    # =========================================================================
    # 3. CONTACT MANAGEMENT SERVICES
    # =========================================================================

    def list_contacts(
        self,
        search: Optional[str] = None,
        account_id: Optional[str] = None,
        include_unassigned: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        query = self.db.query(Contact).options(joinedload(Contact.account))

        if account_id:
            if include_unassigned:
                query = query.filter(or_(Contact.account_id == account_id, Contact.account_id.is_(None)))
            else:
                query = query.filter(Contact.account_id == account_id)

        if search:
            s = f"%{search.strip().lower()}%"
            query = query.filter(
                (func.lower(Contact.name).like(s)) |
                (func.lower(Contact.contact_id).like(s)) |
                (func.lower(Contact.email).like(s)) |
                (func.lower(Contact.mobile_number).like(s)) |
                (func.lower(Contact.designation).like(s))
            )

        total = query.count()
        contacts = query.order_by(Contact.name.asc()).offset(offset).limit(limit).all()

        con_ids = [c.id for c in contacts]
        opp_counts = dict(
            self.db.query(Opportunity.contact_id, func.count(Opportunity.id))
            .filter(Opportunity.contact_id.in_(con_ids))
            .group_by(Opportunity.contact_id)
            .all()
        )

        formatted = [
            {
                "id": c.id,
                "contactId": c.contact_id,
                "accountId": c.account_id,
                "accountName": c.account.name if c.account else None,
                "name": c.name,
                "firstName": c.first_name,
                "lastName": c.last_name,
                "email": c.email,
                "mobileNumber": c.mobile_number,
                "whatsappNumber": c.whatsapp_number,
                "designation": c.designation,
                "isPrimary": bool(c.is_primary),
                "createdById": c.created_by_id,
                "updatedById": c.updated_by_id,
                "isActive": c.is_active,
                "opportunityCount": opp_counts.get(c.id, 0),
                "createdAt": c.created_at.isoformat() if c.created_at else None,
                "updatedAt": c.updated_at.isoformat() if c.updated_at else None
            }
            for c in contacts
        ]
        return formatted, total

    def get_contact(self, contact_id: str) -> Dict[str, Any]:
        c = self.db.query(Contact).options(joinedload(Contact.account)).filter(
            or_(Contact.id == contact_id, Contact.contact_id == contact_id)
        ).first()
        if not c:
            raise NotFoundError(f"Contact '{contact_id}' not found.")

        leads = self.db.query(Lead).filter(
            Lead.contact_id == c.id
        ).order_by(Lead.created_at.desc()).all()

        opportunities = self.db.query(Opportunity).filter(
            Opportunity.contact_id == c.id
        ).order_by(Opportunity.created_at.desc()).all()

        opportunities_list = [
            {
                "id": o.id,
                "opportunityId": o.opportunity_id,
                "name": o.name,
                "status": o.status,
                "currency": o.currency,
                "estimatedValue": float(o.estimated_value) if o.estimated_value is not None else None,
                "createdAt": o.created_at.isoformat() if o.created_at else None
            }
            for o in opportunities
        ]

        return {
            "id": c.id,
            "contactId": c.contact_id,
            "accountId": c.account_id,
            "accountName": c.account.name if c.account else None,
            "account": {
                "id": c.account.id,
                "accountId": c.account.account_id,
                "name": c.account.name
            } if c.account else None,
            "name": c.name,
            "firstName": c.first_name,
            "lastName": c.last_name,
            "email": c.email,
            "mobileNumber": c.mobile_number,
            "whatsappNumber": c.whatsapp_number,
            "designation": c.designation,
            "isPrimary": bool(c.is_primary),
            "createdById": c.created_by_id,
            "updatedById": c.updated_by_id,
            "isActive": c.is_active,
            "opportunityCount": len(opportunities),
            "opportunities": opportunities_list,
            "createdAt": c.created_at.isoformat() if c.created_at else None,
            "updatedAt": c.updated_at.isoformat() if c.updated_at else None,
            "leads": [
                {
                    "id": l.id,
                    "leadId": l.lead_id,
                    "leadName": l.lead_name or l.lead_id,
                    "businessArea": l.business_area,
                    "lifecycleStatus": l.lifecycle_status,
                    "requestedProductService": l.requested_product_service
                }
                for l in leads
            ]
        }

    def search_contact_matches(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        mobile_number: Optional[str] = None,
        account_id: Optional[str] = None,
        exclude_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Sensible, transparent duplicate and similarity matching for Contacts.
        Matches by normalized email, mobile number, and person name.
        """
        con_filters = []
        clean_email = email.strip().lower() if email else ""
        if clean_email:
            con_filters.append(func.lower(Contact.email) == clean_email)

        clean_phone = mobile_number.strip() if mobile_number else ""
        phone_digits = "".join(filter(str.isdigit, clean_phone)) if clean_phone else ""
        if len(phone_digits) >= 6:
            con_filters.append(func.lower(Contact.mobile_number).like(f"%{phone_digits[-10:]}%"))

        clean_name = name.strip() if name else ""
        if clean_name and len(clean_name) >= 3:
            con_filters.append(func.lower(Contact.name).like(f"%{clean_name.lower()}%"))

        if not con_filters:
            return []

        query = self.db.query(Contact).options(joinedload(Contact.account)).filter(
            Contact.is_active == True,
            or_(*con_filters)
        )
        if exclude_id:
            query = query.filter(Contact.id != exclude_id, Contact.contact_id != exclude_id)
        if account_id:
            query = query.filter(or_(Contact.account_id == account_id, Contact.account_id.is_(None)))

        contacts = query.limit(limit).all()
        if not contacts:
            return []

        results = []
        for c in contacts:
            reasons = []
            if clean_email and c.email and clean_email == c.email.lower():
                reasons.append("Exact email match")
            if phone_digits and c.mobile_number:
                c_digits = "".join(filter(str.isdigit, c.mobile_number))
                if phone_digits[-10:] in c_digits or c_digits[-10:] in phone_digits:
                    reasons.append("Phone number match")
            if clean_name and clean_name.lower() in c.name.lower():
                if clean_name.lower() == c.name.lower():
                    reasons.append("Exact contact name match")
                else:
                    reasons.append("Similar contact name match")

            results.append({
                "id": c.id,
                "contactId": c.contact_id,
                "accountId": c.account_id,
                "accountName": c.account.name if c.account else None,
                "name": c.name,
                "email": c.email,
                "mobileNumber": c.mobile_number,
                "designation": c.designation,
                "matchReasons": reasons or ["Potential duplicate contact"]
            })

        def match_priority(r):
            if "Exact email match" in r["matchReasons"]:
                return 0
            if "Phone number match" in r["matchReasons"]:
                return 1
            if "Exact contact name match" in r["matchReasons"]:
                return 2
            return 3

        results.sort(key=match_priority)
        return results

    def create_contact(
        self,
        actor: CurrentUser,
        payload: ContactCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        clean_name = payload.name.strip()
        if not clean_name:
            raise ValidationError("Contact name cannot be empty.")

        account = None
        if payload.accountId:
            account = self.db.query(Account).filter(
                or_(Account.id == payload.accountId, Account.account_id == payload.accountId),
                Account.is_active == True
            ).first()
            if not account:
                raise NotFoundError(f"Account '{payload.accountId}' does not exist or is inactive.")

        clean_email = payload.email.strip().lower() if payload.email else None
        clean_phone = payload.mobileNumber.strip() if payload.mobileNumber else None

        # Duplicate check on email or phone
        if clean_email and not payload.confirmDuplicate:
            existing_email = self.db.query(Contact).filter(
                func.lower(Contact.email) == clean_email,
                Contact.is_active == True
            ).first()
            if existing_email:
                matches = self.search_contact_matches(email=clean_email, mobile_number=clean_phone, name=clean_name)
                raise ConflictError(
                    message=f"A contact with email '{clean_email}' already exists ({existing_email.contact_id}).",
                    details={
                        "existingContactId": existing_email.id,
                        "existingContactNumber": existing_email.contact_id,
                        "matches": matches
                    }
                )

        if clean_phone and not payload.confirmDuplicate:
            phone_digits = "".join(filter(str.isdigit, clean_phone))
            if phone_digits and len(phone_digits) >= 6:
                existing_contacts = self.db.query(Contact).filter(
                    Contact.mobile_number.isnot(None),
                    Contact.is_active == True
                ).all()
                for ec in existing_contacts:
                    ec_digits = "".join(filter(str.isdigit, ec.mobile_number or ""))
                    if ec_digits and ec_digits[-10:] == phone_digits[-10:]:
                        matches = self.search_contact_matches(email=clean_email, mobile_number=clean_phone, name=clean_name)
                        raise ConflictError(
                            message=f"A contact with mobile number '{clean_phone}' already exists ({ec.contact_id}).",
                            details={
                                "existingContactId": ec.id,
                                "existingContactNumber": ec.contact_id,
                                "matches": matches
                            }
                        )

        clean_first = payload.firstName.strip() if payload.firstName else None
        clean_last = payload.lastName.strip() if payload.lastName else None
        if not clean_first and not clean_last and clean_name:
            parts = clean_name.split(None, 1)
            clean_first = parts[0]
            clean_last = parts[1] if len(parts) > 1 else None

        clean_whatsapp = payload.whatsappNumber.strip() if payload.whatsappNumber else None
        is_primary = bool(payload.isPrimary)

        if is_primary and account:
            self.db.query(Contact).filter(
                Contact.account_id == account.id,
                Contact.is_primary == True
            ).update({"is_primary": False})

        contact_code = get_next_sequence_id(self.db, "CONTACT", "CON")
        contact = Contact(
            contact_id=contact_code,
            account_id=account.id if account else None,
            first_name=clean_first,
            last_name=clean_last,
            name=clean_name,
            email=clean_email,
            mobile_number=clean_phone,
            whatsapp_number=clean_whatsapp,
            designation=payload.designation.strip() if payload.designation else None,
            is_primary=is_primary,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None,
            is_active=True
        )

        try:
            self.db.add(contact)
            self.db.commit()
            self.db.refresh(contact)
        except IntegrityError:
            self.db.rollback()
            raise ValidationError("Could not save contact due to a database constraint.")

        try:
            self.audit_service.log(
                action="CRM_CONTACT_CREATED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "recordId": contact.id,
                    "contactCode": contact.contact_id,
                    "contactName": contact.name,
                    "accountName": account.name if account else None,
                    "details": f"Created CRM Contact '{contact.name}' ({contact.contact_id})."
                }
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for contact {contact.contact_id}: {audit_err}")

        return {
            "id": contact.id,
            "contactId": contact.contact_id,
            "accountId": contact.account_id,
            "accountName": account.name if account else None,
            "name": contact.name,
            "firstName": contact.first_name,
            "lastName": contact.last_name,
            "email": contact.email,
            "mobileNumber": contact.mobile_number,
            "whatsappNumber": contact.whatsapp_number,
            "designation": contact.designation,
            "isPrimary": bool(contact.is_primary),
            "createdById": contact.created_by_id,
            "updatedById": contact.updated_by_id,
            "isActive": contact.is_active,
            "opportunityCount": 0,
            "opportunities": [],
            "createdAt": contact.created_at.isoformat() if contact.created_at else None,
            "updatedAt": contact.updated_at.isoformat() if contact.updated_at else None,
            "leads": []
        }

    def update_contact(
        self,
        actor: CurrentUser,
        contact_id: str,
        payload: ContactUpdate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        c = self.db.query(Contact).options(joinedload(Contact.account)).filter(
            or_(Contact.id == contact_id, Contact.contact_id == contact_id)
        ).first()
        if not c:
            raise NotFoundError(f"Contact '{contact_id}' not found.")

        before_state = {
            "name": c.name,
            "accountId": c.account_id,
            "email": c.email,
            "mobileNumber": c.mobile_number,
            "designation": c.designation,
            "isActive": c.is_active
        }

        if payload.firstName is not None or payload.lastName is not None:
            if payload.firstName is not None:
                c.first_name = payload.firstName.strip() if payload.firstName else None
            if payload.lastName is not None:
                c.last_name = payload.lastName.strip() if payload.lastName else None
            c.name = f"{c.first_name or ''} {c.last_name or ''}".strip()
        elif payload.name is not None:
            clean_name = payload.name.strip()
            if not clean_name:
                raise ValidationError("Contact name cannot be empty.")
            c.name = clean_name
            parts = clean_name.split(None, 1)
            c.first_name = parts[0]
            c.last_name = parts[1] if len(parts) > 1 else None

        if payload.whatsappNumber is not None:
            c.whatsapp_number = payload.whatsappNumber.strip() if payload.whatsappNumber else None

        if payload.isPrimary is not None:
            c.is_primary = bool(payload.isPrimary)
            if c.is_primary and c.account_id:
                self.db.query(Contact).filter(
                    Contact.account_id == c.account_id,
                    Contact.id != c.id,
                    Contact.is_primary == True
                ).update({"is_primary": False})

        c.updated_by_id = str(actor.id) if actor.id else None

        if payload.accountId is not None:
            if payload.accountId == "" or payload.accountId is None:
                c.account_id = None
            else:
                account = self.db.query(Account).filter(
                    or_(Account.id == payload.accountId, Account.account_id == payload.accountId),
                    Account.is_active == True
                ).first()
                if not account:
                    raise NotFoundError(f"Account '{payload.accountId}' does not exist or is inactive.")
                c.account_id = account.id

        if payload.email is not None:
            clean_email = payload.email.strip().lower() if payload.email else None
            if clean_email and not payload.confirmDuplicate:
                existing_email = self.db.query(Contact).filter(
                    func.lower(Contact.email) == clean_email,
                    Contact.id != c.id,
                    Contact.is_active == True
                ).first()
                if existing_email:
                    matches = self.search_contact_matches(email=clean_email, exclude_id=c.id)
                    raise ConflictError(
                        message=f"Another contact with email '{clean_email}' already exists ({existing_email.contact_id}).",
                        details={"existingContactId": existing_email.id, "existingContactNumber": existing_email.contact_id, "matches": matches}
                    )
            c.email = clean_email

        if payload.mobileNumber is not None:
            clean_phone = payload.mobileNumber.strip() if payload.mobileNumber else None
            if clean_phone and not payload.confirmDuplicate:
                phone_digits = "".join(filter(str.isdigit, clean_phone))
                if phone_digits and len(phone_digits) >= 6:
                    existing_contacts = self.db.query(Contact).filter(
                        Contact.mobile_number.isnot(None),
                        Contact.id != c.id,
                        Contact.is_active == True
                    ).all()
                    for ec in existing_contacts:
                        ec_digits = "".join(filter(str.isdigit, ec.mobile_number or ""))
                        if ec_digits and ec_digits[-10:] == phone_digits[-10:]:
                            matches = self.search_contact_matches(mobile_number=clean_phone, exclude_id=c.id)
                            raise ConflictError(
                                message=f"Another contact with mobile number '{clean_phone}' already exists ({ec.contact_id}).",
                                details={"existingContactId": ec.id, "existingContactNumber": ec.contact_id, "matches": matches}
                            )
            c.mobile_number = clean_phone

        if payload.designation is not None:
            c.designation = payload.designation.strip() if payload.designation else None
        if payload.isActive is not None:
            c.is_active = payload.isActive

        self.db.commit()
        self.db.refresh(c)

        after_state = {
            "name": c.name,
            "accountId": c.account_id,
            "email": c.email,
            "mobileNumber": c.mobile_number,
            "designation": c.designation,
            "isActive": c.is_active
        }

        try:
            self.audit_service.log(
                action="CRM_CONTACT_UPDATED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "recordId": c.id,
                    "contactCode": c.contact_id,
                    "contactName": c.name,
                    "details": f"Updated CRM Contact '{c.name}' ({c.contact_id})."
                },
                before_state=before_state,
                after_state=after_state
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for contact update {c.contact_id}: {audit_err}")

        return self.get_contact(c.id)

    # =========================================================================
    # 4. LEAD MANAGEMENT SERVICES
    # =========================================================================

    def _validate_assignee(self, user_id: str) -> User:
        user = self.db.query(User).filter(User.id == user_id, User.is_hard_deleted == False).first()
        if not user or user.status != "active":
            raise ValidationError(f"Target user '{user_id}' does not exist or is not active.")

        crm_mod = self._get_crm_module()
        mem = self.db.query(UserModuleMembership).filter(
            UserModuleMembership.user_id == user.id,
            UserModuleMembership.module_id == crm_mod.id,
            UserModuleMembership.is_active == True
        ).first()

        if not mem or not mem.role or not mem.role.is_active:
            raise ValidationError(f"User '{user.username}' does not have active CRM membership or an assigned CRM role.")

        if not mem.role.code.startswith("CRM_"):
            raise ValidationError(f"User '{user.username}' does not have an eligible CRM role.")

        return user

    def create_lead(
        self,
        actor: CurrentUser,
        payload: LeadCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        is_sqlite = bool(self.db.bind and "sqlite" in str(self.db.bind.url))
        if is_sqlite:
            with _sqlite_write_lock:
                return self._create_lead_impl(actor, payload, request)
        return self._create_lead_impl(actor, payload, request)

    def _create_lead_impl(
        self,
        actor: CurrentUser,
        payload: LeadCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        # 0. Database-backed Idempotency Check (Persistent across backend restarts & multi-worker deployments)
        client_req_id = payload.clientRequestId.strip() if payload.clientRequestId and payload.clientRequestId.strip() else None
        idempotency_rec = None

        if client_req_id and getattr(actor, "id", None):
            user_uuid = str(actor.id)
            # Check existing persistent idempotency record in PostgreSQL
            idempotency_rec = self.db.query(CrmIdempotencyRecord).filter(
                CrmIdempotencyRecord.user_id == user_uuid,
                CrmIdempotencyRecord.client_request_id == client_req_id
            ).first()

            if idempotency_rec:
                if idempotency_rec.status == "COMPLETED" and idempotency_rec.lead_id:
                    existing_lead = self.db.query(Lead).filter(Lead.id == idempotency_rec.lead_id).first()
                    if existing_lead:
                        logger.info(f"Database idempotency hit for user={user_uuid}, clientRequestId={client_req_id}. Returning Lead {existing_lead.lead_id}")
                        return self.get_lead(actor, existing_lead.id)
                elif idempotency_rec.status == "PROCESSING":
                    # Concurrent request already in flight; wait briefly for resolution (up to 3s)
                    for _ in range(15):
                        time.sleep(0.2)
                        self.db.expire(idempotency_rec)
                        refreshed = self.db.query(CrmIdempotencyRecord).filter(
                            CrmIdempotencyRecord.id == idempotency_rec.id
                        ).first()
                        if refreshed and refreshed.status == "COMPLETED" and refreshed.lead_id:
                            existing_lead = self.db.query(Lead).filter(Lead.id == refreshed.lead_id).first()
                            if existing_lead:
                                logger.info(f"Concurrent idempotency resolved for user={user_uuid}, clientRequestId={client_req_id}. Returning Lead {existing_lead.lead_id}")
                                return self.get_lead(actor, existing_lead.id)
            else:
                # Reserve idempotency key in DB to synchronize concurrent workers
                try:
                    idempotency_rec = CrmIdempotencyRecord(
                        user_id=user_uuid,
                        client_request_id=client_req_id,
                        status="PROCESSING"
                    )
                    self.db.add(idempotency_rec)
                    self.db.flush()
                except IntegrityError:
                    self.db.rollback()
                    # Concurrency collision: another thread/worker just inserted this key
                    idempotency_rec = self.db.query(CrmIdempotencyRecord).filter(
                        CrmIdempotencyRecord.user_id == user_uuid,
                        CrmIdempotencyRecord.client_request_id == client_req_id
                    ).first()
                    if idempotency_rec and idempotency_rec.status == "COMPLETED" and idempotency_rec.lead_id:
                        existing_lead = self.db.query(Lead).filter(Lead.id == idempotency_rec.lead_id).first()
                        if existing_lead:
                            return self.get_lead(actor, existing_lead.id)

        # 1. Contact (optional at creation time)
        contact = None
        if payload.contactId:
            contact = self.db.query(Contact).filter(
                or_(Contact.id == payload.contactId, Contact.contact_id == payload.contactId),
                Contact.is_active == True
            ).first()
            if not contact:
                raise NotFoundError(f"Contact '{payload.contactId}' not found or is inactive.")

        # 2. Account (optional at creation time)
        account = None
        if payload.accountId:
            account = self.db.query(Account).filter(
                or_(Account.id == payload.accountId, Account.account_id == payload.accountId),
                Account.is_active == True
            ).first()
            if not account:
                raise NotFoundError(f"Account '{payload.accountId}' not found or is inactive.")

            # Validate Contact-Account relationship if both provided
            if contact and contact.account_id and contact.account_id != account.id:
                raise ValidationError("The selected Contact belongs to a different Account.")
            elif contact and not contact.account_id:
                contact.account_id = account.id
        elif contact and contact.account_id:
            # Auto-populate lead's account from contact's account
            account = self.db.query(Account).filter(
                Account.id == contact.account_id,
                Account.is_active == True
            ).first()

        # 3. Validate Assignee if provided
        assignee = None
        if payload.assignedToUserId:
            assignee = self._validate_assignee(payload.assignedToUserId)

        # 4. Multi-Select Requirement Types (optional during initial creation)
        req_types = payload.requirementTypes if payload.requirementTypes is not None else ([payload.requirementType] if payload.requirementType else [])
        req_types = normalize_and_validate_req_types(req_types)
        primary_req_type = req_types[0] if req_types else None

        clean_req = payload.requestedProductService.strip() if payload.requestedProductService and payload.requestedProductService.strip() else None
        norm_req = normalize_text(clean_req) if clean_req else None
        acc_id = account.id if account else None
        con_id = contact.id if contact else None

        # Lead Title is optional per Section 4
        clean_title = payload.leadName.strip() if payload.leadName and payload.leadName.strip() else None

        lead = None
        for attempt in range(5):
            lead_code = get_next_sequence_id(self.db, "LEAD", "LEAD", commit=False)
            lead = Lead(
                lead_id=lead_code,
                lead_name=clean_title,
                business_area=payload.businessArea or "Biogas",
                requirement_type=primary_req_type,
                requirement_summary=payload.requirementSummary.strip() if payload.requirementSummary else None,
                requested_product_service=clean_req,
                normalized_requirement=norm_req,
                lead_source=payload.leadSource or "Website",
                connected_date=payload.connectedDate,
                account_id=acc_id,
                contact_id=con_id,
                assigned_to_user_id=assignee.id if assignee else None,
                lifecycle_status=payload.lifecycleStatus or "New",
                communication_channel=payload.communicationChannel or "Email",
                remarks=payload.remarks.strip() if payload.remarks else None,
                next_follow_up_date=payload.nextFollowUpDate,
                next_follow_up_action=payload.nextFollowUpAction.strip() if payload.nextFollowUpAction else None,
                website_link=payload.websiteLink.strip() if payload.websiteLink else None,
                location=payload.location.strip() if payload.location else None,
                site_name=payload.siteName.strip() if payload.siteName else None,
                created_by_id=str(actor.id) if actor.id else None,

                # Direct Section 1 Contact Fields
                first_name=payload.firstName.strip() if payload.firstName else None,
                last_name=payload.lastName.strip() if payload.lastName else None,
                job_title=payload.jobTitle.strip() if payload.jobTitle else None,
                business_phone=payload.businessPhone.strip() if payload.businessPhone else None,
                mobile_phone=payload.mobilePhone.strip() if payload.mobilePhone else None,
                contact_email=payload.contactEmail.strip().lower() if payload.contactEmail else None,

                # Direct Section 2 Company Fields
                company_name=payload.companyName.strip() if payload.companyName else None,
                company_email=payload.companyEmail.strip().lower() if payload.companyEmail else None,

                # Section 3 & 4 Fields
                rating=payload.rating,
                client_status=payload.clientStatus or "New",
                description=payload.description.strip() if payload.description else None,
                industry=payload.industry.strip() if payload.industry else None,
                number_of_employees=payload.numberOfEmployees,
                currency=payload.currency or "INR",

                # Section 5 Contact Method
                preferred_contact_method=payload.preferredContactMethod
            )

            # Add normalized requirement type relationship records
            for rt in req_types:
                lead.requirement_types.append(LeadRequirementType(requirement_type=rt))

            # Add structured contact methods
            if payload.contactMethods:
                for method in payload.contactMethods:
                    lead.contact_methods.append(LeadContactMethod(contact_method=method))

            # Add additional contacts if provided
            if payload.additionalContactIds:
                for cid in payload.additionalContactIds:
                    if not cid or (con_id and (cid == con_id or cid == payload.contactId)):
                        continue
                    add_con = self.db.query(Contact).filter(
                        or_(Contact.id == cid, Contact.contact_id == cid),
                        Contact.is_active == True
                    ).first()
                    if not add_con:
                        raise NotFoundError(f"Additional Contact '{cid}' not found or is inactive.")
                    if account and add_con.account_id and add_con.account_id != account.id:
                        raise ValidationError(f"Additional Contact '{add_con.name}' belongs to a different Account.")
                    elif account and not add_con.account_id:
                        add_con.account_id = account.id
                    if add_con not in lead.additional_contacts:
                        lead.additional_contacts.append(add_con)

            try:
                self.db.add(lead)
                self.db.flush()
                break
            except IntegrityError as e:
                self.db.rollback()
                err_str = str(e).lower()
                if "lead_id" in err_str or "leads.lead_id" in err_str:
                    logger.warning(f"Sequence collision on {lead_code}, retrying ({attempt+1}/5)...")
                    continue
                logger.error(f"IntegrityError creating lead: {e}")
                raise ValidationError("Could not save lead due to a database integrity constraint.")
            except OperationalError as e:
                self.db.rollback()
                if "locked" in str(e).lower() and attempt < 4:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                raise
        else:
            raise ValidationError("Could not generate a unique Lead ID after multiple attempts.")

        # Automatic Lead Nurturing Initialization (Mandatory requirement, unified in same transaction)
        lead_ref_code = getattr(lead, "lead_id", "")
        try:
            from app.crm.nurturing_service import LeadNurturingService
            nurturing_svc = LeadNurturingService(self.db, self.audit_service)
            nurturing_svc.initialize_lead_nurturing(
                lead=lead,
                actor_id=str(actor.id) if actor.id else None,
                commit=False
            )

            # Single atomic database commit for Lead, Nurturing, and Idempotency records
            if idempotency_rec:
                idempotency_rec.lead_id = lead.id
                idempotency_rec.status = "COMPLETED"
                idempotency_rec.response_code = 201

            self.db.commit()
            self.db.refresh(lead)
        except Exception as nurture_err:
            try:
                self.db.rollback()
            except Exception:
                pass
            logger.error(f"Failed to auto-initialize nurturing for lead {lead_ref_code}: {nurture_err}")
            raise ValidationError(f"Could not complete atomic lead creation and nurturing setup: {str(nurture_err)}")

        try:
            self.audit_service.log(
                action="CRM_LEAD_CREATED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "recordId": lead.id,
                    "leadNumber": lead.lead_id,
                    "leadName": lead.lead_name or lead.lead_id,
                    "businessArea": lead.business_area,
                    "requirementTypes": req_types,
                    "assignedTo": assignee.username if assignee else None,
                    "details": f"Created Lead '{lead.lead_name or lead.lead_id}' ({lead.lead_id}) for {lead.business_area}."
                }
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for lead {lead.lead_id}: {audit_err}")

        return self.get_lead(actor, lead.id)

    def update_lead(
        self,
        actor: CurrentUser,
        lead_id: str,
        payload: LeadUpdate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        lead = self.db.query(Lead).options(
            joinedload(Lead.requirement_types),
            joinedload(Lead.contact_methods)
        ).filter(
            or_(Lead.id == lead_id, Lead.lead_id == lead_id)
        ).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        before_state = {
            "leadId": lead.lead_id,
            "status": lead.lifecycle_status,
            "assignedTo": lead.assigned_to_user_id
        }

        # Validate Contact if changed
        contact = None
        if "contactId" in payload.model_fields_set:
            if not payload.contactId or not str(payload.contactId).strip():
                lead.contact_id = None
            else:
                contact = self.db.query(Contact).filter(
                    or_(Contact.id == payload.contactId, Contact.contact_id == payload.contactId),
                    Contact.is_active == True
                ).first()
                if not contact:
                    raise NotFoundError(f"Contact '{payload.contactId}' not found or is inactive.")
                lead.contact_id = contact.id
        elif lead.contact_id:
            contact = lead.contact or self.db.query(Contact).filter(Contact.id == lead.contact_id).first()

        # Validate Account if changed
        account = None
        if "accountId" in payload.model_fields_set:
            if not payload.accountId:
                lead.account_id = None
            else:
                account = self.db.query(Account).filter(
                    or_(Account.id == payload.accountId, Account.account_id == payload.accountId),
                    Account.is_active == True
                ).first()
                if not account:
                    raise NotFoundError(f"Account '{payload.accountId}' not found or is inactive.")
                lead.account_id = account.id
        elif lead.account_id:
            account = lead.account or self.db.query(Account).filter(Account.id == lead.account_id).first()

        # Enforce consistency between lead's contact and account if both are present
        if account and contact:
            if contact.account_id and contact.account_id != account.id:
                raise ValidationError("The selected Contact belongs to a different Account.")
            elif not contact.account_id:
                contact.account_id = account.id

        # Validate Assignee if changed
        assignee_changed = False
        if payload.assignedToUserId is not None:
            if payload.assignedToUserId == "":
                if lead.assigned_to_user_id is not None:
                    lead.assigned_to_user_id = None
                    assignee_changed = True
            else:
                new_assignee = self._validate_assignee(payload.assignedToUserId)
                if lead.assigned_to_user_id != new_assignee.id:
                    lead.assigned_to_user_id = new_assignee.id
                    assignee_changed = True

        if payload.requestedProductService is not None:
            clean_req = payload.requestedProductService.strip() if payload.requestedProductService.strip() else None
            norm = normalize_text(clean_req) if clean_req else None
            lead.requested_product_service = clean_req
            lead.normalized_requirement = norm

        status_changed = False
        if payload.lifecycleStatus and payload.lifecycleStatus != lead.lifecycle_status:
            lead.lifecycle_status = payload.lifecycleStatus
            status_changed = True

        # Lead Title can be changed or cleared (Section 4)
        if "leadName" in payload.model_fields_set:
            lead.lead_name = payload.leadName.strip() if payload.leadName and payload.leadName.strip() else None

        if payload.businessArea:
            lead.business_area = payload.businessArea

        # Requirement Types update
        if payload.requirementTypes is not None or payload.requirementType is not None:
            types = payload.requirementTypes if payload.requirementTypes is not None else ([payload.requirementType] if payload.requirementType else [])
            req_types = normalize_and_validate_req_types(types)
            lead.requirement_type = req_types[0] if req_types else None

            # Replace relationship rows
            self.db.query(LeadRequirementType).filter(LeadRequirementType.lead_id == lead.id).delete()
            for rt in req_types:
                self.db.add(LeadRequirementType(lead_id=lead.id, requirement_type=rt))

        # Contact methods update
        if payload.contactMethods is not None:
            self.db.query(LeadContactMethod).filter(LeadContactMethod.lead_id == lead.id).delete()
            for cm in payload.contactMethods:
                self.db.add(LeadContactMethod(lead_id=lead.id, contact_method=cm))

        # Direct Section 1 Contact Fields
        if "firstName" in payload.model_fields_set:
            lead.first_name = payload.firstName.strip() if payload.firstName else None
        if "lastName" in payload.model_fields_set:
            lead.last_name = payload.lastName.strip() if payload.lastName else None
        if "jobTitle" in payload.model_fields_set:
            lead.job_title = payload.jobTitle.strip() if payload.jobTitle else None
        if "businessPhone" in payload.model_fields_set:
            lead.business_phone = payload.businessPhone.strip() if payload.businessPhone else None
        if "mobilePhone" in payload.model_fields_set:
            lead.mobile_phone = payload.mobilePhone.strip() if payload.mobilePhone else None
        if "contactEmail" in payload.model_fields_set:
            lead.contact_email = payload.contactEmail.strip().lower() if payload.contactEmail else None

        # Direct Section 2 Company Fields
        if "companyName" in payload.model_fields_set:
            lead.company_name = payload.companyName.strip() if payload.companyName else None
        if "companyEmail" in payload.model_fields_set:
            lead.company_email = payload.companyEmail.strip().lower() if payload.companyEmail else None

        # Section 3 & 4 Fields
        if "rating" in payload.model_fields_set:
            lead.rating = payload.rating
        if "clientStatus" in payload.model_fields_set:
            lead.client_status = payload.clientStatus or "New"
        if "description" in payload.model_fields_set:
            lead.description = payload.description.strip() if payload.description else None
        if "industry" in payload.model_fields_set:
            lead.industry = payload.industry.strip() if payload.industry else None
        if "numberOfEmployees" in payload.model_fields_set:
            lead.number_of_employees = payload.numberOfEmployees
        if "currency" in payload.model_fields_set:
            lead.currency = payload.currency or "INR"
        if "preferredContactMethod" in payload.model_fields_set:
            lead.preferred_contact_method = payload.preferredContactMethod

        if "connectedDate" in payload.model_fields_set:
            lead.connected_date = payload.connectedDate
            try:
                from app.crm.nurturing_service import LeadNurturingService
                nurturing_svc = LeadNurturingService(self.db, self.audit_service)
                nurturing_svc.recalculate_on_connected_date_change(
                    lead=lead,
                    new_connected_date=payload.connectedDate,
                    actor_id=str(actor.id) if actor.id else None
                )
            except Exception as nurture_calc_err:
                logger.warning(f"Failed to recalculate nurturing schedule: {nurture_calc_err}")

        # Additional Contacts update
        if payload.additionalContactIds is not None:
            new_additional = []
            for cid in payload.additionalContactIds:
                if not cid or cid == lead.contact_id or (contact and (cid == contact.id or cid == contact.contact_id)):
                    continue
                add_con = self.db.query(Contact).filter(
                    or_(Contact.id == cid, Contact.contact_id == cid),
                    Contact.is_active == True
                ).first()
                if not add_con:
                    raise NotFoundError(f"Additional Contact '{cid}' not found or is inactive.")
                if account and add_con.account_id and add_con.account_id != account.id:
                    raise ValidationError(f"Additional Contact '{add_con.name}' belongs to a different Account.")
                elif account and not add_con.account_id:
                    add_con.account_id = account.id
                if add_con not in new_additional:
                    new_additional.append(add_con)
            lead.additional_contacts = new_additional
        elif "accountId" in payload.model_fields_set and lead.additional_contacts:
            for con in lead.additional_contacts:
                if account and con.account_id and con.account_id != account.id:
                    raise ValidationError(f"Associated Additional Contact '{con.name}' belongs to a different Account.")
                elif account and not con.account_id:
                    con.account_id = account.id

        if payload.requirementSummary is not None:
            lead.requirement_summary = payload.requirementSummary.strip() if payload.requirementSummary else None
        if payload.leadSource:
            lead.lead_source = payload.leadSource
        if payload.websiteLink is not None:
            lead.website_link = payload.websiteLink.strip() if payload.websiteLink else None
        if payload.location is not None:
            lead.location = payload.location.strip() if payload.location else None
        if payload.siteName is not None:
            lead.site_name = payload.siteName.strip() if payload.siteName else None
        if payload.communicationChannel is not None:
            lead.communication_channel = payload.communicationChannel.strip() if payload.communicationChannel else None
        if payload.remarks is not None:
            lead.remarks = payload.remarks.strip() if payload.remarks else None
        if payload.nextFollowUpDate is not None:
            lead.next_follow_up_date = payload.nextFollowUpDate
        if payload.nextFollowUpAction is not None:
            lead.next_follow_up_action = payload.nextFollowUpAction.strip() if payload.nextFollowUpAction else None

        lead.updated_by_id = str(actor.id) if actor.id else None

        try:
            self.db.commit()
            self.db.refresh(lead)
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"IntegrityError updating lead: {e}")
            raise ValidationError("Update failed due to a database integrity constraint.")

        if assignee_changed:
            self.audit_service.log(
                action="CRM_LEAD_REASSIGNED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "recordId": lead.id,
                    "leadNumber": lead.lead_id,
                    "newAssigneeId": lead.assigned_to_user_id,
                    "details": f"Reassigned Lead '{lead.lead_id}' to user ID {lead.assigned_to_user_id}."
                },
                before_state=before_state,
                after_state={"assignedTo": lead.assigned_to_user_id}
            )

        if status_changed:
            self.audit_service.log(
                action="CRM_LEAD_STATUS_CHANGED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "recordId": lead.id,
                    "leadNumber": lead.lead_id,
                    "newStatus": lead.lifecycle_status,
                    "details": f"Transitioned Lead '{lead.lead_id}' status to '{lead.lifecycle_status}'."
                },
                before_state=before_state,
                after_state={"status": lead.lifecycle_status}
            )

        return self.get_lead(actor, lead.id)

    def transition_lead_status(
        self,
        actor: CurrentUser,
        lead_id: str,
        new_status: str,
        remarks: Optional[str] = None,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        clean_status = (new_status or "").strip()
        if clean_status not in ALLOWED_LIFECYCLE_STATUSES:
            raise ValidationError(f"Invalid status '{new_status}'. Must be one of: {sorted(ALLOWED_LIFECYCLE_STATUSES)}")

        lead = self.db.query(Lead).filter(
            or_(Lead.id == lead_id, Lead.lead_id == lead_id)
        ).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        before_status = lead.lifecycle_status
        lead.lifecycle_status = clean_status
        if remarks:
            lead.remarks = remarks.strip()
        if clean_status == "Disqualified":
            lead.disqualification_reason = remarks.strip() if remarks else "Disqualified during lead nurturing"
        elif clean_status != "Dormant":
            lead.disqualification_reason = None
        lead.updated_by_id = str(actor.id) if actor.id else None

        # Record Lead Status Change interaction for unified timeline
        try:
            comm_code = get_next_sequence_id(self.db, "COMMUNICATION", "COM", commit=False)
            status_comm = LeadCommunicationHistory(
                communication_id=comm_code,
                lead_id=lead.id,
                communication_date=datetime.now(timezone.utc),
                channel="Other",
                event_type=f"Lead Status: {clean_status}",
                subject=f"Status changed from {before_status} to {clean_status}",
                summary=remarks.strip() if remarks else f"Lead business status transitioned from {before_status} to {clean_status}.",
                outcome=clean_status,
                interaction_source="Lead Status Change",
                created_by_id=str(actor.id) if actor.id else None,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(status_comm)
        except Exception as comm_err:
            logger.warning(f"Could not log status transition interaction: {comm_err}")

        try:
            self.db.commit()
            self.db.refresh(lead)
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"IntegrityError transitioning status: {e}")
            raise ValidationError("Status update failed due to a database constraint.")

        self.audit_service.log(
            action="CRM_LEAD_STATUS_CHANGED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=actor.active_role,
            target_info={
                "recordId": lead.id,
                "leadNumber": lead.lead_id,
                "previousStatus": before_status,
                "newStatus": clean_status,
                "remarks": remarks,
                "details": f"Transitioned Lead '{lead.lead_id}' from '{before_status}' to '{clean_status}'."
            },
            before_state={"status": before_status},
            after_state={"status": clean_status}
        )

        return self.get_lead(actor, lead.id)

    def list_leads(
        self,
        actor: CurrentUser,
        view: str = "open",
        search: Optional[str] = None,
        business_area: Optional[str] = None,
        requirement_type: Optional[str] = None,
        lifecycle_status: Optional[str] = None,
        assigned_to_user_id: Optional[str] = None,
        account_id: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        query = (
            self.db.query(Lead)
            .options(
                joinedload(Lead.account),
                joinedload(Lead.contact).joinedload(Contact.account),
                joinedload(Lead.assigned_to),
                joinedload(Lead.created_by),
                joinedload(Lead.qualified_by),
                joinedload(Lead.opportunity),
                selectinload(Lead.opportunities),
                joinedload(Lead.requirement_types),
                joinedload(Lead.contact_methods)
            )
        )

        # 1. Apply Saved View Filters
        clean_view = (view or "open").strip().lower()

        if clean_view == "open":
            query = query.filter(
                Lead.lifecycle_status.in_(["New", "Contacted", "In Discussion"]),
                Lead.lifecycle_status != "Qualified",
                Lead.qualified_at.is_(None),
                Lead.opportunity_id.is_(None)
            )
        elif clean_view == "all":
            pass
        elif clean_view == "qualified":
            query = query.filter(
                or_(
                    Lead.lifecycle_status == "Qualified",
                    Lead.qualified_at.isnot(None),
                    Lead.opportunity_id.isnot(None)
                )
            )
        elif clean_view in ("unqualified", "dormant"):
            query = query.filter(
                Lead.lifecycle_status.in_(["Dormant", "Disqualified"]),
                Lead.lifecycle_status != "Qualified",
                Lead.qualified_at.is_(None),
                Lead.opportunity_id.is_(None)
            )
        elif clean_view == "my_leads":
            query = query.filter(
                Lead.assigned_to_user_id == str(actor.id),
                Lead.lifecycle_status.in_(["New", "Contacted", "In Discussion"]),
                Lead.lifecycle_status != "Qualified",
                Lead.qualified_at.is_(None),
                Lead.opportunity_id.is_(None)
            )
        elif clean_view == "follow_ups_due":
            due_window = date.today() + timedelta(days=1)
            query = query.filter(
                Lead.lifecycle_status.notin_(["Dormant", "Disqualified", "Qualified"]),
                Lead.qualified_at.is_(None),
                Lead.opportunity_id.is_(None),
                Lead.next_follow_up_date.isnot(None),
                Lead.next_follow_up_date <= due_window
            )

        # 2. Facet Filters
        if business_area and business_area != "ALL":
            clean_ba = business_area.strip()
            if clean_ba.lower() in ("waste water", "wwt", "wastewater", "wastewater treatment (wwt)"):
                query = query.filter(Lead.business_area.in_(["Waste Water", "WWT", "Wastewater", "Wastewater Treatment (WWT)"]))
            else:
                query = query.filter(Lead.business_area == clean_ba)

        if requirement_type and requirement_type != "ALL":
            clean_rt = requirement_type.strip()
            # Match either the normalized table or legacy column
            query = query.filter(
                or_(
                    Lead.requirement_types.any(LeadRequirementType.requirement_type == clean_rt),
                    Lead.requirement_type == clean_rt
                )
            )

        if lifecycle_status and lifecycle_status != "ALL":
            query = query.filter(Lead.lifecycle_status == lifecycle_status.strip())

        if assigned_to_user_id:
            query = query.filter(Lead.assigned_to_user_id == assigned_to_user_id.strip())

        if account_id:
            query = query.filter(Lead.account_id == account_id.strip())

        # 3. Global Search
        if search:
            s = f"%{search.strip().lower()}%"
            query = query.outerjoin(Lead.account).outerjoin(Lead.contact).filter(
                or_(
                    func.lower(Lead.lead_id).like(s),
                    func.lower(Lead.lead_name).like(s),
                    func.lower(Lead.company_name).like(s),
                    func.lower(Lead.first_name).like(s),
                    func.lower(Lead.last_name).like(s),
                    func.lower(Lead.contact_email).like(s),
                    func.lower(Lead.company_email).like(s),
                    func.lower(Lead.requested_product_service).like(s),
                    func.lower(Lead.location).like(s),
                    func.lower(Lead.site_name).like(s),
                    func.lower(Contact.name).like(s),
                    func.lower(Contact.email).like(s),
                    func.lower(Account.name).like(s),
                    Lead.requirement_types.any(func.lower(LeadRequirementType.requirement_type).like(s))
                )
            )

        total_count = query.count()

        # 4. Sorting
        sortable_fields = {
            "created_at": Lead.created_at,
            "lead_id": Lead.lead_id,
            "lead_name": func.coalesce(Lead.lead_name, Lead.lead_id),
            "next_follow_up_date": Lead.next_follow_up_date,
            "last_connected_date": Lead.last_connected_date,
            "lifecycle_status": Lead.lifecycle_status
        }
        col = sortable_fields.get(sort_by.lower(), Lead.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(col.asc())
        else:
            query = query.order_by(col.desc())

        # 5. Pagination
        safe_page = max(1, page)
        safe_page_size = min(max(1, page_size), 100)
        offset = (safe_page - 1) * safe_page_size
        totalPages = max(1, (total_count + safe_page_size - 1) // safe_page_size)

        leads = query.offset(offset).limit(safe_page_size).all()

        return {
            "success": True,
            "count": len(leads),
            "total": total_count,
            "totalCount": total_count,
            "page": safe_page,
            "pageSize": safe_page_size,
            "totalPages": totalPages,
            "leads": [self._format_lead(l) for l in leads]
        }

    def get_lead(self, actor: CurrentUser, lead_id: str) -> Dict[str, Any]:
        clean_id = (lead_id or "").strip()
        lead = (
            self.db.query(Lead)
            .options(
                joinedload(Lead.account),
                joinedload(Lead.contact).joinedload(Contact.account),
                joinedload(Lead.assigned_to),
                joinedload(Lead.created_by),
                joinedload(Lead.qualified_by),
                joinedload(Lead.opportunity).joinedload(Opportunity.account),
                joinedload(Lead.opportunity).joinedload(Opportunity.contact),
                selectinload(Lead.opportunities).joinedload(Opportunity.account),
                selectinload(Lead.opportunities).joinedload(Opportunity.contact),
                joinedload(Lead.requirement_types),
                joinedload(Lead.contact_methods)
            )
            .filter(or_(
                Lead.id == clean_id,
                func.lower(Lead.id) == clean_id.lower(),
                func.lower(Lead.lead_id) == clean_id.lower()
            ))
            .first()
        )
        if not lead:
            raise NotFoundError(f"Lead '{clean_id}' not found.")

        return self._format_lead(lead)

    def _format_lead(self, lead: Lead) -> Dict[str, Any]:
        # Multi-select requirement types
        types = [rt.requirement_type for rt in lead.requirement_types] if lead.requirement_types else []
        if not types and lead.requirement_type:
            types = [lead.requirement_type]

        contact_methods = [cm.contact_method for cm in lead.contact_methods] if getattr(lead, "contact_methods", None) else []

        display_name = lead.lead_name or lead.company_name or f"{lead.first_name or ''} {lead.last_name or ''}".strip() or lead.lead_id or "Untitled Lead"

        account_obj = None
        if lead.account:
            account_obj = {
                "id": lead.account.id,
                "accountId": lead.account.account_id,
                "name": lead.account.name,
                "industry": lead.account.industry,
                "website": lead.account.website,
                "phone": lead.account.phone,
                "email": lead.account.email,
                "address": lead.account.address,
            }

        contact_obj = None
        if lead.contact:
            contact_account_name = None
            if lead.contact.account:
                contact_account_name = lead.contact.account.name
            elif lead.account:
                contact_account_name = lead.account.name

            contact_obj = {
                "id": lead.contact.id,
                "contactId": lead.contact.contact_id,
                "name": lead.contact.name,
                "designation": lead.contact.designation,
                "email": lead.contact.email,
                "mobileNumber": lead.contact.mobile_number,
                "accountId": lead.contact.account_id or (lead.account_id if lead.account else None),
                "accountName": contact_account_name,
            }

        assigned_to_obj = None
        if lead.assigned_to:
            assigned_to_obj = {
                "id": str(lead.assigned_to.id),
                "name": lead.assigned_to.name,
                "username": lead.assigned_to.username,
                "email": lead.assigned_to.email,
            }

        created_by_obj = None
        if lead.created_by:
            created_by_obj = {
                "id": str(lead.created_by.id),
                "name": lead.created_by.name,
                "username": lead.created_by.username,
                "email": lead.created_by.email,
            }

        additional_contacts_list = []
        additional_contact_ids = []
        if lead.additional_contacts:
            for c in lead.additional_contacts:
                additional_contact_ids.append(c.id)
                c_acc_name = None
                if c.account:
                    c_acc_name = c.account.name
                elif lead.account:
                    c_acc_name = lead.account.name
                additional_contacts_list.append({
                    "id": c.id,
                    "contactId": c.contact_id,
                    "name": c.name,
                    "designation": c.designation,
                    "email": c.email,
                    "mobileNumber": c.mobile_number,
                    "accountId": c.account_id or (lead.account_id if lead.account else None),
                    "accountName": c_acc_name,
                })

        # Resolved contact display name & details
        contact_name = lead.contact.name if lead.contact else None
        if not contact_name and (lead.first_name or lead.last_name):
            contact_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip() or None

        # Resolved company display name
        company_name = lead.company_name or (lead.account.name if lead.account else None)

        opp_obj = None
        if getattr(lead, "opportunity", None):
            opp = lead.opportunity
            opp_obj = {
                "id": opp.id,
                "opportunityId": opp.opportunity_id,
                "name": opp.name,
                "status": opp.status,
                "stage": opp.stage,
                "subStatus": opp.sub_status,
                "sub_status": opp.sub_status,
                "currency": opp.currency,
                "estimatedValue": float(opp.estimated_value) if opp.estimated_value is not None else None,
                "description": opp.description,
                "accountId": opp.account_id,
                "accountName": opp.account.name if opp.account else None,
                "contactId": opp.contact_id,
                "contactName": opp.contact.name if opp.contact else None
            }

        opps_list = []
        if getattr(lead, "opportunities", None):
            for opp_item in lead.opportunities:
                opps_list.append({
                    "id": opp_item.id,
                    "opportunityId": opp_item.opportunity_id,
                    "name": opp_item.name,
                    "status": opp_item.status or "Open",
                    "stage": opp_item.stage or "Enquiry",
                    "subStatus": opp_item.sub_status,
                    "sub_status": opp_item.sub_status,
                    "currency": opp_item.currency or "INR",
                    "estimatedValue": float(opp_item.estimated_value) if opp_item.estimated_value is not None else None,
                    "expectedCloseDate": opp_item.expected_close_date.isoformat() if opp_item.expected_close_date else None,
                    "accountId": opp_item.account_id,
                    "accountName": opp_item.account.name if opp_item.account else None,
                    "contactId": opp_item.contact_id,
                    "contactName": opp_item.contact.name if opp_item.contact else None
                })
        elif opp_obj:
            opps_list.append(opp_obj)

        return {
            "id": lead.id,
            "leadId": lead.lead_id,
            "leadName": lead.lead_name,
            "displayName": display_name,
            "businessArea": lead.business_area or "Biogas",
            "requirementType": ", ".join(types) if types else None,
            "requirementTypes": types,
            "requirementSummary": lead.requirement_summary,
            "requestedProductService": lead.requested_product_service,
            "leadSource": lead.lead_source or "Website",
            "lifecycleStatus": lead.lifecycle_status or "New",
            "communicationChannel": lead.communication_channel,
            "remarks": lead.remarks,
            "nextFollowUpDate": _iso_utc(lead.next_follow_up_date),
            "nextFollowUpAction": lead.next_follow_up_action,
            "connectedDate": _iso_utc(lead.connected_date),
            "lastConnectedDate": _iso_utc(lead.last_connected_date),
            "websiteLink": lead.website_link,
            "location": lead.location,
            "siteName": lead.site_name,
            "createdAt": _iso_utc(lead.created_at),
            "updatedAt": _iso_utc(lead.updated_at),

            # Section 1 Direct Contact Fields
            "firstName": lead.first_name,
            "lastName": lead.last_name,
            "jobTitle": lead.job_title,
            "businessPhone": lead.business_phone,
            "mobilePhone": lead.mobile_phone,
            "contactEmail": lead.contact_email,

            # Section 2 Direct Company Fields
            "companyName": company_name,
            "companyEmail": lead.company_email,

            # Section 3 & 4 Fields
            "rating": lead.rating,
            "clientStatus": lead.client_status or "New",
            "description": lead.description,
            "industry": lead.industry,
            "numberOfEmployees": lead.number_of_employees,
            "currency": lead.currency or "INR",

            # Section 5 Contact Methods
            "contactMethods": contact_methods,
            "preferredContactMethod": lead.preferred_contact_method,

            "disqualificationReason": lead.disqualification_reason,
            "convertedAt": _iso_utc(lead.converted_at),
            "convertedById": lead.converted_by_id,
            "convertedByName": lead.converted_by.name if getattr(lead, "converted_by", None) else None,
            "isConverted": bool(lead.converted_at or lead.opportunity_id),

            # Linkages
            "accountId": lead.account_id,
            "accountName": lead.account.name if lead.account else company_name,
            "contactId": lead.contact_id,
            "contactName": contact_name,
            "contactEmailRel": lead.contact.email if lead.contact else lead.contact_email,
            "contactPhoneRel": lead.contact.mobile_number if lead.contact else (lead.mobile_phone or lead.business_phone),
            "additionalContacts": additional_contacts_list,
            "additionalContactIds": additional_contact_ids,
            "assignedToUserId": lead.assigned_to_user_id,
            "assignedToName": lead.assigned_to.name if lead.assigned_to else None,
            "assignedToEmail": lead.assigned_to.email if lead.assigned_to else None,
            "createdById": lead.created_by_id,
            "createdByName": lead.created_by.name if lead.created_by else None,
            "account": account_obj,
            "contact": contact_obj,
            "assignedTo": assigned_to_obj,
            "createdBy": created_by_obj,

            # Qualification details
            "opportunityId": lead.opportunity_id,
            "opportunityName": lead.opportunity.name if getattr(lead, "opportunity", None) else None,
            "opportunity": opp_obj,
            "opportunities": opps_list,
            "isQualified": bool(lead.qualified_at or lead.lifecycle_status == "Qualified"),
            "qualifiedAt": _iso_utc(lead.qualified_at),
            "qualifiedById": lead.qualified_by_id,
            "qualifiedByName": lead.qualified_by.name if getattr(lead, "qualified_by", None) else None,
        }

    def _format_quotation(self, q: OpportunityQuotation) -> Dict[str, Any]:
        return {
            "id": q.id,
            "quotationNumber": q.quotation_number,
            "opportunityId": q.opportunity_id,
            "revisionNumber": q.revision_number,
            "version": q.version,
            "isActive": q.is_active,
            "title": q.title,
            "status": q.status,
            "amount": float(q.amount) if q.amount is not None else 0.0,
            "currency": q.currency or "INR",
            "quotationDate": q.quotation_date.isoformat() if q.quotation_date else None,
            "validUntilDate": q.valid_until_date.isoformat() if q.valid_until_date else None,
            "termsAndConditions": q.terms_and_conditions,
            "notes": q.notes,
            "rejectionReason": q.rejection_reason,
            "fileId": q.file_id,
            "documentName": q.document_name,
            "approvedById": q.approved_by_id,
            "approvedByName": q.approved_by.name if getattr(q, "approved_by", None) else None,
            "approvedAt": q.approved_at.isoformat() if q.approved_at else None,
            "sentMethod": q.sent_method,
            "sentTo": q.sent_to,
            "sentAt": q.sent_at.isoformat() if q.sent_at else None,
            "sentById": q.sent_by_id,
            "sentByName": q.sent_by.name if getattr(q, "sent_by", None) else None,
            "sendingEvidence": q.sending_evidence,
            "createdById": q.created_by_id,
            "createdByName": q.created_by.name if getattr(q, "created_by", None) else None,
            "createdAt": q.created_at.isoformat() if q.created_at else None,
            "updatedAt": q.updated_at.isoformat() if q.updated_at else None,
        }

    def _format_opportunity(self, opp: Opportunity) -> Dict[str, Any]:
        req_list = [r.strip() for r in (opp.requirement_types or "").split(",") if r.strip()]
        milestone_count = len(opp.milestones) if getattr(opp, "milestones", None) else 0
        ce_count = len(opp.consulting_engagements) if getattr(opp, "consulting_engagements", None) else 0
        ss_count = len(opp.sample_submissions) if getattr(opp, "sample_submissions", None) else 0
        pt_count = len(opp.product_transactions) if getattr(opp, "product_transactions", None) else 0
        workstream_count = ce_count + ss_count + pt_count

        # Quotation metrics
        active_quote = None
        quote_count = 0
        if getattr(opp, "quotations", None) is not None:
            quotes = list(opp.quotations)
            quote_count = len(quotes)
            active_quotes = [q for q in quotes if q.is_active]
            if active_quotes:
                active_quote = active_quotes[0]
        else:
            quotes = self.db.query(OpportunityQuotation).filter(OpportunityQuotation.opportunity_id == opp.id).all()
            quote_count = len(quotes)
            active_quotes = [q for q in quotes if q.is_active]
            if active_quotes:
                active_quote = active_quotes[0]

        has_mismatch = False
        active_quote_amount = None
        active_quote_currency = None
        formatted_active_quote = None
        if active_quote:
            formatted_active_quote = self._format_quotation(active_quote)
            active_quote_amount = float(active_quote.amount) if active_quote.amount is not None else 0.0
            active_quote_currency = active_quote.currency
            if opp.estimated_value is not None:
                has_mismatch = bool(round(float(opp.estimated_value), 2) != round(active_quote_amount, 2))

        account_obj = None
        if opp.account:
            account_obj = {
                "id": opp.account.id,
                "accountId": opp.account.account_id,
                "customerId": getattr(opp.account, "customer_id", None),
                "name": opp.account.name,
                "industry": opp.account.industry,
                "website": opp.account.website,
                "phone": opp.account.phone,
                "email": opp.account.email,
                "address": opp.account.address,
                "billingAddress": opp.account.billing_address,
                "shippingAddress": opp.account.shipping_address,
                "siteName": opp.account.site_name,
                "businessArea": opp.account.business_area,
                "gstNumber": getattr(opp.account, "gst_number", None),
                "panNumber": getattr(opp.account, "pan_number", None),
                "city": opp.account.city,
                "state": opp.account.state,
                "country": opp.account.country
            }

        contact_obj = None
        if opp.contact:
            contact_obj = {
                "id": opp.contact.id,
                "contactId": opp.contact.contact_id,
                "name": opp.contact.name,
                "firstName": opp.contact.first_name,
                "lastName": opp.contact.last_name,
                "designation": opp.contact.designation,
                "email": opp.contact.email,
                "mobileNumber": opp.contact.mobile_number,
                "whatsappNumber": opp.contact.whatsapp_number,
                "isPrimary": opp.contact.is_primary,
                "accountId": opp.contact.account_id,
                "accountName": opp.contact.account.name if opp.contact.account else (opp.account.name if opp.account else None)
            }

        orig_lead_obj = None
        if opp.originating_lead:
            orig_lead_obj = {
                "id": opp.originating_lead.id,
                "leadId": opp.originating_lead.lead_id,
                "leadName": opp.originating_lead.lead_name,
                "leadSource": opp.originating_lead.lead_source,
                "lifecycleStatus": opp.originating_lead.lifecycle_status,
                "businessArea": opp.originating_lead.business_area
            }

        return {
            "id": opp.id,
            "opportunityId": opp.opportunity_id,
            "name": opp.name,
            "accountId": opp.account_id,
            "accountName": opp.account.name if opp.account else None,
            "contactId": opp.contact_id,
            "contactName": opp.contact.name if opp.contact else None,
            "account": account_obj,
            "contact": contact_obj,
            "originatingLead": orig_lead_obj,
            "originatingLeadId": opp.originating_lead_id,
            "originatingLeadNumber": opp.originating_lead.lead_id if opp.originating_lead else None,
            "status": opp.status or "Open",
            "stage": opp.stage or "Enquiry",
            "lossReason": opp.loss_reason,
            "wonReason": opp.won_reason,
            "closedById": opp.closed_by_id,
            "closedByName": opp.closed_by.name if getattr(opp, "closed_by", None) else None,
            "reopenedAt": opp.reopened_at.isoformat() if opp.reopened_at else None,
            "reopenedById": opp.reopened_by_id,
            "reopenedByName": opp.reopened_by.name if getattr(opp, "reopened_by", None) else None,
            "subStatus": opp.sub_status,
            "sub_status": opp.sub_status,
            "businessArea": opp.business_area or "Biogas",
            "expectedCloseDate": opp.expected_close_date.isoformat() if opp.expected_close_date else None,
            "actualCloseDate": opp.actual_close_date.isoformat() if opp.actual_close_date else None,
            "currency": opp.currency or "INR",
            "estimatedValue": float(opp.estimated_value) if opp.estimated_value is not None else None,
            "description": opp.description,
            "requirementSummary": opp.requirement_summary,
            "requirementTypes": req_list,
            "assignedToUserId": opp.assigned_to_user_id,
            "assignedToName": opp.assigned_to.name if opp.assigned_to else None,
            "createdById": opp.created_by_id,
            "createdByName": opp.created_by.name if opp.created_by else None,
            "createdAt": opp.created_at.isoformat() if opp.created_at else None,
            "updatedAt": opp.updated_at.isoformat() if opp.updated_at else None,
            "milestoneCount": milestone_count,
            "workstreamCount": workstream_count,
            "quotationCount": quote_count,
            "activeQuotation": formatted_active_quote,
            "hasQuotationMismatch": has_mismatch,
            "activeQuotationAmount": active_quote_amount,
            "activeQuotationCurrency": active_quote_currency,
            "canReopen": bool(opp.status in ("Won", "Lost"))
        }

    def _format_milestone(self, m: Milestone) -> Dict[str, Any]:
        KOLKATA_TZ = zoneinfo.ZoneInfo("Asia/Kolkata")
        today_ist = datetime.now(KOLKATA_TZ).date()
        is_overdue = bool(m.due_date and m.due_date < today_ist and m.status not in ("Completed", "Cancelled"))
        return {
            "id": m.id,
            "milestoneId": m.milestone_id,
            "opportunityId": m.opportunity_id,
            "opportunityName": m.opportunity.name if getattr(m, "opportunity", None) else None,
            "workstreamType": m.workstream_type,
            "workstreamId": m.workstream_id,
            "title": m.title,
            "description": m.description,
            "plannedStartDate": m.planned_start_date.isoformat() if m.planned_start_date else None,
            "dueDate": m.due_date.isoformat() if m.due_date else None,
            "status": m.status or "Pending",
            "completedAt": m.completed_at.isoformat() if m.completed_at else None,
            "completionNotes": m.completion_notes,
            "assignedToUserId": m.assigned_to_user_id,
            "assignedToName": m.assigned_to.name if getattr(m, "assigned_to", None) else None,
            "createdById": m.created_by_id,
            "createdByName": m.created_by.name if getattr(m, "created_by", None) else None,
            "createdAt": m.created_at.isoformat() if m.created_at else None,
            "updatedAt": m.updated_at.isoformat() if m.updated_at else None,
            "isOverdue": is_overdue
        }

    def _format_workstream(self, item_type: str, item: Any) -> Dict[str, Any]:
        if item_type == "consulting":
            return {
                "type": "consulting",
                "id": item.id,
                "recordNumber": item.engagement_id,
                "title": item.title,
                "status": item.status,
                "details": {
                    "agreedFee": float(item.agreed_fee) if item.agreed_fee is not None else 0.0,
                    "billingArrangement": item.billing_arrangement,
                    "durationMonths": item.duration_months,
                    "contractStartDate": item.contract_start_date.isoformat() if item.contract_start_date else None,
                    "contractEndDate": item.contract_end_date.isoformat() if item.contract_end_date else None,
                    "scopeDescription": item.scope_description
                },
                "createdAt": item.created_at.isoformat() if item.created_at else None
            }
        elif item_type == "sample_testing":
            return {
                "type": "sample_testing",
                "id": item.id,
                "recordNumber": item.sample_id,
                "title": item.sample_description,
                "status": item.status,
                "details": {
                    "sampleType": item.sample_type,
                    "receiptDate": item.receipt_date.isoformat() if item.receipt_date else None,
                    "conditionOnReceipt": item.condition_on_receipt,
                    "sampleLevelCharge": float(item.sample_level_charge) if item.sample_level_charge is not None else 0.0,
                    "isUnsuitable": item.is_unsuitable
                },
                "createdAt": item.created_at.isoformat() if item.created_at else None
            }
        elif item_type == "product":
            return {
                "type": "product",
                "id": item.id,
                "recordNumber": item.transaction_id,
                "title": item.product_name,
                "status": item.status,
                "details": {
                    "skuCode": item.sku_code,
                    "transactionType": item.transaction_type,
                    "quantity": float(item.quantity) if item.quantity is not None else 1.0,
                    "unitOfMeasure": item.unit_of_measure,
                    "unitRate": float(item.unit_rate) if item.unit_rate is not None else 0.0,
                    "calculatedAmount": float(item.calculated_amount) if item.calculated_amount is not None else 0.0
                },
                "createdAt": item.created_at.isoformat() if item.created_at else None
            }
        return {}

    def search_qualification_matches(self, actor: CurrentUser, lead_id: str) -> Dict[str, Any]:
        lead = self.db.query(Lead).options(
            joinedload(Lead.account),
            joinedload(Lead.contact),
            joinedload(Lead.contact_methods),
            joinedload(Lead.requirement_types)
        ).filter(
            or_(Lead.id == lead_id, Lead.lead_id == lead_id)
        ).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        matching_accounts = []
        matching_contacts = []

        # 1. Search Accounts
        comp_name = (lead.company_name or "").strip()
        comp_email = (lead.company_email or "").strip().lower()
        comp_web = (lead.website_link or "").strip().lower()
        comp_phone = (lead.business_phone or "").strip()

        acc_filters = []
        if comp_name and len(comp_name) >= 2:
            acc_filters.append(func.lower(Account.name).like(f"%{comp_name.lower()}%"))
        if comp_email:
            acc_filters.append(func.lower(Account.email) == comp_email)
        if comp_web:
            clean_domain = comp_web.replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0]
            if clean_domain and len(clean_domain) >= 3:
                acc_filters.append(func.lower(Account.website).like(f"%{clean_domain}%"))
        if comp_phone:
            clean_digits = "".join(filter(str.isdigit, comp_phone))
            if len(clean_digits) >= 6:
                acc_filters.append(func.lower(Account.phone).like(f"%{clean_digits[-10:]}%"))

        if acc_filters:
            accounts = self.db.query(Account).filter(
                Account.is_active == True,
                or_(*acc_filters)
            ).limit(10).all()

            for a in accounts:
                reasons = []
                if comp_name and a.name.lower() == comp_name.lower():
                    reasons.append("Exact company name match")
                elif comp_name and comp_name.lower() in a.name.lower():
                    reasons.append("Partial company name match")
                if comp_email and a.email and a.email.lower() == comp_email:
                    reasons.append("Exact company email match")
                if comp_web and a.website and comp_web in a.website.lower():
                    reasons.append("Website match")
                if comp_phone and a.phone:
                    clean_digits = "".join(filter(str.isdigit, comp_phone))
                    a_digits = "".join(filter(str.isdigit, a.phone))
                    if clean_digits[-10:] in a_digits or a_digits[-10:] in clean_digits:
                        reasons.append("Company phone number match")

                matching_accounts.append({
                    "id": a.id,
                    "accountId": a.account_id,
                    "name": a.name,
                    "siteName": a.site_name,
                    "industry": a.industry,
                    "website": a.website,
                    "phone": a.phone,
                    "email": a.email,
                    "address": a.address,
                    "matchReasons": reasons
                })

        # 2. Search Contacts
        c_email = (lead.contact_email or (lead.contact.email if lead.contact else "") or "").strip().lower()
        c_phone = (lead.mobile_phone or (lead.contact.mobile_number if lead.contact else "") or "").strip()
        first_name = (lead.first_name or "").strip()
        last_name = (lead.last_name or "").strip()
        full_person_name = f"{first_name} {last_name}".strip()

        con_filters = []
        if c_email:
            con_filters.append(func.lower(Contact.email) == c_email)
        if c_phone:
            phone_digits = "".join(filter(str.isdigit, c_phone))
            if len(phone_digits) >= 6:
                con_filters.append(func.lower(Contact.mobile_number).like(f"%{phone_digits[-10:]}%"))
        if full_person_name and len(full_person_name) >= 3:
            con_filters.append(func.lower(Contact.name).like(f"%{full_person_name.lower()}%"))

        if con_filters:
            contacts = self.db.query(Contact).options(joinedload(Contact.account)).filter(
                Contact.is_active == True,
                or_(*con_filters)
            ).limit(10).all()

            for c in contacts:
                reasons = []
                if c_email and c.email and c.email.lower() == c_email:
                    reasons.append("Exact email match")
                if c_phone and c.mobile_number and "".join(filter(str.isdigit, c_phone)) in "".join(filter(str.isdigit, c.mobile_number)):
                    reasons.append("Phone match")
                if full_person_name and c.name.lower() == full_person_name.lower():
                    reasons.append("Exact name match")

                matching_contacts.append({
                    "id": c.id,
                    "contactId": c.contact_id,
                    "name": c.name,
                    "email": c.email,
                    "mobileNumber": c.mobile_number,
                    "designation": c.designation,
                    "accountId": c.account_id,
                    "accountName": c.account.name if c.account else None,
                    "matchReasons": reasons
                })

        # Suggest default account and contact
        suggested_acc = matching_accounts[0] if matching_accounts else None
        suggested_con = matching_contacts[0] if matching_contacts else None
        suggested_status = "Existing" if (matching_accounts or matching_contacts) else "New"

        return {
            "success": True,
            "leadId": lead.id,
            "matchingAccounts": matching_accounts,
            "matchingContacts": matching_contacts,
            "suggestedAccount": suggested_acc,
            "suggestedContact": suggested_con,
            "suggestedClientStatus": suggested_status
        }

    def _sanitize_user_id(self, user_id: Optional[str]) -> Optional[str]:
        """Validates that user_id is a non-empty string. On PostgreSQL, ensures target user exists to prevent FK violation."""
        if not user_id or not str(user_id).strip():
            return None
        uid = str(user_id).strip()
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            user_row = self.db.query(User.id).filter(User.id == uid).first()
            return uid if user_row else None
        return uid

    def qualify_lead(
        self,
        actor: CurrentUser,
        lead_id: str,
        payload: LeadQualifyRequest,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        # Concurrency Protection: Acquire exclusive row lock strictly on the Lead row
        # using a minimal query with no joins, eliminating any PostgreSQL outer-join locking errors
        lead_id_row = self.db.query(Lead.id).filter(
            or_(Lead.id == lead_id, Lead.lead_id == lead_id)
        ).with_for_update().first()

        if not lead_id_row:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        # Load Lead and required relationships within the same locked transaction
        lead = self.db.query(Lead).options(
            selectinload(Lead.requirement_types),
            selectinload(Lead.contact_methods),
            selectinload(Lead.opportunity),
            selectinload(Lead.account),
            selectinload(Lead.contact)
        ).filter(
            Lead.id == lead_id_row[0]
        ).first()

        # Lifecycle check: Dormant and Disqualified leads cannot be qualified directly
        if lead.lifecycle_status in ("Dormant", "Disqualified"):
            raise ValidationError(
                f"Cannot qualify {lead.lifecycle_status} Lead '{lead.lead_id}'. {lead.lifecycle_status} leads must be reactivated before qualification."
            )

        # Idempotency / Retry-Safety:
        # If the lead is already qualified and linked to an opportunity, return existing linked records safely without creating duplicates
        if (lead.qualified_at or lead.converted_at) and lead.opportunity_id:
            opp = self.db.query(Opportunity).options(
                joinedload(Opportunity.account),
                joinedload(Opportunity.contact)
            ).filter(Opportunity.id == lead.opportunity_id).first()
            if opp:
                return {
                    "success": True,
                    "message": f"Lead '{lead.lead_id}' is already qualified with Opportunity '{opp.opportunity_id}'.",
                    "lead": self._format_lead(lead),
                    "account": {
                        "id": opp.account.id,
                        "accountId": opp.account.account_id,
                        "name": opp.account.name,
                        "siteName": opp.account.site_name,
                        "industry": opp.account.industry,
                        "website": opp.account.website,
                        "phone": opp.account.phone,
                        "email": opp.account.email
                    } if opp.account else {},
                    "contact": {
                        "id": opp.contact.id,
                        "contactId": opp.contact.contact_id,
                        "name": opp.contact.name
                    } if opp.contact else None,
                    "opportunity": self._format_opportunity(opp)
                }

        actor_user_id = self._sanitize_user_id(str(actor.id) if actor and getattr(actor, "id", None) else None)

        try:
            # 1. Resolve Account
            account = None
            if payload.account:
                acc_action = (payload.account.action or "create").strip().lower()
                if acc_action == "reuse":
                    if not payload.account.accountId:
                        raise ValidationError("accountId is required when reusing an existing account.")
                    account = self.db.query(Account).filter(
                        or_(Account.id == payload.account.accountId, Account.account_id == payload.account.accountId),
                        Account.is_active == True
                    ).first()
                    if not account:
                        raise NotFoundError(f"Account '{payload.account.accountId}' does not exist or is inactive.")

                    # Handle siteName: if user explicitly provided a new siteName, apply it; if empty on account, enrich with lead.site_name
                    if payload.account.siteName is not None and payload.account.siteName.strip():
                        account.site_name = payload.account.siteName.strip()
                    elif not account.site_name and lead.site_name:
                        account.site_name = lead.site_name.strip()

                    # Safely enrich existing account fields if empty on account but present in payload/lead
                    if not account.website and (payload.account.website or lead.website_link):
                        account.website = (payload.account.website or lead.website_link).strip()
                    if not account.email and (payload.account.email or lead.company_email):
                        account.email = (payload.account.email or lead.company_email).strip().lower()
                    if not account.phone and (payload.account.phone or lead.business_phone):
                        account.phone = (payload.account.phone or lead.business_phone).strip()
                    if not account.industry and (payload.account.industry or lead.industry):
                        account.industry = (payload.account.industry or lead.industry).strip()
                elif acc_action == "create":
                    acc_name = (payload.account.name or lead.company_name or "").strip()
                    if not acc_name:
                        raise ValidationError("Account name is required when creating a new Account.")

                    # Check whether appropriate Account already exists to avoid duplicate accounts
                    existing_acc = self.db.query(Account).filter(
                        func.lower(Account.name) == acc_name.lower(),
                        Account.is_active == True
                    ).first()

                    if existing_acc:
                        account = existing_acc
                        site_name = (payload.account.siteName or lead.site_name or "").strip()
                        if site_name and not account.site_name:
                            account.site_name = site_name
                        if not account.website and (payload.account.website or lead.website_link):
                            account.website = (payload.account.website or lead.website_link).strip()
                        if not account.email and (payload.account.email or lead.company_email):
                            account.email = (payload.account.email or lead.company_email).strip().lower()
                        if not account.phone and (payload.account.phone or lead.business_phone):
                            account.phone = (payload.account.phone or lead.business_phone).strip()
                        if not account.industry and (payload.account.industry or lead.industry):
                            account.industry = (payload.account.industry or lead.industry).strip()
                        if not account.address and (payload.account.address or lead.location):
                            account.address = (payload.account.address or lead.location).strip()
                    else:
                        account_code = get_next_sequence_id(self.db, "ACCOUNT", "ACC", commit=False)
                        site_name = (payload.account.siteName or lead.site_name or "").strip() or None
                        phone = (payload.account.phone or lead.business_phone or "").strip() or None
                        email = (payload.account.email or lead.company_email or "").strip().lower() or None
                        address = (payload.account.address or lead.location or "").strip() or None
                        acc_biz_area = getattr(payload.account, "businessArea", None) or lead.business_area or "Biogas"

                        account = Account(
                            account_id=account_code,
                            name=acc_name,
                            site_name=site_name,
                            industry=(payload.account.industry or lead.industry or "").strip() or None,
                            website=(payload.account.website or lead.website_link or "").strip() or None,
                            phone=phone,
                            email=email,
                            address=address,
                            business_area=acc_biz_area,
                            created_by_id=actor_user_id,
                            updated_by_id=actor_user_id,
                            is_active=True
                        )
                        self.db.add(account)
                        self.db.flush()
                else:
                    raise ValidationError(f"Invalid account action '{payload.account.action}'. Must be 'reuse' or 'create'.")
            else:
                # Read Lead's existing company/account information
                if lead.account_id:
                    account = self.db.query(Account).filter(Account.id == lead.account_id, Account.is_active == True).first()
                if not account and lead.company_name:
                    acc_name = lead.company_name.strip()
                    existing_acc = self.db.query(Account).filter(func.lower(Account.name) == acc_name.lower(), Account.is_active == True).first()
                    if existing_acc:
                        account = existing_acc
                    else:
                        account_code = get_next_sequence_id(self.db, "ACCOUNT", "ACC", commit=False)
                        account = Account(
                            account_id=account_code,
                            name=acc_name,
                            site_name=lead.site_name,
                            industry=lead.industry,
                            website=lead.website_link,
                            phone=lead.business_phone,
                            email=lead.company_email,
                            address=lead.location,
                            business_area=lead.business_area or "Biogas",
                            created_by_id=actor_user_id,
                            updated_by_id=actor_user_id,
                            is_active=True
                        )
                        self.db.add(account)
                        self.db.flush()

            if not account:
                raise ValidationError("Company / Account information is required to qualify this Lead into an Opportunity.")

            # 2. Resolve Contact (Mandatory designated Primary Contact)
            contact = None
            if payload.contact:
                con_action = (payload.contact.action or "create").strip().lower()
                if con_action == "reuse":
                    if not payload.contact.contactId:
                        raise ValidationError("contactId is required when reusing an existing contact.")
                    contact = self.db.query(Contact).filter(
                        or_(Contact.id == payload.contact.contactId, Contact.contact_id == payload.contact.contactId),
                        Contact.is_active == True
                    ).first()
                    if not contact:
                        raise NotFoundError(f"Contact '{payload.contact.contactId}' does not exist or is inactive.")

                    # Ensure selected contact belongs to the chosen Account or link them if unassigned
                    if contact.account_id and contact.account_id != account.id:
                        raise ValidationError(
                            f"Selected Contact '{contact.name}' belongs to a different Account ({contact.account.name if contact.account else contact.account_id})."
                        )
                    elif not contact.account_id:
                        contact.account_id = account.id
                elif con_action == "create":
                    con_name = (payload.contact.name or "").strip()
                    if not con_name and (lead.first_name or lead.last_name):
                        con_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip()
                    if not con_name:
                        raise ValidationError("Contact name is required when creating a new Contact.")

                    con_email = (payload.contact.email or lead.contact_email or "").strip().lower() or None
                    con_phone = (payload.contact.mobileNumber or lead.mobile_phone or "").strip() or None
                    con_desig = (payload.contact.designation or lead.job_title or "").strip() or None

                    # If an existing contact has this email under a DIFFERENT account, reject with explanation
                    # If under SAME account, reuse existing contact
                    if con_email:
                        existing_con = self.db.query(Contact).filter(
                            func.lower(Contact.email) == con_email,
                            Contact.is_active == True
                        ).first()
                        if existing_con and existing_con.account_id and existing_con.account_id != account.id:
                            raise ValidationError(
                                f"A contact with email '{con_email}' already exists under account '{existing_con.account.name if existing_con.account else existing_con.account_id}'."
                            )
                        elif existing_con and existing_con.account_id == account.id:
                            contact = existing_con

                    if not contact:
                        # Check by name under the same account to avoid duplicate contacts
                        existing_by_name = self.db.query(Contact).filter(
                            func.lower(Contact.name) == con_name.lower(),
                            Contact.account_id == account.id,
                            Contact.is_active == True
                        ).first()
                        if existing_by_name:
                            contact = existing_by_name

                    if not contact:
                        con_first = lead.first_name
                        con_last = lead.last_name
                        if not con_first and not con_last and con_name:
                            parts = con_name.strip().split(maxsplit=1)
                            con_first = parts[0]
                            con_last = parts[1] if len(parts) > 1 else ""

                        contact_code = get_next_sequence_id(self.db, "CONTACT", "CON", commit=False)
                        contact = Contact(
                            contact_id=contact_code,
                            account_id=account.id,
                            first_name=con_first,
                            last_name=con_last,
                            name=con_name,
                            email=con_email,
                            mobile_number=con_phone,
                            whatsapp_number=lead.mobile_phone,
                            designation=con_desig,
                            is_primary=True,
                            created_by_id=actor_user_id,
                            updated_by_id=actor_user_id,
                            is_active=True
                        )
                        self.db.add(contact)
                        self.db.flush()
                else:
                    raise ValidationError(f"Invalid contact action '{payload.contact.action}'. Must be 'reuse' or 'create'.")
            elif lead.contact_id:
                contact = self.db.query(Contact).filter(Contact.id == lead.contact_id).first()
                if contact:
                    if contact.account_id and contact.account_id != account.id:
                        raise ValidationError(
                            f"Lead's existing Contact '{contact.name}' belongs to a different Account ({contact.account.name if contact.account else contact.account_id})."
                        )
                    elif not contact.account_id:
                        contact.account_id = account.id
            else:
                # Read lead contact info
                con_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip()
                if con_name:
                    existing_con = None
                    if lead.contact_email:
                        existing_con = self.db.query(Contact).filter(
                            func.lower(Contact.email) == lead.contact_email.strip().lower(),
                            Contact.account_id == account.id,
                            Contact.is_active == True
                        ).first()
                    if not existing_con:
                        existing_con = self.db.query(Contact).filter(
                            func.lower(Contact.name) == con_name.lower(),
                            Contact.account_id == account.id,
                            Contact.is_active == True
                        ).first()
                    if existing_con:
                        contact = existing_con
                    else:
                        contact_code = get_next_sequence_id(self.db, "CONTACT", "CON", commit=False)
                        contact = Contact(
                            contact_id=contact_code,
                            account_id=account.id,
                            first_name=lead.first_name,
                            last_name=lead.last_name,
                            name=con_name,
                            email=lead.contact_email,
                            mobile_number=lead.mobile_phone,
                            whatsapp_number=lead.mobile_phone,
                            designation=lead.job_title,
                            is_primary=True,
                            created_by_id=actor_user_id,
                            updated_by_id=actor_user_id,
                            is_active=True
                        )
                        self.db.add(contact)
                        self.db.flush()

            # Enforce Primary Contact presence
            if not contact:
                raise ValidationError("A designated Primary Contact is required to qualify a Lead into an Opportunity.")

            # Validate Contact-Account relationship consistency
            if contact.account_id and contact.account_id != account.id:
                raise ValidationError(
                    f"Selected Primary Contact '{contact.name}' belongs to a different Account ({contact.account.name if contact.account else contact.account_id})."
                )

            # 3. Create or Link Opportunity (Prevent duplicate Opportunities)
            existing_opp = None
            if lead.opportunity_id:
                existing_opp = self.db.query(Opportunity).filter(Opportunity.id == lead.opportunity_id).first()
            if not existing_opp:
                existing_opp = self.db.query(Opportunity).filter(Opportunity.originating_lead_id == lead.id).first()

            if existing_opp:
                opportunity = existing_opp
                opportunity.account_id = account.id
                opportunity.contact_id = contact.id
                if payload.opportunityName:
                    opportunity.name = payload.opportunityName.strip()
                if payload.opportunityDescription:
                    opportunity.description = payload.opportunityDescription.strip()
                if payload.estimatedValue is not None:
                    opportunity.estimated_value = payload.estimatedValue
            else:
                opp_code = get_next_sequence_id(self.db, "OPPORTUNITY", "OPP", commit=False)
                opp_name = (payload.opportunityName or lead.lead_name or f"Opportunity - {account.name}").strip()
                req_types_str = ", ".join([rt.requirement_type for rt in lead.requirement_types]) if lead.requirement_types else "Consulting"
                assigned_user_id = self._sanitize_user_id(payload.assignedToUserId or lead.assigned_to_user_id)

                opportunity = Opportunity(
                    opportunity_id=opp_code,
                    name=opp_name,
                    account_id=account.id,
                    contact_id=contact.id,  # Mandatory Primary Contact
                    originating_lead_id=lead.id,
                    status="Open",
                    stage="Enquiry",
                    business_area=lead.business_area or "Biogas",
                    currency=lead.currency or "INR",
                    estimated_value=payload.estimatedValue,
                    description=payload.opportunityDescription or lead.description,
                    requirement_summary=lead.requirement_summary,
                    requirement_types=req_types_str,
                    assigned_to_user_id=assigned_user_id,
                    created_by_id=actor_user_id,
                    updated_by_id=actor_user_id
                )
                self.db.add(opportunity)
                self.db.flush()
                record_opportunity_stage_transition(
                    db=self.db,
                    opp=opportunity,
                    new_stage="Enquiry",
                    triggering_event="LEAD_QUALIFIED",
                    actor=actor,
                    remarks=f"Qualified from Lead {lead.lead_id}",
                    commit=False
                )

            self.db.flush()

            # 4. Update Lead Lifecycle and Qualification Metadata
            before_state = {
                "leadId": lead.lead_id,
                "status": lead.lifecycle_status,
                "accountId": lead.account_id,
                "contactId": lead.contact_id
            }

            now_utc = datetime.now(timezone.utc)
            lead.account_id = account.id
            lead.contact_id = contact.id
            lead.opportunity_id = opportunity.id
            lead.lifecycle_status = "Qualified"
            lead.qualified_at = now_utc
            lead.qualified_by_id = actor_user_id
            lead.converted_at = now_utc
            lead.converted_by_id = actor_user_id
            lead.updated_by_id = actor_user_id

            # Optional client relationship update
            if payload.clientStatus and payload.clientStatus in ("New", "Existing"):
                lead.client_status = payload.clientStatus

            self.db.commit()

        except ValidationError as ve:
            self.db.rollback()
            self.db.expire_all()
            recheck_lead = self.db.query(Lead).filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id)).first()
            if recheck_lead and recheck_lead.opportunity_id:
                opp = self.db.query(Opportunity).options(
                    joinedload(Opportunity.account),
                    joinedload(Opportunity.contact)
                ).filter(Opportunity.id == recheck_lead.opportunity_id).first()
                if opp:
                    return {
                        "success": True,
                        "message": f"Lead '{recheck_lead.lead_id}' is already qualified with Opportunity '{opp.opportunity_id}'.",
                        "lead": self._format_lead(recheck_lead),
                        "account": {
                            "id": opp.account.id,
                            "accountId": opp.account.account_id,
                            "name": opp.account.name,
                            "siteName": opp.account.site_name,
                            "industry": opp.account.industry,
                            "website": opp.account.website,
                            "phone": opp.account.phone,
                            "email": opp.account.email
                        } if opp.account else {},
                        "contact": {
                            "id": opp.contact.id,
                            "contactId": opp.contact.contact_id,
                            "name": opp.contact.name
                        } if opp.contact else None,
                        "opportunity": self._format_opportunity(opp)
                    }
            raise ve
        except NotFoundError:
            self.db.rollback()
            raise
        except (IntegrityError, OperationalError) as e:
            self.db.rollback()
            self.db.expire_all()

            orig = getattr(e, "orig", None)
            pgcode = getattr(orig, "pgcode", None)
            diag = getattr(orig, "diag", None)
            constraint_name = getattr(diag, "constraint_name", None) if diag else None
            table_name = getattr(diag, "table_name", None) if diag else None
            column_name = getattr(diag, "column_name", None) if diag else None
            detail = getattr(diag, "message_detail", None) if diag else str(e)

            logger.error(
                f"[CRM QUALIFY INTEGRITY ERROR] Lead: {lead_id}, Actor: {actor.id if actor else None}, "
                f"SQLSTATE: {pgcode}, Constraint: {constraint_name}, Table: {table_name}, Column: {column_name}, "
                f"Detail: {detail}", exc_info=True
            )

            for attempt in range(15):
                time.sleep(0.08)
                self.db.expire_all()
                recheck_lead = self.db.query(Lead).filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id)).first()
                if recheck_lead and (recheck_lead.opportunity_id or recheck_lead.qualified_at or recheck_lead.converted_at):
                    opp = self.db.query(Opportunity).options(
                        joinedload(Opportunity.account),
                        joinedload(Opportunity.contact)
                    ).filter(Opportunity.id == recheck_lead.opportunity_id).first()
                    if opp:
                        return {
                            "success": True,
                            "message": f"Lead '{recheck_lead.lead_id}' is already qualified with Opportunity '{opp.opportunity_id}'.",
                            "lead": self._format_lead(recheck_lead),
                            "account": {
                                "id": opp.account.id,
                                "accountId": opp.account.account_id,
                                "name": opp.account.name,
                                "siteName": opp.account.site_name,
                                "industry": opp.account.industry,
                                "website": opp.account.website,
                                "phone": opp.account.phone,
                                "email": opp.account.email
                            } if opp.account else {},
                            "contact": {
                                "id": opp.contact.id,
                                "contactId": opp.contact.contact_id,
                                "name": opp.contact.name
                            } if opp.contact else None,
                            "opportunity": self._format_opportunity(opp)
                        }

            err_msg = f"Lead qualification failed due to a database integrity constraint ({constraint_name or 'constraint violation'})."
            if detail and "already exists" in detail.lower():
                err_msg = f"A record with this information already exists: {detail}"
            raise ValidationError(err_msg)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error during lead qualification: {e}")
            raise

        self.db.refresh(lead)
        self.db.refresh(opportunity)
        self.db.refresh(account)
        if contact:
            self.db.refresh(contact)

        # Audit logs (protected with try/except)
        try:
            self.audit_service.log(
                action="CRM_LEAD_QUALIFIED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=getattr(actor, "name", None) or getattr(actor, "username", "Unknown"),
                role_used=getattr(actor, "active_role", None),
                target_info={
                    "recordId": lead.id,
                    "leadNumber": lead.lead_id,
                    "accountId": account.id,
                    "accountCode": account.account_id,
                    "accountName": account.name,
                    "contactId": contact.id if contact else None,
                    "contactName": contact.name if contact else None,
                    "opportunityId": opportunity.id,
                    "opportunityNumber": opportunity.opportunity_id,
                    "opportunityName": opportunity.name,
                    "details": f"Qualified Lead '{lead.lead_id}' into Opportunity '{opportunity.opportunity_id}' with Account '{account.name}'."
                },
                before_state=before_state,
                after_state={
                    "status": "Qualified",
                    "accountId": account.id,
                    "contactId": contact.id if contact else None,
                    "opportunityId": opportunity.id
                }
            )
        except Exception as e:
            logger.warning(f"Failed to record audit log for lead qualification: {e}")

        return {
            "success": True,
            "message": f"Lead '{lead.lead_id}' successfully qualified into Opportunity '{opportunity.opportunity_id}'.",
            "lead": self._format_lead(lead),
            "account": {
                "id": account.id,
                "accountId": account.account_id,
                "name": account.name,
                "siteName": account.site_name,
                "industry": account.industry,
                "website": account.website,
                "phone": account.phone,
                "email": account.email
            },
            "contact": {
                "id": contact.id,
                "contactId": contact.contact_id,
                "name": contact.name,
                "email": contact.email,
                "mobileNumber": contact.mobile_number,
                "designation": contact.designation
            } if contact else None,
            "opportunity": self._format_opportunity(opportunity)
        }

    def unqualify_lead(
        self,
        actor: CurrentUser,
        lead_id: str,
        reason: str,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        lead = self.db.query(Lead).filter(
            or_(Lead.id == lead_id, Lead.lead_id == lead_id)
        ).with_for_update().first()

        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        clean_reason = (reason or "").strip()
        if not clean_reason:
            raise ValidationError("A disqualification reason is mandatory to unqualify a lead.")

        if lead.opportunity_id or lead.qualified_at or lead.converted_at:
            raise ValidationError(
                f"Lead '{lead.lead_id}' has already been qualified/converted to an Opportunity and cannot be unqualified."
            )

        if lead.lifecycle_status in ("Dormant", "Disqualified") and lead.disqualification_reason:
            raise ValidationError(
                f"Lead '{lead.lead_id}' is already unqualified / dormant."
            )

        lead.disqualification_reason = clean_reason
        lead.lifecycle_status = "Dormant"
        lead.updated_by_id = str(actor.id) if actor.id else None

        comm_code = get_next_sequence_id(self.db, "COMMUNICATION", "COM", commit=False)
        comm = LeadCommunicationHistory(
            communication_id=comm_code,
            lead_id=lead.id,
            communication_date=datetime.now(timezone.utc),
            channel="System Event",
            event_type="Status Change",
            interaction_source="Lead Status Change",
            subject="Lead Unqualified",
            summary=f"Lead marked as unqualified. Reason: {clean_reason}",
            created_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(comm)

        if hasattr(lead, 'nurturing_process') and lead.nurturing_process:
            if lead.nurturing_process.nurturing_status == "Active":
                lead.nurturing_process.nurturing_status = "Cancelled"
                lead.nurturing_process.stopped_at = datetime.now(timezone.utc)
                lead.nurturing_process.stop_reason = f"Lead unqualified: {clean_reason}"

        self.db.commit()
        self.db.refresh(lead)

        try:
            self.audit_service.log(
                action="CRM_LEAD_DISQUALIFIED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "recordId": lead.id,
                    "leadCode": lead.lead_id,
                    "reason": clean_reason,
                    "details": f"Unqualified lead {lead.lead_id}. Reason: {clean_reason}"
                }
            )
        except Exception as e:
            logger.warning(f"Audit log failed for lead unqualification {lead.lead_id}: {e}")

        return {
            "success": True,
            "message": f"Lead '{lead.lead_id}' has been unqualified successfully.",
            "lead": self._format_lead(lead)
        }

    def list_opportunities(
        self,
        actor: CurrentUser,
        search: Optional[str] = None,
        account_id: Optional[str] = None,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        business_area: Optional[str] = None,
        assigned_to_user_id: Optional[str] = None,
        view: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        base_query = self.db.query(Opportunity)
        if view:
            v = view.strip().lower()
            if v == "open":
                base_query = base_query.filter(Opportunity.status == "Open")
            elif v == "won":
                base_query = base_query.filter(Opportunity.status == "Won")
            elif v == "lost":
                base_query = base_query.filter(Opportunity.status == "Lost")
            elif v == "my":
                base_query = base_query.filter(Opportunity.assigned_to_user_id == str(actor.id))

        if status and status.strip().upper() != "ALL":
            raw_s = status.strip()
            if raw_s in ("Open Pipeline", "open_pipeline", "Open", "OPEN"):
                base_query = base_query.filter(Opportunity.status == "Open")
            elif raw_s in ("Closed Won", "closed_won", "Won", "WON"):
                base_query = base_query.filter(Opportunity.status == "Won")
            elif raw_s in ("Closed Lost", "closed_lost", "Lost", "LOST"):
                base_query = base_query.filter(Opportunity.status == "Lost")
            else:
                base_query = base_query.filter(Opportunity.status == raw_s)

        if stage and stage.strip().upper() != "ALL":
            raw_stg = stage.strip()
            base_query = base_query.filter(Opportunity.stage == raw_stg)

        if business_area and business_area.strip().upper() != "ALL":
            clean_ba = business_area.strip()
            if clean_ba.lower() in ("waste water", "wwt", "wastewater", "wastewater treatment (wwt)"):
                base_query = base_query.filter(Opportunity.business_area.in_(["Waste Water", "WWT", "Wastewater", "Wastewater Treatment (WWT)"]))
            else:
                base_query = base_query.filter(Opportunity.business_area == clean_ba)
        if assigned_to_user_id and assigned_to_user_id.strip().upper() != "ALL":
            base_query = base_query.filter(Opportunity.assigned_to_user_id == assigned_to_user_id.strip())
        if account_id and account_id.strip().upper() != "ALL":
            base_query = base_query.filter(Opportunity.account_id == account_id.strip())
        if search:
            s = f"%{search.strip().lower()}%"
            base_query = base_query.outerjoin(Opportunity.account).filter(
                or_(
                    func.lower(Opportunity.name).like(s),
                    func.lower(Opportunity.opportunity_id).like(s),
                    func.lower(Account.name).like(s)
                )
            )

        total_count = base_query.count()
        opps = (
            base_query
            .options(
                joinedload(Opportunity.account),
                joinedload(Opportunity.contact),
                joinedload(Opportunity.originating_lead),
                joinedload(Opportunity.assigned_to),
                joinedload(Opportunity.created_by),
                selectinload(Opportunity.milestones),
                selectinload(Opportunity.consulting_engagements),
                selectinload(Opportunity.sample_submissions),
                selectinload(Opportunity.product_transactions),
                selectinload(Opportunity.quotations)
            )
            .order_by(Opportunity.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [self._format_opportunity(o) for o in opps], total_count

    def get_opportunity(self, opp_id: str) -> Dict[str, Any]:
        opp = self.db.query(Opportunity).options(
            joinedload(Opportunity.account),
            joinedload(Opportunity.contact),
            joinedload(Opportunity.originating_lead),
            joinedload(Opportunity.assigned_to),
            joinedload(Opportunity.created_by),
            joinedload(Opportunity.milestones),
            joinedload(Opportunity.consulting_engagements),
            joinedload(Opportunity.sample_submissions),
            joinedload(Opportunity.product_transactions),
            selectinload(Opportunity.quotations)
        ).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")
        return self._format_opportunity(opp)

    def create_opportunity(
        self,
        actor: CurrentUser,
        payload: OpportunityCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        account = None
        if payload.accountId and str(payload.accountId).strip():
            account = self.db.query(Account).filter(
                or_(Account.id == payload.accountId.strip(), Account.account_id == payload.accountId.strip()),
                Account.is_active == True
            ).first()
            if not account:
                raise NotFoundError(f"Account '{payload.accountId}' not found.")

        contact = None
        if payload.contactId and str(payload.contactId).strip():
            contact = self.db.query(Contact).filter(
                or_(Contact.id == payload.contactId.strip(), Contact.contact_id == payload.contactId.strip()),
                Contact.is_active == True
            ).first()
            if not contact:
                raise NotFoundError(f"Contact '{payload.contactId}' not found.")
            if account and contact.account_id and contact.account_id != account.id:
                raise ValidationError("Selected Contact belongs to a different Account.")

        if not account and not contact:
            raise ValidationError("At least one primary relationship (Primary Account or Primary Contact) is required.")

        lead = None
        if payload.originatingLeadId:
            lead = self.db.query(Lead).filter(
                or_(Lead.id == payload.originatingLeadId, Lead.lead_id == payload.originatingLeadId)
            ).first()
            if not lead:
                raise NotFoundError(f"Lead '{payload.originatingLeadId}' not found.")

        if payload.estimatedValue is not None and payload.estimatedValue < 0:
            raise ValidationError("Estimated value cannot be negative.")

        raw_stage = (payload.stage or "Enquiry").strip()
        if raw_stage not in OPPORTUNITY_STAGES:
            raise ValidationError(f"Invalid stage '{raw_stage}'. Permitted stages are: {', '.join(OPPORTUNITY_STAGES)}")

        raw_status = (payload.status or "Open").strip()
        if raw_status not in ("Open", "Won", "Lost"):
            raise ValidationError(f"Invalid status '{raw_status}'. Permitted statuses are Open, Won, Lost.")

        if raw_status == "Lost" and not (payload.lossReason and str(payload.lossReason).strip()):
            raise ValidationError("Loss reason is mandatory when marking an opportunity as Lost.")
        if raw_status == "Won" and not (getattr(payload, "wonReason", None) and str(payload.wonReason).strip()):
            raise ValidationError("Won reason is mandatory when marking an opportunity as Won.")

        opp_code = get_next_sequence_id(self.db, "OPPORTUNITY", "OPP")
        req_types_str = ", ".join(payload.requirementTypes) if payload.requirementTypes else None
        sub_status_val = (payload.subStatus or payload.sub_status or "").strip() or None

        opp = Opportunity(
            opportunity_id=opp_code,
            name=payload.name.strip(),
            account_id=account.id if account else None,
            contact_id=contact.id if contact else None,
            originating_lead_id=lead.id if lead else None,
            status=raw_status,
            stage=raw_stage,
            loss_reason=payload.lossReason.strip() if (raw_status == "Lost" and payload.lossReason) else None,
            sub_status=sub_status_val,
            currency=payload.currency or "INR",
            estimated_value=payload.estimatedValue,
            description=payload.description,
            requirement_summary=payload.requirementSummary,
            requirement_types=req_types_str,
            assigned_to_user_id=payload.assignedToUserId,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(opp)
        self.db.flush()
        record_opportunity_stage_transition(
            db=self.db,
            opp=opp,
            new_stage=raw_stage,
            triggering_event="OPPORTUNITY_CREATED",
            actor=actor,
            remarks="Opportunity created",
            commit=False
        )
        self.db.commit()
        self.db.refresh(opp)

        self.audit_service.log(
            action="CRM_OPPORTUNITY_CREATED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=actor.active_role,
            target_info={
                "recordId": opp.id,
                "opportunityNumber": opp.opportunity_id,
                "name": opp.name,
                "originatingLeadId": opp.originating_lead_id,
                "accountId": opp.account_id,
                "contactId": opp.contact_id,
                "stage": opp.stage,
                "status": opp.status
            },
            after_state={"opportunityId": opp.opportunity_id, "name": opp.name, "stage": opp.stage, "status": opp.status}
        )

        return self.get_opportunity(opp.id)

    def create_lead_opportunity(
        self,
        actor: CurrentUser,
        lead_id: str,
        payload: OpportunityCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        lead = self.db.query(Lead).options(
            joinedload(Lead.account),
            joinedload(Lead.contact)
        ).filter(
            or_(Lead.id == lead_id, Lead.lead_id == lead_id)
        ).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        if lead.lifecycle_status in ("Dormant", "Disqualified"):
            raise ValidationError(f"Cannot create opportunity for Dormant Lead '{lead.lead_id}'. Please reactivate first.")

        account_id = payload.accountId or lead.account_id
        if not account_id:
            account_name = lead.company_name or lead.lead_name or f"Account for {lead.lead_id}"
            acc = self.db.query(Account).filter(func.lower(Account.name) == account_name.lower().strip()).first()
            if not acc:
                acc_code = get_next_sequence_id(self.db, "ACCOUNT", "ACC")
                acc = Account(
                    account_id=acc_code,
                    name=account_name.strip(),
                    site_name=lead.site_name,
                    email=lead.company_email,
                    phone=lead.business_phone,
                    address=lead.location,
                    is_active=True
                )
                self.db.add(acc)
                self.db.flush()
            account_id = acc.id
            lead.account_id = acc.id

        if not payload.contactId and not lead.contact_id:
            contact_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip() or (lead.contact.name if lead.contact else None)
            if contact_name or lead.contact_email or lead.mobile_phone:
                c_name = contact_name or f"Contact for {lead.lead_id}"
                con_code = get_next_sequence_id(self.db, "CONTACT", "CON")
                con = Contact(
                    contact_id=con_code,
                    account_id=account_id,
                    name=c_name,
                    email=lead.contact_email,
                    mobile_number=lead.mobile_phone,
                    designation=lead.job_title,
                    is_active=True
                )
                self.db.add(con)
                self.db.flush()
                lead.contact_id = con.id

        payload.accountId = account_id
        if not payload.contactId and lead.contact_id:
            payload.contactId = lead.contact_id
        payload.originatingLeadId = lead.id

        return self.create_opportunity(actor, payload, request)

    def get_pipeline_summary(self, actor: CurrentUser) -> Dict[str, Any]:
        stages = OPPORTUNITY_STAGES
        stage_metrics = []
        for stg in stages:
            row = self.db.query(
                func.count(Opportunity.id),
                func.coalesce(func.sum(Opportunity.estimated_value), 0.0)
            ).filter(
                Opportunity.stage == stg,
                Opportunity.status == "Open"
            ).first()
            cnt = row[0] or 0
            val = float(row[1] or 0.0)
            stage_metrics.append({"stage": stg, "count": cnt, "totalValue": val})

        open_val_row = self.db.query(
            func.coalesce(func.sum(Opportunity.estimated_value), 0.0)
        ).filter(
            Opportunity.status == "Open"
        ).first()
        total_open_value = float(open_val_row[0] or 0.0)

        # Currency-grouped values
        open_currencies = self.db.query(
            Opportunity.currency,
            func.coalesce(func.sum(Opportunity.estimated_value), 0.0)
        ).filter(
            Opportunity.status == "Open"
        ).group_by(Opportunity.currency).all()
        open_by_currency = {c or "INR": float(v or 0.0) for c, v in open_currencies}

        won_currencies = self.db.query(
            Opportunity.currency,
            func.coalesce(func.sum(Opportunity.estimated_value), 0.0)
        ).filter(
            Opportunity.status == "Won"
        ).group_by(Opportunity.currency).all()
        won_by_currency = {c or "INR": float(v or 0.0) for c, v in won_currencies}

        lost_currencies = self.db.query(
            Opportunity.currency,
            func.coalesce(func.sum(Opportunity.estimated_value), 0.0)
        ).filter(
            Opportunity.status == "Lost"
        ).group_by(Opportunity.currency).all()
        lost_by_currency = {c or "INR": float(v or 0.0) for c, v in lost_currencies}

        status_counts = {}
        for st in ["Open", "Won", "Lost"]:
            c = self.db.query(func.count(Opportunity.id)).filter(Opportunity.status == st).scalar() or 0
            status_counts[st] = c

        total_count = sum(status_counts.values())

        return {
            "success": True,
            "totalCount": total_count,
            "totalOpenValue": total_open_value,
            "openPipelineValueByCurrency": open_by_currency,
            "wonOpportunityValueByCurrency": won_by_currency,
            "lostOpportunityValueByCurrency": lost_by_currency,
            "byStage": stage_metrics,
            "byStatus": status_counts
        }

    def transition_opportunity_stage(
        self,
        actor: CurrentUser,
        opp_id: str,
        payload: OpportunityStageTransitionRequest,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        opp = self.db.query(Opportunity).options(
            joinedload(Opportunity.account),
            joinedload(Opportunity.contact),
            joinedload(Opportunity.originating_lead),
            joinedload(Opportunity.assigned_to),
            joinedload(Opportunity.created_by),
            joinedload(Opportunity.milestones),
            joinedload(Opportunity.consulting_engagements),
            joinedload(Opportunity.sample_submissions),
            joinedload(Opportunity.product_transactions),
            selectinload(Opportunity.quotations)
        ).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).with_for_update(of=Opportunity).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")

        valid_stages = OPPORTUNITY_STAGES
        new_stage = (payload.newStage or "").strip()
        if new_stage not in valid_stages:
            raise ValidationError(f"Invalid stage '{new_stage}'. Permitted stages are: {', '.join(valid_stages)}")

        # Automated Stage Transition Governance:
        # Opportunity stages are automated strictly by CRM business events; direct manual stage hopping is rejected.
        if new_stage and new_stage != opp.stage:
            raise ValidationError(
                "Direct manual stage transitions are disabled. Opportunity stages are strictly controlled "
                "by CRM business events (e.g. Lead Qualification, Quotation Creation, Commercial Revision, "
                "Proforma Invoice Issuance, Order Confirmation, Payment Tracking)."
            )

        STAGE_INDEX = {s: i for i, s in enumerate(valid_stages)}
        old_stage = opp.stage or "Enquiry"
        old_idx = STAGE_INDEX.get(old_stage, 0)
        new_idx = STAGE_INDEX.get(new_stage, 0)

        # Backward stage movement permission: only authorized managers
        if new_idx < old_idx:
            user_roles = set(actor.roles or [])
            if actor.active_role:
                user_roles.add(actor.active_role)
            crm_roles = set(actor.module_roles.get("CRM", [])) if actor.module_roles else set()
            all_user_roles = user_roles.union(crm_roles)
            is_manager = bool(
                actor.is_global_admin or
                "Admin" in all_user_roles or
                "SuperAdmin" in all_user_roles or
                "IT_ADMIN" in all_user_roles or
                "DIRECTOR" in all_user_roles or
                "CRM_SALES_MANAGER" in all_user_roles or
                "CRM_ADMIN" in all_user_roles
            )
            if not is_manager:
                raise PermissionDeniedError("Only authorized sales managers or CRM administrators can move an opportunity backward through the pipeline.")

        old_status = opp.status
        target_status = payload.status.strip() if payload.status else None

        if target_status and target_status not in ["Open", "Won", "Lost"]:
            raise ValidationError(f"Invalid status '{target_status}'. Permitted statuses are Open, Won, Lost.")

        # Stage and outcome combined business rules
        if target_status == "Lost":
            if not payload.lossReason or not payload.lossReason.strip():
                raise ValidationError("Loss reason is mandatory when marking an opportunity as Lost.")
            opp.status = "Lost"
            opp.stage = new_stage
            opp.loss_reason = payload.lossReason.strip()
            opp.won_reason = None
            opp.closed_by_id = str(actor.id) if actor.id else None
            close_dt = payload.actualCloseDate or datetime.now(timezone.utc)
            opp.actual_close_date = close_dt if isinstance(close_dt, datetime) else datetime.combine(close_dt, datetime.min.time(), tzinfo=timezone.utc)
        elif target_status == "Won":
            if not payload.wonReason or not payload.wonReason.strip():
                raise ValidationError("Won reason is mandatory when marking an opportunity as Won.")
            opp.status = "Won"
            opp.stage = new_stage
            opp.won_reason = payload.wonReason.strip()
            opp.loss_reason = None
            opp.closed_by_id = str(actor.id) if actor.id else None
            close_dt = payload.actualCloseDate or datetime.now(timezone.utc)
            opp.actual_close_date = close_dt if isinstance(close_dt, datetime) else datetime.combine(close_dt, datetime.min.time(), tzinfo=timezone.utc)
        else:
            opp.stage = new_stage
            opp.status = "Open"
            opp.loss_reason = None
            opp.won_reason = None
            opp.closed_by_id = None
            opp.actual_close_date = None

        opp.updated_by_id = str(actor.id) if actor.id else None
        opp.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(opp)

        try:
            self.audit_service.log(
                action="CRM_OPPORTUNITY_STAGE_CHANGED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "opportunity_id": opp.opportunity_id,
                    "old_stage": old_stage,
                    "new_stage": opp.stage,
                    "old_status": old_status,
                    "new_status": opp.status,
                    "remarks": payload.remarks
                }
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for opportunity stage change {opp.opportunity_id}: {audit_err}")

        return self._format_opportunity(opp)

    def update_opportunity(
        self,
        actor: CurrentUser,
        opp_id: str,
        payload: OpportunityUpdateRequest,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        opp = self.db.query(Opportunity).options(
            joinedload(Opportunity.account),
            joinedload(Opportunity.contact),
            joinedload(Opportunity.originating_lead),
            joinedload(Opportunity.assigned_to),
            joinedload(Opportunity.created_by),
            joinedload(Opportunity.milestones),
            joinedload(Opportunity.consulting_engagements),
            joinedload(Opportunity.sample_submissions),
            joinedload(Opportunity.product_transactions),
            selectinload(Opportunity.quotations)
        ).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).with_for_update(of=Opportunity).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")

        valid_stages = OPPORTUNITY_STAGES
        STAGE_INDEX = {s: i for i, s in enumerate(valid_stages)}
        changes = {}

        if payload.name is not None:
            clean_name = payload.name.strip()
            if not clean_name:
                raise ValidationError("Opportunity name cannot be empty.")
            changes["name"] = {"old": opp.name, "new": clean_name}
            opp.name = clean_name

        if payload.currency is not None:
            clean_curr = payload.currency.strip().upper()
            if clean_curr not in APPROVED_CURRENCIES:
                raise ValidationError(f"Invalid currency '{clean_curr}'. Approved currencies are: {', '.join(APPROVED_CURRENCIES)}")
            if clean_curr != opp.currency:
                changes["currency"] = {"old": opp.currency, "new": clean_curr}
                opp.currency = clean_curr

        if payload.estimatedValue is not None:
            if payload.estimatedValue < 0:
                raise ValidationError("Estimated value cannot be negative.")
            old_val = float(opp.estimated_value) if opp.estimated_value is not None else None
            changes["estimated_value"] = {"old": old_val, "new": payload.estimatedValue}
            if payload.estimatedValueChangeReason:
                changes["estimated_value_change_reason"] = payload.estimatedValueChangeReason.strip()
            opp.estimated_value = payload.estimatedValue

        if payload.expectedCloseDate is not None:
            changes["expected_close_date"] = {"old": opp.expected_close_date.isoformat() if opp.expected_close_date else None, "new": payload.expectedCloseDate.isoformat()}
            opp.expected_close_date = payload.expectedCloseDate

        if payload.businessArea is not None:
            changes["business_area"] = {"old": opp.business_area, "new": payload.businessArea}
            opp.business_area = payload.businessArea

        if payload.requirementTypes is not None:
            canonical_types = normalize_and_validate_req_types(payload.requirementTypes)
            new_req_str = ", ".join(canonical_types)
            changes["requirement_types"] = {"old": opp.requirement_types, "new": new_req_str}
            opp.requirement_types = new_req_str

        if payload.description is not None:
            changes["description"] = {"old": opp.description, "new": payload.description}
            opp.description = payload.description

        if payload.assignedToUserId is not None:
            if payload.assignedToUserId.strip():
                user_exists = self.db.query(User).filter(User.id == payload.assignedToUserId.strip()).first()
                if not user_exists:
                    raise ValidationError(f"Assigned user '{payload.assignedToUserId}' does not exist.")
                opp.assigned_to_user_id = payload.assignedToUserId.strip()
            else:
                opp.assigned_to_user_id = None

        # Relationships: account_id and contact_id
        new_account_id = opp.account_id
        if "accountId" in payload.model_fields_set:
            if payload.accountId and payload.accountId.strip():
                acc = self.db.query(Account).filter(or_(Account.id == payload.accountId.strip(), Account.account_id == payload.accountId.strip()), Account.is_active == True).first()
                if not acc:
                    raise NotFoundError(f"Account '{payload.accountId}' not found.")
                new_account_id = acc.id
            else:
                new_account_id = None

        new_contact_id = opp.contact_id
        if "contactId" in payload.model_fields_set:
            if payload.contactId and payload.contactId.strip():
                con = self.db.query(Contact).filter(or_(Contact.id == payload.contactId.strip(), Contact.contact_id == payload.contactId.strip()), Contact.is_active == True).first()
                if not con:
                    raise NotFoundError(f"Contact '{payload.contactId}' not found.")
                new_contact_id = con.id
            else:
                new_contact_id = None

        if not new_account_id and not new_contact_id:
            raise ValidationError("At least one primary relationship (Primary Account or Primary Contact) is required.")

        if new_account_id and new_contact_id:
            con_obj = self.db.query(Contact).filter(Contact.id == new_contact_id).first()
            if con_obj and con_obj.account_id and con_obj.account_id != new_account_id:
                raise ValidationError("Selected Contact belongs to a different Account.")

        if new_account_id != opp.account_id:
            changes["account_id"] = {"old": opp.account_id, "new": new_account_id}
            opp.account_id = new_account_id

        if new_contact_id != opp.contact_id:
            changes["contact_id"] = {"old": opp.contact_id, "new": new_contact_id}
            opp.contact_id = new_contact_id

        # Stage and Status validation & updates
        proposed_stage = opp.stage or "Enquiry"

        if payload.stage is not None:
            clean_stg = payload.stage.strip()
            if clean_stg not in valid_stages:
                raise ValidationError(f"Invalid stage '{clean_stg}'. Permitted stages are: {', '.join(valid_stages)}")
            if clean_stg != opp.stage:
                raise ValidationError(
                    "Opportunity stages are fully automated by CRM business events (Quotation, PI, Order confirmation) "
                    "and cannot be manually modified."
                )
            proposed_stage = clean_stg

        proposed_status = opp.status or "Open"
        if payload.status is not None:
            clean_stat = payload.status.strip()
            if clean_stat not in ("Open", "Won", "Lost"):
                raise ValidationError(f"Invalid status '{clean_stat}'. Permitted statuses are Open, Won, Lost.")
            proposed_status = clean_stat

        # Check backward transition permission
        if proposed_stage != opp.stage:
            old_idx = STAGE_INDEX.get(opp.stage, 0)
            new_idx = STAGE_INDEX.get(proposed_stage, 0)
            if new_idx < old_idx:
                user_roles = set(actor.roles or [])
                if actor.active_role:
                    user_roles.add(actor.active_role)
                crm_roles = set(actor.module_roles.get("CRM", [])) if actor.module_roles else set()
                all_user_roles = user_roles.union(crm_roles)
                is_manager = bool(
                    actor.is_global_admin or
                    "Admin" in all_user_roles or
                    "SuperAdmin" in all_user_roles or
                    "IT_ADMIN" in all_user_roles or
                    "DIRECTOR" in all_user_roles or
                    "CRM_SALES_MANAGER" in all_user_roles or
                    "CRM_ADMIN" in all_user_roles
                )
                if not is_manager:
                    raise PermissionDeniedError("Only authorized sales managers or CRM administrators can move an opportunity backward through the pipeline.")

        # Combined stage and outcome validation
        if proposed_status == "Lost":
            loss_r = payload.lossReason or opp.loss_reason
            if not loss_r or not str(loss_r).strip():
                raise ValidationError("Loss reason is mandatory when marking an opportunity as Lost.")
        if proposed_status == "Won":
            won_r = payload.wonReason or opp.won_reason
            if not won_r or not str(won_r).strip():
                raise ValidationError("Won reason is mandatory when marking an opportunity as Won.")

        # Reopening guard: if moving from Closed to Open
        if opp.status in ("Won", "Lost") and proposed_status == "Open":
            user_roles = set(actor.roles or [])
            if actor.active_role:
                user_roles.add(actor.active_role)
            crm_roles = set(actor.module_roles.get("CRM", [])) if actor.module_roles else set()
            all_user_roles = user_roles.union(crm_roles)
            can_reopen = bool(
                actor.is_global_admin or
                "Admin" in all_user_roles or
                "SuperAdmin" in all_user_roles or
                "CRM_ADMIN" in all_user_roles or
                "IT_ADMIN" in all_user_roles or
                "DIRECTOR" in all_user_roles
            )
            if not can_reopen:
                raise PermissionDeniedError("Reopening a closed Opportunity requires CRM Administrator authorization.")

        if proposed_stage != opp.stage:
            changes["stage"] = {"old": opp.stage, "new": proposed_stage}
            opp.stage = proposed_stage

        if proposed_status != opp.status:
            changes["status"] = {"old": opp.status, "new": proposed_status}
            opp.status = proposed_status

        if proposed_status == "Lost":
            loss_r = payload.lossReason or opp.loss_reason
            opp.loss_reason = loss_r.strip() if loss_r else None
            close_dt = payload.actualCloseDate or opp.actual_close_date or datetime.now(timezone.utc)
            opp.actual_close_date = close_dt if isinstance(close_dt, datetime) else datetime.combine(close_dt, datetime.min.time(), tzinfo=timezone.utc)
        elif proposed_status == "Won":
            opp.loss_reason = None
            close_dt = payload.actualCloseDate or opp.actual_close_date or datetime.now(timezone.utc)
            opp.actual_close_date = close_dt if isinstance(close_dt, datetime) else datetime.combine(close_dt, datetime.min.time(), tzinfo=timezone.utc)
        else:
            opp.loss_reason = None
            opp.actual_close_date = None

        if "subStatus" in payload.model_fields_set or "sub_status" in payload.model_fields_set:
            val = payload.subStatus if "subStatus" in payload.model_fields_set else payload.sub_status
            clean_sub = str(val).strip() if (val is not None and str(val).strip()) else None
            changes["sub_status"] = {"old": opp.sub_status, "new": clean_sub}
            opp.sub_status = clean_sub

        # Safely synchronize updated opportunity info into active quotation without touching commercial line items
        if "name" in changes:
            active_q = self.db.query(OpportunityQuotation).filter(
                OpportunityQuotation.opportunity_id == opp.id,
                OpportunityQuotation.is_active == True
            ).first()
            if active_q and (not active_q.title or "Quotation for" in active_q.title):
                active_q.title = f"Quotation for {opp.name}"

        opp.updated_by_id = str(actor.id) if actor.id else None
        opp.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(opp)

        try:
            self.audit_service.log(
                action="CRM_OPPORTUNITY_UPDATED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={"opportunity_id": opp.opportunity_id, "changes": changes}
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for opportunity update {opp.opportunity_id}: {audit_err}")

        return self._format_opportunity(opp)

    def confirm_order_and_start_supply(
        self,
        actor: CurrentUser,
        opp_id: str,
        order_reference: Optional[str] = None,
        execution_start_date: Optional[date] = None,
        notes: Optional[str] = None,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        opp = self.db.query(Opportunity).options(
            joinedload(Opportunity.account),
            joinedload(Opportunity.contact),
            joinedload(Opportunity.originating_lead),
            joinedload(Opportunity.assigned_to),
            joinedload(Opportunity.created_by),
            joinedload(Opportunity.milestones),
            joinedload(Opportunity.consulting_engagements),
            joinedload(Opportunity.sample_submissions),
            joinedload(Opportunity.product_transactions),
            selectinload(Opportunity.quotations)
        ).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).with_for_update(of=Opportunity).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")

        remarks_parts = []
        if order_reference:
            remarks_parts.append(f"Order Ref: {order_reference}")
        if execution_start_date:
            remarks_parts.append(f"Start Date: {execution_start_date}")
        if notes:
            remarks_parts.append(notes)
        remarks_str = " | ".join(remarks_parts) if remarks_parts else "Order confirmed and supply execution started"

        record_opportunity_stage_transition(
            db=self.db,
            opp=opp,
            new_stage="Supply",
            triggering_event="ORDER_CONFIRMED_SUPPLY_STARTED",
            actor=actor,
            remarks=remarks_str,
            commit=True
        )

        try:
            self.audit_service.log(
                action="CRM_OPPORTUNITY_ORDER_CONFIRMED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={"opportunity_id": opp.opportunity_id, "stage": "Supply", "order_reference": order_reference}
            )
        except Exception:
            pass

        return self._format_opportunity(opp)

    def start_payment_tracking(
        self,
        actor: CurrentUser,
        opp_id: str,
        payment_terms: Optional[str] = None,
        expected_payment_date: Optional[date] = None,
        outstanding_amount: Optional[float] = None,
        notes: Optional[str] = None,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        opp = self.db.query(Opportunity).options(
            joinedload(Opportunity.account),
            joinedload(Opportunity.contact),
            joinedload(Opportunity.originating_lead),
            joinedload(Opportunity.assigned_to),
            joinedload(Opportunity.created_by),
            joinedload(Opportunity.milestones),
            joinedload(Opportunity.consulting_engagements),
            joinedload(Opportunity.sample_submissions),
            joinedload(Opportunity.product_transactions),
            selectinload(Opportunity.quotations)
        ).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).with_for_update(of=Opportunity).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")

        remarks_parts = []
        if payment_terms:
            remarks_parts.append(f"Terms: {payment_terms}")
        if expected_payment_date:
            remarks_parts.append(f"Expected Date: {expected_payment_date}")
        if outstanding_amount is not None:
            remarks_parts.append(f"Amount: {outstanding_amount}")
        if notes:
            remarks_parts.append(notes)
        remarks_str = " | ".join(remarks_parts) if remarks_parts else "Payment tracking and collection started"

        record_opportunity_stage_transition(
            db=self.db,
            opp=opp,
            new_stage="Payment",
            triggering_event="PAYMENT_TRACKING_STARTED",
            actor=actor,
            remarks=remarks_str,
            commit=True
        )

        try:
            self.audit_service.log(
                action="CRM_OPPORTUNITY_PAYMENT_TRACKING_STARTED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={"opportunity_id": opp.opportunity_id, "stage": "Payment"}
            )
        except Exception:
            pass

        return self._format_opportunity(opp)

    def mark_opportunity_dormant(
        self,
        actor: CurrentUser,
        opp_id: str,
        dormancy_reason: str,
        notes: Optional[str] = None,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        if not dormancy_reason or not dormancy_reason.strip():
            raise ValidationError("Dormancy reason is mandatory when marking an Opportunity as Dormant.")

        opp = self.db.query(Opportunity).options(
            joinedload(Opportunity.account),
            joinedload(Opportunity.contact),
            joinedload(Opportunity.originating_lead),
            joinedload(Opportunity.assigned_to),
            joinedload(Opportunity.created_by),
            joinedload(Opportunity.milestones),
            joinedload(Opportunity.consulting_engagements),
            joinedload(Opportunity.sample_submissions),
            joinedload(Opportunity.product_transactions),
            selectinload(Opportunity.quotations)
        ).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).with_for_update(of=Opportunity).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")

        remarks_str = f"Reason: {dormancy_reason.strip()}"
        if notes and notes.strip():
            remarks_str += f" | Notes: {notes.strip()}"

        record_opportunity_stage_transition(
            db=self.db,
            opp=opp,
            new_stage="Dormant",
            triggering_event="OPPORTUNITY_MARKED_DORMANT",
            actor=actor,
            remarks=remarks_str,
            commit=True
        )

        try:
            self.audit_service.log(
                action="CRM_OPPORTUNITY_MARKED_DORMANT",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={"opportunity_id": opp.opportunity_id, "stage": "Dormant", "reason": dormancy_reason.strip()}
            )
        except Exception:
            pass

        return self._format_opportunity(opp)

    def reactivate_opportunity(
        self,
        actor: CurrentUser,
        opp_id: str,
        notes: Optional[str] = None,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        opp = self.db.query(Opportunity).options(
            joinedload(Opportunity.account),
            joinedload(Opportunity.contact),
            joinedload(Opportunity.originating_lead),
            joinedload(Opportunity.assigned_to),
            joinedload(Opportunity.created_by),
            joinedload(Opportunity.milestones),
            joinedload(Opportunity.consulting_engagements),
            joinedload(Opportunity.sample_submissions),
            joinedload(Opportunity.product_transactions),
            selectinload(Opportunity.quotations)
        ).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).with_for_update(of=Opportunity).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")

        if opp.stage != "Dormant":
            raise ValidationError(f"Opportunity '{opp.opportunity_id}' is not in Dormant stage.")

        prev_hist = self.db.query(OpportunityStageHistory).filter(
            OpportunityStageHistory.opportunity_id == opp.id,
            OpportunityStageHistory.new_stage != "Dormant"
        ).order_by(OpportunityStageHistory.created_at.desc()).first()

        target_stage = prev_hist.new_stage if prev_hist else "Enquiry"

        record_opportunity_stage_transition(
            db=self.db,
            opp=opp,
            new_stage=target_stage,
            triggering_event="OPPORTUNITY_REACTIVATED",
            actor=actor,
            remarks=notes or f"Opportunity reactivated from Dormant to {target_stage}",
            commit=True
        )

        try:
            self.audit_service.log(
                action="CRM_OPPORTUNITY_REACTIVATED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={"opportunity_id": opp.opportunity_id, "new_stage": target_stage}
            )
        except Exception:
            pass

        return self._format_opportunity(opp)

    def get_opportunity_stage_history(self, opp_id: str) -> List[Dict[str, Any]]:
        opp = self._get_opportunity_or_404(opp_id)
        entries = self.db.query(OpportunityStageHistory).filter(
            OpportunityStageHistory.opportunity_id == opp.id
        ).order_by(desc(OpportunityStageHistory.created_at)).all()

        return [
            {
                "id": e.id,
                "opportunityId": e.opportunity_id,
                "previousStage": e.previous_stage,
                "newStage": e.new_stage,
                "triggeringEvent": e.triggering_event,
                "triggeringUserId": e.triggering_user_id,
                "triggeringUserName": e.triggering_user_name,
                "remarks": e.remarks,
                "createdAt": e.created_at.isoformat() if e.created_at else None
            }
            for e in entries
        ]

    def get_opportunity_workstreams(self, opp_id: str) -> List[Dict[str, Any]]:
        opp = self.db.query(Opportunity).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")

        workstreams = []
        ces = self.db.query(ConsultingEngagement).filter(ConsultingEngagement.opportunity_id == opp.id).all()
        for ce in ces:
            workstreams.append(self._format_workstream("consulting", ce))

        sss = self.db.query(SampleSubmission).filter(SampleSubmission.opportunity_id == opp.id).all()
        for ss in sss:
            workstreams.append(self._format_workstream("sample_testing", ss))

        pts = self.db.query(ProductTransaction).filter(ProductTransaction.opportunity_id == opp.id).all()
        for pt in pts:
            workstreams.append(self._format_workstream("product", pt))

        return workstreams

    def route_opportunity_requirements(
        self,
        actor: CurrentUser,
        opp_id: str,
        payload: RequirementRouteRequest,
        request: Optional[Request] = None
    ) -> Tuple[List[Dict[str, Any]], str]:
        opp = self.db.query(Opportunity).options(
            joinedload(Opportunity.account),
            joinedload(Opportunity.contact)
        ).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).with_for_update(of=Opportunity).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")

        if payload.requirementTypes is not None:
            req_types = normalize_and_validate_req_types(payload.requirementTypes) if payload.requirementTypes else []
            opp.requirement_types = ", ".join(req_types)
        else:
            raw = [r.strip() for r in (opp.requirement_types or "").split(",") if r.strip()]
            req_types = normalize_and_validate_req_types(raw) if raw else []

        newly_created = []
        if "Consulting" in req_types:
            existing = self.db.query(ConsultingEngagement).filter(ConsultingEngagement.opportunity_id == opp.id).first()
            if not existing:
                eng_code = get_next_sequence_id(self.db, "ENGAGEMENT", "ENG", commit=False)
                ce = ConsultingEngagement(
                    engagement_id=eng_code,
                    account_id=opp.account_id,
                    contact_id=opp.contact_id,
                    lead_id=opp.originating_lead_id,
                    opportunity_id=opp.id,
                    title=f"Consulting Engagement - {opp.name}"[:255],
                    scope_description=opp.description or opp.requirement_summary or "Consulting engagement initiated from Opportunity pipeline.",
                    agreed_fee=opp.estimated_value or 0.0,
                    billing_arrangement="Milestone-based",
                    status="Draft"
                )
                self.db.add(ce)
                newly_created.append(f"Consulting Engagement ({eng_code})")

        if "Sample Testing" in req_types:
            existing = self.db.query(SampleSubmission).filter(SampleSubmission.opportunity_id == opp.id).first()
            if not existing:
                smp_code = get_next_sequence_id(self.db, "SAMPLE", "SMP", commit=False)
                ss = SampleSubmission(
                    sample_id=smp_code,
                    account_id=opp.account_id,
                    contact_id=opp.contact_id,
                    lead_id=opp.originating_lead_id,
                    opportunity_id=opp.id,
                    sample_description=f"Sample Testing - {opp.name}"[:255],
                    sample_type=opp.business_area or "Biogas",
                    status="Received",
                    sample_level_charge=0.0
                )
                self.db.add(ss)
                newly_created.append(f"Sample Submission ({smp_code})")

        if "Product" in req_types:
            existing = self.db.query(ProductTransaction).filter(ProductTransaction.opportunity_id == opp.id).first()
            if not existing:
                prd_code = get_next_sequence_id(self.db, "PRODUCT_TX", "PRD", commit=False)
                pt = ProductTransaction(
                    transaction_id=prd_code,
                    account_id=opp.account_id,
                    contact_id=opp.contact_id,
                    lead_id=opp.originating_lead_id,
                    opportunity_id=opp.id,
                    product_name=f"Product - {opp.name}"[:255],
                    transaction_type="Recommendation",
                    status="Pending",
                    quantity=1.0,
                    unit_of_measure="litres",
                    unit_rate=0.0,
                    calculated_amount=opp.estimated_value or 0.0
                )
                self.db.add(pt)
                newly_created.append(f"Product Transaction ({prd_code})")

        opp.updated_by_id = str(actor.id) if actor.id else None
        opp.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        try:
            self.audit_service.log(
                action="CRM_OPPORTUNITY_REQUIREMENTS_ROUTED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "opportunity_id": opp.opportunity_id,
                    "requirement_types": req_types,
                    "newly_routed": newly_created
                }
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for requirement routing on {opp.opportunity_id}: {audit_err}")

        all_workstreams = self.get_opportunity_workstreams(opp.id)
        if not req_types:
            msg = "No requirement types configured or selected for routing."
        elif newly_created:
            msg = f"Requirements successfully routed: {', '.join(newly_created)}"
        else:
            msg = "All selected requirements are already routed to workstreams (idempotent)."
        return all_workstreams, msg

    def list_milestones(
        self,
        actor: CurrentUser,
        opportunity_id: Optional[str] = None,
        status: Optional[str] = None,
        assigned_to_user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = self.db.query(Milestone).options(
            joinedload(Milestone.opportunity),
            joinedload(Milestone.assigned_to),
            joinedload(Milestone.created_by)
        )
        if opportunity_id:
            query = query.join(Milestone.opportunity).filter(
                or_(Milestone.opportunity_id == opportunity_id, Opportunity.opportunity_id == opportunity_id)
            )
        if status and status.strip().upper() != "ALL":
            query = query.filter(Milestone.status == status.strip())
        if assigned_to_user_id:
            query = query.filter(Milestone.assigned_to_user_id == assigned_to_user_id.strip())

        milestones = query.order_by(Milestone.due_date.asc().nulls_last(), Milestone.created_at.desc()).all()
        return [self._format_milestone(m) for m in milestones]

    def get_milestone(self, milestone_id: str) -> Dict[str, Any]:
        m = self.db.query(Milestone).options(
            joinedload(Milestone.opportunity),
            joinedload(Milestone.assigned_to),
            joinedload(Milestone.created_by)
        ).filter(
            or_(Milestone.id == milestone_id, Milestone.milestone_id == milestone_id)
        ).first()
        if not m:
            raise NotFoundError(f"Milestone '{milestone_id}' not found.")
        return self._format_milestone(m)

    def create_milestone(
        self,
        actor: CurrentUser,
        opp_id: str,
        payload: MilestoneCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        opp = self.db.query(Opportunity).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")

        if payload.assignedToUserId and payload.assignedToUserId.strip():
            u = self.db.query(User).filter(User.id == payload.assignedToUserId.strip()).first()
            if not u:
                raise ValidationError(f"Assigned user '{payload.assignedToUserId}' does not exist.")

        mls_code = get_next_sequence_id(self.db, "MILESTONE", "MLS", commit=False)
        m = Milestone(
            milestone_id=mls_code,
            opportunity_id=opp.id,
            workstream_type=payload.workstreamType,
            workstream_id=payload.workstreamId,
            title=payload.title.strip(),
            description=payload.description.strip() if payload.description else None,
            planned_start_date=payload.plannedStartDate,
            due_date=payload.dueDate,
            status="Pending",
            assigned_to_user_id=payload.assignedToUserId.strip() if payload.assignedToUserId else None,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)

        try:
            self.audit_service.log(
                action="CRM_MILESTONE_CREATED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={"milestone_id": m.milestone_id, "opportunity_id": opp.opportunity_id, "title": m.title}
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for milestone create {m.milestone_id}: {audit_err}")

        return self._format_milestone(m)

    def update_milestone(
        self,
        actor: CurrentUser,
        milestone_id: str,
        payload: MilestoneUpdate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        m = self.db.query(Milestone).options(
            joinedload(Milestone.opportunity),
            joinedload(Milestone.assigned_to)
        ).filter(
            or_(Milestone.id == milestone_id, Milestone.milestone_id == milestone_id)
        ).first()
        if not m:
            raise NotFoundError(f"Milestone '{milestone_id}' not found.")

        if payload.title is not None:
            clean_title = payload.title.strip()
            if not clean_title:
                raise ValidationError("Milestone title cannot be empty.")
            m.title = clean_title

        if payload.description is not None:
            m.description = payload.description.strip() if payload.description else None

        if payload.workstreamType is not None:
            m.workstream_type = payload.workstreamType

        if payload.workstreamId is not None:
            m.workstream_id = payload.workstreamId

        if payload.plannedStartDate is not None:
            m.planned_start_date = payload.plannedStartDate

        if payload.dueDate is not None:
            m.due_date = payload.dueDate

        if payload.assignedToUserId is not None:
            if payload.assignedToUserId.strip():
                u = self.db.query(User).filter(User.id == payload.assignedToUserId.strip()).first()
                if not u:
                    raise ValidationError(f"Assigned user '{payload.assignedToUserId}' does not exist.")
                m.assigned_to_user_id = payload.assignedToUserId.strip()
            else:
                m.assigned_to_user_id = None

        if payload.completionNotes is not None:
            m.completion_notes = payload.completionNotes

        m.updated_by_id = str(actor.id) if actor.id else None
        m.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(m)
        return self._format_milestone(m)

    def transition_milestone_status(
        self,
        actor: CurrentUser,
        milestone_id: str,
        payload: MilestoneStatusTransitionRequest,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        m = self.db.query(Milestone).options(
            joinedload(Milestone.opportunity),
            joinedload(Milestone.assigned_to)
        ).filter(
            or_(Milestone.id == milestone_id, Milestone.milestone_id == milestone_id)
        ).first()
        if not m:
            raise NotFoundError(f"Milestone '{milestone_id}' not found.")

        valid_statuses = ["Pending", "In Progress", "Completed", "Cancelled"]
        target_status = (payload.status or "").strip()
        if target_status not in valid_statuses:
            raise ValidationError(f"Invalid status '{target_status}'. Permitted: {', '.join(valid_statuses)}")

        old_status = m.status
        m.status = target_status
        if payload.completionNotes is not None:
            m.completion_notes = payload.completionNotes

        if target_status == "Completed":
            m.completed_at = payload.completedAt or datetime.now(timezone.utc)
        else:
            m.completed_at = None

        m.updated_by_id = str(actor.id) if actor.id else None
        m.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(m)

        try:
            self.audit_service.log(
                action="CRM_MILESTONE_STATUS_CHANGED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={"milestone_id": m.milestone_id, "old_status": old_status, "new_status": m.status}
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for milestone status change {m.milestone_id}: {audit_err}")

        return self._format_milestone(m)

    def delete_milestone(
        self,
        actor: CurrentUser,
        milestone_id: str,
        request: Optional[Request] = None
    ) -> None:
        m = self.db.query(Milestone).filter(
            or_(Milestone.id == milestone_id, Milestone.milestone_id == milestone_id)
        ).first()
        if not m:
            raise NotFoundError(f"Milestone '{milestone_id}' not found.")

        mls_id = m.milestone_id
        self.db.delete(m)
        self.db.commit()

        try:
            self.audit_service.log(
                action="CRM_MILESTONE_DELETED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={"milestone_id": mls_id}
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for milestone delete {mls_id}: {audit_err}")

    def get_upcoming_milestones(
        self,
        actor: CurrentUser,
        days: int = 14,
        assigned_to_user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        KOLKATA_TZ = zoneinfo.ZoneInfo("Asia/Kolkata")
        today_ist = datetime.now(KOLKATA_TZ).date()
        cutoff_date = today_ist + timedelta(days=days)

        query = self.db.query(Milestone).options(
            joinedload(Milestone.opportunity),
            joinedload(Milestone.assigned_to)
        ).filter(
            Milestone.status.in_(["Pending", "In Progress"]),
            Milestone.due_date != None,
            Milestone.due_date <= cutoff_date
        )
        if assigned_to_user_id:
            query = query.filter(Milestone.assigned_to_user_id == assigned_to_user_id.strip())

        milestones = query.order_by(Milestone.due_date.asc()).all()
        return [self._format_milestone(m) for m in milestones]

    # =========================================================================
    # 4B. PHASE 5A: OPPORTUNITY REOPENING, REVENUE & QUOTATION SERVICES
    # =========================================================================

    def reopen_opportunity(
        self,
        actor: CurrentUser,
        opp_id: str,
        payload: OpportunityReopenRequest,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        user_roles = set(actor.roles or [])
        if actor.active_role:
            user_roles.add(actor.active_role)
        crm_roles = set(actor.module_roles.get("CRM", [])) if actor.module_roles else set()
        all_user_roles = user_roles.union(crm_roles)

        can_reopen = bool(
            actor.is_global_admin or
            "Admin" in all_user_roles or
            "SuperAdmin" in all_user_roles or
            "CRM_ADMIN" in all_user_roles or
            "IT_ADMIN" in all_user_roles or
            "DIRECTOR" in all_user_roles
        )
        if not can_reopen:
            raise PermissionDeniedError("Reopening a closed Opportunity requires CRM Administrator authorization.")

        opp = self.db.query(Opportunity).options(
            joinedload(Opportunity.account),
            joinedload(Opportunity.contact),
            joinedload(Opportunity.originating_lead),
            joinedload(Opportunity.assigned_to),
            joinedload(Opportunity.created_by),
            selectinload(Opportunity.milestones),
            selectinload(Opportunity.consulting_engagements),
            selectinload(Opportunity.sample_submissions),
            selectinload(Opportunity.product_transactions),
            selectinload(Opportunity.quotations)
        ).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).with_for_update(of=Opportunity).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")

        if opp.status not in ("Won", "Lost"):
            raise ValidationError(f"Opportunity '{opp.opportunity_id}' is currently '{opp.status}'. Only Won or Lost opportunities can be reopened.")

        reason = (payload.reason or "").strip()
        if not reason:
            raise ValidationError("Mandatory justification reason must be provided to reopen a closed Opportunity.")

        target_stage = (payload.reopenStage or "").strip()
        open_stages = ["Enquiry", "Offer", "Negotiation", "Supply", "Payment"]
        if target_stage not in open_stages:
            raise ValidationError(f"Invalid reopen stage '{target_stage}'. Permitted stages are: {', '.join(open_stages)}")

        old_status = opp.status
        old_stage = opp.stage
        old_close_date = opp.actual_close_date.isoformat() if opp.actual_close_date else None
        old_loss_reason = opp.loss_reason

        now_utc = datetime.now(timezone.utc)
        opp.status = "Open"
        opp.stage = target_stage
        opp.actual_close_date = None
        opp.loss_reason = None
        opp.won_reason = None
        opp.closed_by_id = None
        opp.reopened_at = now_utc
        opp.reopened_by_id = str(actor.id) if actor.id else None
        opp.updated_by_id = str(actor.id) if actor.id else None
        opp.updated_at = now_utc
        self.db.commit()
        self.db.refresh(opp)

        try:
            self.audit_service.log(
                action="CRM_OPPORTUNITY_REOPENED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "opportunity_id": opp.opportunity_id,
                    "previous_status": old_status,
                    "previous_stage": old_stage,
                    "new_status": "Open",
                    "new_stage": opp.stage,
                    "previous_actual_close_date": old_close_date,
                    "previous_loss_reason": old_loss_reason,
                    "reason": reason
                }
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for opportunity reopen {opp.opportunity_id}: {audit_err}")

        return self._format_opportunity(opp)

    def get_sales_hub_revenue_metrics(self, actor: CurrentUser) -> Dict[str, Any]:
        stages = OPPORTUNITY_STAGES
        stage_metrics = []
        for stg in stages:
            row = self.db.query(
                func.count(Opportunity.id),
                func.coalesce(func.sum(Opportunity.estimated_value), 0.0)
            ).filter(
                Opportunity.stage == stg,
                Opportunity.status == "Open"
            ).first()
            cnt = row[0] or 0
            val = float(row[1] or 0.0)
            stage_metrics.append({"stage": stg, "count": cnt, "totalValue": val})

        # Totals by currency
        open_currencies = self.db.query(
            Opportunity.currency,
            func.coalesce(func.sum(Opportunity.estimated_value), 0.0)
        ).filter(
            Opportunity.status == "Open"
        ).group_by(Opportunity.currency).all()
        open_by_currency = {c or "INR": float(v or 0.0) for c, v in open_currencies}

        won_currencies = self.db.query(
            Opportunity.currency,
            func.coalesce(func.sum(Opportunity.estimated_value), 0.0)
        ).filter(
            Opportunity.status == "Won"
        ).group_by(Opportunity.currency).all()
        won_by_currency = {c or "INR": float(v or 0.0) for c, v in won_currencies}

        lost_currencies = self.db.query(
            Opportunity.currency,
            func.coalesce(func.sum(Opportunity.estimated_value), 0.0)
        ).filter(
            Opportunity.status == "Lost"
        ).group_by(Opportunity.currency).all()
        lost_by_currency = {c or "INR": float(v or 0.0) for c, v in lost_currencies}

        open_count = self.db.query(func.count(Opportunity.id)).filter(Opportunity.status == "Open").scalar() or 0
        won_count = self.db.query(func.count(Opportunity.id)).filter(Opportunity.status == "Won").scalar() or 0
        lost_count = self.db.query(func.count(Opportunity.id)).filter(Opportunity.status == "Lost").scalar() or 0
        total_count = open_count + won_count + lost_count

        return {
            "success": True,
            "totalCount": total_count,
            "openCount": open_count,
            "wonCount": won_count,
            "lostCount": lost_count,
            "openPipelineValueByCurrency": open_by_currency,
            "wonOpportunityValueByCurrency": won_by_currency,
            "lostOpportunityValueByCurrency": lost_by_currency,
            "byStage": stage_metrics,
            "labelingNotice": "Won Opportunity Value represents signed commercial commitments and does not represent collected cash or recognized accounting revenue."
        }

    def _get_opportunity_or_404(self, opp_id: str, for_update: bool = False) -> Opportunity:
        q = self.db.query(Opportunity).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        )
        if for_update:
            q = q.with_for_update(of=Opportunity)
        opp = q.first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")
        return opp

    def list_opportunity_quotations(self, opp_id: str) -> Dict[str, Any]:
        opp = self._get_opportunity_or_404(opp_id)
        quotes = (
            self.db.query(OpportunityQuotation)
            .options(
                joinedload(OpportunityQuotation.approved_by),
                joinedload(OpportunityQuotation.sent_by),
                joinedload(OpportunityQuotation.created_by),
                joinedload(OpportunityQuotation.updated_by)
            )
            .filter(OpportunityQuotation.opportunity_id == opp.id)
            .order_by(OpportunityQuotation.created_at.desc())
            .all()
        )
        formatted = [self._format_quotation(q) for q in quotes]
        active = next((f for f in formatted if f["isActive"]), None)
        return {
            "success": True,
            "count": len(formatted),
            "activeQuotation": active,
            "quotations": formatted
        }

    def get_quotation(self, opp_id: str, quotation_id: str) -> Dict[str, Any]:
        opp = self._get_opportunity_or_404(opp_id)
        q = self.db.query(OpportunityQuotation).options(
            joinedload(OpportunityQuotation.approved_by),
            joinedload(OpportunityQuotation.sent_by),
            joinedload(OpportunityQuotation.created_by),
            joinedload(OpportunityQuotation.updated_by)
        ).filter(
            OpportunityQuotation.opportunity_id == opp.id,
            or_(OpportunityQuotation.id == quotation_id, OpportunityQuotation.quotation_number == quotation_id)
        ).first()
        if not q:
            raise NotFoundError(f"Quotation '{quotation_id}' not found for Opportunity '{opp.opportunity_id}'.")
        return {"success": True, "quotation": self._format_quotation(q)}

    def create_opportunity_quotation(
        self,
        actor: CurrentUser,
        opp_id: str,
        payload: OpportunityQuotationCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        if not is_crm_admin_or_manager(actor):
            raise PermissionDeniedError("Only CRM Admin and CRM Manager have permission to create quotations.")

        opp = self._get_opportunity_or_404(opp_id, for_update=True)

        currency_val = (payload.currency or opp.currency or "INR").strip().upper()
        if currency_val not in APPROVED_CURRENCIES:
            raise ValidationError(f"Invalid currency '{currency_val}'. Approved currencies are: {', '.join(APPROVED_CURRENCIES)}")

        if payload.amount < 0:
            raise ValidationError("Quotation amount cannot be negative.")

        # Deactivate any existing active quotations for this opportunity
        existing_active = self.db.query(OpportunityQuotation).filter(
            OpportunityQuotation.opportunity_id == opp.id,
            OpportunityQuotation.is_active == True
        ).all()
        for eq in existing_active:
            eq.is_active = False
            if eq.status not in ("Superseded", "Accepted", "Rejected"):
                eq.status = "Superseded"

        quotation_num = get_next_sequence_id(self.db, "QUOTATION", "QT", padding=5, commit=False)

        q = OpportunityQuotation(
            quotation_number=quotation_num,
            opportunity_id=opp.id,
            revision_number=1,
            version="R1",
            is_active=True,
            title=(payload.title or f"Quotation for {opp.name}").strip(),
            status="Draft",
            amount=payload.amount,
            currency=currency_val,
            quotation_date=payload.quotationDate or date.today(),
            valid_until_date=payload.validUntilDate,
            terms_and_conditions=payload.termsAndConditions,
            notes=payload.notes,
            file_id=payload.fileId,
            document_name=payload.documentName,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(q)
        self.db.flush()
        if opp.stage == "Enquiry":
            record_opportunity_stage_transition(
                db=self.db,
                opp=opp,
                new_stage="Offer",
                triggering_event="FIRST_QUOTATION_CREATED",
                actor=actor,
                remarks=f"First quotation created: {q.quotation_number}",
                commit=False
            )
        self.db.commit()
        self.db.refresh(q)

        try:
            self.audit_service.log(
                action="CRM_QUOTATION_CREATED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "quotation_id": q.id,
                    "quotation_number": q.quotation_number,
                    "opportunity_id": opp.opportunity_id,
                    "version": q.version,
                    "amount": float(q.amount),
                    "currency": q.currency
                }
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for quotation creation {q.quotation_number}: {audit_err}")

        return self.get_quotation(opp.id, q.id)

    def update_opportunity_quotation(
        self,
        actor: CurrentUser,
        opp_id: str,
        quotation_id: str,
        payload: OpportunityQuotationUpdate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        if not is_crm_admin_or_manager(actor):
            raise PermissionDeniedError("Only CRM Admin and CRM Manager have permission to edit quotations.")

        opp = self._get_opportunity_or_404(opp_id)
        q = self.db.query(OpportunityQuotation).filter(
            OpportunityQuotation.opportunity_id == opp.id,
            or_(OpportunityQuotation.id == quotation_id, OpportunityQuotation.quotation_number == quotation_id)
        ).with_for_update(of=OpportunityQuotation).first()
        if not q:
            raise NotFoundError(f"Quotation '{quotation_id}' not found for Opportunity '{opp.opportunity_id}'.")

        if q.status in ("Superseded", "Accepted"):
            raise ValidationError(f"Quotation '{q.quotation_number}' is '{q.status}' and cannot be edited. Please create a new revision instead.")

        changes = {}
        approval_invalidated = False

        if payload.title is not None:
            clean_title = payload.title.strip()
            if clean_title != q.title:
                changes["title"] = {"old": q.title, "new": clean_title}
                q.title = clean_title

        if payload.amount is not None:
            if payload.amount < 0:
                raise ValidationError("Quotation amount cannot be negative.")
            if float(q.amount) != float(payload.amount):
                changes["amount"] = {"old": float(q.amount), "new": float(payload.amount)}
                q.amount = payload.amount
                if q.status == "Approved":
                    approval_invalidated = True

        if payload.currency is not None:
            clean_curr = payload.currency.strip().upper()
            if clean_curr not in APPROVED_CURRENCIES:
                raise ValidationError(f"Invalid currency '{clean_curr}'. Approved currencies are: {', '.join(APPROVED_CURRENCIES)}")
            if clean_curr != q.currency:
                changes["currency"] = {"old": q.currency, "new": clean_curr}
                q.currency = clean_curr
                if q.status == "Approved":
                    approval_invalidated = True

        if payload.quotationDate is not None and payload.quotationDate != q.quotation_date:
            changes["quotation_date"] = {"old": q.quotation_date.isoformat() if q.quotation_date else None, "new": payload.quotationDate.isoformat()}
            q.quotation_date = payload.quotationDate

        if payload.validUntilDate is not None and payload.validUntilDate != q.valid_until_date:
            changes["valid_until_date"] = {"old": q.valid_until_date.isoformat() if q.valid_until_date else None, "new": payload.validUntilDate.isoformat()}
            q.valid_until_date = payload.validUntilDate

        if payload.termsAndConditions is not None and payload.termsAndConditions != q.terms_and_conditions:
            changes["terms_and_conditions"] = {"old": q.terms_and_conditions, "new": payload.termsAndConditions}
            q.terms_and_conditions = payload.termsAndConditions
            if q.status == "Approved":
                approval_invalidated = True

        if payload.notes is not None and payload.notes != q.notes:
            changes["notes"] = {"old": q.notes, "new": payload.notes}
            q.notes = payload.notes

        if payload.fileId is not None and payload.fileId != q.file_id:
            changes["file_id"] = {"old": q.file_id, "new": payload.fileId}
            q.file_id = payload.fileId

        if payload.documentName is not None and payload.documentName != q.document_name:
            changes["document_name"] = {"old": q.document_name, "new": payload.documentName}
            q.document_name = payload.documentName

        if approval_invalidated:
            changes["status"] = {"old": "Approved", "new": "Draft", "reason": "Approval invalidated due to material edit"}
            q.status = "Draft"
            q.approved_by_id = None
            q.approved_at = None

        q.updated_by_id = str(actor.id) if actor.id else None
        q.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(q)

        try:
            self.audit_service.log(
                action="CRM_QUOTATION_UPDATED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "quotation_id": q.id,
                    "quotation_number": q.quotation_number,
                    "opportunity_id": opp.opportunity_id,
                    "changes": changes,
                    "approval_invalidated": approval_invalidated
                }
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for quotation update {q.quotation_number}: {audit_err}")

        return self.get_quotation(opp.id, q.id)

    def submit_quotation_for_review(
        self,
        actor: CurrentUser,
        opp_id: str,
        quotation_id: str,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        opp = self._get_opportunity_or_404(opp_id)
        q = self.db.query(OpportunityQuotation).filter(
            OpportunityQuotation.opportunity_id == opp.id,
            or_(OpportunityQuotation.id == quotation_id, OpportunityQuotation.quotation_number == quotation_id)
        ).with_for_update(of=OpportunityQuotation).first()
        if not q:
            raise NotFoundError(f"Quotation '{quotation_id}' not found for Opportunity '{opp.opportunity_id}'.")

        if q.status not in ("Draft", "Rejected"):
            raise ValidationError(f"Quotation '{q.quotation_number}' is in '{q.status}' status and cannot be submitted for internal review.")

        q.status = "Under Review"
        q.rejection_reason = None
        q.updated_by_id = str(actor.id) if actor.id else None
        q.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(q)

        try:
            self.audit_service.log(
                action="CRM_QUOTATION_SUBMITTED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "quotation_id": q.id,
                    "quotation_number": q.quotation_number,
                    "opportunity_id": opp.opportunity_id,
                    "status": q.status
                }
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for quotation submission {q.quotation_number}: {audit_err}")

        return self.get_quotation(opp.id, q.id)

    def approve_quotation(
        self,
        actor: CurrentUser,
        opp_id: str,
        quotation_id: str,
        payload: OpportunityQuotationApprovalRequest,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        user_roles = set(actor.roles or [])
        if actor.active_role:
            user_roles.add(actor.active_role)
        crm_roles = set(actor.module_roles.get("CRM", [])) if actor.module_roles else set()
        all_user_roles = user_roles.union(crm_roles)

        is_sales_manager = bool(
            actor.is_global_admin or
            "Admin" in all_user_roles or
            "SuperAdmin" in all_user_roles or
            "CRM_SALES_MANAGER" in all_user_roles
        )
        if not is_sales_manager:
            raise PermissionDeniedError("Only users with the CRM Sales Manager role are authorized to approve quotations.")

        opp = self._get_opportunity_or_404(opp_id)
        q = self.db.query(OpportunityQuotation).filter(
            OpportunityQuotation.opportunity_id == opp.id,
            or_(OpportunityQuotation.id == quotation_id, OpportunityQuotation.quotation_number == quotation_id)
        ).with_for_update(of=OpportunityQuotation).first()
        if not q:
            raise NotFoundError(f"Quotation '{quotation_id}' not found for Opportunity '{opp.opportunity_id}'.")

        action_type = payload.action.strip().lower()
        if action_type == "approve":
            if q.status not in ("Draft", "Internal Review", "Under Review"):
                raise ValidationError(f"Quotation '{q.quotation_number}' cannot be approved from '{q.status}' status.")
            q.status = "Approved"
            q.approved_by_id = str(actor.id) if actor.id else None
            q.approved_at = datetime.now(timezone.utc)
            q.rejection_reason = None
            audit_action = "CRM_QUOTATION_APPROVED"
        elif action_type == "reject":
            if not payload.reason or not payload.reason.strip():
                raise ValidationError("Rejection reason is mandatory when rejecting a quotation.")
            q.status = "Rejected"
            q.rejection_reason = payload.reason.strip()
            q.approved_by_id = None
            q.approved_at = None
            audit_action = "CRM_QUOTATION_REJECTED"
        else:
            raise ValidationError(f"Invalid approval action '{payload.action}'. Expected 'approve' or 'reject'.")

        q.updated_by_id = str(actor.id) if actor.id else None
        q.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(q)

        try:
            self.audit_service.log(
                action=audit_action,
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "quotation_id": q.id,
                    "quotation_number": q.quotation_number,
                    "opportunity_id": opp.opportunity_id,
                    "action": action_type,
                    "rejection_reason": q.rejection_reason
                }
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for quotation approval {q.quotation_number}: {audit_err}")

        return self.get_quotation(opp.id, q.id)

    def mark_quotation_shared(
        self,
        actor: CurrentUser,
        opp_id: str,
        quotation_id: str,
        payload: OpportunityQuotationShareRequest,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        opp = self._get_opportunity_or_404(opp_id)
        q = self.db.query(OpportunityQuotation).filter(
            OpportunityQuotation.opportunity_id == opp.id,
            or_(OpportunityQuotation.id == quotation_id, OpportunityQuotation.quotation_number == quotation_id)
        ).with_for_update(of=OpportunityQuotation).first()
        if not q:
            raise NotFoundError(f"Quotation '{quotation_id}' not found for Opportunity '{opp.opportunity_id}'.")

        if q.status != "Approved":
            raise ValidationError(f"Quotation '{q.quotation_number}' is in '{q.status}' status. Only Approved quotations may be shared externally with clients.")

        sent_method = payload.sentMethod.strip()
        sent_to = payload.sentTo.strip()
        if not sent_to:
            raise ValidationError("Recipient (sentTo) is mandatory when marking a quotation as shared.")

        q.status = "Shared"
        q.sent_method = sent_method
        q.sent_to = sent_to
        q.sent_at = datetime.now(timezone.utc)
        q.sent_by_id = str(actor.id) if actor.id else None
        q.sending_evidence = payload.sendingEvidence.strip() if payload.sendingEvidence else None
        q.updated_by_id = str(actor.id) if actor.id else None
        q.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(q)

        try:
            self.audit_service.log(
                action="CRM_QUOTATION_SHARED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "quotation_id": q.id,
                    "quotation_number": q.quotation_number,
                    "opportunity_id": opp.opportunity_id,
                    "sent_method": q.sent_method,
                    "sent_to": q.sent_to,
                    "sending_evidence": q.sending_evidence
                }
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for quotation shared {q.quotation_number}: {audit_err}")

        return self.get_quotation(opp.id, q.id)

    def revise_opportunity_quotation(
        self,
        actor: CurrentUser,
        opp_id: str,
        quotation_id: str,
        payload: OpportunityQuotationCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        if not is_crm_admin_or_manager(actor):
            raise PermissionDeniedError("Only CRM Admin and CRM Manager have permission to revise quotations.")

        opp = self._get_opportunity_or_404(opp_id, for_update=True)
        base_q = self.db.query(OpportunityQuotation).filter(
            OpportunityQuotation.opportunity_id == opp.id,
            or_(OpportunityQuotation.id == quotation_id, OpportunityQuotation.quotation_number == quotation_id)
        ).with_for_update(of=OpportunityQuotation).first()
        if not base_q:
            raise NotFoundError(f"Quotation '{quotation_id}' not found for Opportunity '{opp.opportunity_id}'.")

        currency_val = (payload.currency or base_q.currency or opp.currency or "INR").strip().upper()
        if currency_val not in APPROVED_CURRENCIES:
            raise ValidationError(f"Invalid currency '{currency_val}'. Approved currencies are: {', '.join(APPROVED_CURRENCIES)}")

        if payload.amount < 0:
            raise ValidationError("Quotation amount cannot be negative.")

        # Supersede base quotation and deactivate all existing active quotations
        existing_active = self.db.query(OpportunityQuotation).filter(
            OpportunityQuotation.opportunity_id == opp.id,
            OpportunityQuotation.is_active == True
        ).all()
        for eq in existing_active:
            eq.is_active = False
            if eq.status not in ("Superseded", "Accepted", "Rejected"):
                eq.status = "Superseded"

        next_rev_num = base_q.revision_number + 1
        ver_label = f"R{next_rev_num}"

        revised_q = OpportunityQuotation(
            quotation_number=base_q.quotation_number,
            opportunity_id=opp.id,
            revision_number=next_rev_num,
            version=ver_label,
            is_active=True,
            title=(payload.title or base_q.title or f"Quotation for {opp.name}").strip(),
            status="Draft",
            amount=payload.amount if payload.amount is not None and payload.amount > 0 else base_q.amount,
            subtotal=base_q.subtotal,
            tax_type=base_q.tax_type,
            tax_configuration_id=base_q.tax_configuration_id,
            cgst_amount=base_q.cgst_amount,
            sgst_amount=base_q.sgst_amount,
            igst_amount=base_q.igst_amount,
            total_tax=base_q.total_tax,
            discount_amount=base_q.discount_amount,
            currency=currency_val,
            quotation_date=payload.quotationDate or date.today(),
            valid_until_date=payload.validUntilDate or base_q.valid_until_date,
            terms_and_conditions=payload.termsAndConditions if payload.termsAndConditions is not None else base_q.terms_and_conditions,
            notes=payload.notes if payload.notes is not None else base_q.notes,
            file_id=payload.fileId if payload.fileId is not None else base_q.file_id,
            document_name=payload.documentName if payload.documentName is not None else base_q.document_name,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(revised_q)
        self.db.flush()

        # Copy line items over from base_q to revised_q to preserve commercial continuity
        item_id_map = {}
        for base_item in base_q.items:
            new_item = OpportunityQuotationItem(
                quotation_id=revised_q.id,
                item_type=base_item.item_type,
                service_id=base_item.service_id,
                package_id=base_item.package_id,
                package_version_id=base_item.package_version_id,
                item_code=base_item.item_code,
                item_name=base_item.item_name,
                description=base_item.description,
                billing_unit=base_item.billing_unit,
                quantity=base_item.quantity,
                standard_price=base_item.standard_price,
                unit_price=base_item.unit_price,
                discount_amount=base_item.discount_amount,
                total_price=base_item.total_price,
                currency=base_item.currency,
                testing_method_snapshot=base_item.testing_method_snapshot,
                reporting_parameters_snapshot=base_item.reporting_parameters_snapshot,
                package_components_snapshot=base_item.package_components_snapshot,
                tax_configuration_id=base_item.tax_configuration_id,
                tax_type=base_item.tax_type,
                taxable_amount=base_item.taxable_amount,
                cgst_rate=base_item.cgst_rate,
                cgst_amount=base_item.cgst_amount,
                sgst_rate=base_item.sgst_rate,
                sgst_amount=base_item.sgst_amount,
                igst_rate=base_item.igst_rate,
                igst_amount=base_item.igst_amount,
                total_tax=base_item.total_tax,
                final_total=base_item.final_total
            )
            self.db.add(new_item)
            self.db.flush()
            item_id_map[base_item.id] = new_item.id

        # Remap parent_item_id on copied child add-on items
        for base_item in base_q.items:
            if base_item.parent_item_id and base_item.parent_item_id in item_id_map:
                new_item_id = item_id_map[base_item.id]
                new_parent_id = item_id_map[base_item.parent_item_id]
                copied_item = self.db.query(OpportunityQuotationItem).filter(OpportunityQuotationItem.id == new_item_id).first()
                if copied_item:
                    copied_item.parent_item_id = new_parent_id

        if opp.stage in ("Enquiry", "Offer"):
            record_opportunity_stage_transition(
                db=self.db,
                opp=opp,
                new_stage="Negotiation",
                triggering_event="COMMERCIAL_QUOTATION_REVISED",
                actor=actor,
                remarks=f"Commercial quotation revised to {revised_q.version}",
                commit=False
            )

        self.db.commit()
        self.db.refresh(revised_q)

        try:
            self.audit_service.log(
                action="CRM_QUOTATION_REVISED",
                request=request,
                performed_by_employee_id=str(actor.id) if actor.id else None,
                performed_by_name=actor.name or actor.username,
                role_used=actor.active_role,
                target_info={
                    "quotation_id": revised_q.id,
                    "quotation_number": revised_q.quotation_number,
                    "previous_revision": base_q.revision_number,
                    "new_revision": revised_q.revision_number,
                    "version": revised_q.version,
                    "opportunity_id": opp.opportunity_id,
                    "amount": float(revised_q.amount),
                    "currency": revised_q.currency
                }
            )
        except Exception as audit_err:
            logger.warning(f"Audit log failed for quotation revision {revised_q.quotation_number}: {audit_err}")

        return self.get_quotation(opp.id, revised_q.id)

    # =========================================================================
    # 5. COMMUNICATION HISTORY SERVICES
    # =========================================================================

    def list_communications(self, lead_id: str) -> List[Dict[str, Any]]:
        lead = self.db.query(Lead).filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id)).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        comms = (
            self.db.query(LeadCommunicationHistory)
            .options(joinedload(LeadCommunicationHistory.created_by))
            .filter(LeadCommunicationHistory.lead_id == lead.id)
            .order_by(LeadCommunicationHistory.communication_date.desc())
            .all()
        )

        return [
            {
                "id": c.id,
                "communicationId": c.communication_id,
                "leadId": lead.lead_id,
                "communicationDate": c.communication_date.isoformat(),
                "channel": c.channel,
                "eventType": c.event_type,
                "summary": c.summary,
                "outcome": c.outcome,
                "nextAction": c.next_action,
                "followUpDate": c.follow_up_date.isoformat() if c.follow_up_date else None,
                "createdById": c.created_by_id,
                "createdByName": c.created_by.name if c.created_by else None,
                "createdAt": c.created_at.isoformat() if c.created_at else None
            }
            for c in comms
        ]

    def create_communication(
        self,
        actor: CurrentUser,
        lead_id: str,
        payload: CommunicationCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        lead = self.db.query(Lead).filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id)).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        comm_code = get_next_sequence_id(self.db, "COMMUNICATION", "COM")
        comm_date = payload.date or datetime.now(timezone.utc)

        comm = LeadCommunicationHistory(
            communication_id=comm_code,
            lead_id=lead.id,
            communication_date=comm_date,
            channel=payload.channel,
            event_type=payload.eventType,
            subject=payload.eventType,
            summary=payload.summary.strip() if payload.summary else None,
            outcome=payload.outcome.strip() if payload.outcome else None,
            next_action=payload.nextAction.strip() if payload.nextAction else None,
            follow_up_date=payload.followUpDate,
            interaction_source="Manual",
            created_by_id=str(actor.id) if actor.id else None,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(comm)

        if is_qualifying_client_interaction(payload.eventType):
            lead.last_connected_date = comm_date

        if payload.followUpDate:
            lead.next_follow_up_date = payload.followUpDate
        if payload.nextAction:
            lead.next_follow_up_action = payload.nextAction.strip()

        if payload.summary:
            lead.remarks = f"{payload.eventType.strip()}: {payload.summary.strip()}"

        lead.updated_by_id = str(actor.id) if actor.id else None
        self.db.commit()
        self.db.refresh(comm)

        self.audit_service.log(
            action="CRM_COMMUNICATION_LOGGED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=actor.active_role,
            target_info={
                "recordId": comm.id,
                "communicationCode": comm.communication_id,
                "leadId": lead.lead_id,
                "channel": comm.channel,
                "eventType": comm.event_type,
                "details": f"Logged {comm.channel} interaction ({comm.event_type}) for Lead {lead.lead_id}."
            }
        )

        return {
            "id": comm.id,
            "communicationId": comm.communication_id,
            "leadId": lead.lead_id,
            "communicationDate": comm.communication_date.isoformat(),
            "channel": comm.channel,
            "eventType": comm.event_type,
            "summary": comm.summary,
            "outcome": comm.outcome,
            "nextAction": comm.next_action,
            "followUpDate": comm.follow_up_date.isoformat() if comm.follow_up_date else None,
            "createdById": comm.created_by_id,
            "createdByName": actor.name or actor.username,
            "createdAt": comm.created_at.isoformat() if comm.created_at else None
        }

    def list_opportunity_communications(self, opp_id: str) -> List[Dict[str, Any]]:
        opp = self.db.query(Opportunity).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")

        filters = [LeadCommunicationHistory.opportunity_id == opp.id]
        if opp.originating_lead_id:
            filters.append(LeadCommunicationHistory.lead_id == opp.originating_lead_id)

        comms = (
            self.db.query(LeadCommunicationHistory)
            .options(
                joinedload(LeadCommunicationHistory.created_by),
                joinedload(LeadCommunicationHistory.lead)
            )
            .filter(or_(*filters))
            .order_by(LeadCommunicationHistory.communication_date.asc())
            .all()
        )

        return [
            {
                "id": c.id,
                "communicationId": c.communication_id,
                "opportunityId": opp.opportunity_id,
                "leadId": c.lead.lead_id if c.lead else None,
                "communicationDate": c.communication_date.isoformat(),
                "channel": c.channel,
                "eventType": c.event_type,
                "subject": c.subject or c.event_type,
                "summary": c.summary,
                "outcome": c.outcome,
                "nextAction": c.next_action,
                "followUpDate": c.follow_up_date.isoformat() if c.follow_up_date else None,
                "createdById": c.created_by_id,
                "createdByName": c.created_by.name if c.created_by else None,
                "createdAt": c.created_at.isoformat() if c.created_at else None
            }
            for c in comms
        ]

    def create_opportunity_communication(
        self,
        actor: CurrentUser,
        opp_id: str,
        payload: CommunicationCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        opp = self.db.query(Opportunity).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")

        comm_code = get_next_sequence_id(self.db, "COMMUNICATION", "COM")
        comm_date = payload.date or datetime.now(timezone.utc)
        subject = payload.subject or payload.eventType

        comm = LeadCommunicationHistory(
            communication_id=comm_code,
            opportunity_id=opp.id,
            lead_id=opp.originating_lead_id,
            communication_date=comm_date,
            channel=payload.channel,
            event_type=payload.eventType,
            subject=subject,
            summary=payload.summary.strip() if payload.summary else None,
            outcome=payload.outcome.strip() if payload.outcome else None,
            next_action=payload.nextAction.strip() if payload.nextAction else None,
            follow_up_date=payload.followUpDate,
            interaction_source="Manual",
            created_by_id=str(actor.id) if actor.id else None,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(comm)
        self.db.commit()
        self.db.refresh(comm)

        self.audit_service.log(
            action="CRM_COMMUNICATION_LOGGED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=actor.active_role,
            target_info={
                "recordId": comm.id,
                "communicationCode": comm.communication_id,
                "opportunityId": opp.opportunity_id,
                "channel": comm.channel,
                "eventType": comm.event_type,
                "details": f"Logged {comm.channel} interaction ({comm.event_type}) for Opportunity {opp.opportunity_id}."
            }
        )

        return {
            "id": comm.id,
            "communicationId": comm.communication_id,
            "opportunityId": opp.opportunity_id,
            "leadId": opp.originating_lead.lead_id if opp.originating_lead else None,
            "communicationDate": comm.communication_date.isoformat(),
            "channel": comm.channel,
            "eventType": comm.event_type,
            "subject": comm.subject,
            "summary": comm.summary,
            "outcome": comm.outcome,
            "nextAction": comm.next_action,
            "followUpDate": comm.follow_up_date.isoformat() if comm.follow_up_date else None,
            "createdById": comm.created_by_id,
            "createdByName": actor.name or actor.username,
            "createdAt": comm.created_at.isoformat() if comm.created_at else None
        }

    # =========================================================================
    # 6. DASHBOARD METRICS & ASSIGNEES
    # =========================================================================

    def get_dashboard_metrics(self, actor: CurrentUser) -> Dict[str, Any]:
        total_leads = self.db.query(func.count(Lead.id)).scalar() or 0
        open_leads = self.db.query(func.count(Lead.id)).filter(
            Lead.lifecycle_status.in_(["New", "Contacted", "In Discussion"]),
            Lead.lifecycle_status != "Qualified",
            Lead.qualified_at.is_(None),
            Lead.opportunity_id.is_(None)
        ).scalar() or 0
        qualified_leads = self.db.query(func.count(Lead.id)).filter(
            or_(
                Lead.qualified_at.isnot(None),
                Lead.opportunity_id.isnot(None),
                Lead.lifecycle_status == "Qualified"
            )
        ).scalar() or 0
        disqualified_leads = self.db.query(func.count(Lead.id)).filter(
            Lead.lifecycle_status.in_(["Dormant", "Disqualified"])
        ).scalar() or 0

        my_leads = 0
        if actor and actor.id:
            my_leads = self.db.query(func.count(Lead.id)).filter(Lead.assigned_to_user_id == str(actor.id)).scalar() or 0

        KOLKATA_TZ = zoneinfo.ZoneInfo("Asia/Kolkata")
        today_ist = datetime.now(KOLKATA_TZ).date()
        due_window = today_ist + timedelta(days=1)
        follow_ups_due = self.db.query(func.count(Lead.id)).filter(
            Lead.lifecycle_status.notin_(["Dormant", "Disqualified"]),
            Lead.next_follow_up_date.isnot(None),
            Lead.next_follow_up_date <= due_window
        ).scalar() or 0

        overdue_follow_ups = self.db.query(func.count(Lead.id)).filter(
            Lead.lifecycle_status.notin_(["Dormant", "Disqualified"]),
            Lead.next_follow_up_date.isnot(None),
            Lead.next_follow_up_date < today_ist
        ).scalar() or 0

        # Sales Funnel Metrics
        quotations_created = self.db.query(func.count(func.distinct(OpportunityQuotation.opportunity_id))).scalar() or 0
        pis_created = self.db.query(func.count(func.distinct(ProformaInvoice.opportunity_id))).scalar() or 0

        lead_to_qual_rate = round((qualified_leads / total_leads * 100), 1) if total_leads > 0 else 0.0
        qual_to_quote_rate = round((quotations_created / qualified_leads * 100), 1) if qualified_leads > 0 else 0.0
        quote_to_pi_rate = round((pis_created / quotations_created * 100), 1) if quotations_created > 0 else 0.0
        overall_lead_to_pi_rate = round((pis_created / total_leads * 100), 1) if total_leads > 0 else 0.0

        stage_counts = {}
        for stg in OPPORTUNITY_STAGES:
            cnt = self.db.query(func.count(Opportunity.id)).filter(Opportunity.stage == stg).scalar() or 0
            stage_counts[stg] = cnt

        return {
            "success": True,
            "totalLeads": total_leads,
            "openLeads": open_leads,
            "qualifiedLeads": qualified_leads,
            "disqualifiedLeads": disqualified_leads,
            "myLeads": my_leads,
            "followUpsDue": follow_ups_due,
            "overdueFollowUps": overdue_follow_ups,
            "quotationsCreated": quotations_created,
            "pisCreated": pis_created,
            "leadToQualificationRate": lead_to_qual_rate,
            "qualificationToQuotationRate": qual_to_quote_rate,
            "quotationToPiRate": quote_to_pi_rate,
            "overallLeadToPiRate": overall_lead_to_pi_rate,
            "opportunityCountByStage": stage_counts
        }

    def list_eligible_assignees(self) -> List[Dict[str, Any]]:
        crm_mod = self._get_crm_module()
        memberships = (
            self.db.query(UserModuleMembership)
            .options(joinedload(UserModuleMembership.user), joinedload(UserModuleMembership.role))
            .filter(UserModuleMembership.module_id == crm_mod.id, UserModuleMembership.is_active == True)
            .all()
        )

        assignees = []
        for m in memberships:
            u = m.user
            if u and not u.is_hard_deleted and u.status == "active":
                if m.role and m.role.code.startswith("CRM_"):
                    assignees.append({
                        "id": u.id,
                        "name": u.name or u.username,
                        "username": u.username,
                        "email": u.email,
                        "roleCode": m.role.code,
                        "roleName": m.role.name
                    })

        assignees.sort(key=lambda x: x["name"])
        return assignees

    # =========================================================================
    # 7. CHARGE-READY BUSINESS DOMAIN SERVICES (PHASE 1 SPECIFICATION)
    # =========================================================================

    def create_consulting_engagement(
        self,
        actor: CurrentUser,
        payload: ConsultingEngagementCreate
    ) -> ConsultingEngagement:
        acc = self.db.query(Account).filter(Account.id == payload.accountId).first()
        if not acc:
            raise NotFoundError(f"Account '{payload.accountId}' not found.")

        eng_code = get_next_sequence_id(self.db, "ENGAGEMENT", "ENG")
        engagement = ConsultingEngagement(
            engagement_id=eng_code,
            account_id=acc.id,
            contact_id=payload.contactId,
            lead_id=payload.leadId,
            title=payload.title,
            scope_description=payload.scopeDescription,
            contract_start_date=payload.contractStartDate,
            contract_end_date=payload.contractEndDate,
            duration_months=payload.durationMonths,
            agreed_fee=Decimal(str(payload.agreedFee)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            billing_arrangement=payload.billingArrangement or "Monthly",
            status=payload.status or "Draft"
        )
        self.db.add(engagement)
        self.db.commit()
        self.db.refresh(engagement)
        return engagement

    def create_sample_submission(
        self,
        actor: CurrentUser,
        payload: SampleSubmissionCreate
    ) -> SampleSubmission:
        acc = self.db.query(Account).filter(Account.id == payload.accountId).first()
        if not acc:
            raise NotFoundError(f"Account '{payload.accountId}' not found.")

        smp_code = get_next_sequence_id(self.db, "SAMPLE", "SMP")
        sample = SampleSubmission(
            sample_id=smp_code,
            account_id=acc.id,
            contact_id=payload.contactId,
            lead_id=payload.leadId,
            sample_description=payload.sampleDescription,
            sample_type=payload.sampleType,
            receipt_date=payload.receiptDate or date.today(),
            condition_on_receipt=payload.conditionOnReceipt or "Good",
            status="Received",
            sample_level_charge=Decimal(str(payload.sampleLevelCharge)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            notes=payload.notes
        )

        for t_input in payload.tests:
            tst_code = get_next_sequence_id(self.db, "TEST", "TST")
            unit_price = Decimal(str(t_input.unitPrice)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            qty = Decimal(str(t_input.quantity)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            sample.tests.append(SampleTestRequest(
                test_record_id=tst_code,
                test_name=t_input.testName,
                test_type=t_input.testType,
                unit_price=unit_price,
                quantity=qty,
                notes=t_input.notes
            ))

        self.db.add(sample)
        self.db.commit()
        self.db.refresh(sample)
        return sample

    def calculate_testing_charges(
        self,
        sample_level_charge: Decimal,
        test_items: List[Tuple[Decimal, Decimal]],  # [(unit_price, quantity), ...]
        additional_charges: Decimal = Decimal("0.00"),
        discounts: Decimal = Decimal("0.00")
    ) -> Dict[str, Decimal]:
        """
        Total testing charges = applicable sample-level charges + sum of individual test charges + approved additional charges - applicable discounts.
        Strict decimal precision with bankers / standard rounding.
        """
        sample_charge = Decimal(str(sample_level_charge)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tests_sum = Decimal("0.00")
        for unit_price, qty in test_items:
            p = Decimal(str(unit_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            q = Decimal(str(qty)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            tests_sum += (p * q).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        add = Decimal(str(additional_charges)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        disc = Decimal(str(discounts)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        total = sample_charge + tests_sum + add - disc
        if total < Decimal("0.00"):
            total = Decimal("0.00")

        return {
            "sample_charge": sample_charge,
            "tests_total": tests_sum,
            "additional_charges": add,
            "discounts": disc,
            "final_total": total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        }

    def record_testing_charge(
        self,
        actor: CurrentUser,
        sample_id: str,
        additional_charges: Decimal = Decimal("0.00"),
        discounts: Decimal = Decimal("0.00"),
        idempotency_key: Optional[str] = None
    ) -> TestingChargeRecord:
        if idempotency_key:
            existing = self.db.query(TestingChargeRecord).filter(TestingChargeRecord.idempotency_key == idempotency_key).first()
            if existing:
                return existing

        sample = self.db.query(SampleSubmission).options(joinedload(SampleSubmission.tests)).filter(
            or_(SampleSubmission.id == sample_id, SampleSubmission.sample_id == sample_id)
        ).first()
        if not sample:
            raise NotFoundError(f"Sample '{sample_id}' not found.")

        test_items = [(t.unit_price, t.quantity) for t in sample.tests]
        calc = self.calculate_testing_charges(
            sample_level_charge=sample.sample_level_charge,
            test_items=test_items,
            additional_charges=additional_charges,
            discounts=discounts
        )

        chg_code = get_next_sequence_id(self.db, "CHARGE", "CHG")
        charge = TestingChargeRecord(
            charge_id=chg_code,
            sample_id=sample.id,
            lead_id=sample.lead_id,
            account_id=sample.account_id,
            sample_charge_applied=calc["sample_charge"],
            tests_total=calc["tests_total"],
            approved_additional_charges=calc["additional_charges"],
            applicable_discounts=calc["discounts"],
            final_calculated_total=calc["final_total"],
            currency="INR",
            billing_status="Pending",
            idempotency_key=idempotency_key
        )
        self.db.add(charge)
        self.db.commit()
        self.db.refresh(charge)
        return charge

    def create_product_transaction(
        self,
        actor: CurrentUser,
        payload: ProductTransactionCreate
    ) -> ProductTransaction:
        acc = self.db.query(Account).filter(Account.id == payload.accountId).first()
        if not acc:
            raise NotFoundError(f"Account '{payload.accountId}' not found.")

        qty = Decimal(str(payload.quantity)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rate = Decimal(str(payload.unitRate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        disc = Decimal(str(payload.discountAmount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total = (qty * rate - disc).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if total < Decimal("0.00"):
            total = Decimal("0.00")

        prd_code = get_next_sequence_id(self.db, "PRODUCT_TX", "PRD")
        tx = ProductTransaction(
            transaction_id=prd_code,
            lead_id=payload.leadId,
            account_id=acc.id,
            contact_id=payload.contactId,
            product_name=payload.productName,
            sku_code=payload.skuCode,
            transaction_type=payload.transactionType or "Recommendation",
            status=payload.status or "Pending",
            quantity=qty,
            unit_of_measure=payload.unitOfMeasure or "litres",
            unit_rate=rate,
            discount_amount=disc,
            calculated_amount=total,
            currency=payload.currency or "INR",
            notes=payload.notes
        )
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)
        return tx


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS FOR CHARGE-READY OPERATIONS
# =============================================================================

def create_consulting_engagement(
    db: Session,
    actor: Any = None,
    payload: Any = None,
    engagement_data: Optional[Dict[str, Any]] = None
) -> ConsultingEngagement:
    if engagement_data and not payload:
        eng_code = get_next_sequence_id(db, "ENGAGEMENT", "ENG")
        engagement = ConsultingEngagement(
            engagement_id=eng_code,
            lead_id=engagement_data.get("lead_id"),
            account_id=engagement_data.get("account_id"),
            contact_id=engagement_data.get("contact_id"),
            title=engagement_data.get("title") or engagement_data.get("duration_description") or "Consulting Engagement",
            contract_start_date=engagement_data.get("contract_start_date"),
            contract_end_date=engagement_data.get("contract_end_date"),
            duration_description=engagement_data.get("duration_description"),
            agreed_fee=Decimal(str(engagement_data.get("agreed_fee", 0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            billing_arrangement=engagement_data.get("billing_arrangement", "Configurable"),
            status=engagement_data.get("status", "Active"),
            notes=engagement_data.get("notes")
        )
        db.add(engagement)
        db.commit()
        db.refresh(engagement)
        return engagement
    srv = CRMService(db)
    return srv.create_consulting_engagement(actor, payload)


def create_sample_submission(
    db: Session,
    actor: Any = None,
    payload: Any = None,
    sample_data: Optional[Dict[str, Any]] = None,
    tests_data: Optional[List[Dict[str, Any]]] = None
) -> SampleSubmission:
    if sample_data and not payload:
        smp_code = get_next_sequence_id(db, "SAMPLE", "SMP")
        sample = SampleSubmission(
            sample_id=smp_code,
            lead_id=sample_data.get("lead_id"),
            account_id=sample_data.get("account_id"),
            contact_id=sample_data.get("contact_id"),
            sample_description=sample_data.get("sample_description"),
            sample_type=sample_data.get("sample_type"),
            receipt_date=sample_data.get("receipt_date", date.today()),
            condition_on_receipt=sample_data.get("sample_condition") or sample_data.get("condition_on_receipt") or "Good",
            status=sample_data.get("sample_status") or sample_data.get("status") or "Received",
            sample_level_charge=Decimal(str(sample_data.get("sample_charge") or sample_data.get("sample_level_charge") or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            failure_reason=sample_data.get("failure_reason"),
            stage_reached=sample_data.get("stage_reached"),
            work_performed=sample_data.get("work_performed_notes") or sample_data.get("work_performed"),
            charge_decision=sample_data.get("charge_decision"),
            authorized_charge_amount=Decimal(str(sample_data.get("chargeable_amount") or sample_data.get("authorized_charge_amount") or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if (sample_data.get("chargeable_amount") is not None or sample_data.get("authorized_charge_amount") is not None) else None,
            replacement_of_sample_id=sample_data.get("replacement_for_sample_id") or sample_data.get("replacement_of_sample_id"),
            notes=sample_data.get("notes")
        )
        if tests_data:
            for t_item in tests_data:
                tst_code = get_next_sequence_id(db, "TEST", "TST")
                sample.requested_tests.append(SampleTestRequest(
                    test_record_id=tst_code,
                    test_name=t_item.get("test_name", t_item.get("test_type", "Standard Test")),
                    test_type=t_item.get("test_type", "Standard"),
                    unit_price=Decimal(str(t_item.get("test_rate") or t_item.get("unit_price") or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                    quantity=Decimal(str(t_item.get("billable_units") or t_item.get("quantity") or 1)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                    notes=t_item.get("notes")
                ))
        db.add(sample)
        db.commit()
        db.refresh(sample)
        return sample
    srv = CRMService(db)
    return srv.create_sample_submission(actor, payload)


def calculate_testing_charges(
    db: Session,
    sample_submission_id: Optional[str] = None,
    sample_level_charge: Optional[Decimal] = None,
    test_items: Any = None,
    additional_charge: Decimal = Decimal("0.00"),
    additional_charges: Decimal = Decimal("0.00"),
    discount_amount: Decimal = Decimal("0.00"),
    discounts: Decimal = Decimal("0.00")
) -> Dict[str, Decimal]:
    if sample_submission_id:
        sub = db.query(SampleSubmission).filter(SampleSubmission.id == sample_submission_id).first()
        if not sub:
            raise NotFoundError(f"SampleSubmission '{sample_submission_id}' not found.")
        s_charge = Decimal(str(sub.sample_charge or 0.0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        test_sum = Decimal("0.00")
        for t in sub.requested_tests:
            rate = Decimal(str(t.test_rate or 0.0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            units = Decimal(str(t.billable_units or 1)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            test_sum += (rate * units).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        add = Decimal(str(additional_charge or additional_charges or 0.0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        disc = Decimal(str(discount_amount or discounts or 0.0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total = s_charge + test_sum + add - disc
        if total < Decimal("0.00"):
            total = Decimal("0.00")
        return {
            "sample_level_charge": s_charge,
            "sum_of_test_charges": test_sum,
            "additional_charges": add,
            "discounts": disc,
            "total_charge": total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        }
    srv = CRMService(db)
    return srv.calculate_testing_charges(sample_level_charge, test_items, additional_charges, discounts)


def record_testing_charge(
    db: Session,
    actor: Any = None,
    sample_submission_id: Optional[str] = None,
    sample_id: Optional[str] = None,
    test_request_id: Optional[str] = None,
    charge_type: str = "TEST_CHARGE",
    description: Optional[str] = None,
    charge_amount: Optional[Decimal] = None,
    agreed_unit_rate: Optional[Decimal] = None,
    billable_units: int = 1,
    idempotency_key: Optional[str] = None,
    applied_by_user_id: Optional[str] = None,
    additional_charges: Decimal = Decimal("0.00"),
    discounts: Decimal = Decimal("0.00")
) -> TestingChargeRecord:
    sid = sample_submission_id or sample_id
    sub = db.query(SampleSubmission).filter(SampleSubmission.id == sid).first()
    if not sub:
        raise NotFoundError(f"SampleSubmission '{sid}' not found.")
    if idempotency_key:
        existing = db.query(TestingChargeRecord).filter(TestingChargeRecord.idempotency_key == idempotency_key).first()
        if existing:
            return existing
    chg_code = get_next_sequence_id(db, "CHARGE", "CHG")
    charge = TestingChargeRecord(
        charge_id=chg_code,
        sample_id=sub.id,
        lead_id=sub.lead_id,
        account_id=sub.account_id,
        sample_charge_applied=sub.sample_charge or Decimal("0.00"),
        tests_total=charge_amount or Decimal("0.00"),
        approved_additional_charges=additional_charges,
        applicable_discounts=discounts,
        final_calculated_total=charge_amount or Decimal("0.00"),
        agreed_unit_rate=agreed_unit_rate or Decimal("0.00"),
        charge_amount=charge_amount or Decimal("0.00"),
        currency="INR",
        billing_status="PENDING",
        idempotency_key=idempotency_key,
        notes=f"Applied by user: {applied_by_user_id}" if applied_by_user_id else None
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


def create_product_transaction(
    db: Session,
    actor: Any = None,
    payload: Any = None,
    product_data: Optional[Dict[str, Any]] = None
) -> ProductTransaction:
    if product_data and not payload:
        acc = db.query(Account).filter(Account.id == product_data["account_id"]).first()
        if not acc:
            raise NotFoundError(f"Account '{product_data['account_id']}' not found.")
        qty = Decimal(str(product_data.get("quantity", 0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rate = Decimal(str(product_data.get("unit_rate", 0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        disc = Decimal(str(product_data.get("discount_amount", 0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total = (qty * rate - disc).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if total < Decimal("0.00"):
            total = Decimal("0.00")
        prd_code = get_next_sequence_id(db, "PRODUCT_TX", "PRD")
        tx = ProductTransaction(
            transaction_id=prd_code,
            lead_id=product_data.get("lead_id"),
            account_id=acc.id,
            contact_id=product_data.get("contact_id"),
            product_reference=product_data.get("product_reference"),
            status=product_data.get("status", "RECOMMENDED"),
            quantity=qty,
            unit_of_measure=product_data.get("unit_of_measure", "litres"),
            unit_rate=rate,
            discount_amount=disc,
            calculated_amount=total,
            currency=product_data.get("currency", "INR"),
            notes=product_data.get("notes")
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx
    srv = CRMService(db)
    return srv.create_product_transaction(actor, payload)
