import os

service_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "crm", "service.py")
with open(service_path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace("\r\n", "\n")

# 1. create_lead hook
target_1 = """        except Exception as audit_err:
            logger.warning(f"Audit log failed for lead {lead.lead_id}: {audit_err}")

        return self.get_lead(actor, lead.id)"""

replacement_1 = """        except Exception as audit_err:
            logger.warning(f"Audit log failed for lead {lead.lead_id}: {audit_err}")

        # Automatic Lead Nurturing Initialization (Mandatory requirement)
        try:
            from app.crm.nurturing_service import LeadNurturingService
            nurturing_svc = LeadNurturingService(self.db, self.audit_service)
            nurturing_svc.initialize_lead_nurturing(
                lead=lead,
                actor_id=str(actor.id) if actor.id else None,
                commit=True
            )
        except Exception as nurture_err:
            logger.error(f"Failed to auto-initialize nurturing for lead {lead.lead_id}: {nurture_err}")

        return self.get_lead(actor, lead.id)"""

assert target_1 in c, "target_1 not found!"
c = c.replace(target_1, replacement_1)

# 2. update_lead hook
target_2 = """        if "connectedDate" in payload.model_fields_set:
            lead.connected_date = payload.connectedDate"""

replacement_2 = """        if "connectedDate" in payload.model_fields_set:
            lead.connected_date = payload.connectedDate
            try:
                from app.crm.nurturing_service import LeadNurturingService
                nurturing_svc = LeadNurturingService(self.db, self.audit_service)
                nurturing_svc.recalculate_on_connected_date_change(
                    lead=lead,
                    new_connected_date=payload.connectedDate,
                    actor_id=str(actor.id) if actor.id else None
                )
            except Exception as nurture_calc_err:
                logger.warning(f"Failed to recalculate nurturing schedule: {nurture_calc_err}")"""

assert target_2 in c, "target_2 not found!"
c = c.replace(target_2, replacement_2)

# 3. transition_lead_status hook
target_3 = """        lead.lifecycle_status = clean_status
        if remarks:
            lead.remarks = remarks.strip()
        lead.updated_by_id = str(actor.id) if actor.id else None"""

replacement_3 = """        lead.lifecycle_status = clean_status
        if remarks:
            lead.remarks = remarks.strip()
        lead.updated_by_id = str(actor.id) if actor.id else None

        # Record Lead Status Change interaction for unified timeline
        try:
            comm_code = get_next_sequence_id(self.db, "COMMUNICATION", "COM", commit=False)
            status_comm = LeadCommunicationHistory(
                communication_id=comm_code,
                lead_id=lead.id,
                communication_date=datetime.now(timezone.utc),
                channel="Other",
                event_type=f"Lead Status: {clean_status}",
                subject=f"Status changed from {before_status} to {clean_status}",
                summary=remarks.strip() if remarks else f"Lead business status transitioned from {before_status} to {clean_status}.",
                outcome=clean_status,
                interaction_source="Lead Status Change",
                created_by_id=str(actor.id) if actor.id else None,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(status_comm)
        except Exception as comm_err:
            logger.warning(f"Could not log status transition interaction: {comm_err}")"""

assert target_3 in c, "target_3 not found!"
c = c.replace(target_3, replacement_3)

# 4. create_communication hook
target_4 = """        comm = LeadCommunicationHistory(
            communication_id=comm_code,
            lead_id=lead.id,
            communication_date=comm_date,
            channel=payload.channel,
            event_type=payload.eventType,
            summary=payload.summary.strip() if payload.summary else None,
            outcome=payload.outcome.strip() if payload.outcome else None,
            next_action=payload.nextAction.strip() if payload.nextAction else None,
            follow_up_date=payload.followUpDate,
            created_by_id=str(actor.id) if actor.id else None
        )"""

replacement_4 = """        comm = LeadCommunicationHistory(
            communication_id=comm_code,
            lead_id=lead.id,
            communication_date=comm_date,
            channel=payload.channel,
            event_type=payload.eventType,
            subject=payload.eventType,
            summary=payload.summary.strip() if payload.summary else None,
            outcome=payload.outcome.strip() if payload.outcome else None,
            next_action=payload.nextAction.strip() if payload.nextAction else None,
            follow_up_date=payload.followUpDate,
            interaction_source="Manual",
            created_by_id=str(actor.id) if actor.id else None,
            created_at=datetime.now(timezone.utc)
        )"""

assert target_4 in c, "target_4 not found!"
c = c.replace(target_4, replacement_4)

with open(service_path, "w", encoding="utf-8") as f:
    f.write(c)

print("Updated app/crm/service.py successfully")

