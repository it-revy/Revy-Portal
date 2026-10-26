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
    CrmUserAssignRequest,
    AvailableUserListResponse,
    AccountCreate,
    AccountUpdate,
    AccountListResponse,
    AccountDetailResponse,
    AccountMatchResponse,
    ContactCreate,
    ContactUpdate,
    ContactListResponse,
    ContactDetailResponse,
    ContactMatchResponse,
    LeadCreate,
    LeadUpdate,
    LeadStatusTransitionRequest,
    LeadListResponse,
    LeadDetailResponse,
    LeadQualificationMatchesResponse,
    LeadQualifyRequest,
    LeadQualifyResponse,
    OpportunityListResponse,
    OpportunityDetailResponse,
    OpportunityStageTransitionRequest,
    OpportunityUpdateRequest,
    OpportunityPipelineSummaryResponse,
    WorkstreamItem,
    OpportunityWorkstreamsResponse,
    RequirementRouteRequest,
    RequirementRouteResponse,
    MilestoneCreate,
    MilestoneUpdate,
    MilestoneStatusTransitionRequest,
    MilestoneItem,
    MilestoneListResponse,
    MilestoneDetailResponse,
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


@router.get("/available-users", response_model=AvailableUserListResponse)
def list_available_central_users(
    search: Optional[str] = Query(None, description="Search central users by name, username, email, phone, or designation"),
    current_user: CurrentUser = Depends(require_permission("crm.user.manage")),
    db: Session = Depends(get_db)
):
    """
    Retrieves eligible Central Users who are not currently assigned to the CRM module.
    Strictly restricted to CRM Admin and Global Administrators.
    """
    service = CrmService(db)
    users = service.list_available_central_users(search=search)
    return {"success": True, "count": len(users), "users": users}


@router.post("/users/assign")
def assign_user_to_crm(
    payload: CrmUserAssignRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.user.manage")),
    db: Session = Depends(get_db)
):
    """
    Assigns an existing Central User to the CRM module with an appropriate CRM role and status.
    Strictly restricted to CRM Admin and Global Administrators.
    """
    service = CrmService(db)
    result = service.assign_user_to_crm(
        actor=current_user,
        user_id=payload.userId,
        role_code=payload.roleCode,
        is_active=payload.isActive,
        request=request
    )
    return {
        "success": True,
        "message": f"User {result['username']} successfully assigned to CRM module.",
        "user": result
    }


@router.get("/users/{user_id}")
def get_crm_user_details(
    user_id: str,
    current_user: CurrentUser = Depends(require_permission("crm.user.manage")),
    db: Session = Depends(get_db)
):
    """
    Retrieves central user identity details (read-only) along with CRM membership and role.
    Strictly restricted to CRM Admin and Global Administrators.
    """
    service = CrmService(db)
    user_data = service.get_crm_user_details(user_id)
    return {"success": True, "user": user_data}


@router.delete("/users/{user_id}/membership")
def remove_crm_membership(
    user_id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.user.manage")),
    db: Session = Depends(get_db)
):
    """
    Removes user membership from the CRM module without deleting the Central User record.
    Strictly restricted to CRM Admin and Global Administrators.
    """
    service = CrmService(db)
    result = service.remove_crm_membership(actor=current_user, user_id=user_id, request=request)
    return {
        "success": True,
        "message": result.get("message") or f"User {result.get('username', '')} removed from CRM module successfully.",
        "user": result
    }


# =========================================================================
# 2. ACCOUNT ENDPOINTS
# =========================================================================

