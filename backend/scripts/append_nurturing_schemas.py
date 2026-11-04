import os

schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "crm", "schema.py")

nurturing_schemas = '''

# =========================================================================
# LEAD NURTURING & UNIFIED TIMELINE SCHEMAS
# =========================================================================

class NurturingActivityCompleteRequest(BaseModel):
    notes: Optional[str] = Field(None, description="Completion notes or interaction summary")
    outcome: Optional[str] = Field(None, description="Activity completion outcome")
    emailMessageReference: Optional[str] = Field(None, description="External email ID, subject or delivery reference")


class NurturingActivityRescheduleRequest(BaseModel):
    newDueDate: py_date = Field(..., description="New scheduled due date (YYYY-MM-DD)")
    reason: str = Field(..., min_length=1, description="Mandatory reason for rescheduling")


class NurturingActivitySkipRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Mandatory business reason for skipping this nurturing activity")


class CustomerResponseRequest(BaseModel):
    channel: str = Field(..., description="Communication channel: 'Email', 'Phone / Call', 'WhatsApp', 'In-Person Meeting', etc.")
    responseNotes: str = Field(..., min_length=1, description="Details and customer feedback received")
    outcome: str = Field(..., description="Customer interest level or sentiment: 'Interested', 'Not Interested', 'Callback Requested', 'Information Requested', etc.")
    targetLifecycleStatus: Optional[str] = Field(None, description="Optional approved lifecycle status: 'Negotiation', 'Offer', 'Dormant', etc.")
    pauseNurturing: bool = Field(True, description="Whether to automatically pause nurturing workflow upon recording response")


class NurturingPauseRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for pausing nurturing")


class NurturingResumeRequest(BaseModel):
    nextDueDate: Optional[py_date] = Field(None, description="Rescheduled next due date (default: today + 5 calendar days)")


class NurturingCancelRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Mandatory reason for cancelling nurturing")


class NurturingActivityItem(BaseModel):
    id: str
    activityId: str
    stageNumber: int
    subject: str
    activityType: str
    description: Optional[str] = None
    dueDate: Optional[str] = None
    status: str
    isOverdue: bool = False
    completedAt: Optional[str] = None
    notes: Optional[str] = None
    outcome: Optional[str] = None
    skipReason: Optional[str] = None
    rescheduleReason: Optional[str] = None


class NextActivityItem(BaseModel):
    processStatus: str
    currentStage: int
    currentStageName: Optional[str] = None
    activityId: Optional[str] = None
    activityCode: Optional[str] = None
    stageNumber: Optional[int] = None
    subject: Optional[str] = None
    activityType: Optional[str] = None
    description: Optional[str] = None
    dueDate: Optional[str] = None
    status: Optional[str] = None
    isOverdue: bool = False
    overdueDays: int = 0
    remainingDays: int = 0
    owner: Optional[Dict[str, Any]] = None
    isPaused: Optional[bool] = None
    pauseReason: Optional[str] = None
    pausedAt: Optional[str] = None
    isTerminal: Optional[bool] = None
    stopReason: Optional[str] = None


class NurturingDetailsResponse(BaseModel):
    success: bool = True
    nurturing: Dict[str, Any]


class NextActivityResponse(BaseModel):
    success: bool = True
    nextActivity: Optional[Dict[str, Any]] = None


class UnifiedTimelineResponse(BaseModel):
    success: bool = True
    count: int
    timeline: List[Dict[str, Any]]
'''

with open(schema_path, "a", encoding="utf-8") as f:
    f.write(nurturing_schemas)

print("Appended nurturing schemas to app/crm/schema.py successfully")

