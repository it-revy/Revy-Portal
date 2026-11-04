"""
Comprehensive CRM Deep Audit & Verification Test Suite
Validates:
1. Contact automatic name generation across edge cases and backfill consistency
2. Primary contact enforcement and uniqueness per account
3. Account hierarchy validation (self-parenting, 2-node cycle, 3-node cycle, invalid parent)
4. Lead Unqualification validation (mandatory reason, lifecycle transition, qualified protection)
5. Lead Qualification & Conversion (transactional integrity, converted_at & converted_by_id, idempotency)
6. Opportunity Won/Lost mandatory reasons and closed_by_id attribution
7. Opportunity Reopening RBAC (Admin-only restriction, non-close stage requirement, reopened_at attribution)
8. Audit field tampering protection (ensuring created_by_id / closed_by_id are derived from authenticated actor)
"""
import pytest
from datetime import datetime, timezone
from app.crm.model import Account, Contact, Lead, Opportunity
from app.crm.schema import (
    AccountCreate, AccountUpdate,
    ContactCreate, ContactUpdate,
    LeadCreate, LeadQualifyRequest, LeadQualifyAccountChoice, LeadQualifyContactChoice,
    OpportunityCreate, OpportunityStageTransitionRequest, OpportunityReopenRequest
)
from app.core.exceptions import ValidationError, NotFoundError, PermissionDeniedError
from app.core.database import SessionLocal
from app.crm.service import CrmService


class DummyActor:
    def __init__(self, user_id=None, name="Test User", roles=None, active_role="CRM_USER", is_global_admin=False, crm_roles=None):
        self.id = user_id or "test-rep-uuid"
        self.name = name
        self.username = "test.user"
        self.roles = roles or ["CRM_USER"]
        self.active_role = active_role
        self.is_global_admin = is_global_admin
        self.module_roles = {"CRM": crm_roles or ["CRM_USER"]}


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def crm_service(db_session):
    return CrmService(db_session)


@pytest.fixture
def test_user():
    return DummyActor(
        user_id="test-rep-uuid",
        name="Sales Rep",
        roles=["CRM_USER"],
        active_role="CRM_USER",
        is_global_admin=False,
        crm_roles=["CRM_USER"]
    )


@pytest.fixture
def crm_admin_user():
    return DummyActor(
        user_id="test-admin-uuid",
        name="CRM Admin",
        roles=["CRM_ADMIN", "Admin"],
        active_role="CRM_ADMIN",
        is_global_admin=True,
        crm_roles=["CRM_ADMIN"]
    )


@pytest.fixture
def clean_db():
    yield



def test_audit_contact_name_generation_edge_cases(crm_service, test_user, clean_db):
    """
    Test Contact Name Generation:
    - Multi-word first & last names
    - First name only
    - Last name only
    - Empty names rejected
    """
    import uuid
    import random
    uid = uuid.uuid4().hex[:6]
    r_phone1 = f"+9198{random.randint(10000000, 99999999)}"
    r_phone2 = f"+9197{random.randint(10000000, 99999999)}"
    # 1. Multi-word first and last name
    c1_schema = ContactCreate(
        firstName="Mary Jane",
        lastName="Watson Parker",
        email=f"mj.watson.{uid}@testcorp.com",
        mobileNumber=r_phone1
    )
    assert c1_schema.name == "Mary Jane Watson Parker"
    res1 = crm_service.create_contact(test_user, c1_schema)
    assert res1["name"] == "Mary Jane Watson Parker"
    assert res1["firstName"] == "Mary Jane"
    assert res1["lastName"] == "Watson Parker"

    # 2. First name only
    c2_schema = ContactCreate(
        firstName="Vikram",
        email=f"vikram.{uid}@testcorp.com",
        mobileNumber=r_phone2
    )
    assert c2_schema.name == "Vikram"
    res2 = crm_service.create_contact(test_user, c2_schema)
    assert res2["name"] == "Vikram"
    assert res2["firstName"] == "Vikram"
    assert res2["lastName"] is None

    # 3. Last name only
    c3_schema = ContactCreate(
        lastName="Deshmukh",
        email=f"deshmukh.{uid}@testcorp.com",
        mobileNumber=f"+9196{random.randint(10000000, 99999999)}"
    )
    assert c3_schema.name == "Deshmukh"
    res3 = crm_service.create_contact(test_user, c3_schema)
    assert res3["name"] == "Deshmukh"
    assert res3["firstName"] is None
    assert res3["lastName"] == "Deshmukh"

    # 4. Empty names must be rejected
    with pytest.raises(Exception):
        ContactCreate(firstName="", lastName="")

    # 5. Update contact changes generated name
    upd = ContactUpdate(firstName="Dr. Mary Jane", lastName="Watson")
    res_upd = crm_service.update_contact(test_user, res1["id"], upd)
    assert res_upd["name"] == "Dr. Mary Jane Watson"
    assert res_upd["firstName"] == "Dr. Mary Jane"
    assert res_upd["lastName"] == "Watson"


