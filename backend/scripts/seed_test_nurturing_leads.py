"""
REVY CRM - Seed Controlled Test Leads for Lead Nurturing & Unified Timeline
Seeds the 8 mandatory test lead scenarios on the canonical Neon PostgreSQL database:
1. Newly created lead (Pending Introduction Email, due Date Connected + 5 days)
2. Lead with future Date Connected (due Date Connected + 5 days)
3. Lead with past Date Connected (due Date Connected + 5 days)
4. Lead with completed Introduction Email (auto-interaction logged, Stage 2/3 active)
5. Lead with overdue activity (due date in past, flagged Overdue)
6. Lead with customer response recorded (nurturing paused, interaction logged)
7. Lead with nurturing paused (explicitly paused with reason)
8. Lead with manually logged interactions (unified timeline with manual + cadence)
"""
import os
import sys
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

# Ensure app is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure models are registered
import app.models

from app.core.database import SessionLocal
from app.users.model import User
from app.crm.model import Lead, LeadCommunicationHistory, LeadNurturingProcess, NurturingActivity
from app.crm.schema import LeadCreate
from app.crm.service import CrmService
from app.crm.nurturing_service import LeadNurturingService, get_current_kolkata_date, get_current_kolkata_datetime
from app.core.dependencies import CurrentUser

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")


