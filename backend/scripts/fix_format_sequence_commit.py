import os

nurturing_svc_file = os.path.join(os.path.dirname(__file__), "..", "app", "crm", "nurturing_service.py")
with open(nurturing_svc_file, "r", encoding="utf-8") as f:
    code = f.read()

target = "code = get_next_sequence_id(db, entity_name, prefix, padding, commit=False)"
replacement = "code = get_next_sequence_id(db, entity_name, prefix, padding, commit=True)"

if target in code:
    code = code.replace(target, replacement)
    with open(nurturing_svc_file, "w", encoding="utf-8") as f:
        f.write(code)
    print("Updated format_sequence_id to commit=True successfully!")
else:
    print("Target not found in nurturing_service.py")

