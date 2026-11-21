import os
import sys
import pytest
from datetime import datetime, timezone

os.environ["TESTING"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.users.model import User
from app.core.dependencies import CurrentUser
from app.crm.model import Lead
from app.crm.schema import LeadCreate, ALLOWED_BUSINESS_AREAS
from app.crm.service import CrmService

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_actor(db_session):
    user = db_session.query(User).filter(User.username == "admin_funnel_test").first()
    if not user:
        user = User(
            username="admin_funnel_test",
            name="Funnel Test Admin",
            email="admin_funnel_test@revyenvironmental.com",
            password_hash="test_hash_pw",
            status="Active"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    return CurrentUser(
        user=user,
        active_role="CRM_ADMIN",
        roles=["CRM_ADMIN"],
        permissions=["*"],
        all_permissions=["*"],
        permissions_by_role={"CRM_ADMIN": ["*"]},
        modules=["CRM"],
        module_roles={"CRM": ["CRM_ADMIN"]},
        is_global_admin=True
    )


def test_allowed_business_areas_includes_biogas_and_waste_water():
    """Verify that ALLOWED_BUSINESS_AREAS includes Biogas and Waste Water."""
    assert "Biogas" in ALLOWED_BUSINESS_AREAS
    assert "Waste Water" in ALLOWED_BUSINESS_AREAS
    assert "WWT" in ALLOWED_BUSINESS_AREAS


def test_create_and_filter_lead_with_waste_water(db_session, test_actor):
    """Verify lead creation works with 'Waste Water' and filtering returns it, without rating/employees."""
    crm_service = CrmService(db_session)
    ts = int(datetime.now(timezone.utc).timestamp())
    payload = LeadCreate(
        topic=f"Waste Water Lead Test {ts}",
        companyName=f"Clean Streams Ltd {ts}",
        businessArea="Waste Water",
        leadSource="Website",
        clientStatus="New"
    )

    created = crm_service.create_lead(test_actor, payload)
    try:
        assert created["businessArea"] == "Waste Water"
        assert created["companyName"] == f"Clean Streams Ltd {ts}"

        # Verify query by business area returns the created lead
        result = crm_service.list_leads(test_actor, view="all", business_area="Waste Water")
        leads_list = result.get("leads", [])
        found = any(l["id"] == created["id"] for l in leads_list)
        assert found, "Lead with 'Waste Water' should be found when filtering by 'Waste Water'"
    finally:
        # Clean up test record to preserve exact funnel count
        db_session.query(Lead).filter(Lead.id == created["id"]).delete()
        db_session.commit()


def test_create_lead_with_biogas_without_optional_fields(db_session, test_actor):
    """Verify lead creation works with 'Biogas' and without rating/employees/requirementTypes."""
    crm_service = CrmService(db_session)
    ts = int(datetime.now(timezone.utc).timestamp())
    payload = LeadCreate(
        topic=f"Biogas Lead Test {ts}",
        companyName=f"Green Gas Works {ts}",
        businessArea="Biogas",
        leadSource="Website",
        clientStatus="New"
    )

    created = crm_service.create_lead(test_actor, payload)
    try:
        assert created["businessArea"] == "Biogas"
        assert created["companyName"] == f"Green Gas Works {ts}"
    finally:
        # Clean up test record to preserve exact funnel count
        db_session.query(Lead).filter(Lead.id == created["id"]).delete()
        db_session.commit()
