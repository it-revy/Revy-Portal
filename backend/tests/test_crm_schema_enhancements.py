import os
import sys
sys.path.insert(0, 'backend')
os.environ["TESTING"] = "1"
import app.models  # Ensure all mapper relationships are configured
import pytest
from app.core.database import SessionLocal
from app.crm.service import CrmService
from app.crm.schema import (
    AccountCreate, AccountUpdate,
    ContactCreate, ContactUpdate,
    LeadCreate, LeadQualifyRequest, LeadQualifyAccountChoice, LeadQualifyContactChoice,
    OpportunityStageTransitionRequest, OpportunityReopenRequest
)
from app.core.exceptions import ValidationError, ConflictError, NotFoundError
from app.users.model import User


class DummyActor:
    def __init__(self, user_id=None, name="Test Admin", roles=None, active_role="CRM_ADMIN", is_global_admin=True):
        self.id = user_id or "test-admin-uuid"
        self.name = name
        self.username = "test.admin"
        self.roles = roles or ["CRM_ADMIN", "Admin"]
        self.active_role = active_role
        self.is_global_admin = is_global_admin
        self.module_roles = {"CRM": ["CRM_ADMIN"]}


def test_contact_auto_name_generation():
    db = SessionLocal()
    service = CrmService(db)
    actor = DummyActor()
    import uuid
    suffix = uuid.uuid4().hex[:6]

    try:
        # 1. Both first and last name
        payload1 = ContactCreate(firstName="Amit", lastName="Shah", email=f"amit.{suffix}@testexample.com")
        assert payload1.name == "Amit Shah"
        con1 = service.create_contact(actor=actor, payload=payload1)
        assert con1["name"] == "Amit Shah"
        assert con1["firstName"] == "Amit"
        assert con1["lastName"] == "Shah"

        # 2. First name only
        payload2 = ContactCreate(firstName="Priya", email=f"priya.{suffix}@testexample.com")
        assert payload2.name == "Priya"
        con2 = service.create_contact(actor=actor, payload=payload2)
        assert con2["name"] == "Priya"
        assert con2["firstName"] == "Priya"
        assert con2["lastName"] is None

        # 3. Last name only
        payload3 = ContactCreate(lastName="Mehta", email=f"mehta.{suffix}@testexample.com")
        assert payload3.name == "Mehta"
        con3 = service.create_contact(actor=actor, payload=payload3)
        assert con3["name"] == "Mehta"
        assert con3["firstName"] is None
        assert con3["lastName"] == "Mehta"

        # 4. Update contact with new first and last name
        update_payload = ContactUpdate(firstName="Amitkumar", lastName="Patel")
        updated = service.update_contact(actor=actor, contact_id=con1["id"], payload=update_payload)
        assert updated["name"] == "Amitkumar Patel"
        assert updated["firstName"] == "Amitkumar"
        assert updated["lastName"] == "Patel"
    finally:
        db.close()


def test_account_parent_and_circular_prevention():
    db = SessionLocal()
    service = CrmService(db)
    actor = DummyActor()
    import uuid
    suffix = uuid.uuid4().hex[:6]

    try:
        # Create Account A
        acc_a = service.create_account(
            actor=actor,
            payload=AccountCreate(name=f"Enterprise Parent Corp {suffix}", businessArea="Biogas", city="Pune")
        )
        assert acc_a["businessArea"] == "Biogas"
        assert acc_a["city"] == "Pune"

        # Create Account B with Parent A
        acc_b = service.create_account(
            actor=actor,
            payload=AccountCreate(name=f"Subsidiary Division B {suffix}", businessArea="WWT", parentAccountId=acc_a["id"])
        )
        assert acc_b["parentAccountId"] == acc_a["id"]

        # 1. Prevent self-parenting: Account A cannot be its own parent
        with pytest.raises(ValidationError) as exc_self:
            service.update_account(actor=actor, account_id=acc_a["id"], payload=AccountUpdate(parentAccountId=acc_a["id"]))
        assert "cannot be its own parent" in str(exc_self.value).lower()

        # 2. Create Account C with Parent B
        acc_c = service.create_account(
            actor=actor,
            payload=AccountCreate(name=f"Sub-subsidiary C {suffix}", parentAccountId=acc_b["id"])
        )

        # 3. Prevent circular parenting: Setting Account A's parent to C would create A -> B -> C -> A
        with pytest.raises(ValidationError) as exc_circ:
            service.update_account(actor=actor, account_id=acc_a["id"], payload=AccountUpdate(parentAccountId=acc_c["id"]))
        assert "circular parent-account relationship" in str(exc_circ.value).lower()

    finally:
        db.close()


