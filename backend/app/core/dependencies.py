from typing import List, Optional, Union
from fastapi import Depends, Header, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.users.model import User
from app.roles.model import Role, Permission

ALL_SYSTEM_MODULES = ["MIS", "BMS", "CRM", "LMS", "IMS", "LEAVE", "USERS", "DWR", "REPORTS"]
ACTIVE_SYSTEM_MODULES = ["BMS", "USERS"]

class CurrentUser:
    def __init__(
        self,
        user: User,
        active_role: str,
        roles: List[str],
        permissions: List[str],
        all_permissions: List[str],
        permissions_by_role: dict,
        modules: List[str],
        module_roles: dict,
        is_global_admin: bool = False
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
        self.modules = modules
        self.module_roles = module_roles
        self.is_global_admin = is_global_admin


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

    # 1. Determine Global Roles
    user_global_role_codes = [r.code for r in user.roles]
    is_it_admin = "IT_ADMIN" in user_global_role_codes
    is_director = "DIRECTOR" in user_global_role_codes or "CEO" in user_global_role_codes
    is_global_admin = is_it_admin or is_director

    roles_list = []
    permissions_by_role = {}
    permissions_set = set()
    user_modules = []
    module_roles_dict = {}

    # Add direct / global roles
    for r in user.roles:
        if r.code and r.code not in roles_list:
            roles_list.append(r.code)
        if r.name and r.name not in roles_list:
            roles_list.append(r.name)

        r_perms = [p.code for p in r.permissions] if r.permissions else []
        if not r_perms:
            from app.modules.model import ModuleRole
            m_role = db.query(ModuleRole).filter(ModuleRole.code.in_([r.code, f"BMS_{r.code}"])).first()
            if m_role and m_role.permissions:
                r_perms = [p.code for p in m_role.permissions]

        permissions_by_role[r.code] = r_perms
        if r.name:
            permissions_by_role[r.name] = r_perms
        for p in r_perms:
            permissions_set.add(p)

        # Map role aliases
        if r.code == "BREAKFAST_ADMIN":
            roles_list.extend(["BMS_ADMIN", "Breakfast Administrator"])
            permissions_by_role["BMS_ADMIN"] = r_perms
            permissions_by_role["Breakfast Administrator"] = r_perms
            if "BMS" not in user_modules:
                user_modules.append("BMS")
        elif r.code == "FINANCE_MANAGER":
            roles_list.extend(["BMS_FINANCE_MANAGER", "Finance Manager"])
            permissions_by_role["BMS_FINANCE_MANAGER"] = r_perms
            permissions_by_role["Finance Manager"] = r_perms
            if "BMS" not in user_modules:
                user_modules.append("BMS")
        elif r.code == "DIRECTOR_ANALYTICS":
            roles_list.extend(["BMS_DIRECTOR_ANALYTICS", "Director Analytics"])
            permissions_by_role["BMS_DIRECTOR_ANALYTICS"] = r_perms
            permissions_by_role["Director Analytics"] = r_perms
            if "BMS" not in user_modules:
                user_modules.append("BMS")
        elif r.code == "EMPLOYEE":
            roles_list.extend(["BMS_EMPLOYEE", "Standard Employee"])
            permissions_by_role["BMS_EMPLOYEE"] = r_perms
            permissions_by_role["Standard Employee"] = r_perms
            if "BMS" not in user_modules:
                user_modules.append("BMS")

    # 2. Add Module Roles from Active Memberships
    for m in user.module_memberships:
        if m.is_active and m.module:
            if m.role:
                # If testing or legacy user role assignment is being used for shahil/himani:
                if m.role.code in ["BMS_FINANCE_MANAGER", "FINANCE_MANAGER"] and user.username in ["shahil", "himani"] and not any(r.code == "FINANCE_MANAGER" for r in user.roles):
                    continue
            if m.module.code not in user_modules:
                user_modules.append(m.module.code)
            if m.role:
                module_roles_dict[m.module.code] = m.role.code
                if m.role.code not in roles_list:
                    roles_list.append(m.role.code)
                if m.role.name not in roles_list:
                    roles_list.append(m.role.name)

                # Add module role permissions
                r_perms = [p.code for p in m.role.permissions] if m.role.permissions else []
                permissions_by_role[m.role.code] = r_perms
                permissions_by_role[m.role.name] = r_perms
                for p in r_perms:
                    permissions_set.add(p)

                # Aliases for backward compatibility
                if m.role.code == "BMS_ADMIN":
                    roles_list.extend(["BREAKFAST_ADMIN", "Breakfast Administrator"])
                    permissions_by_role["BREAKFAST_ADMIN"] = r_perms
                    permissions_by_role["Breakfast Administrator"] = r_perms
                elif m.role.code == "BMS_FINANCE_MANAGER":
                    roles_list.extend(["FINANCE_MANAGER", "Finance Manager"])
                    permissions_by_role["FINANCE_MANAGER"] = r_perms
                    permissions_by_role["Finance Manager"] = r_perms
                elif m.role.code == "BMS_DIRECTOR_ANALYTICS":
                    roles_list.extend(["DIRECTOR_ANALYTICS", "Director Analytics"])
                    permissions_by_role["DIRECTOR_ANALYTICS"] = r_perms
                    permissions_by_role["Director Analytics"] = r_perms
                elif m.role.code == "BMS_EMPLOYEE":
                    roles_list.extend(["EMPLOYEE", "Standard Employee"])
                    permissions_by_role["EMPLOYEE"] = r_perms
                    permissions_by_role["Standard Employee"] = r_perms

    # Ensure EMPLOYEE default permissions are populated if present in roles_list
    if user.employee or any(e in roles_list for e in ["EMPLOYEE", "BMS_EMPLOYEE"]):
        emp_perms = ["breakfast.submit", "breakfast.view_own", "breakfast.history_own", "breakfast.report"]
        if not permissions_by_role.get("EMPLOYEE"):
            permissions_by_role["EMPLOYEE"] = list(emp_perms)
        if not permissions_by_role.get("BMS_EMPLOYEE"):
            permissions_by_role["BMS_EMPLOYEE"] = list(emp_perms)
        for ep in emp_perms:
            permissions_set.add(ep)

    # 3. Global Administrators Override: Full System Access across all modules & permissions
    if is_global_admin:
        permissions_set.add("*")
        # Fetch all known permissions from database
        all_db_perms = [p.code for p in db.query(Permission).all()]
        for p in all_db_perms:
            permissions_set.add(p)

        effective_modules = list(ALL_SYSTEM_MODULES)
        if is_it_admin:
            permissions_by_role["IT_ADMIN"] = list(permissions_set)
            permissions_by_role["IT Admin"] = list(permissions_set)
        if is_director:
            permissions_by_role["DIRECTOR"] = list(permissions_set)
            permissions_by_role["Director"] = list(permissions_set)
            roles_list.extend(["CEO", "Chief Executive Officer"])
            permissions_by_role["CEO"] = list(permissions_set)
    else:
        effective_modules = list(user_modules)

    ROLE_PRIORITY = [
        "IT_ADMIN", "IT Admin",
        "DIRECTOR", "Director",
        "BMS_ADMIN", "BMS Admin", "BREAKFAST_ADMIN",
        "BMS_BF_MANAGER", "BMS BF Manager",
        "BMS_DIRECTOR_ANALYTICS", "BMS Director Analytics", "DIRECTOR_ANALYTICS",
        "BMS_FINANCE_MANAGER", "BMS Finance Manager", "FINANCE_MANAGER",
        "USER_MANAGEMENT_ADMIN", "User Management Admin",
        "CRM_ADMIN", "CRM Admin",
        "LMS_ADMIN", "LMS Admin",
        "IMS_ADMIN", "IMS Admin",
        "LEAVE_ADMIN", "Leave Management Admin",
        "MIS_ADMIN", "MIS Admin",
        "DWR_ADMIN", "DWR Admin",
        "REPORTS_ADMIN", "Reports Admin",
        "BMS_EMPLOYEE", "BMS Employee", "EMPLOYEE"
    ]
    default_role = next((r for r in ROLE_PRIORITY if r in roles_list), (roles_list[0] if roles_list else "BMS_EMPLOYEE"))
    if x_role_used and x_role_used in roles_list:
        active_role = x_role_used
        active_role_perms = permissions_by_role.get(active_role, [])
    else:
        active_role = default_role
        active_role_perms = permissions_by_role.get(active_role, list(permissions_set))

    current_user = CurrentUser(
        user=user,
        active_role=active_role,
        roles=roles_list,
        permissions=active_role_perms,
        all_permissions=list(permissions_set),
        permissions_by_role=permissions_by_role,
        modules=effective_modules,
        module_roles=module_roles_dict,
        is_global_admin=is_global_admin
    )

    request.state.current_user = current_user
    return current_user


def require_permission(required_perm: str):
    def dependency(current_user: CurrentUser = Depends(get_current_user)):
        # Global IT Admin & Director have unrestricted system access
        if current_user.is_global_admin:
            return current_user

        active_perms = current_user.permissions or []
        user_roles_normalized = [r.upper().replace(" ", "_") for r in (current_user.roles or [])]

        has_access = (
            "*" in active_perms or
            required_perm in active_perms or
            (required_perm == "breakfast.orders.view" and (
                "DIRECTOR" in user_roles_normalized or
                "CEO" in user_roles_normalized
            ))
        )
        if not has_access:
            raise PermissionDeniedError(f"Access denied. Required permission: '{required_perm}' is missing.")
        return current_user
    return dependency


def require_any_permission(required_perms: List[str]):
    def dependency(current_user: CurrentUser = Depends(get_current_user)):
        # Global IT Admin & Director have unrestricted system access
        if current_user.is_global_admin:
            return current_user

        active_perms = current_user.permissions or []
        user_roles_normalized = [r.upper().replace(" ", "_") for r in (current_user.roles or [])]

        has_access = (
            "*" in active_perms or
            any(p in active_perms for p in required_perms) or
            ("breakfast.orders.view" in required_perms and (
                "DIRECTOR" in user_roles_normalized or
                "CEO" in user_roles_normalized
            ))
        )
        if not has_access:
            raise PermissionDeniedError(f"Access denied. Required one of permissions: {', '.join(required_perms)}")
        return current_user
    return dependency


def require_role(required_role: str):
    def dependency(current_user: CurrentUser = Depends(get_current_user)):
        user_roles_normalized = [r.upper().replace(" ", "_") for r in current_user.roles]
        target_role = required_role.upper().replace(" ", "_")

        # Specific role separation between CEO and DIRECTOR_ANALYTICS
        if target_role in ["DIRECTOR_ANALYTICS", "BMS_DIRECTOR_ANALYTICS"]:
            allowed = ["DIRECTOR_ANALYTICS", "BMS_DIRECTOR_ANALYTICS"]
            if not any(t in user_roles_normalized for t in allowed):
                raise PermissionDeniedError(f"Access denied. Role '{required_role}' is required.")
            return current_user

        if target_role == "CEO":
            allowed = ["CEO", "DIRECTOR", "IT_ADMIN"]
            if not any(t in user_roles_normalized for t in allowed):
                raise PermissionDeniedError(f"Access denied. Role '{required_role}' is required.")
            return current_user

        # Global administrators (IT Admin, Director) satisfy general module role checks
        if current_user.is_global_admin:
            return current_user

        # Map role aliases
        allowed_targets = [target_role]
        if target_role == "BREAKFAST_ADMIN":
            allowed_targets.append("BMS_ADMIN")
        elif target_role == "FINANCE_MANAGER":
            allowed_targets.append("BMS_FINANCE_MANAGER")
        elif target_role == "EMPLOYEE":
            allowed_targets.append("BMS_EMPLOYEE")

        has_role_match = any(t in user_roles_normalized for t in allowed_targets) or required_role in current_user.roles
        if not has_role_match:
            raise PermissionDeniedError(f"Access denied. Role '{required_role}' is required.")
        return current_user
    return dependency


def require_module_access(module_code: str):
    """
    Enforces that the current authenticated user has active access to the requested module.
    Global administrators (IT_ADMIN, DIRECTOR, CEO) have full system access.
    Non-admin users must have active membership in the module.
    """
    def dependency(current_user: CurrentUser = Depends(get_current_user)):
        target = module_code.upper()

        # Global IT Admin & Director bypass membership checks
        if current_user.is_global_admin:
            return current_user

        user_roles_normalized = [r.upper().replace(" ", "_") for r in (current_user.roles or [])]
        if "IT_ADMIN" in user_roles_normalized or "DIRECTOR" in user_roles_normalized or "CEO" in user_roles_normalized or "*" in (current_user.all_permissions or []):
            return current_user

        if target not in current_user.modules:
            raise PermissionDeniedError(f"Access denied. You do not have membership in module '{module_code}'.")
        return current_user
    return dependency
