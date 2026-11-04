import os

svc_file = os.path.join(os.path.dirname(__file__), "..", "app", "crm", "service.py")
with open(svc_file, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update get_next_sequence_id rollback on lock
target_seq = """        except (OperationalError, Exception) as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(0.05 * (attempt + 1))
                continue
            raise"""

repl_seq = """        except (OperationalError, Exception) as e:
            try:
                db.rollback()
            except Exception:
                pass
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(0.05 * (attempt + 1))
                continue
            raise"""

# 2. Update create_lead to handle OperationalError locks
target_lead = """            except IntegrityError as e:
                self.db.rollback()
                err_str = str(e).lower()
                if "lead_id" in err_str or "leads.lead_id" in err_str:
                    logger.warning(f"Sequence collision on {lead_code}, retrying ({attempt+1}/5)...")
                    continue
                logger.error(f"IntegrityError creating lead: {e}")
                raise ValidationError("Could not save lead due to a database integrity constraint.")"""

repl_lead = """            except IntegrityError as e:
                self.db.rollback()
                err_str = str(e).lower()
                if "lead_id" in err_str or "leads.lead_id" in err_str:
                    logger.warning(f"Sequence collision on {lead_code}, retrying ({attempt+1}/5)...")
                    continue
                logger.error(f"IntegrityError creating lead: {e}")
                raise ValidationError("Could not save lead due to a database integrity constraint.")
            except OperationalError as e:
                self.db.rollback()
                if "locked" in str(e).lower() and attempt < 4:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                raise"""

# 3. Update nurturing initialization with lock retry
target_nurture = """        lead_ref_code = getattr(lead, "lead_id", str(lead_id if "lead_id" in locals() else ""))
            logger.error(f"Failed to auto-initialize nurturing for lead {lead_ref_code}: {nurture_err}")"""

# Let's inspect the entire try block for nurturing initialization
code_norm = code.replace("\r\n", "\n")
target_seq_norm = target_seq.replace("\r\n", "\n")
repl_seq_norm = repl_seq.replace("\r\n", "\n")

target_lead_norm = target_lead.replace("\r\n", "\n")
repl_lead_norm = repl_lead.replace("\r\n", "\n")

if target_seq_norm in code_norm:
    code_norm = code_norm.replace(target_seq_norm, repl_seq_norm, 1)
    print("get_next_sequence_id updated with rollback!")

if target_lead_norm in code_norm:
    code_norm = code_norm.replace(target_lead_norm, repl_lead_norm, 1)
    print("create_lead updated with OperationalError retry!")

# Now update nurturing block in create_lead
target_nurture_block = """        # Automatic Lead Nurturing Initialization (Mandatory requirement)
        try:
            from app.crm.nurturing_service import LeadNurturingService
            nurturing_svc = LeadNurturingService(self.db, self.audit_service)
            nurturing_svc.initialize_lead_nurturing(
                lead=lead,
                actor_id=str(actor.id) if actor.id else None,
                commit=True
            )
        except Exception as nurture_err:
            lead_ref_code = getattr(lead, "lead_id", str(lead_id if "lead_id" in locals() else ""))
            logger.error(f"Failed to auto-initialize nurturing for lead {lead_ref_code}: {nurture_err}")"""

repl_nurture_block = """        # Automatic Lead Nurturing Initialization (Mandatory requirement)
        lead_ref_code = getattr(lead, "lead_id", "")
        for n_attempt in range(5):
            try:
                from app.crm.nurturing_service import LeadNurturingService
                nurturing_svc = LeadNurturingService(self.db, self.audit_service)
                nurturing_svc.initialize_lead_nurturing(
                    lead=lead,
                    actor_id=str(actor.id) if actor.id else None,
                    commit=True
                )
                break
            except OperationalError as e:
                try:
                    self.db.rollback()
                except Exception:
                    pass
                if "locked" in str(e).lower() and n_attempt < 4:
                    time.sleep(0.05 * (n_attempt + 1))
                    continue
                logger.error(f"Failed to auto-initialize nurturing for lead {lead_ref_code}: {e}")
                break
            except Exception as nurture_err:
                try:
                    self.db.rollback()
                except Exception:
                    pass
                logger.error(f"Failed to auto-initialize nurturing for lead {lead_ref_code}: {nurture_err}")
                break"""

if target_nurture_block in code_norm:
    code_norm = code_norm.replace(target_nurture_block, repl_nurture_block, 1)
    print("nurturing block updated with OperationalError retry!")

if "\r\n" in code:
    code_norm = code_norm.replace("\n", "\r\n")

with open(svc_file, "w", encoding="utf-8") as f:
    f.write(code_norm)
print("service.py fully updated successfully!")

