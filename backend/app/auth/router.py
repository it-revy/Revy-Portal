from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.auth.schema import LoginRequest, ChangePasswordRequest
from app.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
def login(login_req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    input_username = login_req.username or login_req.loginId or ""
    service = AuthService(db)
    token, user_profile = service.login(input_username, login_req.password, request)
    return {
        "success": True,
        "token": token,
        "user": user_profile
    }

@router.get("/me")
def get_me(current_user: CurrentUser = Depends(get_current_user)):
    user = current_user.user
    emp = user.employee

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

    return {
        "success": True,
        "user": {
            "id": user.id,
            "employeeId": emp.employee_id if emp else "",
            "username": user.username,
            "name": user.name or (emp.name if emp else user.username),
            "email": user.email,
            "phone": user.phone or (emp.phone if emp else ""),
            "department": emp.department if emp else "",
            "designation": emp.designation if emp else "",
            "status": user.status,
            "managerId": user.manager_id,
            "managerName": user.manager.name if user.manager else None,
            "roles": current_user.roles,
            "modules": modules_list,
            "breakfastParticipationType": emp.breakfast_participation_type if emp else "NORMAL",
            "forcePasswordChange": bool(user.force_password_change),
            "permissions": current_user.all_permissions,
            "permissionsByRole": current_user.permissions_by_role
        }
    }

@router.post("/change-password")
def change_password(
    pwd_req: ChangePasswordRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    service.change_password(
        user_id=current_user.id,
        current_password=pwd_req.currentPassword or "",
        new_password=pwd_req.newPassword,
        confirm_password=pwd_req.confirmPassword or "",
        request=request
    )
    return {
        "success": True,
        "message": "Password updated successfully. You may now continue using the platform."
    }
