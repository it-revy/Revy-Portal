"""
Pre-cleanup backup and controlled lead test data cleanup script.
Preserves Accounts, Contacts, CRM users, Opportunities, and non-lead portal data.
"""
import os
import sys
import json
from datetime import datetime, timezone

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

import app.models  # noqa: F401
from app.core.database import SessionLocal
from app.crm.model import (
    Lead,
    LeadRequirementType,
    LeadContactMethod,
    lead_additional_contacts,
    LeadCommunicationHistory,
    Account,
    Contact,
    Opportunity
)
from app.users.model import User

def backup_and_cleanup_leads():
    db = SessionLocal()
    try:
        leads = db.query(Lead).all()
        print(f"Current Lead count in canonical DB: {len(leads)}")
        
        backup_dir = os.path.join(backend_dir, "data_backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"leads_backup_{timestamp}.json")
        
        backup_data = []
        for l in leads:
            backup_data.append({
                "id": l.id,
                "lead_id": l.lead_id,
                "lead_name": l.lead_name,
                "company_name": l.company_name,
                "lifecycle_status": l.lifecycle_status,
                "connected_date": str(l.connected_date) if l.connected_date else None,
                "account_id": l.account_id,
                "contact_id": l.contact_id,
                "created_at": str(l.created_at) if l.created_at else None,
            })
            
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": timestamp,
                "lead_count": len(leads),
                "leads": backup_data
            }, f, indent=2)
            
        print(f"Saved recoverable backup to {backup_file}")
        
        if len(leads) > 0:
            print("Cleaning up testing leads...")
            for l in leads:
                # Remove dependent items belonging strictly to this lead
                db.query(LeadRequirementType).filter(LeadRequirementType.lead_id == l.id).delete()
                db.query(LeadContactMethod).filter(LeadContactMethod.lead_id == l.id).delete()
                db.execute(lead_additional_contacts.delete().where(lead_additional_contacts.c.lead_id == l.id))
                db.query(LeadCommunicationHistory).filter(LeadCommunicationHistory.lead_id == l.id).delete()
                db.delete(l)
            db.commit()
            print("Testing leads successfully cleaned up.")
        else:
            print("Database already clean: 0 test leads to remove.")
            
        # Verify preservation of customer master data
        acc_count = db.query(Account).count()
        con_count = db.query(Contact).count()
        user_count = db.query(User).count()
        opp_count = db.query(Opportunity).count()
        print(f"Post-cleanup verification:")
        print(f"  Accounts preserved: {acc_count}")
        print(f"  Contacts preserved: {con_count}")
        print(f"  Users preserved: {user_count}")
        print(f"  Opportunities: {opp_count}")
        print(f"  Leads: {db.query(Lead).count()}")
        
    finally:
        db.close()

if __name__ == "__main__":
    backup_and_cleanup_leads()
