import logging
import threading
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from fastapi import Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import CurrentUser
from app.core.exceptions import (
    PermissionDeniedError,
    ValidationError,
    NotFoundError,
    ConflictError
)
from app.users.model import User
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
    ProductTransaction
)
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


_sequence_lock = threading.Lock()


def get_next_sequence_id(db: Session, entity_name: str, prefix: str, padding: int = 5) -> str:
    """
    Concurrency-safe sequence generator using CrmSequence with thread locking and row locking.
    Generates IDs like LEAD-00001, ACC-00001, CON-00001, COM-00001, ENG-00001, SMP-00001, TST-00001, CHG-00001, PRD-00001.
    """
    entity_key = entity_name.strip().upper()
    with _sequence_lock:
        seq = db.query(CrmSequence).filter(CrmSequence.entity_name == entity_key).with_for_update().first()
        if not seq:
            try:
                seq = CrmSequence(entity_name=entity_key, current_value=1)
                db.add(seq)
                db.commit()
                return f"{prefix}-{1:0{padding}d}"
            except IntegrityError:
                db.rollback()
                seq = db.query(CrmSequence).filter(CrmSequence.entity_name == entity_key).with_for_update().first()

        seq.current_value += 1
        db.commit()
        return f"{prefix}-{seq.current_value:0{padding}d}"


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
    ) -> List[Dict[str, Any]]:
        query = self.db.query(Account)
        if search:
            s = f"%{search.strip().lower()}%"
            query = query.filter(
                (func.lower(Account.name).like(s)) |
                (func.lower(Account.account_id).like(s)) |
                (func.lower(Account.industry).like(s)) |
                (func.lower(Account.website).like(s)) |
                (func.lower(Account.phone).like(s)) |
                (func.lower(Account.email).like(s))
            )

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

        return [
            {
                "id": a.id,
                "accountId": a.account_id,
                "name": a.name,
                "industry": a.industry,
                "website": a.website,
                "phone": a.phone,
                "email": a.email,
                "address": a.address,
                "isActive": a.is_active,
                "contactCount": contact_counts.get(a.id, 0),
                "leadCount": lead_counts.get(a.id, 0),
                "createdAt": a.created_at.isoformat() if a.created_at else None,
                "updatedAt": a.updated_at.isoformat() if a.updated_at else None
            }
            for a in accounts
        ]

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

        return {
            "account": {
                "id": acc.id,
                "accountId": acc.account_id,
                "name": acc.name,
                "industry": acc.industry,
                "website": acc.website,
                "phone": acc.phone,
                "email": acc.email,
                "address": acc.address,
                "isActive": acc.is_active,
                "contactCount": len(contacts),
                "leadCount": len(leads),
                "contacts": contacts_list,
                "leads": leads_list,
                "createdAt": acc.created_at.isoformat() if acc.created_at else None,
                "updatedAt": acc.updated_at.isoformat() if acc.updated_at else None
            },
            "contacts": contacts_list,
            "leads": leads_list
        }

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
        if existing:
            raise ConflictError(
                message=f"An active account with name '{existing.name}' already exists ({existing.account_id}).",
                details={"existingAccountId": existing.id, "existingAccountNumber": existing.account_id}
            )

        account_code = get_next_sequence_id(self.db, "ACCOUNT", "ACC")
        account = Account(
            account_id=account_code,
            name=payload.name.strip(),
            industry=payload.industry.strip() if payload.industry else None,
            website=payload.website.strip() if payload.website else None,
            phone=payload.phone.strip() if payload.phone else None,
            email=payload.email.strip() if payload.email else None,
            address=payload.address.strip() if payload.address else None,
            is_active=True
        )

        try:
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
        except IntegrityError:
            self.db.rollback()
            collision = self.db.query(Account).filter(func.lower(func.trim(Account.name)) == norm_name).first()
            if collision:
                raise ConflictError(
                    message=f"An active account with name '{collision.name}' already exists ({collision.account_id}).",
                    details={"existingAccountId": collision.id, "existingAccountNumber": collision.account_id}
                )
            raise ValidationError("Could not save account due to a database integrity constraint.")

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

        return {
            "id": account.id,
            "accountId": account.account_id,
            "name": account.name,
            "industry": account.industry,
            "website": account.website,
            "phone": account.phone,
            "email": account.email,
            "address": account.address,
            "isActive": account.is_active,
            "contactCount": 0,
            "leadCount": 0,
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
            if conflict:
                raise ConflictError(f"Another active account with name '{conflict.name}' already exists ({conflict.account_id}).")
            acc.name = clean_name

        if payload.industry is not None:
            acc.industry = payload.industry.strip() if payload.industry else None
        if payload.website is not None:
            acc.website = payload.website.strip() if payload.website else None
        if payload.phone is not None:
            acc.phone = payload.phone.strip() if payload.phone else None
        if payload.email is not None:
            acc.email = payload.email.strip() if payload.email else None
        if payload.address is not None:
            acc.address = payload.address.strip() if payload.address else None
        if payload.isActive is not None:
            acc.is_active = payload.isActive

        self.db.commit()
        self.db.refresh(acc)

        after_state = {
            "name": acc.name,
            "industry": acc.industry,
            "website": acc.website,
            "phone": acc.phone,
            "email": acc.email,
            "address": acc.address,
            "isActive": acc.is_active
        }

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
    ) -> List[Dict[str, Any]]:
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

        contacts = query.order_by(Contact.name.asc()).offset(offset).limit(limit).all()

        return [
            {
                "id": c.id,
                "contactId": c.contact_id,
                "accountId": c.account_id,
                "accountName": c.account.name if c.account else None,
                "name": c.name,
                "email": c.email,
                "mobileNumber": c.mobile_number,
                "designation": c.designation,
                "isActive": c.is_active,
                "createdAt": c.created_at.isoformat() if c.created_at else None,
                "updatedAt": c.updated_at.isoformat() if c.updated_at else None
            }
            for c in contacts
        ]

    def get_contact(self, contact_id: str) -> Dict[str, Any]:
        c = self.db.query(Contact).options(joinedload(Contact.account)).filter(
            or_(Contact.id == contact_id, Contact.contact_id == contact_id)
        ).first()
        if not c:
            raise NotFoundError(f"Contact '{contact_id}' not found.")

        leads = self.db.query(Lead).filter(
            Lead.contact_id == c.id
        ).order_by(Lead.created_at.desc()).all()

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
            "email": c.email,
            "mobileNumber": c.mobile_number,
            "designation": c.designation,
            "isActive": c.is_active,
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
        if clean_email:
            existing_email = self.db.query(Contact).filter(
                func.lower(Contact.email) == clean_email,
                Contact.is_active == True
            ).first()
            if existing_email:
                raise ConflictError(
                    message=f"A contact with email '{clean_email}' already exists ({existing_email.contact_id}).",
                    details={"existingContactId": existing_email.id, "existingContactNumber": existing_email.contact_id}
                )

        if clean_phone:
            # normalize phone digits for comparison
            phone_digits = "".join(filter(str.isdigit, clean_phone))
            if phone_digits:
                existing_contacts = self.db.query(Contact).filter(
                    Contact.mobile_number.isnot(None),
                    Contact.is_active == True
                ).all()
                for ec in existing_contacts:
                    if ec.mobile_number and "".join(filter(str.isdigit, ec.mobile_number)) == phone_digits:
                        raise ConflictError(
                            message=f"A contact with mobile number '{clean_phone}' already exists ({ec.contact_id}).",
                            details={"existingContactId": ec.id, "existingContactNumber": ec.contact_id}
                        )

        contact_code = get_next_sequence_id(self.db, "CONTACT", "CON")
        contact = Contact(
            contact_id=contact_code,
            account_id=account.id if account else None,
            name=clean_name,
            email=clean_email,
            mobile_number=clean_phone,
            designation=payload.designation.strip() if payload.designation else None,
            is_active=True
        )

        try:
            self.db.add(contact)
            self.db.commit()
            self.db.refresh(contact)
        except IntegrityError:
            self.db.rollback()
            raise ValidationError("Could not save contact due to a database constraint.")

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

        return {
            "id": contact.id,
            "contactId": contact.contact_id,
            "accountId": contact.account_id,
            "accountName": account.name if account else None,
            "name": contact.name,
            "email": contact.email,
            "mobileNumber": contact.mobile_number,
            "designation": contact.designation,
            "isActive": contact.is_active,
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

        if payload.name is not None:
            clean_name = payload.name.strip()
            if not clean_name:
                raise ValidationError("Contact name cannot be empty.")
            c.name = clean_name

        if payload.accountId is not None:
            if payload.accountId == "":
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
            c.email = payload.email.strip().lower() if payload.email else None
        if payload.mobileNumber is not None:
            c.mobile_number = payload.mobileNumber.strip() if payload.mobileNumber else None
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

        # 4. Multi-Select Requirement Types
        req_types = payload.requirementTypes or ([payload.requirementType] if payload.requirementType else ["Consulting"])
        req_types = normalize_and_validate_req_types(req_types)
        primary_req_type = req_types[0] if req_types else "Consulting"

        clean_req = payload.requestedProductService.strip() if payload.requestedProductService and payload.requestedProductService.strip() else None
        norm_req = normalize_text(clean_req) if clean_req else None
        acc_id = account.id if account else None
        con_id = contact.id if contact else None

        # Lead Title is optional per Section 4
        clean_title = payload.leadName.strip() if payload.leadName and payload.leadName.strip() else None

        lead = None
        for attempt in range(5):
            lead_code = get_next_sequence_id(self.db, "LEAD", "LEAD")
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
                lifecycle_status="Open",
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
                self.db.commit()
                self.db.refresh(lead)
                break
            except IntegrityError as e:
                self.db.rollback()
                err_str = str(e).lower()
                if "lead_id" in err_str or "leads.lead_id" in err_str:
                    logger.warning(f"Sequence collision on {lead_code}, retrying ({attempt+1}/5)...")
                    continue
                logger.error(f"IntegrityError creating lead: {e}")
                raise ValidationError("Could not save lead due to a database integrity constraint.")
        else:
            raise ValidationError("Could not generate a unique Lead ID after multiple attempts.")

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
            types = payload.requirementTypes or ([payload.requirementType] if payload.requirementType else ["Consulting"])
            req_types = normalize_and_validate_req_types(types)
            lead.requirement_type = req_types[0]

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
        lead.updated_by_id = str(actor.id) if actor.id else None

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
                joinedload(Lead.requirement_types),
                joinedload(Lead.contact_methods)
            )
        )

        # 1. Apply Saved View Filters
        clean_view = (view or "open").strip().lower()

        if clean_view == "open":
            query = query.filter(Lead.lifecycle_status == "Open")
        elif clean_view == "all":
            pass
        elif clean_view == "unqualified":
            query = query.filter(Lead.lifecycle_status == "Disqualified")
        elif clean_view == "my_leads":
            query = query.filter(Lead.assigned_to_user_id == str(actor.id))
        elif clean_view == "follow_ups_due":
            due_window = date.today() + timedelta(days=1)
            query = query.filter(
                Lead.lifecycle_status == "Open",
                Lead.next_follow_up_date.isnot(None),
                Lead.next_follow_up_date <= due_window
            )

        # 2. Facet Filters
        if business_area and business_area != "ALL":
            query = query.filter(Lead.business_area == business_area.strip())

        if requirement_type and requirement_type != "ALL":
            clean_rt = requirement_type.strip()
            # Match either the normalized table or legacy column
            query = query.filter(
                or_(
                    Lead.requirement_types.any(LeadRequirementType.requirement_type == clean_rt),
                    Lead.requirement_type == clean_rt
                )
            )

        if lifecycle_status and lifecycle_status != "ALL" and clean_view == "all":
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
            "totalCount": total_count,
            "page": safe_page,
            "pageSize": safe_page_size,
            "totalPages": totalPages,
            "leads": [self._format_lead(l) for l in leads]
        }

    def get_lead(self, actor: CurrentUser, lead_id: str) -> Dict[str, Any]:
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
                joinedload(Lead.requirement_types),
                joinedload(Lead.contact_methods)
            )
            .filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id))
            .first()
        )
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        return self._format_lead(lead)

    def _format_lead(self, lead: Lead) -> Dict[str, Any]:
        # Multi-select requirement types
        types = [rt.requirement_type for rt in lead.requirement_types] if lead.requirement_types else []
        if not types and lead.requirement_type:
            types = [lead.requirement_type]
        if not types:
            types = ["Consulting"]

        contact_methods = [cm.contact_method for cm in lead.contact_methods] if getattr(lead, "contact_methods", None) else []

        display_name = lead.lead_name or lead.lead_id

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
                "currency": opp.currency,
                "estimatedValue": float(opp.estimated_value) if opp.estimated_value is not None else None,
                "description": opp.description,
                "accountId": opp.account_id,
                "accountName": opp.account.name if opp.account else None,
                "contactId": opp.contact_id,
                "contactName": opp.contact.name if opp.contact else None
            }

        return {
            "id": lead.id,
            "leadId": lead.lead_id,
            "leadName": lead.lead_name,
            "displayName": display_name,
            "businessArea": lead.business_area,
            "requirementType": ", ".join(types),
            "requirementTypes": types,
            "requirementSummary": lead.requirement_summary,
            "requestedProductService": lead.requested_product_service,
            "leadSource": lead.lead_source,
            "lifecycleStatus": lead.lifecycle_status,
            "communicationChannel": lead.communication_channel,
            "remarks": lead.remarks,
            "nextFollowUpDate": lead.next_follow_up_date.isoformat() if lead.next_follow_up_date else None,
            "nextFollowUpAction": lead.next_follow_up_action,
            "connectedDate": lead.connected_date.isoformat() if lead.connected_date else None,
            "lastConnectedDate": lead.last_connected_date.isoformat() if lead.last_connected_date else None,
            "websiteLink": lead.website_link,
            "location": lead.location,
            "siteName": lead.site_name,
            "createdAt": lead.created_at.isoformat() if lead.created_at else None,
            "updatedAt": lead.updated_at.isoformat() if lead.updated_at else None,

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
            "qualifiedAt": lead.qualified_at.isoformat() if lead.qualified_at else None,
            "qualifiedById": lead.qualified_by_id,
            "qualifiedByName": lead.qualified_by.name if getattr(lead, "qualified_by", None) else None,
        }

    def _format_opportunity(self, opp: Opportunity) -> Dict[str, Any]:
        req_list = [r.strip() for r in (opp.requirement_types or "").split(",") if r.strip()]
        return {
            "id": opp.id,
            "opportunityId": opp.opportunity_id,
            "name": opp.name,
            "accountId": opp.account_id,
            "accountName": opp.account.name if opp.account else None,
            "contactId": opp.contact_id,
            "contactName": opp.contact.name if opp.contact else None,
            "originatingLeadId": opp.originating_lead_id,
            "originatingLeadNumber": opp.originating_lead.lead_id if opp.originating_lead else None,
            "status": opp.status,
            "currency": opp.currency,
            "estimatedValue": float(opp.estimated_value) if opp.estimated_value is not None else None,
            "description": opp.description,
            "requirementSummary": opp.requirement_summary,
            "requirementTypes": req_list,
            "assignedToUserId": opp.assigned_to_user_id,
            "assignedToName": opp.assigned_to.name if opp.assigned_to else None,
            "createdById": opp.created_by_id,
            "createdByName": opp.created_by.name if opp.created_by else None,
            "createdAt": opp.created_at.isoformat() if opp.created_at else None,
            "updatedAt": opp.updated_at.isoformat() if opp.updated_at else None
        }

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

        acc_filters = []
        if comp_name and len(comp_name) >= 2:
            acc_filters.append(func.lower(Account.name).like(f"%{comp_name.lower()}%"))
        if comp_email:
            acc_filters.append(func.lower(Account.email) == comp_email)
        if comp_web:
            clean_domain = comp_web.replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0]
            if clean_domain and len(clean_domain) >= 3:
                acc_filters.append(func.lower(Account.website).like(f"%{clean_domain}%"))

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

                matching_accounts.append({
                    "id": a.id,
                    "accountId": a.account_id,
                    "name": a.name,
                    "industry": a.industry,
                    "website": a.website,
                    "phone": a.phone,
                    "email": a.email,
                    "address": a.address,
                    "matchReasons": reasons
                })

        # 2. Search Contacts
        c_email = (lead.contact_email or (lead.contact.email if lead.contact else "") or "").strip().lower()
        c_phone = (lead.mobile_phone or lead.business_phone or (lead.contact.mobile_number if lead.contact else "") or "").strip()
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

        return {
            "success": True,
            "leadId": lead.id,
            "matchingAccounts": matching_accounts,
            "matchingContacts": matching_contacts,
            "suggestedAccount": suggested_acc,
            "suggestedContact": suggested_con
        }

    def qualify_lead(
        self,
        actor: CurrentUser,
        lead_id: str,
        payload: LeadQualifyRequest,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        lead = self.db.query(Lead).options(
            joinedload(Lead.requirement_types),
            joinedload(Lead.contact_methods),
            joinedload(Lead.opportunity),
            joinedload(Lead.account),
            joinedload(Lead.contact)
        ).filter(
            or_(Lead.id == lead_id, Lead.lead_id == lead_id)
        ).with_for_update().first()

        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        # Idempotency / Retry-Safety:
        # If the lead is already qualified, return existing linked records safely without creating duplicates
        if lead.lifecycle_status == "Qualified" and lead.opportunity_id:
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
                        "name": opp.account.name
                    } if opp.account else {},
                    "contact": {
                        "id": opp.contact.id,
                        "contactId": opp.contact.contact_id,
                        "name": opp.contact.name
                    } if opp.contact else None,
                    "opportunity": self._format_opportunity(opp)
                }

        # 1. Resolve Account
        acc_action = (payload.account.action or "create").strip().lower()
        account = None
        if acc_action == "reuse":
            if not payload.account.accountId:
                raise ValidationError("accountId is required when reusing an existing account.")
            account = self.db.query(Account).filter(
                or_(Account.id == payload.account.accountId, Account.account_id == payload.account.accountId),
                Account.is_active == True
            ).first()
            if not account:
                raise NotFoundError(f"Account '{payload.account.accountId}' does not exist or is inactive.")
            # Safely enrich existing account fields if empty on account but present in payload/lead
            if not account.website and (payload.account.website or lead.website_link):
                account.website = (payload.account.website or lead.website_link).strip()
            if not account.email and (payload.account.email or lead.company_email):
                account.email = (payload.account.email or lead.company_email).strip().lower()
            if not account.industry and (payload.account.industry or lead.industry):
                account.industry = (payload.account.industry or lead.industry).strip()
        elif acc_action == "create":
            acc_name = (payload.account.name or lead.company_name or "").strip()
            if not acc_name:
                acc_name = (lead.lead_name or f"Account for Lead {lead.lead_id}").strip()

            # Check if active account with same normalized name already exists
            norm_name = normalize_text(acc_name)
            existing_acc = self.db.query(Account).filter(
                func.lower(func.trim(Account.name)) == norm_name,
                Account.is_active == True
            ).first()
            if existing_acc:
                account = existing_acc
            else:
                account_code = get_next_sequence_id(self.db, "ACCOUNT", "ACC")
                account = Account(
                    account_id=account_code,
                    name=acc_name,
                    industry=(payload.account.industry or lead.industry or "").strip() or None,
                    website=(payload.account.website or lead.website_link or "").strip() or None,
                    phone=(payload.account.phone or lead.business_phone or "").strip() or None,
                    email=(payload.account.email or lead.company_email or "").strip().lower() or None,
                    address=(payload.account.address or lead.location or "").strip() or None,
                    is_active=True
                )
                self.db.add(account)
                self.db.flush()
        else:
            raise ValidationError(f"Invalid account action '{payload.account.action}'. Must be 'reuse' or 'create'.")

        # 2. Resolve Contact
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
                    con_name = (lead.lead_name or "Primary Contact").strip()

                con_email = (payload.contact.email or lead.contact_email or "").strip().lower() or None
                con_phone = (payload.contact.mobileNumber or lead.mobile_phone or lead.business_phone or "").strip() or None
                con_desig = (payload.contact.designation or lead.job_title or "").strip() or None

                # Check duplicate email if provided
                if con_email:
                    existing_con = self.db.query(Contact).filter(
                        func.lower(Contact.email) == con_email,
                        Contact.is_active == True
                    ).first()
                    if existing_con:
                        if existing_con.account_id and existing_con.account_id != account.id:
                            raise ValidationError(
                                f"A contact with email '{con_email}' already exists under account '{existing_con.account.name if existing_con.account else existing_con.account_id}'."
                            )
                        elif not existing_con.account_id:
                            existing_con.account_id = account.id
                        contact = existing_con

                if not contact:
                    contact_code = get_next_sequence_id(self.db, "CONTACT", "CON")
                    contact = Contact(
                        contact_id=contact_code,
                        account_id=account.id,
                        name=con_name,
                        email=con_email,
                        mobile_number=con_phone,
                        designation=con_desig,
                        is_active=True
                    )
                    self.db.add(contact)
                    self.db.flush()
            else:
                raise ValidationError(f"Invalid contact action '{payload.contact.action}'. Must be 'reuse' or 'create'.")
        elif lead.contact_id:
            contact = self.db.query(Contact).filter(Contact.id == lead.contact_id).first()
            if contact and not contact.account_id:
                contact.account_id = account.id

        # 3. Create Opportunity
        opp_code = get_next_sequence_id(self.db, "OPPORTUNITY", "OPP")
        opp_name = (payload.opportunityName or lead.lead_name or f"Opportunity - {account.name}").strip()
        req_types_str = ", ".join([rt.requirement_type for rt in lead.requirement_types]) if lead.requirement_types else "Consulting"

        opportunity = Opportunity(
            opportunity_id=opp_code,
            name=opp_name,
            account_id=account.id,
            contact_id=contact.id if contact else None,
            originating_lead_id=lead.id,
            status="Open",
            currency=lead.currency or "INR",
            estimated_value=payload.estimatedValue,
            description=payload.opportunityDescription or lead.description,
            requirement_summary=lead.requirement_summary,
            requirement_types=req_types_str,
            assigned_to_user_id=payload.assignedToUserId or lead.assigned_to_user_id,
            created_by_id=str(actor.id) if actor.id else None,
            updated_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(opportunity)
        self.db.flush()

        # 4. Update Lead
        before_state = {
            "leadId": lead.lead_id,
            "status": lead.lifecycle_status,
            "accountId": lead.account_id,
            "contactId": lead.contact_id
        }

        lead.lifecycle_status = "Qualified"
        lead.account_id = account.id
        if contact:
            lead.contact_id = contact.id
        lead.opportunity_id = opportunity.id
        lead.qualified_at = datetime.now(timezone.utc)
        lead.qualified_by_id = str(actor.id) if actor.id else None
        lead.updated_by_id = str(actor.id) if actor.id else None

        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"IntegrityError during lead qualification: {e}")
            raise ValidationError("Lead qualification failed due to a database integrity constraint.")

        self.db.refresh(lead)
        self.db.refresh(opportunity)
        self.db.refresh(account)
        if contact:
            self.db.refresh(contact)

        # Audit logs
        self.audit_service.log(
            action="CRM_LEAD_QUALIFIED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=actor.active_role,
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

        return {
            "success": True,
            "message": f"Lead '{lead.lead_id}' successfully qualified into Opportunity '{opportunity.opportunity_id}'.",
            "lead": self._format_lead(lead),
            "account": {
                "id": account.id,
                "accountId": account.account_id,
                "name": account.name,
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

    def list_opportunities(
        self,
        actor: CurrentUser,
        search: Optional[str] = None,
        account_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        query = self.db.query(Opportunity).options(
            joinedload(Opportunity.account),
            joinedload(Opportunity.contact),
            joinedload(Opportunity.originating_lead),
            joinedload(Opportunity.assigned_to),
            joinedload(Opportunity.created_by)
        )
        if status:
            query = query.filter(Opportunity.status == status.strip())
        if account_id:
            query = query.filter(Opportunity.account_id == account_id.strip())
        if search:
            s = f"%{search.strip().lower()}%"
            query = query.outerjoin(Opportunity.account).filter(
                or_(
                    func.lower(Opportunity.name).like(s),
                    func.lower(Opportunity.opportunity_id).like(s),
                    func.lower(Account.name).like(s)
                )
            )

        opps = query.order_by(Opportunity.created_at.desc()).offset(offset).limit(limit).all()
        return [self._format_opportunity(o) for o in opps]

    def get_opportunity(self, opp_id: str) -> Dict[str, Any]:
        opp = self.db.query(Opportunity).options(
            joinedload(Opportunity.account),
            joinedload(Opportunity.contact),
            joinedload(Opportunity.originating_lead),
            joinedload(Opportunity.assigned_to),
            joinedload(Opportunity.created_by)
        ).filter(
            or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
        ).first()
        if not opp:
            raise NotFoundError(f"Opportunity '{opp_id}' not found.")
        return self._format_opportunity(opp)

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
            summary=payload.summary.strip() if payload.summary else None,
            outcome=payload.outcome.strip() if payload.outcome else None,
            next_action=payload.nextAction.strip() if payload.nextAction else None,
            follow_up_date=payload.followUpDate,
            created_by_id=str(actor.id) if actor.id else None
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

    # =========================================================================
    # 6. DASHBOARD METRICS & ASSIGNEES
    # =========================================================================

    def get_dashboard_metrics(self, actor: CurrentUser) -> Dict[str, Any]:
        total_leads = self.db.query(func.count(Lead.id)).scalar() or 0
        open_leads = self.db.query(func.count(Lead.id)).filter(Lead.lifecycle_status == "Open").scalar() or 0
        qualified_leads = self.db.query(func.count(Lead.id)).filter(Lead.lifecycle_status == "Qualified").scalar() or 0
        disqualified_leads = self.db.query(func.count(Lead.id)).filter(Lead.lifecycle_status == "Disqualified").scalar() or 0

        my_leads = 0
        if actor and actor.id:
            my_leads = self.db.query(func.count(Lead.id)).filter(Lead.assigned_to_user_id == str(actor.id)).scalar() or 0

        due_window = date.today() + timedelta(days=1)
        follow_ups_due = self.db.query(func.count(Lead.id)).filter(
            Lead.lifecycle_status == "Open",
            Lead.next_follow_up_date.isnot(None),
            Lead.next_follow_up_date <= due_window
        ).scalar() or 0

        overdue_follow_ups = self.db.query(func.count(Lead.id)).filter(
            Lead.lifecycle_status == "Open",
            Lead.next_follow_up_date.isnot(None),
            Lead.next_follow_up_date < date.today()
        ).scalar() or 0

        return {
            "success": True,
            "totalLeads": total_leads,
            "openLeads": open_leads,
            "qualifiedLeads": qualified_leads,
            "disqualifiedLeads": disqualified_leads,
            "myLeads": my_leads,
            "followUpsDue": follow_ups_due,
            "overdueFollowUps": overdue_follow_ups
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
