from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field

class ManagerSummary(BaseModel):
    id: str
    name: str
    username: str
    email: str

class UserModuleSummary(BaseModel):
    moduleCode: str
    moduleName: str
    roleCode: Optional[str] = None
    roleName: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    name: str
    username: str
    email: str
    phone: str = ""
    status: str = "active"
    managerId: Optional[str] = None
    managerName: Optional[str] = None
    managerUsername: Optional[str] = None
    roles: List[str] = []
    modules: List[UserModuleSummary] = []
    hasBmsEmployee: bool = False
    employeeId: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=1)
    username: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = ""
    password: Optional[str] = None
    managerId: Optional[str] = None
    status: Optional[str] = "active"
    roles: Optional[List[str]] = ["EMPLOYEE"]

class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    managerId: Optional[str] = None
    status: Optional[str] = None
    roles: Optional[List[str]] = None

class ResetUserPasswordRequest(BaseModel):
    newPassword: str = Field(..., min_length=6)
    confirmPassword: Optional[str] = None
