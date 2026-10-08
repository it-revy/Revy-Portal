from typing import List, Optional
from pydantic import BaseModel, Field


class AvailableUserResponse(BaseModel):
    id: str
    name: str
    username: str
    email: str
    phone: Optional[str] = ""
    department: Optional[str] = ""
    designation: Optional[str] = ""
    status: str


class AddUserToBmsRequest(BaseModel):
    userId: Optional[str] = None
    user_id: Optional[str] = None  # Backward-compatible snake_case
    roleCode: Optional[str] = "BMS_EMPLOYEE"
    department: Optional[str] = "General"
    designation: Optional[str] = "Employee"
    breakfastParticipationType: Optional[str] = "NORMAL"
    status: Optional[str] = "active"


class CreateEmployeeRequest(BaseModel):
    userId: Optional[str] = None
    user_id: Optional[str] = None
    employeeId: Optional[str] = None
    roleCode: Optional[str] = "BMS_EMPLOYEE"
    department: Optional[str] = "General"
    designation: Optional[str] = "Employee"
    breakfastParticipationType: Optional[str] = "NORMAL"
    status: Optional[str] = "active"
    # Legacy fields
    username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    phone: Optional[str] = ""
    roles: Optional[List[str]] = None


class UpdateEmployeeRequest(BaseModel):
    department: Optional[str] = None
    designation: Optional[str] = None
    breakfastParticipationType: Optional[str] = None
    roleCode: Optional[str] = None
    status: Optional[str] = None
    # For backward compatibility if passed
    name: Optional[str] = None
    phone: Optional[str] = None
    roles: Optional[List[str]] = None


class ResetPasswordRequest(BaseModel):
    newPassword: str
    confirmPassword: str


class HardDeleteRequest(BaseModel):
    confirmCode: str
