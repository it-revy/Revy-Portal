import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.dependencies import CurrentUser
from app.core.exceptions import PermissionDeniedError, ValidationError
from app.modules.model import Module, ModuleRole
from app.roles.model import Role

logger = logging.getLogger("revy.roles.assignment")

RETIRED_ROLES = {"BMS_DIRECTOR_ANALYTICS", "DIRECTOR_ANALYTICS"}

class RoleAssignmentService:
    @staticmethod
    def get_assignable_roles_for_module(actor: CurrentUser, module_code: str, db: Session) -> List[Dict[str, Any]]:
        """
        Returns active roles of module_code that the actor is authorized to assign.
        """
        mod_upper = module_code.strip().upper()
        mod = db.query(Module).filter(Module.code == mod_upper).first()
        if not mod:
            return []

        all_active_roles = (
            db.query(ModuleRole)
            .filter(ModuleRole.module_id == mod.id, ModuleRole.is_active == True)
            .all()
        )
        # Exclude retired roles permanently
        all_active_roles = [r for r in all_active_roles if r.code not in RETIRED_ROLES]

        actor_roles = [r.upper().replace(" ", "_") for r in (actor.roles or [])]
        is_global_admin = actor.is_global_admin or "*" in (actor.permissions or []) or "IT_ADMIN" in actor_roles or "DIRECTOR" in actor_roles

        if mod_upper == "BMS":
            if is_global_admin:
                allowed_codes = {"BMS_EMPLOYEE", "BMS_BF_MANAGER", "BMS_ADMIN", "BMS_FINANCE_MANAGER"}
            elif "BMS_ADMIN" in actor_roles or "BREAKFAST_ADMIN" in actor_roles:
                allowed_codes = {"BMS_EMPLOYEE", "BMS_BF_MANAGER", "BMS_ADMIN"}
            elif "BMS_BF_MANAGER" in actor_roles:
                allowed_codes = {"BMS_EMPLOYEE", "BMS_BF_MANAGER"}
            else:
                allowed_codes = set()

            return [
                {
                    "id": r.id,
                    "code": r.code,
                    "name": r.name,
                    "description": r.description,
                    "moduleId": r.module_id,
                    "isActive": r.is_active
                }
                for r in all_active_roles if r.code in allowed_codes
            ]
        else:
            # Other modules (CRM, LMS, IMS, etc.)
            if is_global_admin:
                return [
                    {
                        "id": r.id,
                        "code": r.code,
                        "name": r.name,
                        "description": r.description,
                        "moduleId": r.module_id,
                        "isActive": r.is_active
                    }
                    for r in all_active_roles
                ]
            mod_admin_role = f"{mod_upper}_ADMIN"
            if mod_admin_role in actor_roles:
                return [
                    {
                        "id": r.id,
                        "code": r.code,
                        "name": r.name,
                        "description": r.description,
                        "moduleId": r.module_id,
                        "isActive": r.is_active
                    }
                    for r in all_active_roles
                ]
            return []

    @staticmethod
    def get_assignable_global_roles(actor: CurrentUser, db: Session) -> List[Dict[str, Any]]:
        actor_roles = [r.upper().replace(" ", "_") for r in (actor.roles or [])]
        is_global_admin = actor.is_global_admin or "*" in (actor.permissions or []) or "IT_ADMIN" in actor_roles or "DIRECTOR" in actor_roles
        if not is_global_admin:
            return []
        roles = db.query(Role).filter(Role.code.in_(["IT_ADMIN", "DIRECTOR"])).all()
        return [
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "description": r.description
            }
            for r in roles
        ]

    @staticmethod
    def validate_role_assignment(
        actor: CurrentUser,
        target_module_code: str,
        target_role_code: str,
        target_user_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> None:
        """
        Enforces authority matrix:
        - BMS BF Manager -> only BMS_EMPLOYEE, BMS_BF_MANAGER
        - BMS Admin -> only BMS_EMPLOYEE, BMS_BF_MANAGER, BMS_ADMIN
        - Global Admin -> permitted across modules
        - Blocks self-escalation, cross-module escalation, and retired roles
        """
        mod_code = target_module_code.strip().upper()
        role_code = target_role_code.strip().upper()

        # Handle aliases
        if mod_code == "BMS":
            if role_code in ["EMPLOYEE", "STANDARD_EMPLOYEE"]:
                role_code = "BMS_EMPLOYEE"
            elif role_code in ["BREAKFAST_ADMIN", "ADMIN"]:
                role_code = "BMS_ADMIN"
            elif role_code in ["FINANCE_MANAGER"]:
                role_code = "BMS_FINANCE_MANAGER"

        # Check retired role
        if role_code in RETIRED_ROLES:
            raise ValidationError("BMS Director Analytics has been retired and cannot be assigned.")

        actor_roles = [r.upper().replace(" ", "_") for r in (actor.roles or [])]
        is_global_admin = actor.is_global_admin or "*" in (actor.permissions or []) or "IT_ADMIN" in actor_roles or "DIRECTOR" in actor_roles

        # Self-escalation check: Non-global users cannot modify or escalate their own roles
        if target_user_id and actor.id and str(target_user_id) == str(actor.id):
            if not is_global_admin:
                raise PermissionDeniedError("Users cannot modify or escalate their own roles.")

        if is_global_admin:
            return

        if mod_code == "BMS":
            is_bms_admin = "BMS_ADMIN" in actor_roles or "BREAKFAST_ADMIN" in actor_roles
            is_bf_manager = "BMS_BF_MANAGER" in actor_roles

            if is_bms_admin:
                permitted = {"BMS_EMPLOYEE", "BMS_BF_MANAGER", "BMS_ADMIN"}
                if role_code not in permitted:
                    if role_code in ["BMS_FINANCE_MANAGER", "FINANCE_MANAGER"]:
                        raise PermissionDeniedError("BMS Admin is not authorized to assign BMS Finance Manager role.")
                    if role_code in ["IT_ADMIN", "DIRECTOR"]:
                        raise PermissionDeniedError("BMS Admin cannot assign global administrator roles.")
                    raise PermissionDeniedError(f"BMS Admin is not authorized to assign role '{target_role_code}'.")
            elif is_bf_manager:
                permitted = {"BMS_EMPLOYEE", "BMS_BF_MANAGER"}
                if role_code not in permitted:
                    if role_code in ["BMS_ADMIN", "BREAKFAST_ADMIN"]:
                        raise PermissionDeniedError("BMS BF Manager is not authorized to assign BMS Admin role.")
                    if role_code in ["BMS_FINANCE_MANAGER", "FINANCE_MANAGER"]:
                        raise PermissionDeniedError("BMS BF Manager is not authorized to assign BMS Finance Manager role.")
                    if role_code in ["IT_ADMIN", "DIRECTOR"]:
                        raise PermissionDeniedError("BMS BF Manager cannot assign global administrator roles.")
                    raise PermissionDeniedError(f"BMS BF Manager is not authorized to assign role '{target_role_code}'.")
            else:
                raise PermissionDeniedError("You do not have permission to assign BMS roles.")
        else:
            # Non-global actor trying to assign role in other modules (CRM, LMS, etc.)
            mod_admin_role = f"{mod_code}_ADMIN"
            if mod_admin_role not in actor_roles:
                raise PermissionDeniedError(f"You are not authorized to assign roles in module '{mod_code}'.")

    @staticmethod
    def validate_global_role_assignment(
        actor: CurrentUser,
        target_role_codes: List[str],
        target_user_id: Optional[str] = None
    ) -> None:
        """
        Enforces that only global administrators can assign global roles (IT_ADMIN, DIRECTOR).
        """
        clean_target_roles = [r.upper().replace(" ", "_") for r in target_role_codes if r]
        global_targets = [r for r in clean_target_roles if r in ["IT_ADMIN", "DIRECTOR", "CEO"]]

        if not global_targets:
            return

        actor_roles = [r.upper().replace(" ", "_") for r in (actor.roles or [])]
        is_global_admin = actor.is_global_admin or "*" in (actor.permissions or []) or "IT_ADMIN" in actor_roles or "DIRECTOR" in actor_roles

        if not is_global_admin:
            raise PermissionDeniedError("Only Global IT Administrators and Directors can assign global system roles.")

        if target_user_id and actor.id and str(target_user_id) == str(actor.id) and not is_global_admin:
            raise PermissionDeniedError("Self-escalation to global administrator is strictly prohibited.")
