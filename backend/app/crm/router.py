from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    require_module_access,
    require_permission,
    require_any_permission,
    CurrentUser
)
from app.crm.service import CrmService
from app.crm.schema import (
    CrmUserListResponse,
    CrmUserAccessRequest,
    CrmUserRoleRequest,
    CrmRoleListResponse,
    AccountCreate,
    AccountUpdate,
    AccountListResponse,
    AccountDetailResponse,
    ContactCreate,
    ContactUpdate,
    ContactListResponse,
    ContactDetailResponse,
    LeadCreate,
    LeadUpdate,
    LeadStatusTransitionRequest,
    LeadListResponse,
    LeadDetailResponse,
    CommunicationCreate,
    CommunicationListResponse,
    DashboardMetricsResponse
)

router = APIRouter(prefix="/crm", tags=["CRM Module"])


# =========================================================================
# 1. STATUS & USER HUB ENDPOINTS
# =========================================================================

@router.get("/status")
def crm_status(current_user: CurrentUser = Depends(require_module_access("CRM"))):
    """
    Backward-compatible CRM module status check.
    """
    return {"success": True, "module": "CRM", "message": "Authorized access to CRM service"}


@router.get("/roles", response_model=CrmRoleListResponse)
def get_crm_roles(
    current_user: CurrentUser = Depends(require_permission("crm.user.manage")),
    db: Session = Depends(get_db)
):
    """
    Returns the list of CRM module roles that the current actor is authorized to assign.
    Strictly restricted to CRM Admin and Global Administrators.
    """
    service = CrmService(db)
    roles = service.get_crm_assignable_roles(current_user)
    return {"success": True, "roles": roles}


@router.get("/users", response_model=CrmUserListResponse)
def list_crm_users(
    search: Optional[str] = Query(None, description="Search by name, username, or email"),
    crmAccess: Optional[bool] = Query(None, description="Filter by active CRM access"),
    roleCode: Optional[str] = Query(None, description="Filter by assigned CRM role code"),
    current_user: CurrentUser = Depends(require_permission("crm.user.manage")),
    db: Session = Depends(get_db)
):
    """
    Lists portal users with their CRM membership status, role, and assigned lead counts.
    Strictly restricted to CRM Admin and Global Administrators.
    """
    service = CrmService(db)
    users = service.list_crm_users(
        actor=current_user,
        search=search,
        crm_access=crmAccess,
        role_code=roleCode
    )
    return {"success": True, "count": len(users), "users": users}


@router.post("/users/{user_id}/access")
def set_crm_user_access(
    user_id: str,
    payload: CrmUserAccessRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.user.manage")),
    db: Session = Depends(get_db)
):
    """
    Enables or disables CRM access for an existing portal user.
    Preserves all historical leads, ownership, and audit attribution when disabled.
    Strictly restricted to CRM Admin and Global Administrators.
    """
    service = CrmService(db)
    is_enabled = payload.enabled if payload.enabled is not None else payload.isEnabled
    if is_enabled is None:
        is_enabled = True

    updated = service.set_crm_access(
        actor=current_user,
        user_id=user_id,
        enabled=is_enabled,
        initial_role_code=payload.roleCode,
        request=request
    )
    return {
        "success": True,
        "message": f"CRM access {'granted to' if is_enabled else 'revoked from'} user {updated['username']}.",
        "user": updated
    }


@router.put("/users/{user_id}/role")
def set_crm_user_role(
    user_id: str,
    payload: CrmUserRoleRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.user.manage")),
    db: Session = Depends(get_db)
):
    """
    Assigns or changes the CRM role for a portal user.
    Strictly restricted to CRM Admin and Global Administrators.
    """
    service = CrmService(db)
    updated = service.set_crm_role(
        actor=current_user,
        user_id=user_id,
        role_code=payload.roleCode,
        request=request
    )
    return {
        "success": True,
        "message": f"CRM role for user {updated['username']} updated to {updated['crmRoleName'] or updated['crmRoleCode']}.",
        "user": updated
    }


# =========================================================================
# 2. ACCOUNT ENDPOINTS
# =========================================================================

@router.get("/accounts", response_model=AccountListResponse)
def list_accounts(
    search: Optional[str] = Query(None, description="Search accounts by name, ID, industry, etc."),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(require_permission("crm.account.view")),
    db: Session = Depends(get_db)
):
    """
    Search and list active CRM Accounts.
    """
    service = CrmService(db)
    accounts = service.list_accounts(search=search, limit=limit, offset=offset)
    return {"success": True, "count": len(accounts), "accounts": accounts}


