from typing import Dict, Any, Tuple
from fastapi import Request
from sqlalchemy.orm import Session
from app.users.model import User
from app.employees.model import Employee
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.exceptions import AuthenticationError, PermissionDeniedError, ValidationError, NotFoundError
from app.audit.service import AuditService

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def login(self, username_input: str, password: str, request: Request) -> Tuple[str, Dict[str, Any]]:
        input_id = (username_input or "").strip().lower()
        if not input_id or not password:
            raise ValidationError("Username and password are required")

        user = self.db.query(User).filter(
            User.username == input_id,
            User.is_hard_deleted == False
        ).first()

        if not user:
            raise AuthenticationError("Invalid username or password")

        if user.status != "active":
            raise PermissionDeniedError("Account is deactivated. Contact IT Administrator.")

        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password")

        from app.core.dependencies import ALL_SYSTEM_MODULES
        from app.roles.model import Permission

        # 1. Determine Global Roles
        user_global_role_codes = [r.code for r in user.roles]
        is_it_admin = "IT_ADMIN" in user_global_role_codes
        is_director = "DIRECTOR" in user_global_role_codes or "CEO" in user_global_role_codes
        is_global_admin = is_it_admin or is_director

        roles_list = []
        permissions_by_role = {}
        permissions_set = set()

        # Add direct / global roles
        for r in user.roles:
            if r.code and r.code not in roles_list:
                roles_list.append(r.code)
            if r.name and r.name not in roles_list:
                roles_list.append(r.name)

            r_perms = [p.code for p in r.permissions] if r.permissions else []
            permissions_by_role[r.code] = r_perms
            if r.name:
                permissions_by_role[r.name] = r_perms
            for p in r_perms:
                permissions_set.add(p)

        # 2. Add Module Roles from Active Memberships
        for m in user.module_memberships:
            if m.is_active and m.module:
                if m.role:
                    if m.role.code not in roles_list:
                        roles_list.append(m.role.code)
                    if m.role.name and m.role.name not in roles_list:
                        roles_list.append(m.role.name)

                    r_perms = [p.code for p in m.role.permissions] if m.role.permissions else []
                    permissions_by_role[m.role.code] = r_perms
                    if m.role.name:
                        permissions_by_role[m.role.name] = r_perms
                    for p in r_perms:
                        permissions_set.add(p)

        # 3. Global Administrators Override: Full System Access across all modules & permissions
        if is_global_admin:
            permissions_set.add("*")
            all_db_perms = [p.code for p in self.db.query(Permission).all()]
            for p in all_db_perms:
                permissions_set.add(p)
            if is_it_admin:
                permissions_by_role["IT_ADMIN"] = list(permissions_set)
                permissions_by_role["IT Admin"] = list(permissions_set)
            if is_director:
                permissions_by_role["DIRECTOR"] = list(permissions_set)
                permissions_by_role["Director"] = list(permissions_set)
                roles_list.extend(["CEO", "Chief Executive Officer"])
                permissions_by_role["CEO"] = list(permissions_set)

        permissions_list = list(permissions_set)

        modules_list = [
            {
                "moduleCode": m.module.code,
                "moduleName": m.module.name,
                "isOpenToAll": m.module.is_open_to_all,
                "roleCode": m.role.code if m.role else None,
                "roleName": m.role.name if m.role else None
            }
            for m in user.module_memberships if m.is_active and m.module
        ]

        if is_global_admin:
            existing_mod_codes = {m["moduleCode"] for m in modules_list}
            for mod_code in ALL_SYSTEM_MODULES:
                if mod_code not in existing_mod_codes:
                    modules_list.append({
                        "moduleCode": mod_code,
                        "moduleName": mod_code,
                        "isOpenToAll": True,
                        "roleCode": "IT_ADMIN" if is_it_admin else "DIRECTOR",
                        "roleName": "Global Administrator"
                    })

        emp = user.employee
        display_name = user.name or (emp.name if emp else user.username)
        emp_id = emp.employee_id if emp else ""

        payload = {
            "userId": user.id,
            "employeeId": emp_id,
            "username": user.username,
            "name": display_name,
            "roles": roles_list
        }

        token = create_access_token(payload)

        user_profile = {
            "id": user.id,
            "employeeId": emp_id,
            "username": user.username,
            "name": display_name,
            "email": user.email,
            "phone": user.phone or (emp.phone if emp else ""),
            "department": emp.department if emp else "",
            "designation": emp.designation if emp else "",
            "status": user.status,
            "managerId": user.manager_id,
            "managerName": user.manager.name if user.manager else None,
            "roles": roles_list,
            "modules": modules_list,
            "breakfastParticipationType": emp.breakfast_participation_type if emp else "NORMAL",
            "forcePasswordChange": bool(user.force_password_change),
            "permissions": permissions_list,
            "permissionsByRole": permissions_by_role
        }

        # Audit login event
        self.audit_service.log(
            action="USER_LOGIN",
            request=request,
            target_info={
                "targetEmployeeId": emp_id or user.username,
                "targetUsername": user.username,
                "details": "User logged in successfully"
            },
            performed_by_employee_id=emp_id or user.username,
            performed_by_name=display_name,
            role_used=roles_list[0] if roles_list else "EMPLOYEE"
        )

        return token, user_profile

    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        confirm_password: str,
        request: Request
    ) -> None:
        if not new_password or len(new_password) < 6:
            raise ValidationError("New password must be at least 6 characters long")

        if confirm_password and new_password != confirm_password:
            raise ValidationError("New password and confirmation do not match")

        user = self.db.query(User).filter(User.id == user_id, User.is_hard_deleted == False).first()
        if not user:
            raise NotFoundError("User account not found")

        # If not in forced mode, verify current password
        if not user.force_password_change and current_password:
            if not verify_password(current_password, user.password_hash):
                raise ValidationError("Current password is incorrect")

        user.password_hash = get_password_hash(new_password)
        user.force_password_change = False
        self.db.commit()

        self.audit_service.log(
            action="PASSWORD_CHANGED",
            request=request,
            target_info={
                "targetEmployeeId": user.employee.employee_id if user.employee else user.username,
                "targetUsername": user.username,
                "details": "User changed their account password"
            },
            performed_by_employee_id=user.employee.employee_id if user.employee else user.username,
            performed_by_name=user.employee.name if user.employee else user.username,
            role_used="EMPLOYEE"
        )
