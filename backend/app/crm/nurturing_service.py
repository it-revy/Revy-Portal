"""
REVY CRM Lead Nurturing & Unified Timeline Service
Enterprise-grade, date-driven Lead Nurturing engine aligned with Microsoft Dynamics 365 Sales Hub.
"""
import logging
import threading
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc, asc
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.audit.service import AuditService
from app.crm.model import (
    Lead,
    LeadNurturingProcess,
    NurturingActivity,
    LeadCommunicationHistory,
    CrmSequence
)
from app.crm.schema import ALLOWED_LIFECYCLE_STATUSES
from app.users.model import User

logger = logging.getLogger("revy.crm.nurturing")
_nurturing_sqlite_lock = threading.Lock()

# Timezone for date calculation and display
KOLKATA_TZ = ZoneInfo("Asia/Kolkata")

# Default 10-stage nurturing workflow sequence (Configurable CRM default)
DEFAULT_NURTURING_STAGES = [
    {
        "stage_number": 1,
        "name": "Introduction Email",
        "activity_type": "Email",
        "interval_days": 5,  # Date Connected + 5 calendar days
        "description": "Send formal introductory email presenting REVY Environmental Solutions capabilities and products/services.",
        "requires_action": True,
        "is_waiting_period": False
    },
    {
        "stage_number": 2,
        "name": "Wait for Response",
        "activity_type": "Waiting Period",
        "interval_days": 5,
        "description": "Waiting period for customer to review introductory email and respond.",
        "requires_action": False,
        "is_waiting_period": True
    },
    {
        "stage_number": 3,
        "name": "Reminder Email",
        "activity_type": "Email",
        "interval_days": 5,
        "description": "Send follow-up reminder email referencing introduction email.",
        "requires_action": True,
        "is_waiting_period": False
    },
    {
        "stage_number": 4,
        "name": "Wait for Response",
        "activity_type": "Waiting Period",
        "interval_days": 5,
        "description": "Waiting period for customer response following reminder email.",
        "requires_action": False,
        "is_waiting_period": True
    },
    {
        "stage_number": 5,
        "name": "Call Customer",
        "activity_type": "Phone Call",
        "interval_days": 5,
        "description": "Phone call to client contact to discuss project requirements, technical specs, and commercial timeline.",
        "requires_action": True,
        "is_waiting_period": False
    },
    {
        "stage_number": 6,
        "name": "Wait for Response",
        "activity_type": "Waiting Period",
        "interval_days": 5,
        "description": "Post-call waiting period for client internal review and technical deliberation.",
        "requires_action": False,
        "is_waiting_period": True
    },
    {
        "stage_number": 7,
        "name": "Thank You / Follow-up Email",
        "activity_type": "Email",
        "interval_days": 5,
        "description": "Send meeting summary or thank you email reiterating call discussion and requested next actions.",
        "requires_action": True,
        "is_waiting_period": False
    },
    {
        "stage_number": 8,
        "name": "Customer Response Review",
        "activity_type": "Review",
        "interval_days": 5,
        "description": "Review customer engagement history, interest level, and determine proposal or qualification route.",
        "requires_action": True,
        "is_waiting_period": False
    },
    {
        "stage_number": 9,
        "name": "Next Follow-up / Meeting",
        "activity_type": "Meeting",
        "interval_days": 5,
        "description": "Schedule technical presentation, lab testing discussion, or formal quotation meeting.",
        "requires_action": True,
        "is_waiting_period": False
    },
    {
        "stage_number": 10,
        "name": "Final Follow-up / Closure",
        "activity_type": "Review",
        "interval_days": 5,
        "description": "Final nurturing review to transition lead to active commercial pipeline or dormant archive.",
        "requires_action": True,
        "is_waiting_period": False
    }
]


def get_current_kolkata_date() -> date:
    """Return current date in Asia/Kolkata timezone."""
    return datetime.now(KOLKATA_TZ).date()


def get_current_kolkata_datetime() -> datetime:
    """Return current timezone-aware datetime."""
    return datetime.now(timezone.utc)


def format_sequence_id(db: Session, entity_name: str, prefix: str, padding: int = 5, commit: bool = True) -> str:
    """Generate concurrency-safe sequence ID without committing outer transaction."""
    from app.crm.service import get_next_sequence_id
    code = get_next_sequence_id(db, entity_name, prefix, padding, commit=commit)
    # Collision-proof guard for sequences across re-seeded databases
    if entity_name.upper() in ("NURTURING", "LEAD_NURTURING"):
        while db.query(LeadNurturingProcess).filter(LeadNurturingProcess.nurturing_id == code).first():
            code = get_next_sequence_id(db, entity_name, prefix, padding, commit=commit)
    elif entity_name.upper() in ("ACTIVITY", "NURTURING_ACTIVITY"):
        while db.query(NurturingActivity).filter(NurturingActivity.activity_id == code).first():
            code = get_next_sequence_id(db, entity_name, prefix, padding, commit=commit)
    return code


