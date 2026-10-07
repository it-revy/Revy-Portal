from typing import List, Optional
from pydantic import BaseModel, Field

class ModuleRoleResponse(BaseModel):
    id: str
    moduleId: str
    code: str
    name: str
    description: Optional[str] = None
    isActive: bool = True

    class Config:
        from_attributes = True

class ModuleResponse(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    isActive: bool = True
    isOpenToAll: bool = False
    roles: List[ModuleRoleResponse] = []

    class Config:
        from_attributes = True

class UserModuleMembershipItem(BaseModel):
    moduleId: str
    moduleCode: str
    moduleName: str
    isOpenToAll: bool = False
    isEnabled: bool
    roleId: Optional[str] = None
    roleCode: Optional[str] = None
    roleName: Optional[str] = None

class ModuleAssignmentInput(BaseModel):
    moduleId: Optional[str] = None
    moduleCode: Optional[str] = None
    enabled: bool
    roleId: Optional[str] = None
    roleCode: Optional[str] = None

class UpdateUserModulesRequest(BaseModel):
    modules: List[ModuleAssignmentInput]