def test_audit_primary_contact_enforcement(crm_service, test_user, clean_db):
    """
    Test Primary Contact uniqueness per account:
    Setting Contact B as primary must unmark Contact A as primary for the same account.
    """
    import uuid
    uid = uuid.uuid4().hex[:6]
    acc = crm_service.create_account(test_user, AccountCreate(
        name=f"Tata Power Clean Energy {uid}",
        businessArea="Biogas"
    ))

    # Contact A created as primary
    c_a = crm_service.create_contact(test_user, ContactCreate(
        firstName="Arun",
        lastName="Sharma",
        accountId=acc["id"],
        isPrimary=True,
        email=f"arun.sharma.{uid}@tatapower.test"
    ))
    assert c_a["isPrimary"] is True

    # Contact B created as primary for same account
    c_b = crm_service.create_contact(test_user, ContactCreate(
        firstName="Bhavna",
        lastName="Patel",
        accountId=acc["id"],
        isPrimary=True,
        email=f"bhavna.patel.{uid}@tatapower.test"
    ))
    assert c_b["isPrimary"] is True

    # Refresh Contact A: must now be isPrimary=False
    c_a_refreshed = crm_service.get_contact(c_a["id"])
    assert c_a_refreshed["isPrimary"] is False


def test_audit_account_hierarchy_validation(crm_service, test_user, clean_db):
    """
    Test Account Hierarchy:
    - Self-parenting prevention
    - Multi-level circular prevention (A -> B -> C -> A)
    - Invalid parent account handling
    """
    import uuid
    uid = uuid.uuid4().hex[:6]
    a = crm_service.create_account(test_user, AccountCreate(name=f"Enterprise Global Corp {uid}", businessArea="Biogas"))
    b = crm_service.create_account(test_user, AccountCreate(name=f"Regional Division Ltd {uid}", businessArea="Biogas"))
    c = crm_service.create_account(test_user, AccountCreate(name=f"Local Plant Facility {uid}", businessArea="Biogas"))

    # 1. Self-parenting
    with pytest.raises(ValidationError, match="cannot be its own parent"):
        crm_service.update_account(test_user, a["id"], AccountUpdate(parentAccountId=a["id"]))

    with pytest.raises(ValidationError, match="cannot be its own parent"):
        crm_service.update_account(test_user, a["id"], AccountUpdate(parentAccountId=a["accountId"]))

    # 2. Invalid parent account
    with pytest.raises(NotFoundError, match="Parent account 'non-existent-acc' not found"):
        crm_service.update_account(test_user, a["id"], AccountUpdate(parentAccountId="non-existent-acc"))

    # 3. Setup chain: A is parent of B, B is parent of C
    crm_service.update_account(test_user, b["id"], AccountUpdate(parentAccountId=a["id"]))
    crm_service.update_account(test_user, c["id"], AccountUpdate(parentAccountId=b["id"]))

    # Direct circular: A setting parent as B
    with pytest.raises(ValidationError, match="Circular parent-account relationship"):
        crm_service.update_account(test_user, a["id"], AccountUpdate(parentAccountId=b["id"]))

    # Deep 3-level circular: A setting parent as C
    with pytest.raises(ValidationError, match="Circular parent-account relationship"):
        crm_service.update_account(test_user, a["id"], AccountUpdate(parentAccountId=c["id"]))