class LeadNurturingService:
    def __init__(self, db: Session, audit_service: Optional[AuditService] = None):
        self.db = db
        self.audit_service = audit_service or AuditService(db)

    # =========================================================================
    # 1. AUTOMATIC NURTURING INITIALIZATION
    # =========================================================================

    def initialize_lead_nurturing(
        self,
        lead: Lead,
        actor_id: Optional[str] = None,
        commit: bool = True
    ) -> LeadNurturingProcess:
        """
        Automatically start nurturing whenever a new lead is created.
        - Process Status: Active
        - Stage 1: Introduction Email (Status: Pending)
        - Follow-up date: Date Connected + 5 calendar days (or creation date + 5 days)
        - Transaction-safe & idempotent.
        """
        # 1. Check if nurturing process already exists (prevent duplicate on retry)
        existing_process = self.db.query(LeadNurturingProcess).filter(
            LeadNurturingProcess.lead_id == lead.id
        ).first()

        if existing_process:
            logger.info(f"Nurturing process already exists for lead {lead.lead_id}: {existing_process.nurturing_id}")
            return existing_process

        now_utc = get_current_kolkata_datetime()
        ref_date = lead.connected_date or (lead.created_at.date() if lead.created_at else get_current_kolkata_date())
        first_due_date = ref_date + timedelta(days=5)

        nurturing_code = format_sequence_id(self.db, "NURTURING", "NUR", commit=commit)
        process = LeadNurturingProcess(
            nurturing_id=nurturing_code,
            lead_id=lead.id,
            assigned_to_user_id=lead.assigned_to_user_id,
            current_stage=1,
            nurturing_status="Active",
            started_at=now_utc,
            next_activity_date=first_due_date,
            created_by_id=actor_id,
            created_at=now_utc
        )
        self.db.add(process)
        self.db.flush()  # Obtain process.id

        # Create Stage 1 Activity: Introduction Email (Pending)
        stage_1_def = DEFAULT_NURTURING_STAGES[0]
        act_code = format_sequence_id(self.db, "ACTIVITY", "ACT", commit=commit)
        stage_1_act = NurturingActivity(
            activity_id=act_code,
            nurturing_id=process.id,
            lead_id=lead.id,
            stage_number=1,
            activity_type=stage_1_def["activity_type"],
            subject=stage_1_def["name"],
            description=stage_1_def["description"],
            scheduled_at=now_utc,
            due_date=first_due_date,
            activity_status="Pending",
            created_by_id=actor_id,
            created_at=now_utc
        )
        self.db.add(stage_1_act)
        self.db.flush()

        # Update process next_activity_id and lead next_follow_up fields
        process.next_activity_id = stage_1_act.id
        lead.next_follow_up_date = first_due_date
        lead.next_follow_up_action = f"Stage 1: {stage_1_act.subject}"

        if commit:
            self.db.commit()
            self.db.refresh(process)

        logger.info(f"Initialized nurturing process {nurturing_code} for Lead {lead.lead_id}. First activity {act_code} due {first_due_date}")
        return process

    # =========================================================================
    # 2. DATE CONNECTED RECALCULATION ENGINE
    # =========================================================================

    def recalculate_on_connected_date_change(
        self,
        lead: Lead,
        new_connected_date: Optional[date],
        actor_id: Optional[str] = None
    ) -> Optional[LeadNurturingProcess]:
        """
        Recalculate pending future follow-up dates when Date Connected changes.
        - Preserves all completed activities without modification.
        - Recalculates first pending activity if no activities completed yet, or future activities.
        """
        process = self.db.query(LeadNurturingProcess).filter(
            LeadNurturingProcess.lead_id == lead.id
        ).first()

        if not process or process.nurturing_status not in ("Active", "Paused"):
            return process

        if not new_connected_date:
            return process

        # Find first activity
        act_1 = self.db.query(NurturingActivity).filter(
            NurturingActivity.nurturing_id == process.id,
            NurturingActivity.stage_number == 1
        ).first()

        # If Stage 1 is still Pending, recalculate its due date to new Date Connected + 5 days
        if act_1 and act_1.activity_status in ("Pending", "In Progress", "Overdue"):
            new_due_date = new_connected_date + timedelta(days=5)
            act_1.due_date = new_due_date
            act_1.activity_status = "Pending"  # Clear overdue if recalculated to future
            process.next_activity_date = new_due_date
            lead.next_follow_up_date = new_due_date
            lead.next_follow_up_action = f"Stage 1: {act_1.subject}"

            logger.info(f"Recalculated Stage 1 due date for Lead {lead.lead_id} to {new_due_date} from new Date Connected {new_connected_date}")

        return process

    # =========================================================================
    # 3. COMPLETE NURTURING ACTIVITY (TRANSACTION-SAFE & IDEMPOTENT)
    # =========================================================================

    def complete_activity(
        self,
        lead_id: str,
        activity_id: str,
        actor: User,
        notes: Optional[str] = None,
        outcome: Optional[str] = None,
        email_message_reference: Optional[str] = None,
        request: Optional[Any] = None
    ) -> Dict[str, Any]:
        is_sqlite = bool(self.db.bind and "sqlite" in str(self.db.bind.url))
        if is_sqlite:
            with _nurturing_sqlite_lock:
                return self._complete_activity_impl(
                    lead_id=lead_id,
                    activity_id=activity_id,
                    actor=actor,
                    notes=notes,
                    outcome=outcome,
                    email_message_reference=email_message_reference,
                    request=request
                )
        return self._complete_activity_impl(
            lead_id=lead_id,
            activity_id=activity_id,
            actor=actor,
            notes=notes,
            outcome=outcome,
            email_message_reference=email_message_reference,
            request=request
        )

    def _complete_activity_impl(
        self,
        lead_id: str,
        activity_id: str,
        actor: User,
        notes: Optional[str] = None,
        outcome: Optional[str] = None,
        email_message_reference: Optional[str] = None,
        request: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Mark a nurturing activity as Completed.
        1. Validate activity can be completed.
        2. Set Completed timestamp and responsible user.
        3. Create linked interaction record in lead_communications (source = 'Lead Nurturing').
        4. Activate next eligible stage (anchor = completion date + 5 calendar days).
        5. Synchronize Lead status and follow-up fields.
        6. Return complete updated state.
        7. Idempotent: If already completed, returns existing state safely.
        """
        # Clean activity_id defensively (strip any 'act_' prefix if passed from client timeline)
        clean_act_id = str(activity_id).strip()
        if clean_act_id.startswith("act_"):
            clean_act_id = clean_act_id[4:]

        activity_query = self.db.query(NurturingActivity).filter(
            or_(
                NurturingActivity.id == clean_act_id,
                NurturingActivity.id == str(activity_id).strip(),
                NurturingActivity.activity_id == clean_act_id,
                NurturingActivity.activity_id == str(activity_id).strip()
            )
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            activity = activity_query.with_for_update().first()
        else:
            activity = activity_query.first()

        if not activity:
            raise NotFoundError(f"Nurturing activity '{activity_id}' not found.")

        lead = self.db.query(Lead).filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id)).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        # Strict Lead Ownership Check
        if activity.lead_id != lead.id:
            raise ValidationError(f"Activity '{activity_id}' does not belong to Lead '{lead_id}'.")

        process = self.db.query(LeadNurturingProcess).filter(
            LeadNurturingProcess.id == activity.nurturing_id
        ).first()

        # Idempotency check: If already completed, return existing completion state safely
        if activity.activity_status == "Completed":
            logger.info(f"Activity {activity.activity_id} is already Completed. Returning existing state.")
            return self.get_nurturing_details(lead.id)

        now_utc = get_current_kolkata_datetime()
        completion_date = now_utc.date()

        # 1. Update activity to Completed
        activity.activity_status = "Completed"
        activity.completed_at = now_utc
        activity.completed_by_id = str(actor.id)
        if notes:
            activity.notes = notes.strip()
        if outcome:
            activity.outcome = outcome.strip()
        if email_message_reference:
            activity.email_message_reference = email_message_reference.strip()

        # 2. Automatically create linked interaction history entry in lead_communications
        # Ensure exactly one interaction record is linked
        existing_comm = self.db.query(LeadCommunicationHistory).filter(
            LeadCommunicationHistory.nurturing_activity_id == activity.id
        ).first()

        if not existing_comm:
            channel_map = {
                "Email": "Email",
                "Phone Call": "Phone / Call",
                "Meeting": "In-Person Meeting",
                "Review": "Other",
                "Waiting Period": "Other"
            }
            channel_val = channel_map.get(activity.activity_type, "Email")
            comm_code = format_sequence_id(self.db, "COMMUNICATION", "COM", commit=False)
            
            summary_text = notes.strip() if notes else f"Completed nurturing stage {activity.stage_number}: {activity.subject}"
            
            comm = LeadCommunicationHistory(
                communication_id=comm_code,
                lead_id=lead.id,
                nurturing_activity_id=activity.id,
                communication_date=now_utc,
                channel=channel_val,
                event_type=f"Nurturing Stage {activity.stage_number}: {activity.subject}",
                subject=activity.subject,
                summary=summary_text,
                outcome=outcome.strip() if outcome else "Completed",
                interaction_source="Lead Nurturing",
                created_by_id=str(actor.id),
                created_at=now_utc
            )
            self.db.add(comm)

        # 3. Lead Status & Follow-up Synchronization
        lead.last_connected_date = now_utc

        # 4. Determine & activate next eligible stage
        current_stage_num = activity.stage_number
        next_stage_num = current_stage_num + 1

        # Skip waiting period stages if they are automated buffers
        next_stage_def = next((s for s in DEFAULT_NURTURING_STAGES if s["stage_number"] == next_stage_num), None)
        
        # If next stage is a waiting period (e.g. Stage 2, 4, 6), record waiting buffer and prepare next actionable stage
        if next_stage_def and next_stage_def.get("is_waiting_period"):
            # Waiting period length is 5 days from completion date
            next_action_due = completion_date + timedelta(days=next_stage_def.get("interval_days", 5))
            
            # The next actionable stage is stage_number + 2
            actionable_stage_num = next_stage_num + 1
            actionable_def = next((s for s in DEFAULT_NURTURING_STAGES if s["stage_number"] == actionable_stage_num), None)
            
            if actionable_def:
                # Concurrency-safe: Ensure next actionable stage does not already exist
                existing_next = self.db.query(NurturingActivity).filter(
                    NurturingActivity.nurturing_id == process.id,
                    NurturingActivity.stage_number == actionable_def["stage_number"]
                ).first()
                if not existing_next:
                    act_code = format_sequence_id(self.db, "ACTIVITY", "ACT", commit=False)
                    next_act = NurturingActivity(
                        activity_id=act_code,
                        nurturing_id=process.id,
                        lead_id=lead.id,
                        stage_number=actionable_def["stage_number"],
                        activity_type=actionable_def["activity_type"],
                        subject=actionable_def["name"],
                        description=actionable_def["description"],
                        scheduled_at=now_utc,
                        due_date=next_action_due,
                        activity_status="Pending",
                        created_by_id=str(actor.id),
                        created_at=now_utc
                    )
                    self.db.add(next_act)
                    self.db.flush()
                    process.next_activity_id = next_act.id
                else:
                    next_act = existing_next

                process.current_stage = actionable_def["stage_number"]
                process.next_activity_date = next_action_due
                process.last_activity_at = now_utc

                lead.next_follow_up_date = next_action_due
                lead.next_follow_up_action = f"Stage {actionable_def['stage_number']}: {actionable_def['name']}"
            else:
                # Nurturing process completed
                process.current_stage = next_stage_num
                process.nurturing_status = "Completed"
                process.completed_at = now_utc
                process.next_activity_date = None
                process.next_activity_id = None
                lead.next_follow_up_action = "Nurturing sequence completed"
        elif next_stage_def:
            # Direct next actionable stage
            next_action_due = completion_date + timedelta(days=next_stage_def.get("interval_days", 5))
            existing_next = self.db.query(NurturingActivity).filter(
                NurturingActivity.nurturing_id == process.id,
                NurturingActivity.stage_number == next_stage_def["stage_number"]
            ).first()
            if not existing_next:
                act_code = format_sequence_id(self.db, "ACTIVITY", "ACT", commit=False)
                next_act = NurturingActivity(
                    activity_id=act_code,
                    nurturing_id=process.id,
                    lead_id=lead.id,
                    stage_number=next_stage_def["stage_number"],
                    activity_type=next_stage_def["activity_type"],
                    subject=next_stage_def["name"],
                    description=next_stage_def["description"],
                    scheduled_at=now_utc,
                    due_date=next_action_due,
                    activity_status="Pending",
                    created_by_id=str(actor.id),
                    created_at=now_utc
                )
                self.db.add(next_act)
                self.db.flush()
                process.next_activity_id = next_act.id
            else:
                next_act = existing_next

            process.current_stage = next_stage_def["stage_number"]
            process.next_activity_date = next_action_due
            process.last_activity_at = now_utc

            lead.next_follow_up_date = next_action_due
            lead.next_follow_up_action = f"Stage {next_stage_def['stage_number']}: {next_stage_def['name']}"
        else:
            # All stages completed
            process.nurturing_status = "Completed"
            process.completed_at = now_utc
            process.next_activity_date = None
            process.next_activity_id = None
            lead.next_follow_up_action = "Nurturing sequence completed"

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            logger.info(f"Integrity collision in complete_activity for lead {lead.id}; returning latest state.")
            return self.get_nurturing_details(lead.id)

        # Audit logging
        self.audit_service.log(
            action="CRM_NURTURING_ACTIVITY_COMPLETED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=getattr(actor, "active_role", "CRM_USER"),
            target_info={
                "leadId": lead.id,
                "leadCode": lead.lead_id,
                "activityId": activity.activity_id,
                "stageNumber": activity.stage_number,
                "activityTitle": activity.subject,
                "completedAt": now_utc.isoformat(),
                "details": f"Completed Stage {activity.stage_number} ({activity.subject}) for Lead {lead.lead_id}."
            }
        )

        return self.get_nurturing_details(lead.id)

    # =========================================================================
    # 4. RESCHEDULE & SKIP ACTIVITIES
    # =========================================================================

    def reschedule_activity(
        self,
        lead_id: str,
        activity_id: str,
        new_due_date: date,
        reason: str,
        actor: User,
        request: Optional[Any] = None
    ) -> Dict[str, Any]:
        is_sqlite = bool(self.db.bind and "sqlite" in str(self.db.bind.url))
        if is_sqlite:
            with _nurturing_sqlite_lock:
                return self._reschedule_activity_impl(
                    lead_id=lead_id,
                    activity_id=activity_id,
                    new_due_date=new_due_date,
                    reason=reason,
                    actor=actor,
                    request=request
                )
        return self._reschedule_activity_impl(
            lead_id=lead_id,
            activity_id=activity_id,
            new_due_date=new_due_date,
            reason=reason,
            actor=actor,
            request=request
        )

    def _reschedule_activity_impl(
        self,
        lead_id: str,
        activity_id: str,
        new_due_date: date,
        reason: str,
        actor: User,
        request: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Reschedule a pending nurturing activity with documented reason."""
        if not reason or not reason.strip():
            raise ValidationError("A reason is required to reschedule an activity.")

        clean_act_id = str(activity_id).strip()
        if clean_act_id.startswith("act_"):
            clean_act_id = clean_act_id[4:]

        activity = self.db.query(NurturingActivity).filter(
            or_(
                NurturingActivity.id == clean_act_id,
                NurturingActivity.id == str(activity_id).strip(),
                NurturingActivity.activity_id == clean_act_id,
                NurturingActivity.activity_id == str(activity_id).strip()
            )
        ).first()

        if not activity:
            raise NotFoundError(f"Activity '{activity_id}' not found.")

        lead = self.db.query(Lead).filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id)).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        # Strict Lead Ownership Check
        if activity.lead_id != lead.id:
            raise ValidationError(f"Activity '{activity_id}' does not belong to Lead '{lead_id}'.")

        # Idempotency check: If already skipped or completed, return existing state safely
        if activity.activity_status in ("Skipped", "Completed"):
            logger.info(f"Activity {activity.activity_id} is already {activity.activity_status}. Returning existing state.")
            return self.get_nurturing_details(lead.id)

        process = self.db.query(LeadNurturingProcess).filter(LeadNurturingProcess.id == activity.nurturing_id).first()

        old_due = activity.due_date
        activity.due_date = new_due_date
        activity.reschedule_reason = reason.strip()
        activity.activity_status = "Pending"

        if process.next_activity_id == activity.id:
            process.next_activity_date = new_due_date
            lead.next_follow_up_date = new_due_date

        self.db.commit()

        self.audit_service.log(
            action="CRM_NURTURING_ACTIVITY_RESCHEDULED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=getattr(actor, "active_role", "CRM_USER"),
            target_info={
                "leadId": lead.id,
                "activityId": activity.activity_id,
                "oldDueDate": str(old_due),
                "newDueDate": str(new_due_date),
                "reason": reason.strip()
            }
        )

        return self.get_nurturing_details(lead.id)

    def skip_activity(
        self,
        lead_id: str,
        activity_id: str,
        reason: str,
        actor: User,
        request: Optional[Any] = None
    ) -> Dict[str, Any]:
        is_sqlite = bool(self.db.bind and "sqlite" in str(self.db.bind.url))
        if is_sqlite:
            with _nurturing_sqlite_lock:
                return self._skip_activity_impl(
                    lead_id=lead_id,
                    activity_id=activity_id,
                    reason=reason,
                    actor=actor,
                    request=request
                )
        return self._skip_activity_impl(
            lead_id=lead_id,
            activity_id=activity_id,
            reason=reason,
            actor=actor,
            request=request
        )

    def _skip_activity_impl(
        self,
        lead_id: str,
        activity_id: str,
        reason: str,
        actor: User,
        request: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Skip a stage with documented reason and advance workflow."""
        if not reason or not reason.strip():
            raise ValidationError("A reason is mandatory when skipping a nurturing activity.")

        clean_act_id = str(activity_id).strip()
        if clean_act_id.startswith("act_"):
            clean_act_id = clean_act_id[4:]

        activity = self.db.query(NurturingActivity).filter(
            or_(
                NurturingActivity.id == clean_act_id,
                NurturingActivity.id == str(activity_id).strip(),
                NurturingActivity.activity_id == clean_act_id,
                NurturingActivity.activity_id == str(activity_id).strip()
            )
        ).first()

        if not activity:
            raise NotFoundError(f"Activity '{activity_id}' not found.")

        lead = self.db.query(Lead).filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id)).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        # Strict Lead Ownership Check
        if activity.lead_id != lead.id:
            raise ValidationError(f"Activity '{activity_id}' does not belong to Lead '{lead_id}'.")

        # Idempotency check: If already skipped or completed, return existing state safely
        if activity.activity_status in ("Skipped", "Completed"):
            logger.info(f"Activity {activity.activity_id} is already {activity.activity_status}. Returning existing state.")
            return self.get_nurturing_details(lead.id)

        process = self.db.query(LeadNurturingProcess).filter(LeadNurturingProcess.id == activity.nurturing_id).first()

        now_utc = get_current_kolkata_datetime()
        activity.activity_status = "Skipped"
        activity.skip_reason = reason.strip()
        activity.completed_at = now_utc
        activity.completed_by_id = str(actor.id)

        # Record timeline event in lead_communications
        comm_code = format_sequence_id(self.db, "COMMUNICATION", "COM", commit=False)
        comm = LeadCommunicationHistory(
            communication_id=comm_code,
            lead_id=lead.id,
            nurturing_activity_id=activity.id,
            communication_date=now_utc,
            channel="Other",
            event_type=f"Stage {activity.stage_number} Skipped: {activity.subject}",
            subject=f"Skipped: {activity.subject}",
            summary=f"Skipped with reason: {reason.strip()}",
            outcome="Skipped",
            interaction_source="Lead Nurturing",
            created_by_id=str(actor.id),
            created_at=now_utc
        )
        self.db.add(comm)

        # Advance to next stage
        next_stage_num = activity.stage_number + 1
        next_stage_def = next((s for s in DEFAULT_NURTURING_STAGES if s["stage_number"] == next_stage_num), None)
        if next_stage_def and next_stage_def.get("is_waiting_period"):
            next_stage_num += 1
            next_stage_def = next((s for s in DEFAULT_NURTURING_STAGES if s["stage_number"] == next_stage_num), None)

        if next_stage_def:
            next_due = now_utc.date() + timedelta(days=5)
            existing_next = self.db.query(NurturingActivity).filter(
                NurturingActivity.nurturing_id == process.id,
                NurturingActivity.stage_number == next_stage_def["stage_number"]
            ).first()
            if not existing_next:
                act_code = format_sequence_id(self.db, "ACTIVITY", "ACT", commit=False)
                next_act = NurturingActivity(
                    activity_id=act_code,
                    nurturing_id=process.id,
                    lead_id=lead.id,
                    stage_number=next_stage_def["stage_number"],
                    activity_type=next_stage_def["activity_type"],
                    subject=next_stage_def["name"],
                    description=next_stage_def["description"],
                    scheduled_at=now_utc,
                    due_date=next_due,
                    activity_status="Pending",
                    created_by_id=str(actor.id),
                    created_at=now_utc
                )
                self.db.add(next_act)
                self.db.flush()
                process.next_activity_id = next_act.id
            else:
                next_act = existing_next

            process.current_stage = next_stage_def["stage_number"]
            process.next_activity_date = next_due
            process.next_activity_id = next_act.id

            lead.next_follow_up_date = next_due
            lead.next_follow_up_action = f"Stage {next_stage_def['stage_number']}: {next_stage_def['name']}"
        else:
            process.nurturing_status = "Completed"
            process.completed_at = now_utc

        self.db.commit()

        self.audit_service.log(
            action="CRM_NURTURING_ACTIVITY_SKIPPED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=getattr(actor, "active_role", "CRM_USER"),
            target_info={
                "leadId": lead.id,
                "activityId": activity.activity_id,
                "stageNumber": activity.stage_number,
                "reason": reason.strip()
            }
        )

        return self.get_nurturing_details(lead.id)

    # =========================================================================
    # 5. CUSTOMER RESPONSE RECORDING & PAUSE HANDLING
    # =========================================================================

    def record_customer_response(
        self,
        lead_id: str,
        channel: str,
        response_notes: str,
        outcome: str,
        actor: User,
        target_lifecycle_status: Optional[str] = None,
        pause_nurturing: bool = True,
        request: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Record a customer response.
        - Automatically pauses nurturing process.
        - Records interaction with source = 'Customer Response'.
        - Updates Lead lifecycle status if requested (e.g. Negotiation if Interested, Dormant if Not Interested).
        """
        lead = self.db.query(Lead).filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id)).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        process = self.db.query(LeadNurturingProcess).filter(
            LeadNurturingProcess.lead_id == lead.id
        ).first()

        now_utc = get_current_kolkata_datetime()

        # 1. Pause nurturing process
        if process and pause_nurturing and process.nurturing_status == "Active":
            process.nurturing_status = "Paused"
            process.paused_at = now_utc
            process.pause_reason = f"Customer response recorded: {outcome} - {response_notes.strip()}"

        # 2. Add customer response interaction to lead_communications
        comm_code = format_sequence_id(self.db, "COMMUNICATION", "COM")
        comm = LeadCommunicationHistory(
            communication_id=comm_code,
            lead_id=lead.id,
            communication_date=now_utc,
            channel=channel or "Email",
            event_type=f"Customer Response: {outcome}",
            subject=f"Customer Response: {outcome}",
            summary=response_notes.strip(),
            outcome=outcome,
            interaction_source="Customer Response",
            created_by_id=str(actor.id),
            created_at=now_utc
        )
        self.db.add(comm)

        # 3. Synchronize Lead status if valid
        if target_lifecycle_status and target_lifecycle_status in ALLOWED_LIFECYCLE_STATUSES:
            lead.lifecycle_status = target_lifecycle_status

        lead.last_connected_date = now_utc
        self.db.commit()

        self.audit_service.log(
            action="CRM_CUSTOMER_RESPONSE_RECORDED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=getattr(actor, "active_role", "CRM_USER"),
            target_info={
                "leadId": lead.id,
                "leadCode": lead.lead_id,
                "channel": channel,
                "outcome": outcome,
                "responseNotes": response_notes,
                "nurturingPaused": pause_nurturing
            }
        )

        return self.get_nurturing_details(lead.id)

    def pause_nurturing(
        self,
        lead_id: str,
        reason: str,
        actor: User,
        request: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Pause active nurturing process."""
        process = self._get_lead_process(lead_id)
        if process.nurturing_status != "Active":
            raise ValidationError(f"Cannot pause nurturing process in '{process.nurturing_status}' status.")

        now_utc = get_current_kolkata_datetime()
        process.nurturing_status = "Paused"
        process.paused_at = now_utc
        process.pause_reason = reason.strip() if reason else "User manually paused nurturing."

        self.db.commit()

        self.audit_service.log(
            action="CRM_NURTURING_PAUSED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=getattr(actor, "active_role", "CRM_USER"),
            target_info={"leadId": process.lead_id, "reason": process.pause_reason}
        )

        return self.get_nurturing_details(process.lead_id)

    def resume_nurturing(
        self,
        lead_id: str,
        next_due_date: Optional[date],
        actor: User,
        request: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Resume paused nurturing process with rescheduled next due date."""
        process = self._get_lead_process(lead_id)
        if process.nurturing_status != "Paused":
            raise ValidationError(f"Cannot resume nurturing process in '{process.nurturing_status}' status.")

        now_utc = get_current_kolkata_datetime()
        new_due = next_due_date or (get_current_kolkata_date() + timedelta(days=5))

        process.nurturing_status = "Active"
        process.paused_at = None
        process.pause_reason = None
        process.next_activity_date = new_due
        process.restart_count = (process.restart_count or 0) + 1

        # Update current pending activity due date
        if process.next_activity_id:
            act = self.db.query(NurturingActivity).filter(NurturingActivity.id == process.next_activity_id).first()
            if act:
                act.due_date = new_due
                act.activity_status = "Pending"

        lead = self.db.query(Lead).filter(Lead.id == process.lead_id).first()
        if lead:
            lead.next_follow_up_date = new_due

        self.db.commit()

        self.audit_service.log(
            action="CRM_NURTURING_RESUMED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=getattr(actor, "active_role", "CRM_USER"),
            target_info={"leadId": process.lead_id, "rescheduledDueDate": str(new_due)}
        )

        return self.get_nurturing_details(process.lead_id)

    def cancel_nurturing(
        self,
        lead_id: str,
        reason: str,
        actor: User,
        request: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Cancel nurturing workflow with documented business reason."""
        if not reason or not reason.strip():
            raise ValidationError("A business reason is mandatory to cancel nurturing.")

        process = self._get_lead_process(lead_id)
        now_utc = get_current_kolkata_datetime()

        process.nurturing_status = "Cancelled"
        process.stopped_at = now_utc
        process.stop_reason = reason.strip()

        # Cancel any pending activities
        pending_acts = self.db.query(NurturingActivity).filter(
            NurturingActivity.nurturing_id == process.id,
            NurturingActivity.activity_status.in_(["Pending", "In Progress", "Overdue"])
        ).all()
        for a in pending_acts:
            a.activity_status = "Cancelled"
            a.skip_reason = reason.strip()

        lead = self.db.query(Lead).filter(Lead.id == process.lead_id).first()
        if lead:
            lead.next_follow_up_action = f"Nurturing cancelled: {reason.strip()}"

        self.db.commit()

        self.audit_service.log(
            action="CRM_NURTURING_CANCELLED",
            request=request,
            performed_by_employee_id=str(actor.id) if actor.id else None,
            performed_by_name=actor.name or actor.username,
            role_used=getattr(actor, "active_role", "CRM_USER"),
            target_info={"leadId": process.lead_id, "reason": reason.strip()}
        )

        return self.get_nurturing_details(process.lead_id)

    # =========================================================================
    # 6. UNIFIED TIMELINE AGGREGATOR
    # =========================================================================

    def get_unified_timeline(
        self,
        lead_id: str,
        sort_order: str = "desc",
        filter_type: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Combine all timeline events in strict chronological order:
        A. Automatic Lead Nurturing activities
        B. Manually logged interactions
        C. Lead Status changes
        D. Customer response records
        E. Important nurturing lifecycle events
        """
        lead = self.db.query(Lead).filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id)).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        timeline_items = []
        today_date = get_current_kolkata_date()

        # 1. Fetch Nurturing Activities
        process = self.db.query(LeadNurturingProcess).filter(
            LeadNurturingProcess.lead_id == lead.id
        ).first()

        if process:
            activities = self.db.query(NurturingActivity).options(
                joinedload(NurturingActivity.completed_by),
                joinedload(NurturingActivity.created_by)
            ).filter(
                NurturingActivity.nurturing_id == process.id
            ).all()

            for act in activities:
                # Derive overdue status
                is_overdue = (
                    act.activity_status in ("Pending", "In Progress") and
                    act.due_date and act.due_date < today_date
                )
                effective_status = "Overdue" if is_overdue else act.activity_status
                overdue_days = (today_date - act.due_date).days if (is_overdue and act.due_date) else 0

                event_timestamp = act.completed_at or act.scheduled_at or act.created_at

                timeline_items.append({
                    "id": f"act_{act.id}",
                    "rawId": act.id,
                    "activityId": act.id,
                    "activityCode": act.activity_id,
                    "code": act.activity_id,
                    "itemType": "nurturing_activity",
                    "source": "Lead Nurturing",
                    "stageNumber": act.stage_number,
                    "title": act.subject,
                    "activityType": act.activity_type,
                    "description": act.description,
                    "notes": act.notes,
                    "outcome": act.outcome,
                    "skipReason": act.skip_reason,
                    "rescheduleReason": act.reschedule_reason,
                    "status": effective_status,
                    "isOverdue": is_overdue,
                    "overdueDays": overdue_days,
                    "dueDate": act.due_date.isoformat() if act.due_date else None,
                    "completedAt": act.completed_at.isoformat() if act.completed_at else None,
                    "timestamp": event_timestamp.isoformat() if event_timestamp else None,
                    "responsibleUser": {
                        "id": act.completed_by.id if act.completed_by else (act.created_by.id if act.created_by else None),
                        "name": act.completed_by.name if act.completed_by else (act.created_by.name if act.created_by else None),
                        "username": act.completed_by.username if act.completed_by else (act.created_by.username if act.created_by else None)
                    } if (act.completed_by or act.created_by) else None
                })

        # 2. Fetch Lead Communications (Manual, Customer Response, Auto Nurturing, Status Changes)
        comms = self.db.query(LeadCommunicationHistory).options(
            joinedload(LeadCommunicationHistory.created_by)
        ).filter(
            LeadCommunicationHistory.lead_id == lead.id
        ).all()

        for c in comms:
            # Avoid duplicate card if linked to a nurturing activity already represented above
            # (The interaction details are embedded in the completed activity card)
            if c.nurturing_activity_id:
                continue

            source = c.interaction_source or "Manual"
            item_type = "interaction"
            if source == "Customer Response":
                item_type = "customer_response"
            elif source == "Lead Status Change":
                item_type = "status_change"
            elif source == "System Event":
                item_type = "system_event"

            timeline_items.append({
                "id": f"comm_{c.id}",
                "rawId": c.id,
                "code": c.communication_id,
                "itemType": item_type,
                "source": source,
                "stageNumber": None,
                "title": c.subject or c.event_type or f"Interaction via {c.channel}",
                "activityType": c.channel,
                "description": c.summary,
                "notes": c.outcome,
                "outcome": c.outcome,
                "nextAction": c.next_action,
                "status": "Completed",
                "isOverdue": False,
                "overdueDays": 0,
                "dueDate": c.follow_up_date.isoformat() if c.follow_up_date else None,
                "completedAt": c.communication_date.isoformat() if c.communication_date else None,
                "timestamp": c.communication_date.isoformat() if c.communication_date else c.created_at.isoformat(),
                "responsibleUser": {
                    "id": c.created_by.id if c.created_by else None,
                    "name": c.created_by.name if c.created_by else None,
                    "username": c.created_by.username if c.created_by else None
                } if c.created_by else None
            })

        # 3. Apply Filters
        clean_filter = (filter_type or "all").lower().strip()
        if clean_filter == "emails":
            timeline_items = [i for i in timeline_items if i.get("activityType") == "Email"]
        elif clean_filter == "calls":
            timeline_items = [i for i in timeline_items if "call" in (i.get("activityType") or "").lower() or "phone" in (i.get("activityType") or "").lower()]
        elif clean_filter == "meetings":
            timeline_items = [i for i in timeline_items if "meeting" in (i.get("activityType") or "").lower()]
        elif clean_filter == "notes":
            timeline_items = [i for i in timeline_items if "note" in (i.get("activityType") or "").lower()]
        elif clean_filter == "nurturing":
            timeline_items = [i for i in timeline_items if i.get("source") == "Lead Nurturing"]
        elif clean_filter == "status_changes":
            timeline_items = [i for i in timeline_items if i.get("itemType") == "status_change"]
        elif clean_filter == "responses":
            timeline_items = [i for i in timeline_items if i.get("itemType") == "customer_response"]

        # 4. Sort Chronologically
        def get_sort_key(item):
            return item.get("timestamp") or item.get("dueDate") or ""

        timeline_items.sort(key=get_sort_key, reverse=(sort_order.lower() == "desc"))
        return timeline_items

    # =========================================================================
    # 7. NEXT ACTIVITY PANEL DATA
    # =========================================================================

    def get_next_activity(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Return the current active next activity details for the Lead Details panel."""
        lead = self.db.query(Lead).filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id)).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        process = self.db.query(LeadNurturingProcess).options(
            joinedload(LeadNurturingProcess.assigned_to)
        ).filter(
            LeadNurturingProcess.lead_id == lead.id
        ).first()

        if not process:
            return None

        today_date = get_current_kolkata_date()

        if process.nurturing_status == "Paused":
            return {
                "processStatus": "Paused",
                "pauseReason": process.pause_reason,
                "pausedAt": process.paused_at.isoformat() if process.paused_at else None,
                "currentStage": process.current_stage,
                "activity": None,
                "isPaused": True
            }

        if process.nurturing_status in ("Completed", "Cancelled"):
            return {
                "processStatus": process.nurturing_status,
                "stopReason": process.stop_reason,
                "completedAt": process.completed_at.isoformat() if process.completed_at else None,
                "currentStage": process.current_stage,
                "activity": None,
                "isTerminal": True
            }

        # Find the active pending activity
        active_act = None
        if process.next_activity_id:
            active_act = self.db.query(NurturingActivity).options(
                joinedload(NurturingActivity.completed_by),
                joinedload(NurturingActivity.created_by)
            ).filter(NurturingActivity.id == process.next_activity_id).first()

        if not active_act:
            # Fallback to first pending activity by stage number
            active_act = self.db.query(NurturingActivity).filter(
                NurturingActivity.nurturing_id == process.id,
                NurturingActivity.activity_status.in_(["Pending", "In Progress", "Overdue"])
            ).order_by(NurturingActivity.stage_number.asc()).first()

        if not active_act:
            return {
                "processStatus": process.nurturing_status,
                "currentStage": process.current_stage,
                "activity": None
            }

        is_overdue = active_act.due_date and active_act.due_date < today_date
        overdue_days = (today_date - active_act.due_date).days if is_overdue else 0
        remaining_days = (active_act.due_date - today_date).days if (active_act.due_date and not is_overdue) else 0

        owner = lead.assigned_to or process.assigned_to

        return {
            "processStatus": process.nurturing_status,
            "currentStage": process.current_stage,
            "currentStageName": active_act.subject,
            "activityId": active_act.id,
            "activityCode": active_act.activity_id,
            "stageNumber": active_act.stage_number,
            "subject": active_act.subject,
            "activityType": active_act.activity_type,
            "description": active_act.description,
            "dueDate": active_act.due_date.isoformat() if active_act.due_date else None,
            "status": "Overdue" if is_overdue else active_act.activity_status,
            "isOverdue": is_overdue,
            "overdueDays": overdue_days,
            "remainingDays": remaining_days,
            "owner": {
                "id": owner.id if owner else None,
                "name": owner.name if owner else (owner.username if owner else "Unassigned"),
                "username": owner.username if owner else None
            } if owner else None
        }

    # =========================================================================
    # 8. GET COMPLETE NURTURING DETAILS
    # =========================================================================

    def get_nurturing_details(self, lead_id: str) -> Dict[str, Any]:
        """Return comprehensive nurturing state for a lead."""
        lead = self.db.query(Lead).filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id)).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        process = self.db.query(LeadNurturingProcess).options(
            joinedload(LeadNurturingProcess.assigned_to),
            joinedload(LeadNurturingProcess.activities)
        ).filter(
            LeadNurturingProcess.lead_id == lead.id
        ).first()

        if not process:
            # Auto-initialize if lead exists but nurturing process was not initialized
            process = self.initialize_lead_nurturing(lead, commit=True)

        next_activity_data = self.get_next_activity(lead.id)

        activities_list = []
        today_date = get_current_kolkata_date()
        for a in process.activities:
            is_overdue = a.activity_status in ("Pending", "In Progress") and a.due_date and a.due_date < today_date
            activities_list.append({
                "id": a.id,
                "activityId": a.activity_id,
                "stageNumber": a.stage_number,
                "subject": a.subject,
                "activityType": a.activity_type,
                "description": a.description,
                "dueDate": a.due_date.isoformat() if a.due_date else None,
                "status": "Overdue" if is_overdue else a.activity_status,
                "isOverdue": is_overdue,
                "completedAt": a.completed_at.isoformat() if a.completed_at else None,
                "notes": a.notes,
                "outcome": a.outcome,
                "skipReason": a.skip_reason,
                "rescheduleReason": a.reschedule_reason
            })

        activities_list.sort(key=lambda x: x["stageNumber"])

        return {
            "id": process.id,
            "nurturingId": process.nurturing_id,
            "leadId": lead.id,
            "leadCode": lead.lead_id,
            "leadName": lead.lead_name or lead.company_name or lead.lead_id,
            "status": process.nurturing_status,
            "currentStage": process.current_stage,
            "startedAt": process.started_at.isoformat() if process.started_at else None,
            "pausedAt": process.paused_at.isoformat() if process.paused_at else None,
            "pauseReason": process.pause_reason,
            "completedAt": process.completed_at.isoformat() if process.completed_at else None,
            "nextActivityDate": process.next_activity_date.isoformat() if process.next_activity_date else None,
            "nextActivity": next_activity_data,
            "activities": activities_list,
            "stagesCount": len(DEFAULT_NURTURING_STAGES)
        }

    def _get_lead_process(self, lead_id: str) -> LeadNurturingProcess:
        lead = self.db.query(Lead).filter(or_(Lead.id == lead_id, Lead.lead_id == lead_id)).first()
        if not lead:
            raise NotFoundError(f"Lead '{lead_id}' not found.")

        process = self.db.query(LeadNurturingProcess).filter(
            LeadNurturingProcess.lead_id == lead.id
        ).first()

        if not process:
            raise NotFoundError(f"No nurturing process found for Lead '{lead_id}'.")

        return process

