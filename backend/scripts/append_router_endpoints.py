import os

router_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "crm", "router.py")
with open(router_path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace("\r\n", "\n")

# Add schema imports
import_target = "    RevenueMetricsResponse\n)"
import_replacement = """    RevenueMetricsResponse,
    NurturingActivityCompleteRequest,
    NurturingActivityRescheduleRequest,
    NurturingActivitySkipRequest,
    CustomerResponseRequest,
    NurturingPauseRequest,
    NurturingResumeRequest,
    NurturingCancelRequest,
    NurturingDetailsResponse,
    NextActivityResponse,
    UnifiedTimelineResponse
)
from app.crm.nurturing_service import LeadNurturingService"""

assert import_target in c, "import_target not found in router.py!"
c = c.replace(import_target, import_replacement)

# Append endpoints
nurturing_endpoints = '''

# =========================================================================
# LEAD NURTURING & UNIFIED TIMELINE ENDPOINTS
# =========================================================================

@router.get("/leads/{lead_id}/nurturing")
def get_lead_nurturing(
    lead_id: str,
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    Retrieve current lead nurturing process status and stages.
    """
    service = LeadNurturingService(db)
    details = service.get_nurturing_details(lead_id)
    return {"success": True, "nurturing": details}


@router.get("/leads/{lead_id}/timeline")
def get_lead_unified_timeline(
    lead_id: str,
    sort: str = Query("desc", description="Sort order: 'desc' (newest first) or 'asc' (oldest first)"),
    filter: str = Query("all", description="Filter: 'all', 'emails', 'calls', 'meetings', 'notes', 'nurturing', 'status_changes', 'responses'"),
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    Retrieve unified chronological timeline combining nurturing activities,
    manual interactions, lead status changes, and customer responses.
    """
    service = LeadNurturingService(db)
    items = service.get_unified_timeline(lead_id=lead_id, sort_order=sort, filter_type=filter)
    return {"success": True, "count": len(items), "timeline": items}


@router.get("/leads/{lead_id}/next-activity")
def get_lead_next_activity(
    lead_id: str,
    current_user: CurrentUser = Depends(require_permission("crm.lead.view")),
    db: Session = Depends(get_db)
):
    """
    Retrieve next actionable nurturing activity or paused/terminal state.
    """
    service = LeadNurturingService(db)
    next_act = service.get_next_activity(lead_id)
    return {"success": True, "nextActivity": next_act}


@router.post("/leads/{lead_id}/nurturing/activities/{activity_id}/complete")
def complete_nurturing_activity(
    lead_id: str,
    activity_id: str,
    payload: NurturingActivityCompleteRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Mark a nurturing activity as Completed.
    Automatically logs an interaction in lead_communications and advances to next stage.
    """
    service = LeadNurturingService(db)
    result = service.complete_activity(
        lead_id=lead_id,
        activity_id=activity_id,
        actor=current_user,
        notes=payload.notes,
        outcome=payload.outcome,
        email_message_reference=payload.emailMessageReference,
        request=request
    )
    return {"success": True, "message": "Activity marked as completed successfully.", "nurturing": result}


@router.post("/leads/{lead_id}/nurturing/activities/{activity_id}/reschedule")
def reschedule_nurturing_activity(
    lead_id: str,
    activity_id: str,
    payload: NurturingActivityRescheduleRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Reschedule a pending nurturing activity with a mandatory reason.
    """
    service = LeadNurturingService(db)
    result = service.reschedule_activity(
        lead_id=lead_id,
        activity_id=activity_id,
        new_due_date=payload.newDueDate,
        reason=payload.reason,
        actor=current_user,
        request=request
    )
    return {"success": True, "message": "Activity rescheduled successfully.", "nurturing": result}


@router.post("/leads/{lead_id}/nurturing/activities/{activity_id}/skip")
def skip_nurturing_activity(
    lead_id: str,
    activity_id: str,
    payload: NurturingActivitySkipRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Skip a stage with mandatory reason and advance workflow.
    """
    service = LeadNurturingService(db)
    result = service.skip_activity(
        lead_id=lead_id,
        activity_id=activity_id,
        reason=payload.reason,
        actor=current_user,
        request=request
    )
    return {"success": True, "message": "Activity skipped and workflow advanced.", "nurturing": result}


@router.post("/leads/{lead_id}/nurturing/customer-response")
def record_customer_response(
    lead_id: str,
    payload: CustomerResponseRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Record customer response, automatically pause nurturing, and optionally update lead status.
    """
    service = LeadNurturingService(db)
    result = service.record_customer_response(
        lead_id=lead_id,
        channel=payload.channel,
        response_notes=payload.responseNotes,
        outcome=payload.outcome,
        actor=current_user,
        target_lifecycle_status=payload.targetLifecycleStatus,
        pause_nurturing=payload.pauseNurturing,
        request=request
    )
    return {"success": True, "message": "Customer response recorded successfully.", "nurturing": result}


@router.post("/leads/{lead_id}/nurturing/pause")
def pause_lead_nurturing(
    lead_id: str,
    payload: NurturingPauseRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Pause active nurturing workflow.
    """
    service = LeadNurturingService(db)
    result = service.pause_nurturing(
        lead_id=lead_id,
        reason=payload.reason or "Paused by user.",
        actor=current_user,
        request=request
    )
    return {"success": True, "message": "Nurturing process paused.", "nurturing": result}


@router.post("/leads/{lead_id}/nurturing/resume")
def resume_lead_nurturing(
    lead_id: str,
    payload: NurturingResumeRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Resume paused nurturing workflow with rescheduled follow-up date.
    """
    service = LeadNurturingService(db)
    result = service.resume_nurturing(
        lead_id=lead_id,
        next_due_date=payload.nextDueDate,
        actor=current_user,
        request=request
    )
    return {"success": True, "message": "Nurturing process resumed.", "nurturing": result}


@router.post("/leads/{lead_id}/nurturing/cancel")
def cancel_lead_nurturing(
    lead_id: str,
    payload: NurturingCancelRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("crm.lead.edit")),
    db: Session = Depends(get_db)
):
    """
    Cancel nurturing workflow with documented business reason.
    """
    service = LeadNurturingService(db)
    result = service.cancel_nurturing(
        lead_id=lead_id,
        reason=payload.reason,
        actor=current_user,
        request=request
    )
    return {"success": True, "message": "Nurturing process cancelled.", "nurturing": result}
'''

c = c + nurturing_endpoints

with open(router_path, "w", encoding="utf-8") as f:
    f.write(c)

print("Updated app/crm/router.py successfully with nurturing endpoints")