@router.get("/accounts", response_model=AccountListResponse)
def list_accounts(
    search: Optional[str] = Query(None, description="Search accounts by name, ID, industry, etc."),
    limit: int = Query(50, ge=1, le=250),
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


@router.get("/accounts/matches", response_model=AccountMatchResponse)
def get_account_matches(
    name: Optional[str] = Query(None, description="Company name to check for potential matches"),
    website: Optional[str] = Query(None, description="Website or domain to check"),
    email: Optional[str] = Query(None, description="Email to check"),
    phone: Optional[str] = Query(None, description="Phone number to check"),
    excludeId: Optional[str] = Query(None, description="Exclude specific account ID if editing"),
    limit: int = Query(10, ge=1, le=50),
    current_user: CurrentUser = Depends(require_permission("crm.account.view")),
    db: Session = Depends(get_db)
):
    """
    Search potential duplicate or matching Accounts using normalized name, domain, email, and phone heuristics.
    """
    service = CrmService(db)
    matches = service.search_account_matches(
        name=name,
        website=website,
        email=email,
        phone=phone,
        exclude_id=excludeId,
        limit=limit
    )
    return {"success": True, "count": len(matches), "matches": matches}


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


@router.get("/contacts/matches", response_model=ContactMatchResponse)
def get_contact_matches(
    name: Optional[str] = Query(None, description="Contact person name to check"),
    email: Optional[str] = Query(None, description="Email address to check"),
    mobileNumber: Optional[str] = Query(None, description="Mobile/phone number to check"),
    accountId: Optional[str] = Query(None, description="Account ID context"),
    excludeId: Optional[str] = Query(None, description="Exclude specific contact ID if editing"),
    limit: int = Query(10, ge=1, le=50),
    current_user: CurrentUser = Depends(require_permission("crm.contact.view")),
    db: Session = Depends(get_db)
):
    """
    Search potential duplicate or matching Contacts using normalized email, mobile number, and name heuristics.
    """
    service = CrmService(db)
    matches = service.search_contact_matches(
        name=name,
        email=email,
        mobile_number=mobileNumber,
        account_id=accountId,
        exclude_id=excludeId,
        limit=limit
    )
    return {"success": True, "count": len(matches), "matches": matches}


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


@router.get("/leads/{lead_id}/qualification-matches", response_model=LeadQualificationMatchesResponse)
def get_lead_qualification_matches(
    lead_id: str,
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    Search for existing matching Accounts and Contacts to suggest reuse before qualification.
    """
    service = CrmService(db)
    return service.search_qualification_matches(actor=current_user, lead_id=lead_id)


@router.post("/leads/{lead_id}/qualify", response_model=LeadQualifyResponse)
def qualify_lead(
    lead_id: str,
    payload: LeadQualifyRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_any_permission(["crm.lead.edit", "crm.lead.status.update"])),
    db: Session = Depends(get_db)
):
    """
    Qualify a Lead into an Opportunity, transactionally creating or reusing Account and Contact records.
    """
    service = CrmService(db)
    return service.qualify_lead(
        actor=current_user,
        lead_id=lead_id,
        payload=payload,
        request=request
    )


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


# =========================================================================
# 7. OPPORTUNITIES ENDPOINTS
# =========================================================================

@router.get("/opportunities", response_model=OpportunityListResponse)
def list_opportunities(
    search: Optional[str] = Query(None, description="Search by name, code, or account"),
    accountId: Optional[str] = Query(None, description="Filter by account ID"),
    status: Optional[str] = Query(None, description="Filter by opportunity status (Open, Won, Lost, ALL)"),
    stage: Optional[str] = Query(None, description="Filter by stage (Qualify, Develop, Propose, Close, ALL)"),
    businessArea: Optional[str] = Query(None, description="Filter by business area"),
    assignedToUserId: Optional[str] = Query(None, description="Filter by assigned user ID"),
    view: Optional[str] = Query(None, description="Preset view: all, open, my, won, lost"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    List Opportunities with advanced filters, pagination, and total count.
    """
    service = CrmService(db)
    opps, total_count = service.list_opportunities(
        actor=current_user,
        search=search,
        account_id=accountId,
        status=status,
        stage=stage,
        business_area=businessArea,
        assigned_to_user_id=assignedToUserId,
        view=view,
        limit=limit,
        offset=offset
    )
    return {"success": True, "count": len(opps), "totalCount": total_count, "opportunities": opps}


@router.get("/opportunities/pipeline-summary", response_model=OpportunityPipelineSummaryResponse)
def get_pipeline_summary(
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    Get authoritative metrics for the Opportunity Pipeline Kanban workspace.
    """
    service = CrmService(db)
    return service.get_pipeline_summary(actor=current_user)


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityDetailResponse)
def get_opportunity(
    opportunity_id: str,
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a single Opportunity.
    """
    service = CrmService(db)
    opp = service.get_opportunity(opportunity_id)
    return {"success": True, "opportunity": opp}


@router.post("/opportunities/{opportunity_id}/stage", response_model=OpportunityDetailResponse)
def transition_opportunity_stage(
    opportunity_id: str,
    payload: OpportunityStageTransitionRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Transition Opportunity stage (Qualify -> Develop -> Propose -> Close) or mark Won/Lost.
    Enforces mandatory lossReason when marking an opportunity as Lost.
    """
    service = CrmService(db)
    opp = service.transition_opportunity_stage(
        actor=current_user,
        opp_id=opportunity_id,
        payload=payload,
        request=request
    )
    return {"success": True, "opportunity": opp}


@router.put("/opportunities/{opportunity_id}", response_model=OpportunityDetailResponse)
def update_opportunity(
    opportunity_id: str,
    payload: OpportunityUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Update core editable fields of an Opportunity (name, estimatedValue, expectedCloseDate, etc.).
    """
    service = CrmService(db)
    opp = service.update_opportunity(
        actor=current_user,
        opp_id=opportunity_id,
        payload=payload,
        request=request
    )
    return {"success": True, "opportunity": opp}


# =========================================================================
# 8. REQUIREMENT ROUTING ENDPOINTS
# =========================================================================

@router.get("/opportunities/{opportunity_id}/workstreams", response_model=OpportunityWorkstreamsResponse)
def get_opportunity_workstreams(
    opportunity_id: str,
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    List all downstream workstreams (Consulting, Sample Testing, Product) linked to an Opportunity.
    """
    service = CrmService(db)
    workstreams = service.get_opportunity_workstreams(opp_id=opportunity_id)
    return {"success": True, "opportunityId": opportunity_id, "workstreams": workstreams}


@router.post("/opportunities/{opportunity_id}/route-requirements", response_model=RequirementRouteResponse)
def route_opportunity_requirements(
    opportunity_id: str,
    payload: RequirementRouteRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Route Opportunity requirement types to downstream workstreams idempotently.
    Consulting -> Consulting Engagement (Draft)
    Sample Testing -> Sample Submission (Received)
    Product -> Product Transaction (Recommendation)
    """
    service = CrmService(db)
    routed, message = service.route_opportunity_requirements(
        actor=current_user,
        opp_id=opportunity_id,
        payload=payload,
        request=request
    )
    return {
        "success": True,
        "message": message,
        "opportunityId": opportunity_id,
        "routedWorkstreams": routed
    }


@router.put("/opportunities/{opportunity_id}/requirements", response_model=OpportunityDetailResponse)
def update_opportunity_requirements(
    opportunity_id: str,
    payload: RequirementRouteRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Update the requirement types for an Opportunity.
    """
    service = CrmService(db)
    update_payload = OpportunityUpdateRequest(requirementTypes=payload.requirementTypes)
    opp = service.update_opportunity(
        actor=current_user,
        opp_id=opportunity_id,
        payload=update_payload,
        request=request
    )
    return {"success": True, "opportunity": opp}


# =========================================================================
# 9. MILESTONE INTEGRATION ENDPOINTS
# =========================================================================

@router.get("/opportunities/{opportunity_id}/milestones", response_model=MilestoneListResponse)
def list_opportunity_milestones(
    opportunity_id: str,
    status: Optional[str] = Query(None, description="Filter by status (Pending, In Progress, Completed, Cancelled)"),
    assignedToUserId: Optional[str] = Query(None, description="Filter by assigned user ID"),
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    List milestones associated with a specific Opportunity.
    """
    service = CrmService(db)
    milestones = service.list_milestones(
        actor=current_user,
        opportunity_id=opportunity_id,
        status=status,
        assigned_to_user_id=assignedToUserId
    )
    return {"success": True, "count": len(milestones), "milestones": milestones}


@router.post("/opportunities/{opportunity_id}/milestones", response_model=MilestoneDetailResponse, status_code=status.HTTP_201_CREATED)
def create_milestone(
    opportunity_id: str,
    payload: MilestoneCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Create a new milestone associated with an Opportunity.
    """
    service = CrmService(db)
    milestone = service.create_milestone(
        actor=current_user,
        opp_id=opportunity_id,
        payload=payload,
        request=request
    )
    return {"success": True, "milestone": milestone}


@router.get("/milestones/upcoming", response_model=MilestoneListResponse)
def get_upcoming_milestones(
    days: int = Query(14, ge=1, le=90, description="Horizon in days to look ahead"),
    assignedToUserId: Optional[str] = Query(None, description="Filter by assigned user ID"),
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    Get all active milestones due within the next N days (Asia/Kolkata timezone aware).
    """
    service = CrmService(db)
    milestones = service.get_upcoming_milestones(
        actor=current_user,
        days=days,
        assigned_to_user_id=assignedToUserId
    )
    return {"success": True, "count": len(milestones), "milestones": milestones}


@router.get("/milestones/{milestone_id}", response_model=MilestoneDetailResponse)
def get_milestone(
    milestone_id: str,
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    Get a single milestone by ID or code.
    """
    service = CrmService(db)
    milestone = service.get_milestone(milestone_id)
    return {"success": True, "milestone": milestone}


@router.put("/milestones/{milestone_id}", response_model=MilestoneDetailResponse)
def update_milestone(
    milestone_id: str,
    payload: MilestoneUpdate,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Update details of an existing milestone.
    """
    service = CrmService(db)
    milestone = service.update_milestone(
        actor=current_user,
        milestone_id=milestone_id,
        payload=payload,
        request=request
    )
    return {"success": True, "milestone": milestone}


@router.post("/milestones/{milestone_id}/status", response_model=MilestoneDetailResponse)
def transition_milestone_status(
    milestone_id: str,
    payload: MilestoneStatusTransitionRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Transition milestone status (Pending -> In Progress -> Completed / Cancelled).
    Sets completed_at automatically when transitioning to Completed.
    """
    service = CrmService(db)
    milestone = service.transition_milestone_status(
        actor=current_user,
        milestone_id=milestone_id,
        payload=payload,
        request=request
    )
    return {"success": True, "milestone": milestone}


@router.delete("/milestones/{milestone_id}")
def delete_milestone(
    milestone_id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Delete a milestone.
    """
    service = CrmService(db)
    service.delete_milestone(
        actor=current_user,
        milestone_id=milestone_id,
        request=request
    )
    return {"success": True, "message": "Milestone deleted successfully."}