def main():
    db = SessionLocal()
    try:
        # 1. Fetch CRM Admin Actor
        user = db.query(User).filter(User.username == "vasudev").first()
        if not user:
            user = db.query(User).first()
        assert user, "No user found in database to act as lead creator"

        actor = CurrentUser(
            user=user,
            active_role="CRM_ADMIN",
            roles=["CRM_ADMIN"],
            permissions=["crm.lead.create", "crm.lead.view", "crm.lead.edit"],
            all_permissions=["crm.lead.create", "crm.lead.view", "crm.lead.edit"],
            permissions_by_role={"CRM_ADMIN": ["crm.lead.create", "crm.lead.view", "crm.lead.edit"]},
            modules=["CRM"],
            module_roles={"CRM": "CRM_ADMIN"},
            is_global_admin=True
        )

        crm_service = CrmService(db)
        nurturing_service = LeadNurturingService(db)
        today = get_current_kolkata_date()
        now_dt = get_current_kolkata_datetime()

        print(f"[*] Seeding test leads as actor: {actor.username} ({actor.id})")
        print(f"[*] Kolkata Reference Date: {today}")

        test_leads_info = []

        # ---------------------------------------------------------------------
        # Scenario 1: Newly Created Lead
        # ---------------------------------------------------------------------
        lead1_name = "DEMO-NUR-01 Newly Created Lead"
        existing1 = db.query(Lead).filter(Lead.lead_name == lead1_name).first()
        if not existing1:
            p1 = LeadCreate(
                leadName=lead1_name,
                companyName="Tata Bio Solutions Ltd",
                businessArea="Biogas",
                requirementType="Direct Product/Service",
                requestedProductService="Specialized Anaerobic Inoculum",
                connectedDate=today,
                contactEmail="contact@tatabio.test",
                leadSource="Website"
            )
            res1 = crm_service.create_lead(actor=actor, payload=p1)
            lead1_id = res1["id"]
            lead1_code = res1["leadId"]
        else:
            lead1_id = existing1.id
            lead1_code = existing1.lead_id

        p1_details = nurturing_service.get_nurturing_details(lead1_id)
        test_leads_info.append({
            "scenario": "1. Newly Created Lead",
            "leadId": lead1_id,
            "leadCode": lead1_code,
            "nurturingStatus": p1_details.get("status"),
            "currentStage": p1_details.get("currentStage"),
            "nextActivityDue": p1_details.get("nextActivityDate")
        })

        # ---------------------------------------------------------------------
        # Scenario 2: Lead with Future Date Connected
        # ---------------------------------------------------------------------
        lead2_name = "DEMO-NUR-02 Future Date Connected"
        future_conn_date = today + timedelta(days=7)
        existing2 = db.query(Lead).filter(Lead.lead_name == lead2_name).first()
        if not existing2:
            p2 = LeadCreate(
                leadName=lead2_name,
                companyName="NextGen Effluent Works",
                businessArea="WWT",
                requirementType="Consulting",
                requestedProductService="Effluent Treatment Feasibility Audit",
                connectedDate=future_conn_date,
                contactEmail="info@nextgenwwt.test",
                leadSource="Referral"
            )
            res2 = crm_service.create_lead(actor=actor, payload=p2)
            lead2_id = res2["id"]
            lead2_code = res2["leadId"]
        else:
            lead2_id = existing2.id
            lead2_code = existing2.lead_id

        p2_details = nurturing_service.get_nurturing_details(lead2_id)
        test_leads_info.append({
            "scenario": "2. Future Date Connected (+7 days)",
            "leadId": lead2_id,
            "leadCode": lead2_code,
            "nurturingStatus": p2_details.get("status"),
            "currentStage": p2_details.get("currentStage"),
            "nextActivityDue": p2_details.get("nextActivityDate")
        })

        # ---------------------------------------------------------------------
        # Scenario 3: Lead with Past Date Connected
        # ---------------------------------------------------------------------
        lead3_name = "DEMO-NUR-03 Past Date Connected"
        past_conn_date = today - timedelta(days=10)
        existing3 = db.query(Lead).filter(Lead.lead_name == lead3_name).first()
        if not existing3:
            p3 = LeadCreate(
                leadName=lead3_name,
                companyName="Heritage Distilleries Biogas",
                businessArea="Biogas",
                requirementType="Direct Product/Service",
                requestedProductService="Digester Booster Culture",
                connectedDate=past_conn_date,
                contactEmail="plant@heritagedistill.test",
                leadSource="Cold Call"
            )
            res3 = crm_service.create_lead(actor=actor, payload=p3)
            lead3_id = res3["id"]
            lead3_code = res3["leadId"]
        else:
            lead3_id = existing3.id
            lead3_code = existing3.lead_id

        p3_details = nurturing_service.get_nurturing_details(lead3_id)
        test_leads_info.append({
            "scenario": "3. Past Date Connected (-10 days)",
            "leadId": lead3_id,
            "leadCode": lead3_code,
            "nurturingStatus": p3_details.get("status"),
            "currentStage": p3_details.get("currentStage"),
            "nextActivityDue": p3_details.get("nextActivityDate")
        })

        # ---------------------------------------------------------------------
        # Scenario 4: Lead with Completed Introduction Email
        # ---------------------------------------------------------------------
        lead4_name = "DEMO-NUR-04 Completed Intro Email"
        existing4 = db.query(Lead).filter(Lead.lead_name == lead4_name).first()
        if not existing4:
            p4 = LeadCreate(
                leadName=lead4_name,
                companyName="Adani Solar Effluent Treatment",
                businessArea="WWT",
                requirementType="Sample Testing",
                requestedProductService="COD & BOD Lab Analysis",
                connectedDate=today - timedelta(days=4),
                contactEmail="procurement@adanisolar.test",
                leadSource="Website"
            )
            res4 = crm_service.create_lead(actor=actor, payload=p4)
            lead4_id = res4["id"]
            lead4_code = res4["leadId"]

            # Complete Stage 1 Introduction Email
            p4_nurturing = nurturing_service.get_nurturing_details(lead4_id)
            act1 = p4_nurturing["activities"][0]
            nurturing_service.complete_activity(
                lead_id=lead4_id,
                activity_id=act1["activityId"],
                notes="Sent REVY introduction presentation and capabilities brochure via company email.",
                outcome="Sent successfully",
                email_message_reference="MSG-TATA-DEMO-001",
                actor=user
            )
        else:
            lead4_id = existing4.id
            lead4_code = existing4.lead_id

        p4_details = nurturing_service.get_nurturing_details(lead4_id)
        test_leads_info.append({
            "scenario": "4. Completed Introduction Email",
            "leadId": lead4_id,
            "leadCode": lead4_code,
            "nurturingStatus": p4_details.get("status"),
            "currentStage": p4_details.get("currentStage"),
            "nextActivityDue": p4_details.get("nextActivityDate")
        })

        # ---------------------------------------------------------------------
        # Scenario 5: Lead with Overdue Activity
        # ---------------------------------------------------------------------
        lead5_name = "DEMO-NUR-05 Overdue Activity"
        existing5 = db.query(Lead).filter(Lead.lead_name == lead5_name).first()
        if not existing5:
            p5 = LeadCreate(
                leadName=lead5_name,
                companyName="Cipla Green Campus",
                businessArea="WWT",
                requirementType="Consulting",
                requestedProductService="Biological Wastewater Troubleshooting",
                connectedDate=today - timedelta(days=12),
                contactEmail="ehs@ciplacampus.test",
                leadSource="Referral"
            )
            res5 = crm_service.create_lead(actor=actor, payload=p5)
            lead5_id = res5["id"]
            lead5_code = res5["leadId"]

            # Set due date in past so it becomes Overdue
            act_overdue = db.query(NurturingActivity).filter(NurturingActivity.lead_id == lead5_id).first()
            if act_overdue:
                act_overdue.due_date = today - timedelta(days=7)
                db.commit()
        else:
            lead5_id = existing5.id
            lead5_code = existing5.lead_id

        p5_details = nurturing_service.get_nurturing_details(lead5_id)
        test_leads_info.append({
            "scenario": "5. Overdue Activity (due 7 days ago)",
            "leadId": lead5_id,
            "leadCode": lead5_code,
            "nurturingStatus": p5_details.get("status"),
            "currentStage": p5_details.get("currentStage"),
            "nextActivityDue": p5_details.get("nextActivityDate")
        })

        # ---------------------------------------------------------------------
        # Scenario 6: Lead with Customer Response Recorded (Paused)
        # ---------------------------------------------------------------------
        lead6_name = "DEMO-NUR-06 Customer Response Recorded"
        existing6 = db.query(Lead).filter(Lead.lead_name == lead6_name).first()
        if not existing6:
            p6 = LeadCreate(
                leadName=lead6_name,
                companyName="Godrej Agrovet Biogas Project",
                businessArea="Biogas",
                requirementType="Direct Product/Service",
                requestedProductService="Specialized Methane Culture",
                connectedDate=today - timedelta(days=3),
                contactEmail="bioenergy@godrejagro.test",
                leadSource="Website"
            )
            res6 = crm_service.create_lead(actor=actor, payload=p6)
            lead6_id = res6["id"]
            lead6_code = res6["leadId"]

            # Record customer response
            nurturing_service.record_customer_response(
                lead_id=lead6_id,
                channel="Phone",
                response_notes="Client called back expressing strong interest in our bio-culture. Requested proposal review meeting.",
                outcome="Interested",
                target_lifecycle_status="Negotiation",
                pause_nurturing=True,
                actor=user
            )
        else:
            lead6_id = existing6.id
            lead6_code = existing6.lead_id

        p6_details = nurturing_service.get_nurturing_details(lead6_id)
        test_leads_info.append({
            "scenario": "6. Customer Response Recorded (Interested, Status=Negotiation)",
            "leadId": lead6_id,
            "leadCode": lead6_code,
            "nurturingStatus": p6_details.get("status"),
            "currentStage": p6_details.get("currentStage"),
            "pauseReason": p6_details.get("pauseReason")
        })

        # ---------------------------------------------------------------------
        # Scenario 7: Lead with Nurturing Manually Paused
        # ---------------------------------------------------------------------
        lead7_name = "DEMO-NUR-07 Explicitly Paused"
        existing7 = db.query(Lead).filter(Lead.lead_name == lead7_name).first()
        if not existing7:
            p7 = LeadCreate(
                leadName=lead7_name,
                companyName="ITC Paperboard Digester",
                businessArea="Biogas",
                requirementType="Consulting",
                requestedProductService="Biogas Plant Efficiency Audit",
                connectedDate=today - timedelta(days=2),
                contactEmail="engg@itcpaper.test",
                leadSource="Investor"
            )
            res7 = crm_service.create_lead(actor=actor, payload=p7)
            lead7_id = res7["id"]
            lead7_code = res7["leadId"]

            # Pause nurturing
            nurturing_service.pause_nurturing(
                lead_id=lead7_id,
                reason="Client requested temporary hold while plant annual shutdown is completed.",
                actor=user
            )
        else:
            lead7_id = existing7.id
            lead7_code = existing7.lead_id

        p7_details = nurturing_service.get_nurturing_details(lead7_id)
        test_leads_info.append({
            "scenario": "7. Nurturing Explicitly Paused",
            "leadId": lead7_id,
            "leadCode": lead7_code,
            "nurturingStatus": p7_details.get("status"),
            "currentStage": p7_details.get("currentStage"),
            "pauseReason": p7_details.get("pauseReason")
        })

        # ---------------------------------------------------------------------
        # Scenario 8: Lead with Manually Logged Interactions
        # ---------------------------------------------------------------------
        lead8_name = "DEMO-NUR-08 Mixed Manual Interactions"
        existing8 = db.query(Lead).filter(Lead.lead_name == lead8_name).first()
        if not existing8:
            p8 = LeadCreate(
                leadName=lead8_name,
                companyName="Biocon Biologics Wastewater Unit",
                businessArea="WWT",
                requirementType="Direct Product/Service",
                requestedProductService="Aerobic Sludge Inoculum 2000L",
                connectedDate=today - timedelta(days=1),
                contactEmail="projects@bioconbio.test",
                leadSource="Website"
            )
            res8 = crm_service.create_lead(actor=actor, payload=p8)
            lead8_id = res8["id"]
            lead8_code = res8["leadId"]

            # Log manual communication
            from app.crm.schema import CommunicationCreate
            comm_payload = CommunicationCreate(
                channel="Phone / Call",
                eventType="Phone call with client",
                summary="Discussed site wastewater characteristics and sent TDS/COD testing specifications.",
                outcome="Client will send effluent sample on Monday."
            )
            crm_service.create_communication(actor=actor, lead_id=lead8_id, payload=comm_payload)
        else:
            lead8_id = existing8.id
            lead8_code = existing8.lead_id

        timeline8 = nurturing_service.get_unified_timeline(lead8_id)
        test_leads_info.append({
            "scenario": "8. Mixed Timeline (Manual + Cadence)",
            "leadId": lead8_id,
            "leadCode": lead8_code,
            "timelineItemCount": len(timeline8),
            "sources": list({item["source"] for item in timeline8})
        })

        print("\n" + "=" * 80)
        print("SEEDING SUMMARY - 8 CONTROLLED TEST LEADS READY FOR DEMO & TESTING")
        print("=" * 80)
        for info in test_leads_info:
            print(f"Scenario: {info['scenario']}")
            print(f"  Lead ID: {info['leadId']} ({info['leadCode']})")
            for k, v in info.items():
                if k not in ("scenario", "leadId", "leadCode"):
                    print(f"  {k}: {v}")
            print("-" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()
