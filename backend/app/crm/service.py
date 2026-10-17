import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta, date
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
    LeadCommunicationHistory,
    CrmSequence
)
from app.crm.schema import (
    AccountCreate,
    ContactCreate,
    LeadCreate,
    LeadUpdate,
    CommunicationCreate,
    ALLOWED_BUSINESS_AREAS,
    ALLOWED_REQUIREMENT_TYPES,
    ALLOWED_LEAD_SOURCES,
    ALLOWED_LIFECYCLE_STATUSES
)
from app.roles.assignment_service import RoleAssignmentService
from app.audit.service import AuditService

logger = logging.getLogger("revy.crm.service")


def normalize_text(val: Optional[str]) -> str:
    """Normalizes text by trimming, lowercasing, and collapsing multiple whitespace."""
    if not val:
        return ""
    return " ".join(val.strip().lower().split())


def get_next_sequence_id(db: Session, entity_name: str, prefix: str, padding: int = 5) -> str:
    """
    Concurrency-safe sequence generator using CrmSequence with row locking.
    Generates IDs like LEAD-00001, ACC-00001, CON-00001, COM-00001.
    """
    entity_key = entity_name.strip().upper()
    seq = db.query(CrmSequence).filter(CrmSequence.entity_name == entity_key).with_for_update().first()
    if not seq:
        try:
            seq = CrmSequence(entity_name=entity_key, current_value=1)
            db.add(seq)
            db.flush()
            return f"{prefix}-{1:0{padding}d}"
        except IntegrityError:
            db.rollback()
            seq = db.query(CrmSequence).filter(CrmSequence.entity_name == entity_key).with_for_update().first()

    seq.current_value += 1
    db.flush()
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

        query = self.db.query(User).filter(User.is_hard_deleted == False)
        if search:
            s = f"%{search.strip().lower()}%"
            query = query.filter(
                (func.lower(User.name).like(s)) |
                (func.lower(User.username).like(s)) |
                (func.lower(User.email).like(s))
            )

        users = query.order_by(User.name.asc(), User.username.asc()).all()

        memberships = self.db.query(UserModuleMembership).filter(
            UserModuleMembership.module_id == crm_mod.id
        ).all()
        mem_map = {m.user_id: m for m in memberships}

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
        for u in users:
            mem = mem_map.get(u.id)
            has_crm = bool(mem and mem.is_active)
            r_code = mem.role.code if (mem and mem.role and mem.is_active) else None
            r_name = mem.role.name if (mem and mem.role and mem.is_active) else None

            if crm_access is not None and has_crm != crm_access:
                continue
            if role_code and (not r_code or r_code.upper() != role_code.strip().upper()):
                continue

            result.append({
                "userId": u.id,
                "username": u.username,
                "name": u.name or u.username,
                "email": u.email,
                "status": u.status,
                "crmAccess": has_crm,
                "crmRoleCode": r_code,
                "crmRoleName": r_name,
                "assignedLeadCount": lead_counts.get(u.id, 0),
                "createdAt": u.created_at.isoformat() if u.created_at else None
            })

        return result

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
        query = self.db.query(Account).filter(Account.is_active == True)
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

        # Batch load contact & lead counts
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
                "createdAt": a.created_at.isoformat() if a.created_at else None
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
                "createdAt": acc.created_at.isoformat() if acc.created_at else None
            },
            "contacts": [
                {
                    "id": c.id,
                    "contactId": c.contact_id,
                    "name": c.name,
                    "email": c.email,
                    "mobileNumber": c.mobile_number,
                    "designation": c.designation
                }
                for c in contacts
            ],
            "leads": [
                {
                    "id": l.id,
                    "leadId": l.lead_id,
                    "leadName": l.lead_name,
                    "businessArea": l.business_area,
                    "lifecycleStatus": l.lifecycle_status,
                    "requestedProductService": l.requested_product_service
                }
                for l in leads
            ]
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
            "createdAt": account.created_at.isoformat() if account.created_at else None
        }

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
        query = self.db.query(Contact).options(joinedload(Contact.account)).filter(Contact.is_active == True)

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
                "createdAt": c.created_at.isoformat() if c.created_at else None
            }
            for c in contacts
        ]

    def get_contact(self, contact_id: str) -> Dict[str, Any]:
        c = self.db.query(Contact).options(joinedload(Contact.account)).filter(
            or_(Contact.id == contact_id, Contact.contact_id == contact_id)
        ).first()
        if not c:
            raise NotFoundError(f"Contact '{contact_id}' not found.")

        return {
            "id": c.id,
            "contactId": c.contact_id,
            "accountId": c.account_id,
            "accountName": c.account.name if c.account else None,
            "name": c.name,
            "email": c.email,
            "mobileNumber": c.mobile_number,
            "designation": c.designation,
            "isActive": c.is_active,
            "createdAt": c.created_at.isoformat() if c.created_at else None
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
            raise ConflictError("A contact with this identifying information already exists.")

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
            "createdAt": contact.created_at.isoformat() if contact.created_at else None
        }

    # =========================================================================
    # 4. LEAD MANAGEMENT SERVICES
    # =========================================================================

    def _validate_assignee(self, user_id: str) -> User:
        """Validates that a target assignee is an active portal user with an active CRM role."""
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

    def check_open_lead_duplicate(
        self,
        account_id: Optional[str],
        contact_id: str,
        normalized_requirement: Optional[str],
        exclude_lead_id: Optional[str] = None
    ) -> Optional[Lead]:
        """
        Duplicate open lead rule:
        - When normalized_requirement is empty/None: product is unknown, no duplicate conflict checked.
        - When an Account is provided: compare against account_id + normalized_requirement where lifecycle_status == 'Open'.
        - When no Account is provided: compare against contact_id + normalized_requirement where lifecycle_status == 'Open' and account_id is None.
        """
        if not normalized_requirement:
            return None

        if account_id:
            query = self.db.query(Lead).filter(
                Lead.account_id == account_id,
                Lead.normalized_requirement == normalized_requirement,
                Lead.lifecycle_status == "Open"
            )
        else:
            query = self.db.query(Lead).filter(
                Lead.contact_id == contact_id,
                Lead.account_id.is_(None),
                Lead.normalized_requirement == normalized_requirement,
                Lead.lifecycle_status == "Open"
            )

        if exclude_lead_id:
            query = query.filter(Lead.id != exclude_lead_id)

        return query.first()

    def create_lead(
        self,
        actor: CurrentUser,
        payload: LeadCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        # 1. Validate Contact
        contact = self.db.query(Contact).filter(
            or_(Contact.id == payload.contactId, Contact.contact_id == payload.contactId),
            Contact.is_active == True
        ).first()
        if not contact:
            raise NotFoundError(f"Contact '{payload.contactId}' not found or is inactive.")

        # 2. Validate Account if provided
        account = None
        if payload.accountId:
            account = self.db.query(Account).filter(
                or_(Account.id == payload.accountId, Account.account_id == payload.accountId),
                Account.is_active == True
            ).first()
            if not account:
                raise NotFoundError(f"Account '{payload.accountId}' not found or is inactive.")

            # Validate Contact-Account relationship: if contact belongs to another account, reject
            if contact.account_id and contact.account_id != account.id:
                raise ValidationError("The selected Contact belongs to a different Account.")
            elif not contact.account_id:
                # Link contact to account
                contact.account_id = account.id
        elif contact.account_id:
            # If account was omitted on lead creation, auto-populate from contact's existing account
            account = self.db.query(Account).filter(
                Account.id == contact.account_id,
                Account.is_active == True
            ).first()

        # 3. Validate Assignee if provided
        assignee = None
        if payload.assignedToUserId:
            assignee = self._validate_assignee(payload.assignedToUserId)

        # 4. Normalize requirement (optional for early enquiries and prospective clients)
        clean_req = payload.requestedProductService.strip() if payload.requestedProductService and payload.requestedProductService.strip() else None
        norm_req = normalize_text(clean_req) if clean_req else None

        # 5. Check duplicate open lead only if requirement specification is known
        acc_id = account.id if account else None
        if norm_req:
            dup_lead = self.check_open_lead_duplicate(
                account_id=acc_id,
                contact_id=contact.id,
                normalized_requirement=norm_req
            )
            if dup_lead:
                target_identity = f"Account '{account.name}'" if account else f"Contact '{contact.name}'"
                raise ConflictError(
                    message=f"An open lead already exists for {target_identity} with requirement '{dup_lead.requested_product_service}' ({dup_lead.lead_id}).",
                    details={
                        "existingLeadId": dup_lead.id,
                        "existingLeadNumber": dup_lead.lead_id,
                        "existingLeadName": dup_lead.lead_name,
                        "lifecycleStatus": dup_lead.lifecycle_status,
                        "assignedToUserId": dup_lead.assigned_to_user_id
                    }
                )

        lead_code = get_next_sequence_id(self.db, "LEAD", "LEAD")
        lead = Lead(
            lead_id=lead_code,
            lead_name=payload.leadName.strip(),
            business_area=payload.businessArea,
            requirement_type=payload.requirementType,
            requirement_summary=payload.requirementSummary.strip() if payload.requirementSummary else None,
            requested_product_service=clean_req,
            normalized_requirement=norm_req,
            lead_source=payload.leadSource or "Website",
            account_id=acc_id,
            contact_id=contact.id,
            assigned_to_user_id=assignee.id if assignee else None,
            lifecycle_status="Open",
            communication_channel=payload.communicationChannel or "Email",
            remarks=payload.remarks.strip() if payload.remarks else None,
            next_follow_up_date=payload.nextFollowUpDate,
            next_follow_up_action=payload.nextFollowUpAction.strip() if payload.nextFollowUpAction else None,
            website_link=payload.websiteLink.strip() if payload.websiteLink else None,
            location=payload.location.strip() if payload.location else None,
            site_name=payload.siteName.strip() if payload.siteName else None,
            created_by_id=str(actor.id) if actor.id else None
        )

        try:
            self.db.add(lead)
            self.db.commit()
            self.db.refresh(lead)
        except IntegrityError:
            self.db.rollback()
            if norm_req:
                collision = self.check_open_lead_duplicate(
                    account_id=acc_id,
                    contact_id=contact.id,
                    normalized_requirement=norm_req
                )
                if collision:
                    target_identity = f"Account '{account.name}'" if account else f"Contact '{contact.name}'"
                    raise ConflictError(
                        message=f"An open lead already exists for {target_identity} with requirement '{collision.requested_product_service}' ({collision.lead_id}).",
                        details={
                            "existingLeadId": collision.id,
                            "existingLeadNumber": collision.lead_id,
                            "existingLeadName": collision.lead_name,
                            "lifecycleStatus": collision.lifecycle_status
                        }
                    )
            raise ValidationError("Could not save lead due to a database integrity conflict.")

        self.audit_service.log(
            action="CRM_LEAD_CREATED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=actor.active_role,
            target_info={
                "recordId": lead.id,
                "leadNumber": lead.lead_id,
                "leadName": lead.lead_name,
                "businessArea": lead.business_area,
                "requirement": lead.requested_product_service,
                "assignedTo": assignee.username if assignee else None,
                "details": f"Created Lead '{lead.lead_name}' ({lead.lead_id}) for {lead.business_area}."
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
        lead = self.db.query(Lead).filter(
            or_(Lead.id == lead_id, Lead.lead_id == lead_id)
        ).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        before_state = {
            "leadId": lead.lead_id,
            "status": lead.lifecycle_status,
            "assignedTo": lead.assigned_to_user_id
        }

        # Validate Contact if changed or provided
        if "contactId" in payload.model_fields_set:
            if not payload.contactId or not str(payload.contactId).strip():
                raise ValidationError("Primary Contact is mandatory and cannot be cleared.")
            contact = self.db.query(Contact).filter(
                or_(Contact.id == payload.contactId, Contact.contact_id == payload.contactId),
                Contact.is_active == True
            ).first()
            if not contact:
                raise NotFoundError(f"Contact '{payload.contactId}' not found or is inactive.")
            lead.contact_id = contact.id
        else:
            contact = lead.contact or self.db.query(Contact).filter(Contact.id == lead.contact_id).first()

        if not contact:
            raise ValidationError("A valid Contact is required for the Lead.")

        # Validate Account if changed or provided
        if "accountId" in payload.model_fields_set:
            if not payload.accountId:
                lead.account_id = None
                account = None
            else:
                account = self.db.query(Account).filter(
                    or_(Account.id == payload.accountId, Account.account_id == payload.accountId),
                    Account.is_active == True
                ).first()
                if not account:
                    raise NotFoundError(f"Account '{payload.accountId}' not found or is inactive.")
                lead.account_id = account.id
        else:
            account = lead.account if lead.account_id else (self.db.query(Account).filter(Account.id == lead.account_id).first() if lead.account_id else None)

        # Enforce consistency between lead's contact and account
        if account and contact:
            if contact.account_id and contact.account_id != account.id:
                raise ValidationError("The selected Contact belongs to a different Account.")
            elif not contact.account_id:
                contact.account_id = account.id
        elif not account and contact and contact.account_id:
            if "accountId" not in payload.model_fields_set:
                lead.account_id = contact.account_id
                account = self.db.query(Account).filter(Account.id == contact.account_id).first()
            else:
                raise ValidationError("Cannot clear Account while the selected Contact belongs to an Account. Please select an unassigned Contact first.")


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

        # Validate requirement change or duplicate check
        req_changed = False
        if payload.requestedProductService is not None:
            clean_req = payload.requestedProductService.strip() if payload.requestedProductService.strip() else None
            norm = normalize_text(clean_req) if clean_req else None
            if norm != lead.normalized_requirement or clean_req != lead.requested_product_service:
                lead.requested_product_service = clean_req
                lead.normalized_requirement = norm
                req_changed = True

        status_changed = False
        if payload.lifecycleStatus and payload.lifecycleStatus != lead.lifecycle_status:
            lead.lifecycle_status = payload.lifecycleStatus
            status_changed = True

        # If lead is Open and requirement is known, verify duplicate rule
        if lead.lifecycle_status == "Open" and lead.normalized_requirement and (req_changed or status_changed or payload.accountId is not None or payload.contactId):
            dup = self.check_open_lead_duplicate(
                account_id=lead.account_id,
                contact_id=lead.contact_id,
                normalized_requirement=lead.normalized_requirement,
                exclude_lead_id=lead.id
            )
            if dup:
                raise ConflictError(
                    message=f"An open lead already exists with requirement '{dup.requested_product_service}' ({dup.lead_id}).",
                    details={"existingLeadId": dup.id, "existingLeadNumber": dup.lead_id}
                )

        if payload.leadName:
            lead.lead_name = payload.leadName.strip()
        if payload.businessArea:
            lead.business_area = payload.businessArea
        if payload.requirementType:
            lead.requirement_type = payload.requirementType
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
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("Update failed due to a duplicate open lead constraint.")

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
        if clean_status == "Open" and before_status != "Open":
            # Check duplicate rule before reopening only if requirement is known
            if lead.normalized_requirement:
                dup = self.check_open_lead_duplicate(
                    account_id=lead.account_id,
                    contact_id=lead.contact_id,
                    normalized_requirement=lead.normalized_requirement,
                    exclude_lead_id=lead.id
                )
                if dup:
                    raise ConflictError(
                        message=f"Cannot reopen: another open lead already exists with requirement '{dup.requested_product_service}' ({dup.lead_id}).",
                        details={"existingLeadId": dup.id, "existingLeadNumber": dup.lead_id}
                    )

        lead.lifecycle_status = clean_status
        if remarks:
            lead.remarks = remarks.strip()
        lead.updated_by_id = str(actor.id) if actor.id else None

        try:
            self.db.commit()
            self.db.refresh(lead)
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("Reopening lead violated duplicate open lead constraint.")

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
                joinedload(Lead.created_by)
            )
        )

        # 1. Apply Saved View Filters
        clean_view = (view or "open").strip().lower()

        if clean_view == "open":
            query = query.filter(Lead.lifecycle_status == "Open")
        elif clean_view == "all":
            pass  # all leads
        elif clean_view == "unqualified":
            query = query.filter(Lead.lifecycle_status == "Disqualified")
        elif clean_view == "my_leads":
            query = query.filter(Lead.assigned_to_user_id == str(actor.id))
        elif clean_view == "follow_ups_due":
            # Due within 24 hours (today or tomorrow) or overdue
            due_window = date.today() + timedelta(days=1)
            query = query.filter(
                Lead.lifecycle_status == "Open",
                Lead.next_follow_up_date.isnot(None),
                Lead.next_follow_up_date <= due_window
            )

        # 2. Additional Facet Filters
        if business_area:
            query = query.filter(Lead.business_area == business_area.strip())
        if requirement_type:
            query = query.filter(Lead.requirement_type == requirement_type.strip())
        if lifecycle_status and clean_view == "all":
            query = query.filter(Lead.lifecycle_status == lifecycle_status.strip())
        if assigned_to_user_id:
            query = query.filter(Lead.assigned_to_user_id == assigned_to_user_id.strip())
        if account_id:
            query = query.filter(Lead.account_id == account_id.strip())

        # 3. Global Search across multiple fields
        if search:
            s = f"%{search.strip().lower()}%"
            query = query.outerjoin(Lead.account).outerjoin(Lead.contact).filter(
                or_(
                    func.lower(Lead.lead_id).like(s),
                    func.lower(Lead.lead_name).like(s),
                    func.lower(Lead.requested_product_service).like(s),
                    func.lower(Lead.location).like(s),
                    func.lower(Lead.site_name).like(s),
                    func.lower(Contact.name).like(s),
                    func.lower(Contact.email).like(s),
                    func.lower(Account.name).like(s)
                )
            )

        total_count = query.count()

        # 4. Allowlisted Sorting
        sortable_fields = {
            "created_at": Lead.created_at,
            "lead_id": Lead.lead_id,
            "lead_name": Lead.lead_name,
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
                joinedload(Lead.created_by)
            )
            .filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id))
            .first()
        )
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        return self._format_lead(lead)

    def _format_lead(self, lead: Lead) -> Dict[str, Any]:
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

        return {
            "id": lead.id,
            "leadId": lead.lead_id,
            "leadName": lead.lead_name,
            "businessArea": lead.business_area,
            "requirementType": lead.requirement_type,
            "requirementSummary": lead.requirement_summary,
            "requestedProductService": lead.requested_product_service,
            "leadSource": lead.lead_source,
            "lifecycleStatus": lead.lifecycle_status,
            "communicationChannel": lead.communication_channel,
            "remarks": lead.remarks,
            "nextFollowUpDate": lead.next_follow_up_date.isoformat() if lead.next_follow_up_date else None,
            "nextFollowUpAction": lead.next_follow_up_action,
            "lastConnectedDate": lead.last_connected_date.isoformat() if lead.last_connected_date else None,
            "websiteLink": lead.website_link,
            "location": lead.location,
            "siteName": lead.site_name,
            "createdAt": lead.created_at.isoformat() if lead.created_at else None,
            "updatedAt": lead.updated_at.isoformat() if lead.updated_at else None,
            "accountId": lead.account_id,
            "accountName": lead.account.name if lead.account else None,
            "contactId": lead.contact_id,
            "contactName": lead.contact.name if lead.contact else None,
            "contactEmail": lead.contact.email if lead.contact else None,
            "contactPhone": lead.contact.mobile_number if lead.contact else None,
            "assignedToUserId": lead.assigned_to_user_id,
            "assignedToName": lead.assigned_to.name if lead.assigned_to else None,
            "assignedToEmail": lead.assigned_to.email if lead.assigned_to else None,
            "createdById": lead.created_by_id,
            "createdByName": lead.created_by.name if lead.created_by else None,
            "account": account_obj,
            "contact": contact_obj,
            "assignedTo": assigned_to_obj,
            "createdBy": created_by_obj
        }


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
                "leadId": c.lead_id,
                "communicationDate": c.communication_date.isoformat() if c.communication_date else None,
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
            channel=payload.channel.strip(),
            event_type=payload.eventType.strip(),
            summary=payload.summary.strip() if payload.summary else None,
            outcome=payload.outcome.strip() if payload.outcome else None,
            next_action=payload.nextAction.strip() if payload.nextAction else None,
            follow_up_date=payload.followUpDate,
            created_by_id=str(actor.id) if actor.id else None
        )
        self.db.add(comm)

        # Update last_connected_date ONLY if qualifying client interaction
        if is_qualifying_client_interaction(payload.eventType):
            lead.last_connected_date = comm_date

        # Update follow-up info if provided
        if payload.followUpDate:
            lead.next_follow_up_date = payload.followUpDate
            if payload.nextAction:
                lead.next_follow_up_action = payload.nextAction.strip()

        # Update summary remarks without deleting communication history
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
                "leadNumber": lead.lead_id,
                "communicationCode": comm.communication_id,
                "eventType": comm.event_type,
                "details": f"Logged interaction '{comm.event_type}' for Lead '{lead.lead_id}'."
            }
        )

        return {
            "id": comm.id,
            "communicationId": comm.communication_id,
            "leadId": comm.lead_id,
            "communicationDate": comm.communication_date.isoformat() if comm.communication_date else None,
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
    # 6. DASHBOARD METRICS SERVICES
    # =========================================================================

    def get_dashboard_metrics(self, actor: CurrentUser) -> Dict[str, Any]:
        """
        Calculates live dashboard metrics from database:
        - Total Leads
        - Open Leads
        - Qualified Leads
        - Disqualified Leads
        - My Leads
        - Follow-ups Due (within next 24 hours)
        - Overdue Follow-ups (before current UTC time)
        """
        now = datetime.now(timezone.utc)
        due_window = now + timedelta(hours=24)

        total_leads = self.db.query(func.count(Lead.id)).scalar() or 0
        open_leads = self.db.query(func.count(Lead.id)).filter(Lead.lifecycle_status == "Open").scalar() or 0
        qualified_leads = self.db.query(func.count(Lead.id)).filter(Lead.lifecycle_status == "Qualified").scalar() or 0
        disqualified_leads = self.db.query(func.count(Lead.id)).filter(Lead.lifecycle_status == "Disqualified").scalar() or 0

        my_leads = self.db.query(func.count(Lead.id)).filter(
            Lead.assigned_to_user_id == str(actor.id)
        ).scalar() or 0

        follow_ups_due = self.db.query(func.count(Lead.id)).filter(
            Lead.lifecycle_status == "Open",
            Lead.next_follow_up_date.isnot(None),
            Lead.next_follow_up_date <= due_window,
            Lead.next_follow_up_date >= now - timedelta(hours=2)
        ).scalar() or 0

        overdue_follow_ups = self.db.query(func.count(Lead.id)).filter(
            Lead.lifecycle_status == "Open",
            Lead.next_follow_up_date.isnot(None),
            Lead.next_follow_up_date < now
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
        """
        Returns list of active portal users who have active CRM membership with an eligible CRM role.
        """
        crm_mod = self._get_crm_module()
        memberships = (
            self.db.query(UserModuleMembership)
            .options(
                joinedload(UserModuleMembership.user),
                joinedload(UserModuleMembership.role)
            )
            .filter(
                UserModuleMembership.module_id == crm_mod.id,
                UserModuleMembership.is_active == True
            )
            .all()
        )

        results = []
        for mem in memberships:
            if mem.user and mem.user.status == "active" and not mem.user.is_hard_deleted:
                if mem.role and mem.role.code.startswith("CRM_"):
                    results.append({
                        "id": mem.user.id,
                        "name": mem.user.name or mem.user.username,
                        "username": mem.user.username,
                        "email": mem.user.email,
                        "roleCode": mem.role.code,
                        "roleName": mem.role.name
                    })
        return sorted(results, key=lambda x: x["name"])


# For backward compatibility
CrmUserHubService = CrmService
