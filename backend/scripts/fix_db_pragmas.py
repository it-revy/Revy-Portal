import os

db_file = os.path.join(os.path.dirname(__file__), "..", "app", "core", "database.py")
with open(db_file, "r", encoding="utf-8") as f:
    code = f.read()

target = """        @event.listens_for(test_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()"""

replacement = """        @event.listens_for(test_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()"""

code_normalized = code.replace("\r\n", "\n")
target_normalized = target.replace("\r\n", "\n")
replacement_normalized = replacement.replace("\r\n", "\n")

if target_normalized in code_normalized:
    new_code = code_normalized.replace(target_normalized, replacement_normalized, 1)
    if "\r\n" in code:
        new_code = new_code.replace("\n", "\r\n")
    with open(db_file, "w", encoding="utf-8") as f:
        f.write(new_code)
    print("Fixed database.py pragmas successfully!")
else:
    print("Target not found in database.py")

