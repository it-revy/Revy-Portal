import re
import json
from typing import List, Optional, Dict, Any
from fastapi import Request
from sqlalchemy.orm import Session
from app.employees.repository import EmployeeRepository
from app.employees.model import Employee, Department
from app.users.model import User
from app.core.security import get_password_hash
from app.core.exceptions import ValidationError, NotFoundError
from app.audit.service import AuditService

class EmployeeService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmployeeRepository(db)
        self.audit_service = AuditService(db)

    def serialize_employee(self, emp: Employee) -> Dict[str, Any]:
        user = emp.user
        roles = [r.code for r in user.roles] if user else []
        return {
            "_id": emp.id,
            "id": emp.id,
            "employeeId": emp.employee_id,
            "username": user.username if user else "",
            "name": emp.name,
            "email": emp.email,
            "phone": emp.phone or "",
            "department": emp.department,
            "designation": emp.designation,
            "status": emp.status,
            "roles": roles,
            "breakfastParticipationType": emp.breakfast_participation_type,
            "forcePasswordChange": bool(user.force_password_change) if user else False,
            "createdAt": emp.created_at.isoformat() if emp.created_at else None,
            "updatedAt": emp.updated_at.isoformat() if emp.updated_at else None
        }

    def create_employee(self, data: dict, request: Optional[Request] = None) -> Dict[str, Any]:
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        department = data.get("department", "").strip()
        designation = data.get("designation", "").strip()

        if not name or not email or not department or not designation:
            raise ValidationError("Name, email, department, and designation are required")

        raw_username = data.get("username")
        if not raw_username:
            raw_username = email.split("@")[0] if "@" in email else name
        raw_username = re.sub(r"[^a-z0-9._-]", "", raw_username.lower().strip())
        if not raw_username:
            raise ValidationError("Valid username is required")

        existing_user = self.repo.get_by_username(raw_username)
        if existing_user:
            raise ValidationError(f'Username "{raw_username}" is already taken')

        existing_email = self.repo.get_by_email(email)
        if existing_email:
            raise ValidationError(f"Email {email} is already registered")

        employee_id = data.get("employeeId")
        if employee_id:
            employee_id = employee_id.strip().upper()
        else:
            employee_id = self.repo.generate_next_employee_id()

        existing_emp = self.repo.get_by_employee_id(employee_id)
        if existing_emp:
            raise ValidationError(f"Employee ID {employee_id} already exists")

        raw_password = data.get("password") or "Password123!"
        password_hash = get_password_hash(raw_password)

        role_codes = data.get("roles") or ["EMPLOYEE"]
        if not isinstance(role_codes, list) or len(role_codes) == 0:
            role_codes = ["EMPLOYEE"]
        roles = self.repo.get_roles_by_codes(role_codes)

        status_val = data.get("status") or "active"
        participation_type = data.get("breakfastParticipationType") or "NORMAL"

        user = User(
            username=raw_username,
            email=email,
            password_hash=password_hash,
            status=status_val,
            force_password_change=True,
            is_hard_deleted=False
        )
        user.roles = roles
        self.db.add(user)
        self.db.flush()

        employee = Employee(
            user_id=user.id,
            employee_id=employee_id,
            name=name,
            email=email,
            phone=data.get("phone", "").strip() if data.get("phone") else "",
            department=department,
            designation=designation,
            status=status_val,
            breakfast_participation_type=participation_type,
            is_hard_deleted=False
        )
        self.db.add(employee)
        self.db.commit()
        self.db.refresh(employee)

        serialized = self.serialize_employee(employee)

        self.audit_service.log(
            action="EMPLOYEE_CREATED",
            request=request,
            target_info={
                "targetEmployeeId": employee.employee_id,
                "targetUsername": user.username,
                "targetEmployeeName": employee.name,
                "details": "Created new employee account"
            },
            after_state=serialized
        )

        return serialized

    def update_employee(self, employee_id: str, data: dict, request: Optional[Request] = None) -> Dict[str, Any]:
        emp = self.repo.get_by_employee_id(employee_id)
        if not emp:
            raise NotFoundError("Employee not found")

        user = emp.user
        before_state = self.serialize_employee(emp)

        new_username = data.get("username")
        if new_username and new_username.strip().lower() != user.username:
            norm_user = new_username.strip().lower()
            existing_user = self.db.query(User).filter(User.username == norm_user, User.id != user.id).first()
            if existing_user:
                raise ValidationError(f'Username "{norm_user}" is already in use')
            user.username = norm_user

        if "name" in data and data["name"]:
            emp.name = data["name"].strip()
        if "email" in data and data["email"]:
            norm_email = data["email"].strip().lower()
            emp.email = norm_email
            user.email = norm_email
        if "phone" in data and data["phone"] is not None:
            emp.phone = data["phone"].strip()
        if "department" in data and data["department"]:
            emp.department = data["department"].strip()
        if "designation" in data and data["designation"]:
            emp.designation = data["designation"].strip()
        if "status" in data and data["status"]:
            emp.status = data["status"]
            user.status = data["status"]
        if "breakfastParticipationType" in data and data["breakfastParticipationType"]:
            emp.breakfast_participation_type = data["breakfastParticipationType"]
        if "roles" in data and isinstance(data["roles"], list):
            roles = self.repo.get_roles_by_codes(data["roles"])
            user.roles = roles

        self.db.commit()
        self.db.refresh(emp)

        after_state = self.serialize_employee(emp)

        # Audit events
        actions = []
        if before_state["username"] != after_state["username"]:
            actions.append("USERNAME_UPDATED")
        if before_state["status"] != after_state["status"]:
            actions.append("EMPLOYEE_ACTIVATED" if after_state["status"] == "active" else "EMPLOYEE_DEACTIVATED")
        if before_state["breakfastParticipationType"] != after_state["breakfastParticipationType"]:
            actions.append("PARTICIPATION_TYPE_CHANGED")
        if json.dumps(before_state["roles"]) != json.dumps(after_state["roles"]):
            actions.append("EMPLOYEE_ROLES_UPDATED")
        if not actions:
            actions.append("EMPLOYEE_UPDATED")

        for act in actions:
            self.audit_service.log(
                action=act,
                request=request,
                target_info={
                    "targetEmployeeId": emp.employee_id,
                    "targetUsername": user.username,
                    "targetEmployeeName": emp.name,
                    "details": f"Updated {act}"
                },
                before_state=before_state,
                after_state=after_state
            )

        return after_state

    def deactivate_employee(self, employee_id: str, request: Optional[Request] = None) -> Dict[str, Any]:
        emp = self.repo.get_by_employee_id(employee_id)
        if not emp:
            raise NotFoundError("Employee not found")

        before_state = self.serialize_employee(emp)
        emp.status = "inactive"
        if emp.user:
            emp.user.status = "inactive"
        self.db.commit()
        self.db.refresh(emp)

        after_state = self.serialize_employee(emp)

        self.audit_service.log(
            action="EMPLOYEE_DEACTIVATED",
            request=request,
            target_info={
                "targetEmployeeId": emp.employee_id,
                "targetEmployeeName": emp.name,
                "details": "Deactivated employee account (Soft Delete)"
            },
            before_state=before_state,
            after_state=after_state
        )

        return after_state

    def reset_password(self, employee_id: str, new_pwd: str, confirm_pwd: str, request: Optional[Request] = None) -> None:
        if not new_pwd or not confirm_pwd:
            raise ValidationError("New password and confirm password are required")
        if len(new_pwd) < 6:
            raise ValidationError("Password must be at least 6 characters long")
        if new_pwd != confirm_pwd:
            raise ValidationError("New password and confirm password do not match")

        emp = self.repo.get_by_employee_id(employee_id)
        if not emp or not emp.user:
            raise NotFoundError("Employee not found")

        emp.user.password_hash = get_password_hash(new_pwd)
        self.db.commit()

        self.audit_service.log(
            action="PASSWORD_CHANGED_BY_ADMIN",
            request=request,
            target_info={
                "targetEmployeeId": emp.employee_id,
                "targetUsername": emp.user.username,
                "targetEmployeeName": emp.name,
                "details": f"Password reset for user {emp.user.username} ({emp.employee_id}) by Admin"
            }
        )

    def hard_delete_employee(self, employee_id: str, confirm_code: str, request: Optional[Request] = None) -> None:
        if confirm_code != "CONFIRM_PERMANENT_DELETE":
            raise ValidationError('Permanent deletion requires explicit confirmation code "CONFIRM_PERMANENT_DELETE".')

        emp = self.repo.get_by_employee_id(employee_id, include_deleted=True)
        if not emp:
            raise NotFoundError("Employee not found")

        before_state = self.serialize_employee(emp)
        emp.is_hard_deleted = True
        emp.status = "inactive"
        if emp.user:
            emp.user.is_hard_deleted = True
            emp.user.status = "inactive"
        self.db.commit()

        self.audit_service.log(
            action="EMPLOYEE_HARD_DELETED",
            request=request,
            target_info={
                "targetEmployeeId": emp.employee_id,
                "targetEmployeeName": emp.name,
                "details": "PERMANENT HARD DELETE executed by IT_ADMIN"
            },
            before_state=before_state,
            after_state={"isHardDeleted": True}
        )
