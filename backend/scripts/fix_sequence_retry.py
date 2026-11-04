import os

svc_file = os.path.join(os.path.dirname(__file__), "..", "app", "crm", "service.py")
with open(svc_file, "r", encoding="utf-8") as f:
    code = f.read()

target = """def get_next_sequence_id(db: Session, entity_name: str, prefix: str, padding: int = 5, commit: bool = True) -> str:
    \"\"\"
    Concurrency-safe sequence generator using CrmSequence with thread locking and row locking.
    Generates IDs like LEAD-00001, ACC-00001, CON-00001, COM-00001, ENG-00001, SMP-00001, TST-00001, CHG-00001, PRD-00001.
    If commit=False, flushes instead of committing to preserve outer transaction atomicity.
    \"\"\"
    entity_key = entity_name.strip().upper()
    with _sequence_lock:
        seq = db.query(CrmSequence).filter(CrmSequence.entity_name == entity_key).with_for_update().first()
        if not seq:
            try:
                seq = CrmSequence(entity_name=entity_key, current_value=1)
                db.add(seq)
                if commit:
                    db.commit()
                else:
                    db.flush()
                return f"{prefix}-{1:0{padding}d}"
            except IntegrityError:
                db.rollback()
                seq = db.query(CrmSequence).filter(CrmSequence.entity_name == entity_key).with_for_update().first()

        seq.current_value += 1
        if commit:
            db.commit()
        else:
            db.flush()
        return f"{prefix}-{seq.current_value:0{padding}d}\""""

replacement = """def get_next_sequence_id(db: Session, entity_name: str, prefix: str, padding: int = 5, commit: bool = True) -> str:
    \"\"\"
    Concurrency-safe sequence generator using CrmSequence with thread locking and row locking.
    Generates IDs like LEAD-00001, ACC-00001, CON-00001, COM-00001, ENG-00001, SMP-00001, TST-00001, CHG-00001, PRD-00001.
    If commit=False, flushes instead of committing to preserve outer transaction atomicity.
    Includes concurrency lock retries for SQLite test environments.
    \"\"\"
    entity_key = entity_name.strip().upper()
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with _sequence_lock:
                seq = db.query(CrmSequence).filter(CrmSequence.entity_name == entity_key).with_for_update().first()
                if not seq:
                    try:
                        seq = CrmSequence(entity_name=entity_key, current_value=1)
                        db.add(seq)
                        if commit:
                            db.commit()
                        else:
                            db.flush()
                        return f"{prefix}-{1:0{padding}d}"
                    except IntegrityError:
                        db.rollback()
                        seq = db.query(CrmSequence).filter(CrmSequence.entity_name == entity_key).with_for_update().first()

                seq.current_value += 1
                if commit:
                    db.commit()
                else:
                    db.flush()
                return f"{prefix}-{seq.current_value:0{padding}d}"
        except (OperationalError, Exception) as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(0.05 * (attempt + 1))
                continue
            raise"""

# Handle CRLF vs LF
code_normalized = code.replace("\r\n", "\n")
target_normalized = target.replace("\r\n", "\n")
replacement_normalized = replacement.replace("\r\n", "\n")

if target_normalized in code_normalized:
    new_code = code_normalized.replace(target_normalized, replacement_normalized, 1)
    # preserve CRLF if original had it
    if "\r\n" in code:
        new_code = new_code.replace("\n", "\r\n")
    with open(svc_file, "w", encoding="utf-8") as f:
        f.write(new_code)
    print("Updated get_next_sequence_id in service.py successfully!")
else:
    print("Target normalized not found in service.py")
