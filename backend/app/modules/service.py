from typing import List, Dict, Any, Optional
from fastapi import Request
from sqlalchemy.orm import Session
from app.modules.model import Module, ModuleRole, UserModuleMembership
from app.users.model import User
from app.employees.model import Employee
from app.core.exceptions import NotFoundError, ValidationError
from app.audit.service import AuditService

class ModuleService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def list_modules(self, only_active: bool = True) -> List[Dict[str, Any]]:
        query = self.db.query(Module)
        if only_active:
            query = query.filter(Module.is_active == True)
        modules = query.order_by(Module.code.asc()).all()
        result = []
        for m in modules:
            roles = [
                {
                    "id": r.id,
                    "moduleId": r.module_id,
                    "code": r.code,
                    "name": r.name,
                    "description": r.description,
                    "isActive": r.is_active
                }
                for r in m.roles if not only_active or r.is_active
            ]
            result.append({
                "id": m.id,
                "code": m.code,
                "name": m.name,
                "description": m.description,
                "isActive": m.is_active,
                "isOpenToAll": m.is_open_to_all,
                "roles": roles
            })
        return result

    def get_module_roles(self, module_identifier: str) -> List[Dict[str, Any]]:
        mod = self.db.query(Module).filter(
            (Module.id == module_identifier) | (Module.code == module_identifier.upper())
        ).first()
        if not mod:
            raise NotFoundError(f"Module '{module_identifier}' not found")
        return [
            {
                "id": r.id,
                "moduleId": r.module_id,
                "code": r.code,
                "name": r.name,
                "description": r.description,
                "isActive": r.is_active
            }
            for r in mod.roles if r.is_active
        ]

    def get_user_module_memberships(self, user_id: str) -> List[Dict[str, Any]]:
        user = self.db.query(User).filter(User.id == user_id, User.is_hard_deleted == False).first()
        if not user:
            raise NotFoundError(f"User with ID '{user_id}' not found")

        all_modules = self.db.query(Module).filter(Module.is_active == True).order_by(Module.code.asc()).all()
        existing_memberships = {m.module_id: m for m in user.module_memberships}

        result = []
        for mod in all_modules:
            membership = existing_memberships.get(mod.id)
            is_enabled = bool(membership and membership.is_active) or mod.is_open_to_all
            role_id = membership.role.id if (membership and membership.role) else None
            role_code = membership.role.code if (membership and membership.role) else None
            role_name = membership.role.name if (membership and membership.role) else None

            result.append({
                "moduleId": mod.id,
                "moduleCode": mod.code,
                "moduleName": mod.name,
                "isOpenToAll": mod.is_open_to_all,
                "isEnabled": is_enabled,
                "roleId": role_id,
                "roleCode": role_code,
                "roleName": role_name
            })
        return result

    def update_user_module_memberships(
        self,
        user_id: str,
        assignments: List[dict],
        request: Optional[Request] = None
    ) -> List[Dict[str, Any]]:
        user = self.db.query(User).filter(User.id == user_id, User.is_hard_deleted == False).first()
        if not user:
            raise NotFoundError(f"User with ID '{user_id}' not found")

        changes_logged = []

        for item in assignments:
            mod_id = item.get("moduleId")
            mod_code = item.get("moduleCode")
            enabled = bool(item.get("enabled", False))
            role_id = item.get("roleId")
            role_code = item.get("roleCode")

            # Resolve module
            mod_query = self.db.query(Module)
            if mod_id:
                mod = mod_query.filter(Module.id == mod_id).first()
            elif mod_code:
                mod = mod_query.filter(Module.code == mod_code.upper()).first()
            else:
                continue

            if not mod:
                continue

            # If module is open to all, it cannot be disabled
            if mod.is_open_to_all:
                continue

            # Resolve role if provided
            role = None
            if enabled and (role_id or role_code):
                role_query = self.db.query(ModuleRole).filter(ModuleRole.module_id == mod.id)
                if role_id:
                    role = role_query.filter(ModuleRole.id == role_id).first()
                elif role_code:
                    role = role_query.filter(ModuleRole.code == role_code.upper()).first()

                if not role and mod.roles:
                    # Default to first active role if invalid
                    role = next((r for r in mod.roles if r.is_active), None)

            # Find existing membership
            membership = self.db.query(UserModuleMembership).filter(
                UserModuleMembership.user_id == user.id,
                UserModuleMembership.module_id == mod.id
            ).first()

            if enabled:
                if not membership:
                    membership = UserModuleMembership(
                        user_id=user.id,
                        module_id=mod.id,
                        role_id=role.id if role else None,
                        is_active=True
                    )
                    self.db.add(membership)
                    changes_logged.append(f"Added to {mod.code} with role {role.name if role else 'None'}")
                else:
                    membership.is_active = True
                    if role:
                        membership.role_id = role.id
                    changes_logged.append(f"Updated {mod.code} membership to role {role.name if role else 'None'}")

                # If module is BMS, ensure corresponding Employee record exists for BMS integration
                if mod.code == "BMS":
                    self._ensure_bms_employee(user, role)
            else:
                if membership:
                    membership.is_active = False
                    changes_logged.append(f"Removed from {mod.code}")
                    # If BMS, deactivate employee participation rather than deleting
                    if mod.code == "BMS" and user.employee:
                        user.employee.status = "inactive"

        self.db.commit()

        # Audit log if request is provided
        if changes_logged:
            performed_by_id = None
            performed_by_name = None
            role_used = None
            if request and hasattr(request.state, "current_user") and request.state.current_user:
                cu = request.state.current_user
                performed_by_id = cu.employee_id or cu.username
                performed_by_name = cu.name or cu.username
                role_used = cu.active_role

            self.audit_service.log(
                action="USER_MODULES_UPDATED",
                request=request,
                target_info={
                    "targetUserId": user.id,
                    "targetUsername": user.username,
                    "changes": "; ".join(changes_logged)
                },
                performed_by_employee_id=performed_by_id,
                performed_by_name=performed_by_name,
                role_used=role_used
            )

        return self.get_user_module_memberships(user.id)

    def _ensure_bms_employee(self, user: User, role: Optional[ModuleRole]):
        """Creates or updates an Employee record when user is assigned to BMS."""
        from app.employees.repository import EmployeeRepository
        repo = EmployeeRepository(self.db)
        emp = user.employee
        if not emp:
            emp_id = repo.generate_next_employee_id()
            emp = Employee(
                user_id=user.id,
                employee_id=emp_id,
                name=user.name or user.username,
                email=user.email,
                phone=user.phone or "",
                department="General",
                designation=role.name if role else "Employee",
                status="active",
                breakfast_participation_type="NORMAL",
                is_hard_deleted=False
            )
            self.db.add(emp)
        else:
            emp.status = "active"
            if not emp.name and user.name:
                emp.name = user.name
            if not emp.phone and user.phone:
                emp.phone = user.phone
