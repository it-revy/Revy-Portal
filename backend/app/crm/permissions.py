from typing import Any
from fastapi import Depends, HTTPException, status
from app.core.dependencies import CurrentUser, get_current_user


def is_crm_admin_or_manager(user: Any) -> bool:
    """
    Returns True if user is CRM Admin, CRM Manager, or Global Admin.
    Authoritative permission check for quotation creation/edit and PI generation/edit.
    """
    if not user:
        return False
    if getattr(user, "is_global_admin", False) or getattr(user, "is_admin", False) or getattr(user, "is_superuser", False):
        return True

    roles = getattr(user, "roles", []) or []
    normalized_roles = {str(r).upper().replace(" ", "_") for r in roles}

    active_role = str(getattr(user, "active_role", "") or "").upper().replace(" ", "_")
    if active_role:
        normalized_roles.add(active_role)

    module_roles = getattr(user, "module_roles", {}) or {}
    crm_mod_roles = module_roles.get("CRM", [])
    if isinstance(crm_mod_roles, list):
        for r in crm_mod_roles:
            normalized_roles.add(str(r).upper().replace(" ", "_"))
    elif isinstance(crm_mod_roles, str):
        normalized_roles.add(crm_mod_roles.upper().replace(" ", "_"))

    allowed_roles = {
        "CRM_ADMIN",
        "CRM_SALES_MANAGER",
        "CRM_MANAGER",
        "IT_ADMIN",
        "DIRECTOR",
        "CEO",
        "SUPER_ADMIN",
        "ADMIN"
    }
    return bool(normalized_roles.intersection(allowed_roles))


def is_crm_user(user: Any) -> bool:
    """
    Returns True if user has CRM read access (any CRM role or global admin).
    """
    if not user:
        return False
    if is_crm_admin_or_manager(user):
        return True

    roles = getattr(user, "roles", []) or []
    normalized_roles = {str(r).upper().replace(" ", "_") for r in roles}

    active_role = str(getattr(user, "active_role", "") or "").upper().replace(" ", "_")
    if active_role:
        normalized_roles.add(active_role)

    module_roles = getattr(user, "module_roles", {}) or {}
    crm_mod_roles = module_roles.get("CRM", [])
    if crm_mod_roles:
        return True

    user_modules = getattr(user, "modules", []) or []
    if "CRM" in user_modules:
        return True

    all_perms = set(getattr(user, "permissions", []) or []).union(set(getattr(user, "all_permissions", []) or []))
    if any(p.startswith("crm.") for p in all_perms) or "*" in all_perms:
        return True

    crm_roles = {
        "CRM_SALES_EXECUTIVE",
        "CRM_EXECUTIVE",
        "CRM_SALES_COORDINATOR",
        "CRM_FINANCE_MANAGER",
        "CRM_REP",
        "SALES_REP",
        "CRM_USER"
    }
    return bool(normalized_roles.intersection(crm_roles)) or any(r.startswith("CRM_") for r in normalized_roles)


def require_crm_read(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """
    Enforces that user is any CRM user (CRM Admin, CRM Manager, or other CRM users).
    Permitted: View quotations, View PIs, Print/Download PIs.
    """
    if not is_crm_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. CRM user authorization required."
        )
    return current_user


def require_crm_write(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """
    Enforces that user is CRM Admin or CRM Manager (or Global Admin).
    Permitted: Create quotation, Edit quotation, Generate PI, Edit issued PI.
    Restricted: Other CRM users receive 403 Forbidden.
    """
    if not is_crm_admin_or_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only CRM Admin and CRM Manager are authorized to create or modify quotations and proforma invoices."
        )
    return current_user
