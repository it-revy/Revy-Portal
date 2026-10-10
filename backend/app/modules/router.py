from typing import List, Optional
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission, require_any_permission, CurrentUser
from app.modules.schema import ModuleResponse, ModuleRoleResponse, UserModuleMembershipItem, UpdateUserModulesRequest
from app.modules.service import ModuleService

router = APIRouter(tags=["Modules"])

@router.get("/modules", response_model=List[ModuleResponse])
def get_all_modules(
    only_active: Optional[bool] = Query(None),
    current_user: CurrentUser = Depends(require_any_permission(["*", "modules.view", "users.view", "users.edit", "breakfast.employee.read", "breakfast.view"])),
    db: Session = Depends(get_db)
):
    service = ModuleService(db)
    return service.list_modules(only_active=False if only_active is None else only_active, only_active_roles=True)

@router.get("/modules/{module_id}/roles", response_model=List[ModuleRoleResponse])
def get_module_roles(
    module_id: str,
    current_user: CurrentUser = Depends(require_any_permission(["*", "modules.view", "users.view", "users.edit", "breakfast.employee.read"])),
    db: Session = Depends(get_db)
):
    service = ModuleService(db)
    return service.get_module_roles(module_id)

@router.get("/users/{user_id}/modules", response_model=List[UserModuleMembershipItem])
def get_user_modules(
    user_id: str,
    current_user: CurrentUser = Depends(require_any_permission(["*", "users.view", "users.edit", "modules.manage"])),
    db: Session = Depends(get_db)
):
    service = ModuleService(db)
    return service.get_user_module_memberships(user_id)

@router.get("/modules/{module_id_or_code}/assignable-roles", response_model=List[ModuleRoleResponse])
def get_assignable_roles_for_module(
    module_id_or_code: str,
    current_user: CurrentUser = Depends(require_any_permission(["*", "modules.view", "users.view", "users.edit", "breakfast.employee.read", "breakfast.employee.create"])),
    db: Session = Depends(get_db)
):
    from app.roles.assignment_service import RoleAssignmentService
    return RoleAssignmentService.get_assignable_roles_for_module(current_user, module_id_or_code, db)

@router.put("/users/{user_id}/modules", response_model=List[UserModuleMembershipItem])
def update_user_modules(
    user_id: str,
    payload: UpdateUserModulesRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_any_permission(["*", "users.edit", "modules.manage"])),
    db: Session = Depends(get_db)
):
    service = ModuleService(db)
    return service.update_user_module_memberships(
        user_id=user_id,
        assignments=[item.model_dump() for item in payload.modules],
        request=request,
        current_user=current_user
    )

