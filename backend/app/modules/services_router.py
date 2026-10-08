from fastapi import APIRouter, Depends
from app.core.dependencies import require_module_access, CurrentUser

crm_router = APIRouter(prefix="/crm", tags=["CRM Module"], dependencies=[Depends(require_module_access("CRM"))])
lms_router = APIRouter(prefix="/lms", tags=["LMS Module"], dependencies=[Depends(require_module_access("LMS"))])
ims_router = APIRouter(prefix="/ims", tags=["IMS Module"], dependencies=[Depends(require_module_access("IMS"))])
leave_router = APIRouter(prefix="/leave", tags=["Leave Module"], dependencies=[Depends(require_module_access("LEAVE"))])
mis_router = APIRouter(prefix="/mis", tags=["MIS Module"], dependencies=[Depends(require_module_access("MIS"))])
dwr_router = APIRouter(prefix="/dwr", tags=["DWR Module"], dependencies=[Depends(require_module_access("DWR"))])

@crm_router.get("/status")
def crm_status(current_user: CurrentUser = Depends(require_module_access("CRM"))):
    return {"success": True, "module": "CRM", "message": "Authorized access to CRM service"}

@lms_router.get("/status")
def lms_status(current_user: CurrentUser = Depends(require_module_access("LMS"))):
    return {"success": True, "module": "LMS", "message": "Authorized access to LMS service"}

@ims_router.get("/status")
def ims_status(current_user: CurrentUser = Depends(require_module_access("IMS"))):
    return {"success": True, "module": "IMS", "message": "Authorized access to IMS service"}

@leave_router.get("/status")
def leave_status(current_user: CurrentUser = Depends(require_module_access("LEAVE"))):
    return {"success": True, "module": "LEAVE", "message": "Authorized access to Leave Management service"}

@mis_router.get("/status")
def mis_status(current_user: CurrentUser = Depends(require_module_access("MIS"))):
    return {"success": True, "module": "MIS", "message": "Authorized access to MIS service"}

@dwr_router.get("/status")
def dwr_status(current_user: CurrentUser = Depends(require_module_access("DWR"))):
    return {"success": True, "module": "DWR", "message": "Authorized access to DWR service"}
