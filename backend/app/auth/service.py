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

        if not user or not user.employee:
            raise AuthenticationError("Invalid username or password")

        if user.status != "active":
            raise PermissionDeniedError("Account is deactivated. Contact IT Administrator.")

        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password")

        roles_list = [r.code for r in user.roles]
        permissions_by_role = {}
        permissions_set = set()

        for r in user.roles:
            r_perms = [p.code for p in r.permissions]
            permissions_by_role[r.code] = r_perms
            for p in r_perms:
                permissions_set.add(p)

        permissions_list = list(permissions_set)

        payload = {
            "employeeId": user.employee.employee_id,
            "username": user.username,
            "name": user.employee.name,
            "roles": roles_list
        }

        token = create_access_token(payload)

        user_profile = {
            "employeeId": user.employee.employee_id,
            "username": user.username,
            "name": user.employee.name,
            "email": user.email,
            "phone": user.employee.phone or "",
            "department": user.employee.department,
            "designation": user.employee.designation,
            "status": user.status,
            "roles": roles_list,
            "breakfastParticipationType": user.employee.breakfast_participation_type,
            "forcePasswordChange": bool(user.force_password_change),
            "permissions": permissions_list,
            "permissionsByRole": permissions_by_role
        }

        # Audit login event
        self.audit_service.log(
            action="USER_LOGIN",
            request=request,
            target_info={
                "targetEmployeeId": user.employee.employee_id,
                "targetUsername": user.username,
                "details": "User logged in successfully"
            },
            performed_by_employee_id=user.employee.employee_id,
            performed_by_name=user.employee.name,
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
