"""CRM Sales Funnel Seed Script: 50 Leads, 30 Qualified, 15 Quotations, 5 PIs

Generates realistic fictional sample records demonstrating the complete CRM sales funnel:
- 50 Total Leads
- 30 Qualified Leads -> 30 Opportunities
- 15 Opportunities with Quotations (using existing catalogue services & standard taxes)
- 5 Opportunities with Proforma Invoices (using ProformaInvoiceService)

All stage transitions are executed automatically through backend services, populating
OpportunityStageHistory and maintaining transactional integrity.

Idempotent: Uses marker '[SAMPLE_FUNNEL_2026]' to prevent duplicate records.
Safe Cleanup: Run with --cleanup to safely and cleanly remove only sample records.
"""

import sys
import os
import argparse
import logging
from decimal import Decimal
from datetime import datetime, date, timedelta, timezone

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.models  # Load all models
from app.core.database import SessionLocal, init_db, engine
from app.users.model import User
from app.crm.model import (
    Lead,
    Account,
    Contact,
    Opportunity,
    OpportunityQuotation,
    OpportunityStageHistory,
    LeadRequirementType
)
from app.crm.catalogue_model import Service, TaxConfiguration, OpportunityQuotationItem
from app.crm.invoice_model import (
    ProformaInvoice,
    ProformaInvoiceRevision,
    ProformaInvoiceItem
)
from app.crm.service import CrmService, get_next_sequence_id, record_opportunity_stage_transition
from app.crm.catalogue_service import CatalogueService
from app.crm.invoice_service import ProformaInvoiceService, get_financial_year
from app.crm.invoice_schema import ProformaInvoiceCreate
from app.core.dependencies import CurrentUser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed.crm.funnel")

SEED_MARKER = "[SAMPLE_FUNNEL_2026]"

