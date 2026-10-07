from typing import List, Optional, Union
from fastapi import Depends, Header, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.users.model import User
from app.roles.model import Role


class CurrentUser:
    def __init__(
        self,
        user: User,
        active_role: str,
        roles: List[str],
        permissions: List[str],
        all_permissions: List[str],
        permissions_by_role: dict
    ):
        self.user = user
        self.id = user.id
        self.username = user.username
        self.email = user.email
        self.employee = user.employee
        self.employee_id = user.employee.employee_id if user.employee else None
        self.name = user.name or (user.employee.name if user.employee else user.username)
        self.phone = user.phone or (user.employee.phone if user.employee else "")
        self.manager_id = user.manager_id
        self.department = user.employee.department if user.employee else ""
        self.designation = user.employee.designation if user.employee else ""
        self.breakfast_participation_type = user.employee.breakfast_participation_type if user.employee else "NORMAL"
        self.status = user.status
        self.force_password_change = user.force_password_change
        self.roles = roles
        self.active_role = active_role
        self.permissions = permissions  # permissions for active role
        self.all_permissions = all_permissions  # union of all roles permissions
        self.permissions_by_role = permissions_by_role
        self.modules = [m.module.code for m in user.module_memberships if m.is_active and m.module]
        self.module_roles = {
            m.module.code: (m.role.code if m.role else None)
            for m in user.module_memberships if m.is_active and m.module
        }


def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_role_used: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Not authorized, no token provided")

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    employee_id = payload.get("employeeId") or payload.get("employee_id")
    username = payload.get("username")

    query = db.query(User).filter(User.is_hard_deleted == False)
    if username:
        user = query.filter(User.username == username.lower()).first()
    elif employee_id:
        from app.employees.model import Employee
        emp = db.query(Employee).filter(Employee.employee_id == employee_id.upper()).first()
        user = emp.user if emp else None
    else:
        user = None

    if not user:
        raise AuthenticationError("User account not found")

    if user.status != "active":
        raise PermissionDeniedError("Account is deactivated. Please contact administrator.")

    roles_list = []
    permissions_by_role = {}
    permissions_set = set()

    for r in user.roles:
        if r.code and r.code not in roles_list:
            roles_list.append(r.code)
        if r.name and r.name not in roles_list:
            roles_list.append(r.name)
        r_perms = [p.code for p in r.permissions]
        permissions_by_role[r.code] = r_perms
        if r.name:
            permissions_by_role[r.name] = r_perms
        for p in r_perms:
            permissions_set.add(p)

    ROLE_PRIORITY = [
        "IT_ADMIN", "IT Administrator",
        "DIRECTOR_ANALYTICS", "Director Analytics",
        "CEO", "Chief Executive Officer",
        "FINANCE_MANAGER", "Finance Manager",
        "BREAKFAST_ADMIN", "Breakfast Administrator",
        "EMPLOYEE", "Standard Employee"
    ]
    default_role = next((r for r in ROLE_PRIORITY if r in roles_list), (roles_list[0] if roles_list else "EMPLOYEE"))
    active_role = x_role_used if x_role_used and x_role_used in roles_list else default_role
    active_role_perms = permissions_by_role.get(active_role, [])

    current_user = CurrentUser(
        user=user,
        active_role=active_role,
        roles=roles_list,
        permissions=active_role_perms,
        all_permissions=list(permissions_set),
        permissions_by_role=permissions_by_role
    )

    request.state.current_user = current_user
    return current_user


def require_permission(required_perm: str):
    def dependency(current_user: CurrentUser = Depends(get_current_user)):
        active_perms = current_user.permissions or []
        all_perms = current_user.all_permissions or []
        user_roles_normalized = [r.upper().replace(" ", "_") for r in (current_user.roles or [])]
        # Allow full admin with '*' or check permission across active or all assigned roles
        has_access = (
            "*" in active_perms or "*" in all_perms or
            required_perm in active_perms or required_perm in all_perms or
            (required_perm == "breakfast.orders.view" and ("CEO" in user_roles_normalized or "CHIEF_EXECUTIVE_OFFICER" in user_roles_normalized))
        )
        if not has_access:
            raise PermissionDeniedError(f"Access denied. Required permission: '{required_perm}' is missing.")
        return current_user
    return dependency


def require_any_permission(required_perms: List[str]):
    def dependency(current_user: CurrentUser = Depends(get_current_user)):
        active_perms = current_user.permissions or []
        all_perms = current_user.all_permissions or []
        user_roles_normalized = [r.upper().replace(" ", "_") for r in (current_user.roles or [])]
        has_access = (
            "*" in active_perms or "*" in all_perms or
            any(p in active_perms or p in all_perms for p in required_perms) or
            ("breakfast.orders.view" in required_perms and ("CEO" in user_roles_normalized or "CHIEF_EXECUTIVE_OFFICER" in user_roles_normalized))
        )
        if not has_access:
            raise PermissionDeniedError(f"Access denied. Required one of permissions: {', '.join(required_perms)}")
        return current_user
    return dependency


def require_role(required_role: str):
    def dependency(current_user: CurrentUser = Depends(get_current_user)):
        user_roles_normalized = [r.upper().replace(" ", "_") for r in current_user.roles]
        target_role = required_role.upper().replace(" ", "_")
        if target_role not in user_roles_normalized and required_role not in current_user.roles:
            raise PermissionDeniedError(f"Access denied. Role '{required_role}' is required.")
        return current_user
    return dependency


def require_module_access(module_code: str):
    """
    Enforces that the current authenticated user has active membership
    in the requested business module. Universal modules (MIS, DWR, REPORTS)
    are accessible to any authenticated user.
    """
    def dependency(current_user: CurrentUser = Depends(get_current_user)):
        target = module_code.upper()
        if target in ["MIS", "DWR", "REPORTS"]:
            return current_user

        # Superadmin / full access override
        if "*" in (current_user.all_permissions or []):
            return current_user

        user_roles_normalized = [r.upper().replace(" ", "_") for r in (current_user.roles or [])]
        if "IT_ADMIN" in user_roles_normalized:
            return current_user

        if target not in current_user.modules:
            raise PermissionDeniedError(f"Access denied. You do not have membership in module '{module_code}'.")
        return current_user
    return dependency

