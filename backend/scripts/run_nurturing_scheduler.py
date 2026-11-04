"""
REVY CRM - Lead Nurturing Background Scheduler
Maintains due and overdue activities, schedules follow-ups in Asia/Kolkata timezone,
and respects paused/cancelled workflows.
"""
import os
import sys
import time
import argparse
import logging
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

import app.models  # noqa: F401
from app.core.database import SessionLocal
from app.crm.model import Lead, LeadNurturingProcess, NurturingActivity
from app.crm.nurturing_service import KOLKATA_TZ, get_current_kolkata_date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [revy.crm.scheduler]: %(message)s"
)
logger = logging.getLogger("revy.crm.scheduler")


def run_scheduler_pass() -> dict:
    """
    Execute one scheduling check pass:
    - Finds all active nurturing processes.
    - Evaluates pending activities against current Asia/Kolkata date.
    - Flags due and overdue activities without prematurely completing them.
    - Safe to rerun (idempotent).
    """
    db = SessionLocal()
    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_processes_scanned": 0,
        "due_today_count": 0,
        "overdue_count": 0,
        "errors": 0
    }

    try:
        today_date = get_current_kolkata_date()
        logger.info(f"Starting nurturing scheduler check for date: {today_date} (Asia/Kolkata)")

        # 1. Fetch active nurturing processes only (respecting paused/completed/cancelled)
        active_processes = db.query(LeadNurturingProcess).filter(
            LeadNurturingProcess.nurturing_status == "Active"
        ).all()

        metrics["active_processes_scanned"] = len(active_processes)

        for proc in active_processes:
            try:
                # Find pending activities for this process
                pending_activities = db.query(NurturingActivity).filter(
                    NurturingActivity.nurturing_id == proc.id,
                    NurturingActivity.activity_status.in_(["Pending", "In Progress", "Overdue"])
                ).all()

                for act in pending_activities:
                    if not act.due_date:
                        continue

                    if act.due_date == today_date:
                        metrics["due_today_count"] += 1
                        logger.info(f"Activity {act.activity_id} (Lead {proc.lead_id}, Stage {act.stage_number}: {act.subject}) is DUE TODAY.")
                    elif act.due_date < today_date:
                        metrics["overdue_count"] += 1
                        days_overdue = (today_date - act.due_date).days
                        # Keep status marked as Overdue in DB if desired, but without changing completion state
                        if act.activity_status != "Overdue":
                            act.activity_status = "Overdue"
                        logger.info(f"Activity {act.activity_id} (Lead {proc.lead_id}, Stage {act.stage_number}) is OVERDUE by {days_overdue} days.")

                # Keep lead next_follow_up_date aligned with the next actionable due date
                lead = db.query(Lead).filter(Lead.id == proc.lead_id).first()
                if lead and proc.next_activity_date:
                    lead.next_follow_up_date = proc.next_activity_date

            except Exception as item_err:
                metrics["errors"] += 1
                logger.error(f"Error processing nurturing process {proc.id}: {item_err}")

        db.commit()
        logger.info(
            f"Scheduler pass completed. Scanned: {metrics['active_processes_scanned']} processes | "
            f"Due today: {metrics['due_today_count']} | Overdue: {metrics['overdue_count']} | "
            f"Errors: {metrics['errors']}"
        )

    except Exception as e:
        db.rollback()
        metrics["errors"] += 1
        logger.error(f"Scheduler pass failed: {e}")
    finally:
        db.close()

    return metrics


def main():
    parser = argparse.ArgumentParser(description="REVY CRM Lead Nurturing Scheduler")
    parser.add_argument("--run-once", action="store_true", help="Run a single scheduling pass and exit")
    parser.add_argument("--interval", type=int, default=300, help="Interval in seconds between passes (default: 300s)")
    args = parser.parse_args()

    if args.run_once:
        run_scheduler_pass()
        return

    logger.info(f"Starting Lead Nurturing Scheduler daemon (interval: {args.interval}s)...")
    try:
        while True:
            run_scheduler_pass()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Scheduler daemon stopped by user.")


if __name__ == "__main__":
    main()

