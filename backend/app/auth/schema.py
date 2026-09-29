from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: Optional[str] = None
    loginId: Optional[str] = None
    password: str


class ChangePasswordRequest(BaseModel):
    currentPassword: Optional[str] = None
    newPassword: str
    confirmPassword: Optional[str] = None


class UserProfileResponse(BaseModel):
    employeeId: str
    username: str
    name: str
    email: str
    phone: Optional[str] = ""
    department: str
    designation: str
    status: str
    roles: List[str]
    breakfastParticipationType: str
    forcePasswordChange: bool
    permissions: List[str]
    permissionsByRole: Dict[str, List[str]]


class LoginResponse(BaseModel):
    success: bool = True
    token: str
    user: UserProfileResponse


class StandardResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None