@router.get("/accounts/{account_id}", response_model=AccountDetailResponse)
def get_account(
    account_id: str,
    current_user: CurrentUser = Depends(require_permission("crm.account.view")),
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific Account, including contacts and leads.
    """
    service = CrmService(db)
    data = service.get_account(account_id)
    return {
        "success": True,
        "account": data["account"],
        "contacts": data["contacts"],
        "leads": data["leads"]
    }


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.account.create")),
    db: Session = Depends(get_db)
):
    """
    Quick-create an Account with duplicate name checking and normalized fields.
    """
    service = CrmService(db)
    account = service.create_account(actor=current_user, payload=payload, request=request)
    return {"success": True, "message": "Account created successfully.", "account": account}


@router.put("/accounts/{account_id}")
def update_account(
    account_id: str,
    payload: AccountUpdate,
    request: Request,
    current_user: CurrentUser = Depends(require_any_permission(["crm.account.edit", "crm.account.create"])),
    db: Session = Depends(get_db)
):
    """
    Update an existing CRM Account.
    """
    service = CrmService(db)
    account = service.update_account(actor=current_user, account_id=account_id, payload=payload, request=request)
    return {"success": True, "message": "Account updated successfully.", "account": account}


# =========================================================================
# 3. CONTACT ENDPOINTS
# =========================================================================

@router.get("/contacts", response_model=ContactListResponse)
def list_contacts(
    search: Optional[str] = Query(None, description="Search contacts by name, email, phone, etc."),
    accountId: Optional[str] = Query(None, description="Filter contacts by account ID"),
    includeUnassigned: bool = Query(False, description="Include contacts without an assigned account"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(require_permission("crm.contact.view")),
    db: Session = Depends(get_db)
):
    """
    Search and list active CRM Contacts, with optional Account filter and unassigned option.
    """
    service = CrmService(db)
    contacts = service.list_contacts(
        search=search,
        account_id=accountId,
        include_unassigned=includeUnassigned,
        limit=limit,
        offset=offset
    )
    return {"success": True, "count": len(contacts), "contacts": contacts}


@router.get("/contacts/{contact_id}", response_model=ContactDetailResponse)
def get_contact(
    contact_id: str,
    current_user: CurrentUser = Depends(require_permission("crm.contact.view")),
    db: Session = Depends(get_db)
):
    """
    Get contact details.
    """
    service = CrmService(db)
    contact = service.get_contact(contact_id)
    return {"success": True, "contact": contact}


@router.post("/contacts", status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.contact.create")),
    db: Session = Depends(get_db)
):
    """
    Quick-create a Contact with duplicate email/phone checking. Supports contacts without accounts.
    """
    service = CrmService(db)
    contact = service.create_contact(actor=current_user, payload=payload, request=request)
    return {"success": True, "message": "Contact created successfully.", "contact": contact}


@router.put("/contacts/{contact_id}")
def update_contact(
    contact_id: str,
    payload: ContactUpdate,
    request: Request,
    current_user: CurrentUser = Depends(require_any_permission(["crm.contact.edit", "crm.contact.create"])),
    db: Session = Depends(get_db)
):
    """
    Update an existing CRM Contact.
    """
    service = CrmService(db)
    contact = service.update_contact(actor=current_user, contact_id=contact_id, payload=payload, request=request)
    return {"success": True, "message": "Contact updated successfully.", "contact": contact}


# =========================================================================
# 4. LEAD MANAGEMENT ENDPOINTS
# =========================================================================

@router.get("/leads", response_model=LeadListResponse)
def list_leads(
    view: str = Query("open", description="Saved view: open, all, unqualified, my_leads, follow_ups_due"),
    search: Optional[str] = Query(None, description="Global search across leads, contacts, and accounts"),
    businessArea: Optional[str] = Query(None, description="Filter by business area: Biogas, WWT"),
    requirementType: Optional[str] = Query(None, description="Filter by requirement type"),
    lifecycleStatus: Optional[str] = Query(None, description="Filter by lifecycle status (for 'all' view)"),
    assignedToUserId: Optional[str] = Query(None, description="Filter by assigned user ID"),
    accountId: Optional[str] = Query(None, description="Filter by account ID"),
    sortBy: str = Query("created_at", description="Sort field: created_at, lead_id, lead_name, next_follow_up_date, last_connected_date"),
    sortOrder: str = Query("desc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    Search, filter, sort, and paginate CRM leads with support for the 5 saved views.
    """
    service = CrmService(db)
    res = service.list_leads(
        actor=current_user,
        view=view,
        search=search,
        business_area=businessArea,
        requirement_type=requirementType,
        lifecycle_status=lifecycleStatus,
        assigned_to_user_id=assignedToUserId,
        account_id=accountId,
        sort_by=sortBy,
        sort_order=sortOrder,
        page=page,
        page_size=pageSize
    )
    return res


@router.get("/leads/{lead_id}", response_model=LeadDetailResponse)
def get_lead(
    lead_id: str,
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    Get full lead details.
    """
    service = CrmService(db)
    lead = service.get_lead(actor=current_user, lead_id=lead_id)
    return {"success": True, "lead": lead}


@router.post("/leads", status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.create")),
    db: Session = Depends(get_db)
):
    """
    Create a new CRM lead.
    Enforces duplicate-open-lead rules, validates assignee CRM membership, and generates LEAD-00001 IDs.
    """
    service = CrmService(db)
    lead = service.create_lead(actor=current_user, payload=payload, request=request)
    return {"success": True, "message": "Lead created successfully.", "lead": lead}


@router.put("/leads/{lead_id}")
def update_lead(
    lead_id: str,
    payload: LeadUpdate,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Update permitted lead fields, reassignment, or requirement.
    """
    service = CrmService(db)
    lead = service.update_lead(actor=current_user, lead_id=lead_id, payload=payload, request=request)
    return {"success": True, "message": "Lead updated successfully.", "lead": lead}


@router.post("/leads/{lead_id}/status")
def transition_lead_status(
    lead_id: str,
    payload: LeadStatusTransitionRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.status.update")),
    db: Session = Depends(get_db)
):
    """
    Dedicated lifecycle-status transition endpoint (Open, Qualified, Disqualified).
    """
    service = CrmService(db)
    lead = service.transition_lead_status(
        actor=current_user,
        lead_id=lead_id,
        new_status=payload.status,
        remarks=payload.remarks,
        request=request
    )
    return {
        "success": True,
        "message": f"Lead status updated to {payload.status}.",
        "lead": lead
    }


# =========================================================================
# 5. LEAD COMMUNICATION HISTORY ENDPOINTS
# =========================================================================

@router.get("/leads/{lead_id}/communications", response_model=CommunicationListResponse)
def list_lead_communications(
    lead_id: str,
    current_user: CurrentUser = Depends(require_permission("crm.communication.view")),
    db: Session = Depends(get_db)
):
    """
    Get chronological customer interaction history for a lead.
    """
    service = CrmService(db)
    comms = service.list_communications(lead_id)
    return {"success": True, "count": len(comms), "communications": comms}


@router.post("/leads/{lead_id}/communications", status_code=status.HTTP_201_CREATED)
def create_lead_communication(
    lead_id: str,
    payload: CommunicationCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.communication.create")),
    db: Session = Depends(get_db)
):
    """
    Log an interaction for a lead.
    Updates last_connected_date only for qualifying client interactions.
    """
    service = CrmService(db)
    comm = service.create_communication(
        actor=current_user,
        lead_id=lead_id,
        payload=payload,
        request=request
    )
    return {"success": True, "message": "Communication logged successfully.", "communication": comm}


# =========================================================================
# 6. DASHBOARD METRICS ENDPOINT
# =========================================================================

@router.get("/dashboard/metrics", response_model=DashboardMetricsResponse)
def get_dashboard_metrics(
    current_user: CurrentUser = Depends(require_permission("crm.dashboard.view")),
    db: Session = Depends(get_db)
):
    """
    Returns actual live database metrics for Total Leads, Open Leads, Qualified, Disqualified, My Leads, and Follow-ups.
    """
    service = CrmService(db)
    return service.get_dashboard_metrics(actor=current_user)


@router.get("/assignees")
def list_crm_assignees(
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    Returns list of active CRM users who can be assigned leads.
    """
    service = CrmService(db)
    assignees = service.list_eligible_assignees()
    return {"success": True, "count": len(assignees), "assignees": assignees}

