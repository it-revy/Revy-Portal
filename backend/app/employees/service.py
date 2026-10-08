import re
import json
from typing import List, Optional, Dict, Any
from fastapi import Request
from sqlalchemy.orm import Session
from app.employees.repository import EmployeeRepository
from app.employees.model import Employee, Department
from app.users.model import User
from app.modules.model import Module, ModuleRole, UserModuleMembership
from app.core.exceptions import ValidationError, NotFoundError
from app.audit.service import AuditService

class EmployeeService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmployeeRepository(db)
        self.audit_service = AuditService(db)

    def serialize_employee(self, emp: Employee) -> Dict[str, Any]:
        user = emp.user
        # Find active BMS module role if present
        bms_role_code = "BMS_EMPLOYEE"
        bms_role_name = "BMS Employee"
        if user:
            for m in user.module_memberships:
                if m.is_active and m.module and m.module.code == "BMS" and m.role:
                    bms_role_code = m.role.code
                    bms_role_name = m.role.name
                    break

        roles = [bms_role_code] if bms_role_code else ([r.code for r in user.roles] if user else [])

        return {
            "_id": emp.id,
            "id": emp.id,
            "userId": user.id if user else None,
            "employeeId": emp.employee_id,
            "username": user.username if user else "",
            "name": emp.name or (user.name if user else ""),
            "email": emp.email or (user.email if user else ""),
            "phone": emp.phone or (user.phone if user else ""),
            "department": emp.department,
            "designation": emp.designation,
            "status": emp.status,
            "bmsRoleCode": bms_role_code,
            "bmsRoleName": bms_role_name,
            "roles": roles,
            "breakfastParticipationType": emp.breakfast_participation_type,
            "createdAt": emp.created_at.isoformat() if emp.created_at else None,
            "updatedAt": emp.updated_at.isoformat() if emp.updated_at else None
        }

    def list_available_users_for_bms(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns active central users who do not currently have an active BMS membership or active BMS employee.
        """
        bms_mod = self.db.query(Module).filter(Module.code == "BMS").first()
        active_bms_user_ids = set()
        if bms_mod:
            active_mems = self.db.query(UserModuleMembership.user_id).filter(
                UserModuleMembership.module_id == bms_mod.id,
                UserModuleMembership.is_active == True
            ).all()
            active_bms_user_ids = {m[0] for m in active_mems}

        active_emps = self.db.query(Employee.user_id).filter(
            Employee.status == "active",
            Employee.is_hard_deleted == False
        ).all()
        active_emp_user_ids = {e[0] for e in active_emps if e[0]}

        excluded_ids = active_bms_user_ids.union(active_emp_user_ids)

        query = self.db.query(User).filter(
            User.is_hard_deleted == False,
            User.status == "active"
        )
        if excluded_ids:
            query = query.filter(User.id.notin_(excluded_ids))

        if search:
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                (User.name.ilike(term)) |
                (User.username.ilike(term)) |
                (User.email.ilike(term)) |
                (User.phone.ilike(term))
            )

        users = query.order_by(User.name.asc(), User.username.asc()).all()
        return [
            {
                "id": u.id,
                "name": u.name or u.username,
                "username": u.username,
                "email": u.email,
                "phone": u.phone or "",
                "department": u.employee.department if u.employee else "",
                "designation": u.employee.designation if u.employee else "",
                "status": u.status
            }
            for u in users
        ]

    def add_user_to_bms(self, data: dict, request: Optional[Request] = None) -> Dict[str, Any]:
        """
        Adds an existing Central User to BMS. Does NOT create a new system user.
        Strictly prevents duplicates.
        """
        user_id = data.get("userId") or data.get("user_id")
        if not user_id:
            raw_email = (data.get("email") or "").strip().lower()
            if raw_email:
                existing_u = self.db.query(User).filter(User.email == raw_email, User.is_hard_deleted == False).first()
                if existing_u:
                    user_id = existing_u.id

        if not user_id:
            raise ValidationError(
                "A valid existing Central User must be selected. BMS cannot create new system user accounts. "
                "Please create the user in Central User Management first."
            )

        user = self.db.query(User).filter(User.id == user_id, User.is_hard_deleted == False).first()
        if not user:
            raise NotFoundError("The specified Central User does not exist.")

        if user.status != "active":
            raise ValidationError("Cannot add an inactive Central User to BMS. Please activate the user account in User Management first.")

        bms_mod = self.db.query(Module).filter(Module.code == "BMS").first()
        if not bms_mod:
            raise ValidationError("BMS module is not initialized in the database.")

        # Duplicate Prevention Check
        existing_mem = self.db.query(UserModuleMembership).filter(
            UserModuleMembership.user_id == user.id,
            UserModuleMembership.module_id == bms_mod.id
        ).first()

        if existing_mem and existing_mem.is_active and user.employee and user.employee.status == "active" and not user.employee.is_hard_deleted:
            raise ValidationError(f'User "{user.name or user.username}" is already an active member of BMS.')

        # Resolve BMS Role
        target_role_code = (data.get("roleCode") or data.get("role") or "BMS_EMPLOYEE").strip().upper()
        # Handle role aliases
        if target_role_code in ["EMPLOYEE", "STANDARD_EMPLOYEE"]:
            target_role_code = "BMS_EMPLOYEE"
        elif target_role_code in ["BREAKFAST_ADMIN", "ADMIN"]:
            target_role_code = "BMS_ADMIN"
        elif target_role_code in ["FINANCE_MANAGER"]:
            target_role_code = "BMS_FINANCE_MANAGER"
        elif target_role_code in ["DIRECTOR_ANALYTICS"]:
            target_role_code = "BMS_DIRECTOR_ANALYTICS"

        bms_role = self.db.query(ModuleRole).filter(
            ModuleRole.module_id == bms_mod.id,
            ModuleRole.code == target_role_code
        ).first()

        if not bms_role:
            # Fallback to BMS_EMPLOYEE
            bms_role = self.db.query(ModuleRole).filter(
                ModuleRole.module_id == bms_mod.id,
                ModuleRole.code == "BMS_EMPLOYEE"
            ).first()

        # Update or create BMS UserModuleMembership
        if existing_mem:
            existing_mem.is_active = True
            if bms_role:
                existing_mem.role_id = bms_role.id
        else:
            new_mem = UserModuleMembership(
                user_id=user.id,
                module_id=bms_mod.id,
                role_id=bms_role.id if bms_role else None,
                is_active=True
            )
            self.db.add(new_mem)

        # Update or create Employee record
        department = (data.get("department") or "General").strip()
        designation = (data.get("designation") or (bms_role.name if bms_role else "Employee")).strip()
        participation_type = data.get("breakfastParticipationType") or "NORMAL"

        emp = user.employee or self.db.query(Employee).filter(Employee.user_id == user.id).first()
        if emp:
            emp.status = "active"
            emp.is_hard_deleted = False
            emp.name = user.name or user.username
            emp.email = user.email
            if user.phone:
                emp.phone = user.phone
            if department:
                emp.department = department
            if designation:
                emp.designation = designation
            if participation_type:
                emp.breakfast_participation_type = participation_type
        else:
            emp_id = self.repo.generate_next_employee_id()
            emp = Employee(
                user_id=user.id,
                employee_id=emp_id,
                name=user.name or user.username,
                email=user.email,
                phone=user.phone or "",
                department=department,
                designation=designation,
                status="active",
                breakfast_participation_type=participation_type,
                is_hard_deleted=False
            )
            self.db.add(emp)

        self.db.commit()
        self.db.refresh(emp)

        serialized = self.serialize_employee(emp)

        self.audit_service.log(
            action="USER_ADDED_TO_BMS",
            request=request,
            target_info={
                "targetEmployeeId": emp.employee_id,
                "targetUserId": user.id,
                "targetUsername": user.username,
                "targetEmployeeName": emp.name,
                "bmsRole": bms_role.code if bms_role else "None",
                "details": f"Added central user {user.username} to BMS with role {bms_role.name if bms_role else 'None'}"
            },
            after_state=serialized
        )

        return serialized

    def create_employee(self, data: dict, request: Optional[Request] = None) -> Dict[str, Any]:
        """
        BMS Employee creation gateway. Strictly delegates to add_user_to_bms.
        Creating arbitrary users/passwords from BMS is disabled.
        """
        user_id = data.get("userId") or data.get("user_id")
        if user_id:
            return self.add_user_to_bms(data, request=request)

        email = (data.get("email") or "").strip().lower()
        if email:
            existing = self.db.query(User).filter(User.email == email, User.is_hard_deleted == False).first()
            if existing:
                data["userId"] = existing.id
                return self.add_user_to_bms(data, request=request)

        # Reject direct user creation from BMS
        raise ValidationError(
            "Users cannot be created directly from BMS. Please create the user account in Central User Management, "
            "then select them in BMS Employees to grant breakfast participation."
        )

    def update_employee(self, employee_id: str, data: dict, request: Optional[Request] = None) -> Dict[str, Any]:
        emp = self.repo.get_by_employee_id(employee_id)
        if not emp:
            raise NotFoundError("Employee not found")

        user = emp.user
        before_state = self.serialize_employee(emp)

        # Update BMS-specific fields
        if "department" in data and data["department"]:
            emp.department = data["department"].strip()
        if "designation" in data and data["designation"]:
            emp.designation = data["designation"].strip()
        if "breakfastParticipationType" in data and data["breakfastParticipationType"]:
            emp.breakfast_participation_type = data["breakfastParticipationType"]
        if "status" in data and data["status"]:
            emp.status = data["status"]

        # If user name/phone are updated in BMS, keep employee in sync without mutating user credentials
        if "name" in data and data["name"]:
            emp.name = data["name"].strip()
        if "phone" in data and data["phone"] is not None:
            emp.phone = data["phone"].strip()

        # Update BMS module role if specified
        target_role_code = data.get("roleCode")
        if not target_role_code and "roles" in data and isinstance(data["roles"], list) and len(data["roles"]) > 0:
            target_role_code = data["roles"][0]

        if target_role_code and user:
            bms_mod = self.db.query(Module).filter(Module.code == "BMS").first()
            if bms_mod:
                clean_code = target_role_code.strip().upper()
                if clean_code in ["EMPLOYEE", "STANDARD_EMPLOYEE"]:
                    clean_code = "BMS_EMPLOYEE"
                elif clean_code in ["BREAKFAST_ADMIN", "ADMIN"]:
                    clean_code = "BMS_ADMIN"
                elif clean_code in ["FINANCE_MANAGER"]:
                    clean_code = "BMS_FINANCE_MANAGER"
                elif clean_code in ["DIRECTOR_ANALYTICS"]:
                    clean_code = "BMS_DIRECTOR_ANALYTICS"

                role = self.db.query(ModuleRole).filter(
                    ModuleRole.module_id == bms_mod.id,
                    ModuleRole.code == clean_code
                ).first()

                if role:
                    mem = self.db.query(UserModuleMembership).filter(
                        UserModuleMembership.user_id == user.id,
                        UserModuleMembership.module_id == bms_mod.id
                    ).first()
                    if mem:
                        mem.role_id = role.id
                        mem.is_active = (emp.status == "active")

        self.db.commit()
        self.db.refresh(emp)

        after_state = self.serialize_employee(emp)

        actions = []
        if before_state["status"] != after_state["status"]:
            actions.append("EMPLOYEE_ACTIVATED" if after_state["status"] == "active" else "EMPLOYEE_DEACTIVATED")
        if before_state["breakfastParticipationType"] != after_state["breakfastParticipationType"]:
            actions.append("PARTICIPATION_TYPE_CHANGED")
        if before_state.get("bmsRoleCode") != after_state.get("bmsRoleCode"):
            actions.append("BMS_ROLE_CHANGED")
        if not actions:
            actions.append("EMPLOYEE_UPDATED")

        for act in actions:
            self.audit_service.log(
                action=act,
                request=request,
                target_info={
                    "targetEmployeeId": emp.employee_id,
                    "targetUsername": user.username if user else "",
                    "targetEmployeeName": emp.name,
                    "details": f"Updated {act}"
                },
                before_state=before_state,
                after_state=after_state
            )

        return after_state

    def deactivate_employee(self, employee_id: str, request: Optional[Request] = None) -> Dict[str, Any]:
        """
        Removes a user from BMS. Sets employee.status = 'inactive' and deactivates BMS module membership.
        Does NOT delete the central User account or historical records!
        """
        emp = self.repo.get_by_employee_id(employee_id)
        if not emp:
            raise NotFoundError("Employee not found")

        before_state = self.serialize_employee(emp)
        emp.status = "inactive"

        # Deactivate BMS module membership, but PRESERVE the Central User
        if emp.user:
            bms_mod = self.db.query(Module).filter(Module.code == "BMS").first()
            if bms_mod:
                mem = self.db.query(UserModuleMembership).filter(
                    UserModuleMembership.user_id == emp.user.id,
                    UserModuleMembership.module_id == bms_mod.id
                ).first()
                if mem:
                    mem.is_active = False

        self.db.commit()
        self.db.refresh(emp)

        after_state = self.serialize_employee(emp)

        self.audit_service.log(
            action="USER_REMOVED_FROM_BMS",
            request=request,
            target_info={
                "targetEmployeeId": emp.employee_id,
                "targetUsername": emp.user.username if emp.user else "",
                "targetEmployeeName": emp.name,
                "details": "Removed user from BMS (Central user account and historical breakfast data preserved)"
            },
            before_state=before_state,
            after_state=after_state
        )

        return after_state

    def reset_password(self, employee_id: str, new_pwd: str, confirm_pwd: str, request: Optional[Request] = None) -> None:
        raise ValidationError(
            "Password reset must be performed via Central User Management. BMS cannot reset passwords."
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
            bms_mod = self.db.query(Module).filter(Module.code == "BMS").first()
            if bms_mod:
                mem = self.db.query(UserModuleMembership).filter(
                    UserModuleMembership.user_id == emp.user.id,
                    UserModuleMembership.module_id == bms_mod.id
                ).first()
                if mem:
                    mem.is_active = False

        self.db.commit()

        self.audit_service.log(
            action="EMPLOYEE_HARD_DELETED",
            request=request,
            target_info={
                "targetEmployeeId": emp.employee_id,
                "targetEmployeeName": emp.name,
                "details": "BMS participation permanently deleted by IT_ADMIN"
            },
            before_state=before_state,
            after_state={"isHardDeleted": True}
        )
