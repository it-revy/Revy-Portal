from typing import List, Optional
from pydantic import BaseModel, Field


class CreateEmployeeRequest(BaseModel):
    employeeId: Optional[str] = None
    username: Optional[str] = None
    name: str
    email: str
    password: Optional[str] = None
    phone: Optional[str] = ""
    department: str
    designation: str
    status: Optional[str] = "active"
    roles: Optional[List[str]] = Field(default_factory=lambda: ["EMPLOYEE"])
    breakfastParticipationType: Optional[str] = "NORMAL"


class UpdateEmployeeRequest(BaseModel):
    username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    status: Optional[str] = None
    roles: Optional[List[str]] = None
    breakfastParticipationType: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    newPassword: str
    confirmPassword: str


class HardDeleteRequest(BaseModel):
    confirmCode: str