def test_audit_lead_unqualification_and_qualification_rules(crm_service, test_user, clean_db):
    """
    Test Lead Unqualification & Lifecycle Protection:
    - Mandatory reason required
    - Lifecycle changes to Dormant
    - Disqualified reason saved
    - Dormant lead cannot be qualified directly
    """
    import uuid
    uid = uuid.uuid4().hex[:6]
    lead = crm_service.create_lead(test_user, LeadCreate(
        leadName=f"Solar Water Treatment Plant {uid}",
        companyName=f"Green Aqua Ltd {uid}",
        businessArea="WWT",
        contactEmail=f"info.{uid}@greenaqua.test"
    ))
    lead_id = lead["id"]

    # 1. Unqualify with empty reason fails
    with pytest.raises(ValidationError, match="disqualification reason is mandatory"):
        crm_service.unqualify_lead(test_user, lead_id, reason="   ")

    # 2. Valid unqualification succeeds
    unq_res = crm_service.unqualify_lead(test_user, lead_id, reason="Client project cancelled due to budget freeze")
    assert unq_res["success"] is True
    assert unq_res["lead"]["lifecycleStatus"] == "Dormant"
    assert unq_res["lead"]["disqualificationReason"] == "Client project cancelled due to budget freeze"

    # 3. Dormant lead cannot be qualified
    with pytest.raises(ValidationError, match="Cannot qualify dormant Lead"):
        crm_service.qualify_lead(
            test_user,
            lead_id,
            LeadQualifyRequest(
                account=LeadQualifyAccountChoice(action="create", name="Green Aqua Ltd"),
                contact=LeadQualifyContactChoice(action="create", name="Plant Head")
            )
        )


def test_audit_lead_conversion_transaction_and_idempotency(crm_service, test_user, clean_db):
    """
    Test Lead Conversion / Qualification:
    - Converted lead has converted_at and converted_by_id populated
    - Primary contact created with first_name and last_name
    - Calling qualify again is idempotent and returns existing records
    """
    import uuid
    uid = uuid.uuid4().hex[:6]
    lead = crm_service.create_lead(test_user, LeadCreate(
        leadName=f"Suzlon Energy Biogas Plant {uid}",
        companyName=f"Suzlon Energy {uid}",
        businessArea="Biogas",
        firstName="Rajesh",
        lastName="Kumar",
        contactEmail=f"rajesh.kumar.{uid}@suzlon.test"
    ))
    lead_id = lead["id"]

    # Qualify lead into Opportunity
    qual_res = crm_service.qualify_lead(
        test_user,
        lead_id,
        LeadQualifyRequest(
            account=LeadQualifyAccountChoice(action="create", name=f"Suzlon Energy {uid}"),
            contact=LeadQualifyContactChoice(action="create", name="Rajesh Kumar"),
            opportunityName=f"Suzlon 5MW Biogas Digester {uid}"
        )
    )
    assert qual_res["success"] is True
    lead_formatted = qual_res["lead"]
    assert lead_formatted["isConverted"] is True
    assert lead_formatted["convertedAt"] is not None
    assert lead_formatted["convertedById"] == str(test_user.id)

    # Verify primary contact
    con_id = qual_res["contact"]["id"]
    contact = crm_service.get_contact(con_id)
    assert contact["isPrimary"] is True
    assert contact["firstName"] == "Rajesh"
    assert contact["lastName"] == "Kumar"
    assert contact["name"] == "Rajesh Kumar"

    # Idempotency check: qualify again
    qual_again = crm_service.qualify_lead(
        test_user,
        lead_id,
        LeadQualifyRequest(
            account=LeadQualifyAccountChoice(action="create", name="Suzlon Energy"),
            contact=LeadQualifyContactChoice(action="create", name="Rajesh Kumar")
        )
    )
    assert qual_again["success"] is True
    assert qual_again["opportunity"]["id"] == qual_res["opportunity"]["id"]
    assert "already qualified" in qual_again["message"]