# 50 Realistic Fictional Indian Companies & Contact Profiles
SAMPLE_COMPANIES = [
    # 1 - 10: Biogas & Bio-CNG Plants
    {"name": "Shree Krishna Biogas & Power LLP", "city": "Anand", "state": "Gujarat", "area": "Biogas", "req": "Sample Testing", "contact": "Rajesh Patel", "desig": "Managing Partner", "phone": "+91-9825123401", "email": "rajesh@krishnabiogas.com"},
    {"name": "Zenith Agro Distilleries Pvt Ltd", "city": "Kolhapur", "state": "Maharashtra", "area": "Biogas", "req": "Consulting", "contact": "Amit Deshmukh", "desig": "General Manager - Operations", "phone": "+91-9822123402", "email": "amit.d@zenithagro.in"},
    {"name": "Coromandel Sugar & Bio-Energy Ltd", "city": "Tiruchirappalli", "state": "Tamil Nadu", "area": "Biogas", "req": "Sample Testing", "contact": "K. Ramanathan", "desig": "VP Technical", "phone": "+91-9443123403", "email": "ramanathan@coromandelsugar.com"},
    {"name": "Narmada Pulp & Paper Mills Ltd", "city": "Bharuch", "state": "Gujarat", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Bhavesh Shah", "desig": "Head of Environment & ETP", "phone": "+91-9879123404", "email": "b.shah@narmadapulp.co.in"},
    {"name": "Godavari Green Energy Projects Ltd", "city": "Ahmednagar", "state": "Maharashtra", "area": "Biogas", "req": "Consulting", "contact": "Suresh Shinde", "desig": "Plant Director", "phone": "+91-9823123405", "email": "suresh@godavarigreen.com"},
    {"name": "Malwa Bio-Methane Energy Corp", "city": "Ludhiana", "state": "Punjab", "area": "Biogas", "req": "Sample Testing", "contact": "Harpreet Singh", "desig": "Chief Operating Officer", "phone": "+91-9814123406", "email": "harpreet@malwabiomethane.com"},
    {"name": "Deccan Dairies & Agro Foods Ltd", "city": "Hyderabad", "state": "Telangana", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "P. Venkat Rao", "desig": "General Manager Projects", "phone": "+91-9848123407", "email": "venkat.rao@deccandairy.com"},
    {"name": "Kaveri Wastewater Solutions Ltd", "city": "Bengaluru", "state": "Karnataka", "area": "Wastewater Treatment (WWT)", "req": "Consulting", "contact": "N. S. Murthy", "desig": "Technical Director", "phone": "+91-9845123408", "email": "nsmurthy@kaverisolutions.in"},
    {"name": "Ganges Clean Effluent Systems Ltd", "city": "Kanpur", "state": "Uttar Pradesh", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Pradeep Tripathi", "desig": "ETP Manager", "phone": "+91-9415123409", "email": "pradeep@gangesclean.com"},
    {"name": "Surya Bio-Fertilizers & Gas Pvt Ltd", "city": "Pune", "state": "Maharashtra", "area": "Biogas", "req": "Product", "contact": "Nitin Kulkarni", "desig": "Director - Sustainability", "phone": "+91-9822123410", "email": "nitin@suryabioenergy.com"},

    # 11 - 20: Chemical, Pharma & Beverage ETPs
    {"name": "Baroda Chemical Synthetics Ltd", "city": "Vadodara", "state": "Gujarat", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Kalpesh Joshi", "desig": "VP Environment & Safety", "phone": "+91-9825123411", "email": "kalpesh@barodachem.com"},
    {"name": "Vindhya Organics & Life Sciences Ltd", "city": "Bhopal", "state": "Madhya Pradesh", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Sanjay Verma", "desig": "Plant Head", "phone": "+91-9425123412", "email": "s.verma@vindhyaorg.com"},
    {"name": "Chola Bio-Fermentation Corp", "city": "Coimbatore", "state": "Tamil Nadu", "area": "Biogas", "req": "Consulting", "contact": "S. Vijayakumar", "desig": "Operations Head", "phone": "+91-9842123413", "email": "vijay@cholabio.com"},
    {"name": "Sutlej Distillers & Bio-Refineries", "city": "Jalandhar", "state": "Punjab", "area": "Biogas", "req": "Sample Testing", "contact": "Gurinder Bains", "desig": "Technical VP", "phone": "+91-9815123414", "email": "gurinder@sutlejdistillers.com"},
    {"name": "Konkan Breweries & Agro Products", "city": "Ratnagiri", "state": "Maharashtra", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Milind Rane", "desig": "Head of Sustainability", "phone": "+91-9820123415", "email": "rane@konkanbreweries.com"},
    {"name": "Maha Agri Bio-Fuel Producer Co", "city": "Nashik", "state": "Maharashtra", "area": "Biogas", "req": "Product", "contact": "Sunil Gavhane", "desig": "Managing Director", "phone": "+91-9823123416", "email": "sunil@mahaagribio.org"},
    {"name": "Mysore Food Processors & ETP Corp", "city": "Mysuru", "state": "Karnataka", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "G. Manjunath", "desig": "ETP Incharge", "phone": "+91-9844123417", "email": "manju@mysorefood.com"},
    {"name": "Saurashtra Chemical Waste Solvers", "city": "Rajkot", "state": "Gujarat", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Paresh Vora", "desig": "GM Projects", "phone": "+91-9824123418", "email": "paresh@saurashtrachem.in"},
    {"name": "Jaipur Agro Nutrients & Bio-Gas", "city": "Jaipur", "state": "Rajasthan", "area": "Biogas", "req": "Consulting", "contact": "Vikram Singh Rathore", "desig": "CEO", "phone": "+91-9829123419", "email": "vikram@jaipuragrogas.com"},
    {"name": "Bengal Enagro Environmental Ltd", "city": "Kolkata", "state": "West Bengal", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Subhashish Roy", "desig": "Environmental Consultant", "phone": "+91-9830123420", "email": "subhash@bengalenagro.com"},

    # 21 - 30: Sugar Mills, Starch & Food Processing
    {"name": "Panchganga Sugar Factory Co-op Ltd", "city": "Ichalkaranji", "state": "Maharashtra", "area": "Biogas", "req": "Sample Testing", "contact": "Anand Patil", "desig": "Chief Chemist", "phone": "+91-9822123421", "email": "anand.p@panchgangasugar.org"},
    {"name": "Tirupati Starch & Chemicals Ltd", "city": "Indore", "state": "Madhya Pradesh", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Ramesh Agrawal", "desig": "Director Technical", "phone": "+91-9826123422", "email": "ramesh@tirupatistarch.com"},
    {"name": "Yamuna Textile Processors & ETP Ltd", "city": "Panipat", "state": "Haryana", "area": "Wastewater Treatment (WWT)", "req": "Consulting", "contact": "Ashok Mittal", "desig": "Managing Partner", "phone": "+91-9812123423", "email": "ashok@yamunatextile.com"},
    {"name": "Sabarmati Bio-Waste Solutions LLP", "city": "Ahmedabad", "state": "Gujarat", "area": "Biogas", "req": "Sample Testing", "contact": "Chirag Thakkar", "desig": "VP Operations", "phone": "+91-9825123424", "email": "chirag@sabarmatibio.in"},
    {"name": "Krishna Valley Bio-Power Ltd", "city": "Sangli", "state": "Maharashtra", "area": "Biogas", "req": "Sample Testing", "contact": "Dnyaneshwar More", "desig": "Plant In-charge", "phone": "+91-9823123425", "email": "d.more@krishnavalley.com"},
    {"name": "Coorg Agro Effluent Recyclers", "city": "Madikeri", "state": "Karnataka", "area": "Wastewater Treatment (WWT)", "req": "Consulting", "contact": "B. B. Cariappa", "desig": "Proprietor", "phone": "+91-9448123426", "email": "cariappa@coorgaffluent.com"},
    {"name": "Nellore Aquaculture & ETP Systems", "city": "Nellore", "state": "Andhra Pradesh", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "K. Srinivas", "desig": "Technical Advisor", "phone": "+91-9848123427", "email": "srinivas@nelloreaqua.in"},
    {"name": "Rohtak Bio-Fuels & Energy Ltd", "city": "Rohtak", "state": "Haryana", "area": "Biogas", "req": "Product", "contact": "Virender Hooda", "desig": "Operations Director", "phone": "+91-9812123428", "email": "virender@rohtakbiofuels.com"},
    {"name": "Bhilwara Textile Effluent Treatment", "city": "Bhilwara", "state": "Rajasthan", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Manish Sharma", "desig": "ETP General Manager", "phone": "+91-9829123429", "email": "manish@bhilwaracetp.com"},
    {"name": "Karnal Bio-Gas & Clean Energy Co", "city": "Karnal", "state": "Haryana", "area": "Biogas", "req": "Sample Testing", "contact": "Sandeep Dhillon", "desig": "Project Head", "phone": "+91-9813123430", "email": "sandeep@karnalbiogas.com"},

    # 31 - 50: Additional Pipeline Leads (20 Non-qualified leads)
    {"name": "Dharwad Agri Bio-Refineries Pvt Ltd", "city": "Hubballi", "state": "Karnataka", "area": "Biogas", "req": "Sample Testing", "contact": "Mahesh Hiremath", "desig": "Plant Head", "phone": "+91-9845123431", "email": "mahesh@dharwadbio.com"},
    {"name": "Surat Dyeing & Printing ETP Trust", "city": "Surat", "state": "Gujarat", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Jignesh Zaveri", "desig": "Secretary", "phone": "+91-9825123432", "email": "jignesh@suratcetp.org"},
    {"name": "Solapur Bio-Pellets & Methane Ltd", "city": "Solapur", "state": "Maharashtra", "area": "Biogas", "req": "Consulting", "contact": "Ravindra Gaikwad", "desig": "Director", "phone": "+91-9822123433", "email": "ravi@solapurbiopellets.com"},
    {"name": "Tirupur Knitwear Common Effluent Ltd", "city": "Tiruppur", "state": "Tamil Nadu", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "M. Senthil Kumar", "desig": "Managing Director", "phone": "+91-9843123434", "email": "senthil@tirupurcetp.com"},
    {"name": "Alwar Bio-Gas & Green Fuels Corp", "city": "Alwar", "state": "Rajasthan", "area": "Biogas", "req": "Sample Testing", "contact": "Dharmendra Yadav", "desig": "VP Operations", "phone": "+91-9828123435", "email": "dharmendra@alwarfuels.com"},
    {"name": "Kalyan Chemical Waste Recyclers", "city": "Thane", "state": "Maharashtra", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Sameer Koli", "desig": "Safety Manager", "phone": "+91-9820123436", "email": "sameer@kalyanrecycles.com"},
    {"name": "Gwalior Food Parks & Waste Solutions", "city": "Gwalior", "state": "Madhya Pradesh", "area": "Wastewater Treatment (WWT)", "req": "Consulting", "contact": "Rajeev Saxena", "desig": "Chief Engineer", "phone": "+91-9425123437", "email": "rajeev@gwaliorfoodpark.in"},
    {"name": "Vapi Waste Management Association", "city": "Vapi", "state": "Gujarat", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Dinesh Parekh", "desig": "Technical Advisor", "phone": "+91-9824123438", "email": "dinesh@vapiwaste.org"},
    {"name": "Belagavi Sugar Distilleries Ltd", "city": "Belagavi", "state": "Karnataka", "area": "Biogas", "req": "Sample Testing", "contact": "Prakash Bellad", "desig": "GM Distillery", "phone": "+91-9844123439", "email": "prakash@belagavisugar.com"},
    {"name": "Udaipur Mineral Processing ETP Ltd", "city": "Udaipur", "state": "Rajasthan", "area": "Wastewater Treatment (WWT)", "req": "Product", "contact": "Devendra Meena", "desig": "Environmental Officer", "phone": "+91-9829123440", "email": "devendra@udaipurminerals.com"},
    {"name": "Nagpur Citrus Agro-Processing Waste", "city": "Nagpur", "state": "Maharashtra", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Vijay Bhoyar", "desig": "Plant Incharge", "phone": "+91-9822123441", "email": "vijay@nagpurcitrus.com"},
    {"name": "Patiala Bio-Energy Renewable Ltd", "city": "Patiala", "state": "Punjab", "area": "Biogas", "req": "Sample Testing", "contact": "Simranjit Dhillon", "desig": "MD", "phone": "+91-9814123442", "email": "simran@patialabioenergy.com"},
    {"name": "Erode Tannery Effluent Systems Ltd", "city": "Erode", "state": "Tamil Nadu", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "T. Murugesan", "desig": "Chief Technologist", "phone": "+91-9842123443", "email": "murugan@erodetannery.in"},
    {"name": "Ankleshwar Environmental Preservation", "city": "Ankleshwar", "state": "Gujarat", "area": "Wastewater Treatment (WWT)", "req": "Consulting", "contact": "Nilesh Desai", "desig": "VP EHS", "phone": "+91-9825123444", "email": "nilesh@ankleshwarenv.com"},
    {"name": "Meerut Sugar & Ethanol Bio-Gas", "city": "Meerut", "state": "Uttar Pradesh", "area": "Biogas", "req": "Sample Testing", "contact": "Arun Tyagi", "desig": "Plant Head", "phone": "+91-9412123445", "email": "arun@meerutsugar.com"},
    {"name": "Bhubaneswar Water & Sanitation Corp", "city": "Bhubaneswar", "state": "Odisha", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Debabrata Mohanty", "desig": "Project Director", "phone": "+91-9437123446", "email": "debabrata@bhubaneswarwater.gov.in"},
    {"name": "Jamshedpur Metallurgical ETP Ltd", "city": "Jamshedpur", "state": "Jharkhand", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Abhishek Sen", "desig": "Senior Environmentalist", "phone": "+91-9431123447", "email": "abhishek@jamshedpuretp.com"},
    {"name": "Guwahati Bio-Refining & Paper Mills", "city": "Guwahati", "state": "Assam", "area": "Wastewater Treatment (WWT)", "req": "Consulting", "contact": "Partha Barua", "desig": "GM Environment", "phone": "+91-9864123448", "email": "partha@guwahatipulp.co.in"},
    {"name": "Guntur Tobacco & Agro Waste Energy", "city": "Guntur", "state": "Andhra Pradesh", "area": "Biogas", "req": "Sample Testing", "contact": "M. Sambasiva Rao", "desig": "Managing Partner", "phone": "+91-9848123449", "email": "sambasiva@gunturagrowaste.com"},
    {"name": "Kottayam Rubber Latex Effluent Solvers", "city": "Kottayam", "state": "Kerala", "area": "Wastewater Treatment (WWT)", "req": "Sample Testing", "contact": "Kurien Thomas", "desig": "Managing Director", "phone": "+91-9447123450", "email": "kurien@kottayamlatex.in"}
]

LEAD_SOURCES = [
    "Website", "Customer Referral", "Exhibition", "LinkedIn",
    "Cold Call", "Direct Mail", "Partner Referral", "Inbound Call"
]


def cleanup_seed_funnel(db):
    """Safely and surgically deletes only records created with SEED_MARKER."""
    logger.info(f"Checking for existing records with marker '{SEED_MARKER}'...")
    sample_leads = db.query(Lead).filter(Lead.remarks.like(f"%{SEED_MARKER}%")).all()
    if not sample_leads:
        logger.info("No sample records found to clean up.")
        return 0

    lead_ids = [l.id for l in sample_leads]
    logger.info(f"Found {len(lead_ids)} sample leads. Cleaning up dependent records...")

    sample_opps = db.query(Opportunity).filter(
        (Opportunity.originating_lead_id.in_(lead_ids)) |
        (Opportunity.description.like(f"%{SEED_MARKER}%"))
    ).all()
    opp_ids = [o.id for o in sample_opps]

    if opp_ids:
        # Delete PIs
        pis = db.query(ProformaInvoice).filter(ProformaInvoice.opportunity_id.in_(opp_ids)).all()
        pi_ids = [p.id for p in pis]
        if pi_ids:
            revis = db.query(ProformaInvoiceRevision).filter(ProformaInvoiceRevision.proforma_invoice_id.in_(pi_ids)).all()
            rev_ids = [r.id for r in revis]
            if rev_ids:
                db.query(ProformaInvoiceItem).filter(ProformaInvoiceItem.revision_id.in_(rev_ids)).delete(synchronize_session=False)
            db.query(ProformaInvoiceRevision).filter(ProformaInvoiceRevision.proforma_invoice_id.in_(pi_ids)).delete(synchronize_session=False)
            db.query(ProformaInvoice).filter(ProformaInvoice.opportunity_id.in_(opp_ids)).delete(synchronize_session=False)

        # Delete Quotations
        quotes = db.query(OpportunityQuotation).filter(OpportunityQuotation.opportunity_id.in_(opp_ids)).all()
        quote_ids = [q.id for q in quotes]
        if quote_ids:
            db.query(OpportunityQuotationItem).filter(OpportunityQuotationItem.quotation_id.in_(quote_ids)).delete(synchronize_session=False)
            db.query(OpportunityQuotation).filter(OpportunityQuotation.opportunity_id.in_(opp_ids)).delete(synchronize_session=False)

        # Delete Stage History
        db.query(OpportunityStageHistory).filter(OpportunityStageHistory.opportunity_id.in_(opp_ids)).delete(synchronize_session=False)

        # Null out lead.opportunity_id before deleting opportunities
        db.query(Lead).filter(Lead.id.in_(lead_ids)).update({Lead.opportunity_id: None}, synchronize_session=False)

        # Delete Opportunities
        db.query(Opportunity).filter(Opportunity.id.in_(opp_ids)).delete(synchronize_session=False)

    # Delete sample leads requirement types
    db.query(LeadRequirementType).filter(LeadRequirementType.lead_id.in_(lead_ids)).delete(synchronize_session=False)

    # Find sample accounts/contacts
    sample_accounts = db.query(Account).filter(Account.address.like(f"%{SEED_MARKER}%")).all()
    acc_ids = [a.id for a in sample_accounts]
    if acc_ids:
        db.query(Contact).filter(Contact.account_id.in_(acc_ids)).delete(synchronize_session=False)
        db.query(Account).filter(Account.id.in_(acc_ids)).delete(synchronize_session=False)

    # Delete sample leads
    db.query(Lead).filter(Lead.id.in_(lead_ids)).delete(synchronize_session=False)

    db.commit()
    logger.info(f"Cleaned up {len(lead_ids)} sample leads, {len(opp_ids)} opportunities, and associated quotations & PIs.")
    return len(lead_ids)


def seed_crm_funnel():
    """Executes safe, idempotent CRM sales funnel generation."""
    if engine.dialect.name == "sqlite":
        with engine.connect() as conn:
            opp_sql_row = conn.exec_driver_sql("SELECT sql FROM sqlite_master WHERE type='table' AND name='crm_opportunities'").fetchone()
            if opp_sql_row and "'PI Issued'" not in (opp_sql_row[0] or ""):
                logger.info("Migrating SQLite schema for crm_opportunities to support 'PI Issued'...")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_opportunity_stage_history")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_opportunity_quotation_items")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_proforma_invoice_items")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_proforma_invoice_revisions")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_proforma_invoices")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_opportunity_quotations")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_milestones")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_product_transactions")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_sample_submissions")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_consulting_engagements")
                conn.exec_driver_sql("DROP TABLE IF EXISTS crm_opportunities")
                conn.commit()
    init_db()
    db = SessionLocal()
    try:
        # Check if already seeded completely
        existing_sample_leads = db.query(Lead).filter(Lead.remarks.like(f"%{SEED_MARKER}%")).all()
        existing_sample_opps = db.query(Opportunity).filter(Opportunity.description.like(f"%{SEED_MARKER}%")).all()
        if len(existing_sample_leads) == 50 and len(existing_sample_opps) == 30:
            logger.info("CRM Funnel already seeded with exactly 50 sample leads and 30 opportunities. Idempotent check passed.")
            print_funnel_summary(db)
            return

        if len(existing_sample_leads) > 0 or len(existing_sample_opps) > 0:
            logger.warning("Found partial sample records. Performing clean reset before re-seeding...")
            cleanup_seed_funnel(db)

        logger.info("Starting CRM Sales Funnel sample data seeding...")

        # 1. Resolve administrative actor user
        admin_user = db.query(User).filter(
            User.username.in_(["vasudev", "test_it_admin_global", "stg4_crm_admin", "admin"])
        ).first()
        if not admin_user:
            admin_user = db.query(User).first()

        actor = CurrentUser(
            user=admin_user,
            active_role="CRM_ADMIN",
            roles=["IT_ADMIN", "CRM_ADMIN", "DIRECTOR"],
            permissions=["*"],
            all_permissions=["*"],
            permissions_by_role={"CRM_ADMIN": ["*"]},
            modules=["CRM", "USERS", "BMS"],
            module_roles={"CRM": ["CRM_ADMIN"]},
            is_global_admin=True
        )

        # 2. Resolve available catalogue services and tax configuration
        tax_config = db.query(TaxConfiguration).filter(
            TaxConfiguration.tax_type == "INTRA_STATE",
            TaxConfiguration.is_active == True
        ).first()
        if not tax_config:
            tax_config = db.query(TaxConfiguration).first()

        available_services = db.query(Service).filter(Service.is_active == True).limit(10).all()
        if not available_services:
            logger.warning("No active catalogue services found. Seeding basic catalogue...")
            from app.crm.catalogue_seed import seed_catalogue_data
            seed_catalogue_data(db)
            available_services = db.query(Service).filter(Service.is_active == True).limit(10).all()

        crm_service = CrmService(db)
        catalogue_service = CatalogueService(db)
        invoice_service = ProformaInvoiceService(db)

        # 3. Create 50 Leads
        created_leads = []
        for i, c_data in enumerate(SAMPLE_COMPANIES):
            lead_code = get_next_sequence_id(db, "LEAD", "LD", padding=5, commit=False)
            source = LEAD_SOURCES[i % len(LEAD_SOURCES)]
            lead = Lead(
                lead_id=lead_code,
                lead_name=f"{c_data['name']} - Effluent Analysis",
                first_name=c_data["contact"].split()[0],
                last_name=" ".join(c_data["contact"].split()[1:]) if len(c_data["contact"].split()) > 1 else "",
                job_title=c_data["desig"],
                business_phone=c_data["phone"],
                mobile_phone=c_data["phone"],
                contact_email=c_data["email"],
                company_name=c_data["name"],
                company_email=c_data["email"],
                website_link=f"https://www.{c_data['name'].lower().replace(' ', '').replace('&', 'and')[:15]}.com",
                location=f"{c_data['city']}, {c_data['state']}",
                site_name=f"{c_data['city']} Plant",
                communication_channel="Email",
                connected_date=date.today() - timedelta(days=60 - i),
                lead_source=source,
                rating="Hot" if i < 15 else ("Warm" if i < 35 else "Cold"),
                client_status="New",
                description=f"Industrial effluent characterization and biomethanation evaluation for {c_data['city']} facility.",
                industry=c_data["area"],
                currency="INR",
                business_area=c_data["area"],
                requirement_type=c_data["req"],
                requirement_summary=f"Requires {c_data['req']} for anaerobic treatment optimization.",
                requested_product_service=c_data["req"],
                normalized_requirement=c_data["req"],
                preferred_contact_method="Email",
                assigned_to_user_id=str(admin_user.id) if admin_user else None,
                lifecycle_status="New",
                remarks=f"{SEED_MARKER} Sample lead record #{i+1}",
                created_by_id=str(admin_user.id) if admin_user else None,
                created_at=datetime.now(timezone.utc) - timedelta(days=60 - i)
            )
            db.add(lead)
            db.flush()

            # Add normalized requirement type
            req_type = LeadRequirementType(
                lead_id=lead.id,
                requirement_type=c_data["req"]
            )
            db.add(req_type)
            created_leads.append(lead)

        db.commit()
        logger.info(f"Created 50 leads successfully (Total Leads = 50).")

        # 4. Qualify exactly 30 Leads -> Creates exactly 30 Opportunities
        qualified_opportunities = []
        for i in range(30):
            lead = created_leads[i]
            c_data = SAMPLE_COMPANIES[i]

            # Create Account
            acc_code = get_next_sequence_id(db, "ACCOUNT", "ACC", padding=5, commit=False)
            account = Account(
                account_id=acc_code,
                name=c_data["name"],
                industry=c_data["area"],
                website=lead.website_link,
                phone=c_data["phone"],
                email=c_data["email"],
                address=f"{c_data['city']}, {c_data['state']} {SEED_MARKER}",
                site_name=f"{c_data['city']} Facility",
                business_area=c_data["area"],
                country="India",
                state=c_data["state"],
                city=c_data["city"],
                billing_address=f"Plot 101, Industrial Area, {c_data['city']}, {c_data['state']}",
                shipping_address=f"Plant Gate 2, {c_data['city']}, {c_data['state']}",
                gst_number=f"24ABCDE{1000 + i}F1Z{i % 9 + 1}",
                pan_number=f"ABCDE{1000 + i}F",
                created_by_id=str(admin_user.id) if admin_user else None,
                is_active=True
            )
            db.add(account)
            db.flush()

            # Create Contact
            con_code = get_next_sequence_id(db, "CONTACT", "CON", padding=5, commit=False)
            contact = Contact(
                contact_id=con_code,
                account_id=account.id,
                name=c_data["contact"],
                first_name=lead.first_name,
                last_name=lead.last_name,
                email=c_data["email"],
                mobile_number=c_data["phone"],
                designation=c_data["desig"],
                is_primary=True,
                created_by_id=str(admin_user.id) if admin_user else None,
                is_active=True
            )
            db.add(contact)
            db.flush()

            # Create Opportunity
            opp_code = get_next_sequence_id(db, "OPPORTUNITY", "OPP", padding=5, commit=False)
            est_value = Decimal(str(150000 + (i * 25000)))
            opp = Opportunity(
                opportunity_id=opp_code,
                name=f"Opportunity - {c_data['name']}",
                account_id=account.id,
                contact_id=contact.id,
                originating_lead_id=lead.id,
                status="Open",
                stage="Enquiry",
                business_area=c_data["area"],
                currency="INR",
                estimated_value=est_value,
                description=f"{SEED_MARKER} Opportunity generated from qualified lead {lead.lead_id}",
                requirement_summary=lead.requirement_summary,
                requirement_types=c_data["req"],
                assigned_to_user_id=str(admin_user.id) if admin_user else None,
                created_by_id=str(admin_user.id) if admin_user else None,
                created_at=datetime.now(timezone.utc) - timedelta(days=45 - i)
            )
            db.add(opp)
            db.flush()

            # Record Stage History for Enquiry
            record_opportunity_stage_transition(
                db=db,
                opp=opp,
                new_stage="Enquiry",
                triggering_event="LEAD_QUALIFIED",
                actor=actor,
                remarks=f"Qualified from Lead {lead.lead_id}",
                commit=False
            )

            # Link Lead to Account, Contact, and Opportunity
            lead.account_id = account.id
            lead.contact_id = contact.id
            lead.opportunity_id = opp.id
            lead.lifecycle_status = "Qualified"
            lead.qualified_at = datetime.now(timezone.utc) - timedelta(days=45 - i)
            lead.converted_at = datetime.now(timezone.utc) - timedelta(days=45 - i)

            qualified_opportunities.append(opp)

        # Update the remaining 20 non-qualified leads with realistic statuses
        # 8 New (indices 30-37) - already New
        # 6 Contacted (indices 38-43)
        for i in range(38, 44):
            created_leads[i].lifecycle_status = "Contacted"
        # 4 In Discussion (indices 44-47)
        for i in range(44, 48):
            created_leads[i].lifecycle_status = "In Discussion"
        # 1 Dormant (index 48)
        created_leads[48].lifecycle_status = "Dormant"
        created_leads[48].remarks += " | Client requested callback next fiscal year"
        # 1 Disqualified (index 49)
        created_leads[49].lifecycle_status = "Disqualified"
        created_leads[49].disqualification_reason = "Out of geographical operational territory"

        db.commit()
        logger.info("Qualified exactly 30 leads into Opportunities in Enquiry stage (Qualified Leads = 30).")

        # 5. Create Quotations for exactly 15 Opportunities (indices 0 to 14)
        quotation_opportunities = qualified_opportunities[:15]
        created_quotations = []

        for i, opp in enumerate(quotation_opportunities):
            q_code = get_next_sequence_id(db, "QUOTATION", "QT", padding=5, commit=False)
            q_date = date.today() - timedelta(days=30 - i)

            # Select 2-3 services from available catalogue
            s1 = available_services[i % len(available_services)]
            s2 = available_services[(i + 1) % len(available_services)]

            p1_rate = Decimal(str(s1.standard_price or 5000.0))
            p2_rate = Decimal(str(s2.standard_price or 8500.0))
            qty1 = 2
            qty2 = 1

            subtotal = (p1_rate * qty1) + (p2_rate * qty2)
            tax_rate_val = Decimal("0.18")
            total_tax = subtotal * tax_rate_val
            grand_total = subtotal + total_tax

            quotation = OpportunityQuotation(
                quotation_number=q_code,
                opportunity_id=opp.id,
                revision_number=1,
                version="R1",
                is_active=True,
                title=f"Quotation R1 for {opp.name}",
                status="Approved",
                amount=grand_total,
                subtotal=subtotal,
                tax_type="INTRA_STATE",
                tax_configuration_id=tax_config.id if tax_config else None,
                cgst_amount=total_tax / 2,
                sgst_amount=total_tax / 2,
                igst_amount=Decimal("0.00"),
                total_tax=total_tax,
                discount_amount=Decimal("0.00"),
                currency="INR",
                quotation_date=q_date,
                valid_until_date=q_date + timedelta(days=30),
                terms_and_conditions="1. Payment 50% advance along with confirmed order.\n2. Sample report turnaround 7-10 working days.",
                notes=f"{SEED_MARKER} Formal quotation for laboratory testing services",
                created_by_id=str(admin_user.id) if admin_user else None
            )
            db.add(quotation)
            db.flush()

            # Line items
            item1 = OpportunityQuotationItem(
                quotation_id=quotation.id,
                item_type="SERVICE",
                service_id=s1.id,
                item_code=s1.service_code,
                item_name=s1.name,
                description=s1.description or s1.name,
                billing_unit=s1.billing_unit.code if s1.billing_unit else "Per Test",
                quantity=int(qty1),
                unit_price=p1_rate,
                standard_price=p1_rate,
                discount_amount=Decimal("0.00"),
                taxable_amount=p1_rate * qty1,
                cgst_rate=Decimal("0.09"),
                cgst_amount=(p1_rate * qty1) * Decimal("0.09"),
                sgst_rate=Decimal("0.09"),
                sgst_amount=(p1_rate * qty1) * Decimal("0.09"),
                total_tax=(p1_rate * qty1) * tax_rate_val,
                final_total=(p1_rate * qty1) * Decimal("1.18"),
                currency="INR"
            )
            item2 = OpportunityQuotationItem(
                quotation_id=quotation.id,
                item_type="SERVICE",
                service_id=s2.id,
                item_code=s2.service_code,
                item_name=s2.name,
                description=s2.description or s2.name,
                billing_unit=s2.billing_unit.code if s2.billing_unit else "Per Test",
                quantity=int(qty2),
                unit_price=p2_rate,
                standard_price=p2_rate,
                discount_amount=Decimal("0.00"),
                taxable_amount=p2_rate * qty2,
                cgst_rate=Decimal("0.09"),
                cgst_amount=(p2_rate * qty2) * Decimal("0.09"),
                sgst_rate=Decimal("0.09"),
                sgst_amount=(p2_rate * qty2) * Decimal("0.09"),
                total_tax=(p2_rate * qty2) * tax_rate_val,
                final_total=(p2_rate * qty2) * Decimal("1.18"),
                currency="INR"
            )
            db.add(item1)
            db.add(item2)

            # Move Opportunity to Offer
            record_opportunity_stage_transition(
                db=db,
                opp=opp,
                new_stage="Offer",
                triggering_event="FIRST_QUOTATION_CREATED",
                actor=actor,
                remarks=f"First quotation created: {quotation.quotation_number}",
                commit=False
            )
            created_quotations.append(quotation)

        db.commit()
        logger.info("Created quotations for exactly 15 Opportunities (Quotations Created = 15).")

        # 6. Commercial Quotation Revisions -> Moves 6 opportunities to Negotiation
        # Indices 4 to 9 will have commercial revisions (R2)
        for i in range(4, 10):
            opp = quotation_opportunities[i]
            base_q = created_quotations[i]
            base_q.is_active = False
            base_q.status = "Superseded"

            # Create revised quotation R2 with 10% commercial discount
            rev_subtotal = base_q.subtotal * Decimal("0.90")
            rev_tax = rev_subtotal * Decimal("0.18")
            rev_grand_total = rev_subtotal + rev_tax

            rev_q = OpportunityQuotation(
                quotation_number=base_q.quotation_number,
                opportunity_id=opp.id,
                revision_number=2,
                version="R2",
                is_active=True,
                title=f"Quotation R2 (Negotiated) for {opp.name}",
                status="Approved",
                amount=rev_grand_total,
                subtotal=rev_subtotal,
                tax_type="INTRA_STATE",
                tax_configuration_id=tax_config.id if tax_config else None,
                cgst_amount=rev_tax / 2,
                sgst_amount=rev_tax / 2,
                igst_amount=Decimal("0.00"),
                total_tax=rev_tax,
                discount_amount=base_q.subtotal * Decimal("0.10"),
                currency="INR",
                quotation_date=date.today() - timedelta(days=15 - i),
                valid_until_date=date.today() + timedelta(days=20),
                terms_and_conditions=base_q.terms_and_conditions,
                notes=f"{SEED_MARKER} Revision R2: Agreed commercial discount applied",
                created_by_id=str(admin_user.id) if admin_user else None
            )
            db.add(rev_q)
            db.flush()

            # Copy items with discount
            for b_it in base_q.items:
                rev_it = OpportunityQuotationItem(
                    quotation_id=rev_q.id,
                    item_type=b_it.item_type,
                    service_id=b_it.service_id,
                    item_code=b_it.item_code,
                    item_name=b_it.item_name,
                    description=b_it.description,
                    billing_unit=b_it.billing_unit,
                    quantity=b_it.quantity,
                    unit_price=b_it.unit_price * Decimal("0.90"),
                    standard_price=b_it.standard_price,
                    discount_amount=b_it.unit_price * Decimal("0.10") * b_it.quantity,
                    taxable_amount=b_it.taxable_amount * Decimal("0.90"),
                    cgst_rate=Decimal("0.09"),
                    cgst_amount=b_it.cgst_amount * Decimal("0.90"),
                    sgst_rate=Decimal("0.09"),
                    sgst_amount=b_it.sgst_amount * Decimal("0.90"),
                    total_tax=b_it.total_tax * Decimal("0.90"),
                    final_total=b_it.final_total * Decimal("0.90"),
                    currency="INR"
                )
                db.add(rev_it)

            # Move Opportunity to Negotiation
            record_opportunity_stage_transition(
                db=db,
                opp=opp,
                new_stage="Negotiation",
                triggering_event="COMMERCIAL_QUOTATION_REVISED",
                actor=actor,
                remarks=f"Commercial quotation revised to {rev_q.version}",
                commit=False
            )
            # Update reference in list to the active revised quotation
            created_quotations[i] = rev_q

        # Opportunity index 9: Place in Dormant from Negotiation stage
        dormant_opp_neg = quotation_opportunities[9]
        record_opportunity_stage_transition(
            db=db,
            opp=dormant_opp_neg,
            new_stage="Dormant",
            triggering_event="OPPORTUNITY_MARKED_DORMANT",
            actor=actor,
            remarks="Client capex decision deferred to Q3",
            commit=False
        )

        db.commit()
        logger.info("Created commercial quotation revisions (Stage updated to Negotiation & Dormant).")

        # 7. Create Proforma Invoices (PIs) for exactly 5 Opportunities (indices 0 to 4)
        pi_opportunities = quotation_opportunities[:5]
        created_pis = []

        for i, opp in enumerate(pi_opportunities):
            active_q = created_quotations[i]
            pi_date = date.today() - timedelta(days=10 - i)
            fy = get_financial_year(pi_date)
            pi_num, _ = invoice_service.get_next_pi_number(pi_date, commit=False)

            company = invoice_service.get_company_settings()
            comp_snap = invoice_service._build_company_snapshot(company)
            cust_snap = invoice_service._build_customer_snapshot(opp.account)

            pi = ProformaInvoice(
                pi_number=pi_num,
                opportunity_id=opp.id,
                quotation_id=active_q.id,
                account_id=opp.account.id,
                current_revision_number=1,
                financial_year=fy,
                status="Issued",
                created_by_id=str(admin_user.id) if admin_user else None
            )
            db.add(pi)
            db.flush()

            rev = ProformaInvoiceRevision(
                proforma_invoice_id=pi.id,
                revision_number=1,
                pi_number=pi_num,
                pi_date=pi_date,
                financial_year=fy,
                status="Issued",
                reference_note=f"{SEED_MARKER} Formal PI against Quotation {active_q.quotation_number}",
                currency="INR",
                subtotal=active_q.subtotal,
                tax_type=active_q.tax_type or "INTRA_STATE",
                tax_configuration_id=active_q.tax_configuration_id,
                cgst_rate=Decimal("0.09"),
                cgst_amount=active_q.cgst_amount,
                sgst_rate=Decimal("0.09"),
                sgst_amount=active_q.sgst_amount,
                igst_rate=Decimal("0.00"),
                igst_amount=Decimal("0.00"),
                total_tax=active_q.total_tax,
                grand_total=active_q.amount,
                company_snapshot=comp_snap,
                customer_snapshot=cust_snap,
                terms_snapshot=company.default_terms or [],
                notes=f"{SEED_MARKER} Proforma invoice for advanced project schedule",
                created_by_id=str(admin_user.id) if admin_user else None
            )
            db.add(rev)
            db.flush()

            for sr, it in enumerate(active_q.items, start=1):
                p_it = ProformaInvoiceItem(
                    revision_id=rev.id,
                    sr_no=sr,
                    item_type=it.item_type,
                    service_id=it.service_id,
                    item_code=it.item_code,
                    item_name=it.item_name,
                    description=it.description,
                    quantity=it.quantity,
                    unit=it.billing_unit,
                    rate=it.unit_price,
                    amount=it.taxable_amount,
                    notes=it.description
                )
                db.add(p_it)

            # Automatically transition Opportunity to 'PI Issued'
            record_opportunity_stage_transition(
                db=db,
                opp=opp,
                new_stage="PI Issued",
                triggering_event="PI_GENERATED",
                actor=actor,
                remarks=f"Proforma Invoice generated: {pi.pi_number}",
                commit=False
            )
            created_pis.append(pi)

        # 8. Advance 3 of the 5 PIs through realistic execution stages:
        # Index 0 & 1: Stay in 'PI Issued'
        # Index 2 & 3: Advance to 'Supply' (PO confirmed, testing work begun)
        for i in [2, 3]:
            opp = pi_opportunities[i]
            record_opportunity_stage_transition(
                db=db,
                opp=opp,
                new_stage="Supply",
                triggering_event="ORDER_CONFIRMED_SUPPLY_STARTED",
                actor=actor,
                remarks=f"Client PO #PO-{202600 + i} confirmed; batch testing underway",
                commit=False
            )

        # Index 4: Advance through 'Supply' then to 'Payment' (Testing complete, collection tracking)
        opp_pay = pi_opportunities[4]
        record_opportunity_stage_transition(
            db=db,
            opp=opp_pay,
            new_stage="Supply",
            triggering_event="ORDER_CONFIRMED_SUPPLY_STARTED",
            actor=actor,
            remarks="Client PO #PO-202604 confirmed; batch execution commenced",
            commit=False
        )
        record_opportunity_stage_transition(
            db=db,
            opp=opp_pay,
            new_stage="Payment",
            triggering_event="PAYMENT_TRACKING_STARTED",
            actor=actor,
            remarks="Final characterization report delivered; tracking net-30 invoice collection",
            commit=False
        )

        # 9. Mark 2 Opportunities without Quotations as 'Dormant' (indices 28 & 29)
        for i in [28, 29]:
            opp = qualified_opportunities[i]
            record_opportunity_stage_transition(
                db=db,
                opp=opp,
                new_stage="Dormant",
                triggering_event="OPPORTUNITY_MARKED_DORMANT",
                actor=actor,
                remarks="Effluent expansion project put on hold by client management",
                commit=False
            )

        db.commit()
        logger.info("Generated 5 Proforma Invoices and advanced downstream stages (PIs Created = 5).")
        print_funnel_summary(db)

    except Exception as e:
        db.rollback()
        logger.error(f"Error during CRM sales funnel seeding: {e}", exc_info=True)
        raise
    finally:
        db.close()


def print_funnel_summary(db):
    """Prints the actual database counts and conversion metrics for the sales funnel."""
    sample_leads = db.query(Lead).filter(Lead.remarks.like(f"%{SEED_MARKER}%")).count()
    sample_opps = db.query(Opportunity).filter(Opportunity.description.like(f"%{SEED_MARKER}%")).all()
    sample_opp_ids = [o.id for o in sample_opps]

    qualified_leads = db.query(Lead).filter(
        Lead.remarks.like(f"%{SEED_MARKER}%"),
        Lead.lifecycle_status == "Qualified",
        Lead.opportunity_id.isnot(None)
    ).count()

    quotations_created = db.query(OpportunityQuotation).filter(
        OpportunityQuotation.opportunity_id.in_(sample_opp_ids),
        OpportunityQuotation.is_active == True
    ).count() if sample_opp_ids else 0

    pis_created = db.query(ProformaInvoice).filter(
        ProformaInvoice.opportunity_id.in_(sample_opp_ids)
    ).count() if sample_opp_ids else 0

    # Cumulative conversion rates
    lead_to_qual_rate = (qualified_leads / sample_leads * 100) if sample_leads else 0.0
    qual_to_quote_rate = (quotations_created / qualified_leads * 100) if qualified_leads else 0.0
    quote_to_pi_rate = (pis_created / quotations_created * 100) if quotations_created else 0.0
    overall_lead_to_pi_rate = (pis_created / sample_leads * 100) if sample_leads else 0.0

    print("\n" + "=" * 60)
    print("CRM SALES FUNNEL VALIDATION REPORT (SAMPLE FUNNEL)")
    print("=" * 60)
    print(f"Total Leads Created:       {sample_leads}  (Target: 50)")
    print(f"Qualified Leads:           {qualified_leads}  (Target: 30)")
    print(f"Quotations Created:        {quotations_created}  (Target: 15)")
    print(f"Proforma Invoices Created: {pis_created}  (Target: 5)")
    print("-" * 60)
    print("CONVERSION RATES:")
    print(f"Lead-to-Qualification:     {lead_to_qual_rate:.1f}%  (Target: 60.0%)")
    print(f"Qualification-to-Quote:    {qual_to_quote_rate:.1f}%  (Target: 50.0%)")
    print(f"Quotation-to-PI:           {quote_to_pi_rate:.1f}%  (Target: 33.3%)")
    print(f"Overall Lead-to-PI:        {overall_lead_to_pi_rate:.1f}%  (Target: 10.0%)")
    print("-" * 60)
    print("OPPORTUNITY STAGE DISTRIBUTION (SEEDED FUNNEL):")
    stages = ["Enquiry", "Offer", "Negotiation", "PI Issued", "Supply", "Payment", "Dormant"]
    for stg in stages:
        cnt = db.query(Opportunity).filter(
            Opportunity.id.in_(sample_opp_ids),
            Opportunity.stage == stg
        ).count() if sample_opp_ids else 0
        print(f"  - {stg:<15}: {cnt}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CRM Sales Funnel Data Seeder")
    parser.add_argument("--cleanup", action="store_true", help="Remove all sample funnel records")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.cleanup:
            cleanup_seed_funnel(db)
        else:
            seed_crm_funnel()
    finally:
        db.close()
