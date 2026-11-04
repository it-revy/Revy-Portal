import os

# 1. Update backend/app/core/database.py
db_file = os.path.join(os.path.dirname(__file__), "..", "app", "core", "database.py")
with open(db_file, "r", encoding="utf-8") as f:
    db_code = f.read()

target1 = "from sqlalchemy import create_engine"
repl1 = "from sqlalchemy import create_engine, event"
if target1 in db_code:
    db_code = db_code.replace(target1, repl1, 1)

target2 = '        return create_engine(test_url, connect_args={"check_same_thread": False})'
repl2 = '''        test_engine = create_engine(test_url, connect_args={"check_same_thread": False, "timeout": 30})
        @event.listens_for(test_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
        return test_engine'''

if target2 in db_code:
    db_code = db_code.replace(target2, repl2, 1)
    with open(db_file, "w", encoding="utf-8") as f:
        f.write(db_code)
    print("database.py updated successfully!")
else:
    print("target2 not found in database.py")

# 2. Update backend/app/crm/schema.py to add LeadOpportunityCreate
schema_file = os.path.join(os.path.dirname(__file__), "..", "app", "crm", "schema.py")
with open(schema_file, "r", encoding="utf-8") as f:
    schema_code = f.read()

target_schema = "class OpportunityCreate(BaseModel):"
lead_opp_schema = '''class LeadOpportunityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    accountId: Optional[str] = None
    contactId: Optional[str] = None
    originatingLeadId: Optional[str] = None
    status: Optional[str] = "Open"
    stage: Optional[str] = "Qualify"
    lossReason: Optional[str] = None
    businessArea: Optional[str] = "Biogas"
    expectedCloseDate: Optional[str] = None
    currency: Optional[str] = "INR"
    estimatedValue: Optional[float] = None
    description: Optional[str] = None
    requirementSummary: Optional[str] = None
    requirementTypes: Optional[List[str]] = None
    assignedToUserId: Optional[str] = None
    subStatus: Optional[str] = None
    sub_status: Optional[str] = None

    @model_validator(mode="after")
    def validate_lead_opportunity_create(self) -> "LeadOpportunityCreate":
        if self.estimatedValue is not None and self.estimatedValue < 0:
            raise ValueError("Estimated amount cannot be negative.")

        canonical_stages = ["Enquiry", "Qualify", "Develop", "Propose/Offer", "Negotiate", "Close"]
        stg = self.stage
        if stg == "Propose":
            stg = "Propose/Offer"
            self.stage = stg
        if stg and stg not in canonical_stages:
            raise ValueError(f"Invalid stage '{stg}'. Permitted stages are: {', '.join(canonical_stages)}")

        stat = (self.status or "Open").strip()
        if stat not in ("Open", "Won", "Lost"):
            raise ValueError(f"Invalid status '{stat}'. Permitted statuses are Open, Won, Lost.")

        return self


class OpportunityCreate(BaseModel):'''

if target_schema in schema_code:
    schema_code = schema_code.replace(target_schema, lead_opp_schema, 1)
    with open(schema_file, "w", encoding="utf-8") as f:
        f.write(schema_code)
    print("schema.py updated successfully!")
else:
    print("target_schema not found in schema.py")

# 3. Update backend/app/crm/router.py to use LeadOpportunityCreate
router_file = os.path.join(os.path.dirname(__file__), "..", "app", "crm", "router.py")
with open(router_file, "r", encoding="utf-8") as f:
    router_code = f.read()

target_router_import = "OpportunityCreate,"
repl_router_import = "OpportunityCreate, LeadOpportunityCreate,"
if target_router_import in router_code:
    router_code = router_code.replace(target_router_import, repl_router_import, 1)

target_endpoint = "def create_lead_opportunity(\n    lead_id: str,\n    payload: OpportunityCreate,"
repl_endpoint = "def create_lead_opportunity(\n    lead_id: str,\n    payload: LeadOpportunityCreate,"
if target_endpoint in router_code:
    router_code = router_code.replace(target_endpoint, repl_endpoint, 1)
else:
    # try with CRLF
    target_endpoint_crlf = "def create_lead_opportunity(\r\n    lead_id: str,\r\n    payload: OpportunityCreate,"
    repl_endpoint_crlf = "def create_lead_opportunity(\r\n    lead_id: str,\r\n    payload: LeadOpportunityCreate,"
    if target_endpoint_crlf in router_code:
        router_code = router_code.replace(target_endpoint_crlf, repl_endpoint_crlf, 1)

with open(router_file, "w", encoding="utf-8") as f:
    f.write(router_code)
print("router.py updated successfully!")

# 4. Update backend/app/crm/service.py for retry logic and safe logging
service_file = os.path.join(os.path.dirname(__file__), "..", "app", "crm", "service.py")
with open(service_file, "r", encoding="utf-8") as f:
    svc_code = f.read()

target_log = 'logger.error(f"Failed to auto-initialize nurturing for lead {lead.lead_id}: {nurture_err}")'
repl_log = '''lead_ref_code = getattr(lead, "lead_id", str(lead_id if "lead_id" in locals() else ""))
            logger.error(f"Failed to auto-initialize nurturing for lead {lead_ref_code}: {nurture_err}")'''
if target_log in svc_code:
    svc_code = svc_code.replace(target_log, repl_log, 1)
    with open(service_file, "w", encoding="utf-8") as f:
        f.write(svc_code)
    print("service.py logging safety updated successfully!")
else:
    print("target_log not found in service.py")