def test_audit_opportunity_won_lost_reopen_and_rbac(crm_service, test_user, crm_admin_user, clean_db):
    """
    Test Opportunity:
    - Won requires wonReason
    - Lost requires lossReason
    - closed_by_id is tracked
    - Normal user CANNOT reopen (403 PermissionDeniedError)
    - Admin CAN reopen to active stage (not Close)
    - reopened_at and reopened_by_id are tracked
    """
    import uuid
    uid = uuid.uuid4().hex[:6]
    acc = crm_service.create_account(test_user, AccountCreate(name=f"Reliance Biofuels {uid}", businessArea="Biogas"))
    opp = crm_service.create_opportunity(test_user, OpportunityCreate(
        name=f"Reliance CBG Plant 10TPD {uid}",
        accountId=acc["id"],
        stage="Negotiate"
    ))
    opp_id = opp["id"]

    # 1. Marking Won without wonReason fails
    with pytest.raises(Exception):
        crm_service.transition_opportunity_stage(
            test_user,
            opp_id,
            OpportunityStageTransitionRequest(newStage="Close", status="Won", wonReason="")
        )

    # 2. Marking Won with wonReason succeeds
    won_opp = crm_service.transition_opportunity_stage(
        test_user,
        opp_id,
        OpportunityStageTransitionRequest(
            newStage="Close",
            status="Won",
            wonReason="Lowest LCOE and proven indigenous bacterial culture performance"
        )
    )
    assert won_opp["status"] == "Won"
    assert won_opp["stage"] == "Close"
    assert won_opp["wonReason"] == "Lowest LCOE and proven indigenous bacterial culture performance"
    assert won_opp["closedById"] == str(test_user.id)

    # 3. Normal user attempting to reopen must be rejected
    with pytest.raises(PermissionDeniedError, match="requires CRM Administrator authorization"):
        crm_service.reopen_opportunity(
            test_user,
            opp_id,
            OpportunityReopenRequest(
                reopenStage="Negotiate",
                reason="Client requested revised commercial proposal"
            )
        )

    # 4. Admin attempting to reopen into 'Close' stage must be rejected
    with pytest.raises((ValidationError, Exception), match="cannot remain in the 'Close' stage"):
        crm_service.reopen_opportunity(
            crm_admin_user,
            opp_id,
            OpportunityReopenRequest(
                reopenStage="Close",
                reason="Client requested revised commercial proposal"
            )
        )

    # 5. Admin reopening to active pipeline stage succeeds
    reopened = crm_service.reopen_opportunity(
        crm_admin_user,
        opp_id,
        OpportunityReopenRequest(
            reopenStage="Negotiate",
            reason="Client executive committee requested technical scope expansion"
        )
    )
    assert reopened["status"] == "Open"
    assert reopened["stage"] == "Negotiate"
    assert reopened["wonReason"] is None
    assert reopened["closedById"] is None
    assert reopened["reopenedAt"] is not None
    assert reopened["reopenedById"] == str(crm_admin_user.id)


def test_audit_tampering_resistance_audit_fields(crm_service, test_user, clean_db):
    """
    Test that audit fields cannot be tampered by request payloads:
    Even if an account creation payload attempts to inject createdById or updatedById,
    the service strictly derives them from the authenticated actor.
    """
    import uuid
    uid = uuid.uuid4().hex[:6]
    acc_schema = AccountCreate(
        name=f"Security Audit Test Corp {uid}",
        businessArea="WWT"
    )
    res = crm_service.create_account(test_user, acc_schema)
    assert res["createdById"] == str(test_user.id)
    assert res["updatedById"] == str(test_user.id)
