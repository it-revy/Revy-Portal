from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission, require_any_permission, CurrentUser
from app.users.schema import (
    UserResponse,
    CreateUserRequest,
    UpdateUserRequest,
    ManagerSummary,
    ResetUserPasswordRequest
)
from app.users.service import UserService
from app.core.security import get_password_hash

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("", response_model=List[UserResponse])
@router.get("/", response_model=List[UserResponse])
def get_users(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    managerId: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_any_permission(["*", "users.view", "users.create", "users.edit", "breakfast.employee.read"])),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    return service.list_users(
        search=search,
        status=status,
        module_code=module,
        manager_id=managerId
    )

@router.get("/managers/list", response_model=List[ManagerSummary])
def get_managers_list(
    excludeUserId: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_any_permission(["*", "users.view", "users.create", "users.edit"])),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    return service.list_potential_managers(exclude_user_id=excludeUserId)

@router.post("", response_model=UserResponse)
@router.post("/", response_model=UserResponse)
def create_user(
    payload: CreateUserRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_any_permission(["*", "users.create"])),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    return service.create_user(payload.model_dump(), request=request)

@router.get("/{id}", response_model=UserResponse)
def get_user_by_id(
    id: str,
    current_user: CurrentUser = Depends(require_any_permission(["*", "users.view", "users.edit", "breakfast.employee.read"])),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    return service.get_user_by_id(id)

@router.put("/{id}", response_model=UserResponse)
def update_user(
    id: str,
    payload: UpdateUserRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_any_permission(["*", "users.edit"])),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    return service.update_user(id, payload.model_dump(exclude_unset=True), request=request)

@router.delete("/{id}")
def deactivate_user(
    id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_any_permission(["*", "users.deactivate", "users.edit"])),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    return service.deactivate_user(id, request=request)

@router.post("/{id}/reset-password")
def reset_user_password(
    id: str,
    payload: ResetUserPasswordRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_any_permission(["*", "users.edit", "user.password.reset"])),
    db: Session = Depends(get_db)
):
    user = UserService(db).db.query(UserService(db).db.query(UserService).first()) if False else None
    from app.users.model import User
    user = db.query(User).filter(User.id == id, User.is_hard_deleted == False).first()
    if not user:
        return {"success": False, "message": "User not found"}
    user.password_hash = get_password_hash(payload.newPassword)
    user.force_password_change = True
    db.commit()
    return {"success": True, "message": "Password reset successfully. User will be prompted to change password on next login."}