def test_lead_unqualification_workflow():
    db = SessionLocal()
    service = CrmService(db)
    actor = DummyActor()
    import uuid
    suffix = uuid.uuid4().hex[:6]

    try:
        # Create active lead
        lead_res = service.create_lead(
            actor=actor,
            payload=LeadCreate(
                firstName="Raj",
                lastName="Verma",
                contactEmail=f"raj.{suffix}@biotrial.org",
                companyName=f"BioTrial Labs {suffix}",
                businessArea="Biogas"
            )
        )
        lead_id = lead_res["id"]

        # 1. Reject empty disqualification reason
        with pytest.raises(ValidationError) as exc_empty:
            service.unqualify_lead(actor=actor, lead_id=lead_id, reason="   ")
        assert "mandatory" in str(exc_empty.value).lower()

        # 2. Unqualify lead with valid reason
        unq_res = service.unqualify_lead(
            actor=actor,
            lead_id=lead_id,
            reason="Project suspended indefinitely due to corporate restructuring"
        )
        assert unq_res["success"] is True
        assert unq_res["lead"]["lifecycleStatus"] == "Dormant"
        assert unq_res["lead"]["disqualificationReason"] == "Project suspended indefinitely due to corporate restructuring"

        # 3. Reject duplicate unqualification of already dormant/unqualified lead
        with pytest.raises(ValidationError) as exc_dup:
            service.unqualify_lead(actor=actor, lead_id=lead_id, reason="Trying to unqualify again")
        assert "already unqualified" in str(exc_dup.value).lower()

    finally:
        db.close()


def test_opportunity_won_lost_reopen_workflow():
    db = SessionLocal()
    service = CrmService(db)
    actor = DummyActor()
    import uuid
    suffix = uuid.uuid4().hex[:6]

    try:
        # Create lead and qualify it to get an Opportunity
        lead = service.create_lead(
            actor=actor,
            payload=LeadCreate(
                firstName="Vikram",
                lastName="Sarin",
                contactEmail=f"vikram.{suffix}@greentech.org",
                companyName=f"GreenTech Bio Corp {suffix}",
                businessArea="Biogas"
            )
        )
        qual_res = service.qualify_lead(
            actor=actor,
            lead_id=lead["id"],
            payload=LeadQualifyRequest(
                account=LeadQualifyAccountChoice(action="create", name=f"GreenTech Bio Corp {suffix}"),
                contact=LeadQualifyContactChoice(action="create", name="Vikram Sarin"),
                opportunityName="Commercial Biogas Phase 1"
            )
        )
        opp_id = qual_res["opportunity"]["id"]

        # 1. Closed Won requires wonReason
        with pytest.raises((ValidationError, Exception)) as exc_won:
            OpportunityStageTransitionRequest(newStage="Close", status="Won")
        assert "won reason is mandatory" in str(exc_won.value).lower()

        # 2. Successfully mark Closed Won with wonReason
        won_opp = service.transition_opportunity_stage(
            actor=actor,
            opp_id=opp_id,
            payload=OpportunityStageTransitionRequest(
                newStage="Close",
                status="Won",
                wonReason="Superior microbial degradation rate verified in pilot test"
            )
        )
        assert won_opp["status"] == "Won"
        assert won_opp["wonReason"] == "Superior microbial degradation rate verified in pilot test"
        assert won_opp["closedById"] is not None

        # 3. Reopen Opportunity requires active stage (cannot be Close)
        with pytest.raises((ValidationError, Exception)) as exc_reopen_stg:
            OpportunityReopenRequest(
                reopenStage="Close",
                reason="Client expanding scope"
            )
        assert "cannot remain in the 'close' stage" in str(exc_reopen_stg.value).lower()

        # 4. Successfully reopen to Negotiate stage
        reopened = service.reopen_opportunity(
            actor=actor,
            opp_id=opp_id,
            payload=OpportunityReopenRequest(
                reopenStage="Negotiate",
                reason="Client requested additional production reactor modules"
            )
        )
        assert reopened["status"] == "Open"
        assert reopened["stage"] == "Negotiate"
        assert reopened["wonReason"] is None
        assert reopened["reopenedAt"] is not None
        assert reopened["reopenedById"] is not None

        # 5. Closed Lost requires lossReason
        with pytest.raises((ValidationError, Exception)) as exc_lost:
            OpportunityStageTransitionRequest(newStage="Close", status="Lost")
        assert "loss reason is mandatory" in str(exc_lost.value).lower()

        # 6. Successfully mark Closed Lost with lossReason
        lost_opp = service.transition_opportunity_stage(
            actor=actor,
            opp_id=opp_id,
            payload=OpportunityStageTransitionRequest(
                newStage="Close",
                status="Lost",
                lossReason="Client chose in-house biological solution"
            )
        )
        assert lost_opp["status"] == "Lost"
        assert lost_opp["lossReason"] == "Client chose in-house biological solution"
        assert lost_opp["wonReason"] is None

    finally:
        db.close()


if __name__ == "__main__":
    print("Running Python CRM Schema Enhancement Tests...")
    test_contact_auto_name_generation()
    print("[PASS] test_contact_auto_name_generation")
    test_account_parent_and_circular_prevention()
    print("[PASS] test_account_parent_and_circular_prevention")
    test_lead_unqualification_workflow()
    print("[PASS] test_lead_unqualification_workflow")
    test_opportunity_won_lost_reopen_workflow()
    print("[PASS] test_opportunity_won_lost_reopen_workflow")
    print("All Python tests completed successfully!")
