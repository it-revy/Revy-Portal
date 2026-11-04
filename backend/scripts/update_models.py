import os

model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "crm", "model.py")
with open(model_path, "r", encoding="utf-8") as f:
    content = f.read()

target = '''    communications = relationship(
        "LeadCommunicationHistory",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="desc(LeadCommunicationHistory.communication_date)"
    )


class LeadCommunicationHistory(Base):
    __tablename__ = "lead_communications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    communication_id = Column(String(50), unique=True, index=True, nullable=False)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    communication_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    channel = Column(String(50), nullable=False)  # Email, Mobile/Call, WhatsApp, Teams, Other
    event_type = Column(String(100), nullable=False)  # Introductory mail sent, Introductory call, etc.
    summary = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    next_action = Column(Text, nullable=True)
    follow_up_date = Column(Date, nullable=True)
    
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="communications")
    created_by = relationship("User", foreign_keys=[created_by_id])'''

replacement = '''    communications = relationship(
        "LeadCommunicationHistory",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="desc(LeadCommunicationHistory.communication_date)"
    )
    nurturing_process = relationship(
        "LeadNurturingProcess",
        back_populates="lead",
        uselist=False,
        cascade="all, delete-orphan"
    )
    nurturing_activities = relationship(
        "NurturingActivity",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="NurturingActivity.stage_number"
    )


class LeadCommunicationHistory(Base):
    __tablename__ = "lead_communications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    communication_id = Column(String(50), unique=True, index=True, nullable=False)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    communication_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    channel = Column(String(50), nullable=False)  # Email, Mobile/Call, WhatsApp, Teams, Other
    event_type = Column(String(100), nullable=False)  # Introductory mail sent, Introductory call, etc.
    summary = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    next_action = Column(Text, nullable=True)
    follow_up_date = Column(Date, nullable=True)

    # Unified Timeline & Nurturing Integration Fields
    subject = Column(String(255), nullable=True)
    interaction_source = Column(String(50), nullable=False, default="Manual")  # Manual, Lead Nurturing, Customer Response, Lead Status Change, System Event
    nurturing_activity_id = Column(String(36), ForeignKey("crm_nurturing_activities.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="communications")
    created_by = relationship("User", foreign_keys=[created_by_id])
    nurturing_activity = relationship("NurturingActivity", back_populates="interaction")

    @property
    def interaction_type(self):
        return self.channel

    @property
    def description(self):
        return self.summary

    @property
    def interaction_at(self):
        return self.communication_date


class LeadNurturingProcess(Base):
    __tablename__ = "crm_lead_nurturing"
    __table_args__ = (
        UniqueConstraint("lead_id", name="uq_crm_lead_nurturing_lead_id"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    nurturing_id = Column(String(50), unique=True, index=True, nullable=False)  # NUR-00001
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    assigned_to_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    current_stage = Column(Integer, nullable=False, default=1)
    nurturing_status = Column(String(50), nullable=False, default="Active", index=True)  # Active, Paused, Completed, Cancelled
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    next_activity_date = Column(Date, nullable=True, index=True)
    next_activity_id = Column(String(36), nullable=True)
    last_activity_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    pause_reason = Column(Text, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    stop_reason = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    restart_count = Column(Integer, nullable=False, default=0)
    review_outcome = Column(String(50), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="nurturing_process")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    activities = relationship(
        "NurturingActivity",
        back_populates="nurturing_process",
        cascade="all, delete-orphan",
        order_by="NurturingActivity.stage_number"
    )

    @property
    def process_status(self):
        return self.nurturing_status

    @process_status.setter
    def process_status(self, val):
        self.nurturing_status = val

    @property
    def current_stage_order(self):
        return self.current_stage


class NurturingActivity(Base):
    __tablename__ = "crm_nurturing_activities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    activity_id = Column(String(50), unique=True, index=True, nullable=False)  # ACT-00001
    nurturing_id = Column(String(36), ForeignKey("crm_lead_nurturing.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_number = Column(Integer, nullable=False, index=True)
    activity_type = Column(String(50), nullable=False)  # Email, Phone Call, Meeting, Review, Waiting Period, Note, Other
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    scheduled_at = Column(DateTime, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    activity_status = Column(String(50), nullable=False, default="Pending", index=True)  # Pending, In Progress, Completed, Overdue, Skipped, Cancelled
    outcome = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    recipient = Column(String(255), nullable=True)
    email_message_reference = Column(String(255), nullable=True)
    skip_reason = Column(Text, nullable=True)
    reschedule_reason = Column(Text, nullable=True)
    callback_requested = Column(Boolean, default=False, nullable=False)
    callback_date = Column(Date, nullable=True)
    meeting_datetime = Column(DateTime, nullable=True)
    customer_response_date = Column(DateTime, nullable=True)
    customer_response_channel = Column(String(50), nullable=True)
    customer_response_notes = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    nurturing_process = relationship("LeadNurturingProcess", back_populates="activities")
    lead = relationship("Lead", back_populates="nurturing_activities")
    created_by = relationship("User", foreign_keys=[created_by_id])
    completed_by = relationship("User", foreign_keys=[completed_by_id])
    interaction = relationship("LeadCommunicationHistory", back_populates="nurturing_activity", uselist=False)

    @property
    def stage_order(self):
        return self.stage_number

    @property
    def activity_title(self):
        return self.subject

    @property
    def due_at(self):
        return self.due_date

    @property
    def completion_notes(self):
        return self.notes'''

norm_content = content.replace('\r\n', '\n')
norm_target = target.replace('\r\n', '\n')
assert norm_target in norm_content, "Target string not found!"
new_content = norm_content.replace(norm_target, replacement.replace('\r\n', '\n'))
with open(model_path, "w", encoding="utf-8") as f:
    f.write(new_content)
print("Successfully updated backend/app/crm/model.py")

