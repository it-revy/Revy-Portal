import re
from typing import List, Dict, Any, Optional
from fastapi import Request
from sqlalchemy.orm import Session
from app.users.model import User
from app.roles.model import Role
from app.modules.model import UserModuleMembership
from app.core.security import get_password_hash
from app.core.exceptions import ValidationError, NotFoundError
from app.audit.service import AuditService

class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def serialize_user(self, user: User) -> Dict[str, Any]:
        manager = user.manager
        roles = [r.code for r in user.roles] if user.roles else []

        modules = []
        for m in user.module_memberships:
            if m.is_active and m.module:
                modules.append({
                    "moduleCode": m.module.code,
                    "moduleName": m.module.name,
                    "roleCode": m.role.code if m.role else None,
                    "roleName": m.role.name if m.role else None
                })

        emp = user.employee
        return {
            "id": user.id,
            "name": user.name or user.username,
            "username": user.username,
            "email": user.email,
            "phone": user.phone or "",
            "status": user.status,
            "managerId": user.manager_id,
            "managerName": manager.name if manager else None,
            "managerUsername": manager.username if manager else None,
            "roles": roles,
            "modules": modules,
            "hasBmsEmployee": bool(emp and not emp.is_hard_deleted),
            "employeeId": emp.employee_id if emp else None,
            "createdAt": user.created_at.isoformat() if user.created_at else None,
            "updatedAt": user.updated_at.isoformat() if user.updated_at else None
        }

    def list_users(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        module_code: Optional[str] = None,
        manager_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = self.db.query(User).filter(User.is_hard_deleted == False)

        if status and status.upper() != "ALL":
            query = query.filter(User.status == status.lower())

        if manager_id:
            query = query.filter(User.manager_id == manager_id)

        if search:
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                (User.name.ilike(term)) |
                (User.username.ilike(term)) |
                (User.email.ilike(term)) |
                (User.phone.ilike(term))
            )

        users = query.order_by(User.name.asc(), User.username.asc()).all()

        if module_code and module_code.upper() != "ALL":
            target = module_code.upper()
            users = [
                u for u in users
                if any(m.module.code == target and m.is_active for m in u.module_memberships if m.module)
            ]

        return [self.serialize_user(u) for u in users]

    def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        user = self.db.query(User).filter(User.id == user_id, User.is_hard_deleted == False).first()
        if not user:
            raise NotFoundError(f"User with ID '{user_id}' not found")
        return self.serialize_user(user)

    def list_potential_managers(self, exclude_user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self.db.query(User).filter(
            User.is_hard_deleted == False,
            User.status == "active"
        )
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)

        users = query.order_by(User.name.asc()).all()
        return [
            {
                "id": u.id,
                "name": u.name or u.username,
                "username": u.username,
                "email": u.email
            }
            for u in users
        ]

    def create_user(self, data: dict, request: Optional[Request] = None) -> Dict[str, Any]:
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()

        if not name or not email:
            raise ValidationError("Name and email are required to create a User")

        # Generate or sanitize username
        raw_username = data.get("username")
        if not raw_username:
            raw_username = email.split("@")[0] if "@" in email else name
        username = re.sub(r"[^a-z0-9._-]", "", raw_username.lower().strip())
        if not username:
            raise ValidationError("A valid username could not be determined")

        # Check existing username
        if self.db.query(User).filter(User.username == username).first():
            raise ValidationError(f'Username "{username}" is already taken')

        # Check existing email
        if self.db.query(User).filter(User.email == email).first():
            raise ValidationError(f'Email "{email}" is already registered')

        # Validate manager
        manager_id = data.get("managerId")
        if manager_id:
            manager = self.db.query(User).filter(User.id == manager_id, User.is_hard_deleted == False).first()
            if not manager:
                raise ValidationError("Specified manager does not exist")
            if manager.status != "active":
                raise ValidationError("Selected manager is inactive")

        phone = (data.get("phone") or "").strip()
        status_val = data.get("status") or "active"

        raw_password = data.get("password") or "Password123!"
        password_hash = get_password_hash(raw_password)

        user = User(
            name=name,
            username=username,
            email=email,
            phone=phone,
            password_hash=password_hash,
            status=status_val,
            manager_id=manager_id,
            force_password_change=True,
            is_hard_deleted=False
        )

        # Assign system global roles if provided (IT_ADMIN or DIRECTOR)
        role_codes = data.get("roles") or []
        if role_codes:
            roles = self.db.query(Role).filter(Role.code.in_(role_codes)).all()
            user.roles = roles

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Audit log user creation
        performed_by_id = None
        performed_by_name = None
        role_used = None
        if request and hasattr(request.state, "current_user") and request.state.current_user:
            cu = request.state.current_user
            performed_by_id = cu.employee_id or cu.username
            performed_by_name = cu.name or cu.username
            role_used = cu.active_role

        self.audit_service.log(
            action="USER_CREATED",
            request=request,
            target_info={
                "targetUserId": user.id,
                "targetUsername": user.username,
                "name": user.name,
                "email": user.email,
                "managerId": user.manager_id
            },
            performed_by_employee_id=performed_by_id,
            performed_by_name=performed_by_name,
            role_used=role_used
        )

        return self.serialize_user(user)

    def update_user(self, user_id: str, data: dict, request: Optional[Request] = None) -> Dict[str, Any]:
        user = self.db.query(User).filter(User.id == user_id, User.is_hard_deleted == False).first()
        if not user:
            raise NotFoundError(f"User with ID '{user_id}' not found")

        changes = []

        if "name" in data and data["name"]:
            new_name = data["name"].strip()
            if new_name != user.name:
                changes.append(f"Name: {user.name} -> {new_name}")
                user.name = new_name
                # If user has employee, sync name
                if user.employee:
                    user.employee.name = new_name

        if "phone" in data and data["phone"] is not None:
            new_phone = data["phone"].strip()
            if new_phone != user.phone:
                changes.append(f"Phone: {user.phone} -> {new_phone}")
                user.phone = new_phone
                if user.employee:
                    user.employee.phone = new_phone

        if "email" in data and data["email"]:
            new_email = data["email"].strip().lower()
            if new_email != user.email:
                existing = self.db.query(User).filter(User.email == new_email, User.id != user.id).first()
                if existing:
                    raise ValidationError(f'Email "{new_email}" is already used by another account')
                changes.append(f"Email: {user.email} -> {new_email}")
                user.email = new_email
                if user.employee:
                    user.employee.email = new_email

        if "managerId" in data:
            new_mgr_id = data["managerId"]
            if new_mgr_id == user.id:
                raise ValidationError("A user cannot be their own manager")
            if new_mgr_id:
                mgr = self.db.query(User).filter(User.id == new_mgr_id, User.is_hard_deleted == False).first()
                if not mgr:
                    raise ValidationError("Selected manager does not exist")
                # Prevent direct circular reference (A reports to B and B reports to A)
                if mgr.manager_id == user.id:
                    raise ValidationError("Circular manager relationship detected: manager reports back to this user")
            if new_mgr_id != user.manager_id:
                changes.append(f"Manager ID: {user.manager_id} -> {new_mgr_id}")
                user.manager_id = new_mgr_id

        if "status" in data and data["status"]:
            new_status = data["status"].strip().lower()
            if new_status in ["active", "inactive"] and new_status != user.status:
                changes.append(f"Status: {user.status} -> {new_status}")
                user.status = new_status
                if new_status == "inactive" and user.employee:
                    user.employee.status = "inactive"

        if "roles" in data and isinstance(data["roles"], list):
            new_roles = self.db.query(Role).filter(Role.code.in_(data["roles"])).all()
            user.roles = new_roles
            changes.append(f"Roles: {', '.join(data['roles'])}")

        self.db.commit()
        self.db.refresh(user)

        if changes:
            performed_by_id = None
            performed_by_name = None
            role_used = None
            if request and hasattr(request.state, "current_user") and request.state.current_user:
                cu = request.state.current_user
                performed_by_id = cu.employee_id or cu.username
                performed_by_name = cu.name or cu.username
                role_used = cu.active_role

            self.audit_service.log(
                action="USER_UPDATED",
                request=request,
                target_info={
                    "targetUserId": user.id,
                    "targetUsername": user.username,
                    "changes": "; ".join(changes)
                },
                performed_by_employee_id=performed_by_id,
                performed_by_name=performed_by_name,
                role_used=role_used
            )

        return self.serialize_user(user)

    def deactivate_user(self, user_id: str, request: Optional[Request] = None) -> Dict[str, Any]:
        user = self.db.query(User).filter(User.id == user_id, User.is_hard_deleted == False).first()
        if not user:
            raise NotFoundError(f"User with ID '{user_id}' not found")

        user.status = "inactive"
        if user.employee:
            user.employee.status = "inactive"

        self.db.commit()

        performed_by_id = None
        performed_by_name = None
        role_used = None
        if request and hasattr(request.state, "current_user") and request.state.current_user:
            cu = request.state.current_user
            performed_by_id = cu.employee_id or cu.username
            performed_by_name = cu.name or cu.username
            role_used = cu.active_role

        self.audit_service.log(
            action="USER_DEACTIVATED",
            request=request,
            target_info={
                "targetUserId": user.id,
                "targetUsername": user.username
            },
            performed_by_employee_id=performed_by_id,
            performed_by_name=performed_by_name,
            role_used=role_used
        )

        return {"success": True, "message": f"User {user.username} deactivated successfully"}
