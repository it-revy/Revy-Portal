import os

# 1. Update backend/app/core/database.py
db_file = os.path.join(os.path.dirname(__file__), "..", "app", "core", "database.py")
with open(db_file, "r", encoding="utf-8") as f:
    db_code = f.read()

target_db = """        test_engine = create_engine(test_url, connect_args={"check_same_thread": False, "timeout": 30})
        @event.listens_for(test_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
        return test_engine"""

repl_db = """        test_engine = create_engine(test_url, connect_args={"check_same_thread": False})
        return test_engine"""

db_code_norm = db_code.replace("\r\n", "\n")
target_db_norm = target_db.replace("\r\n", "\n")
repl_db_norm = repl_db.replace("\r\n", "\n")

if target_db_norm in db_code_norm:
    db_code_norm = db_code_norm.replace(target_db_norm, repl_db_norm, 1)
    if "\r\n" in db_code:
        db_code_norm = db_code_norm.replace("\n", "\r\n")
    with open(db_file, "w", encoding="utf-8") as f:
        f.write(db_code_norm)
    print("database.py reverted cleanly!")
else:
    print("target_db not found in database.py")

# 2. Update backend/app/crm/service.py to serialize lead creation on SQLite
svc_file = os.path.join(os.path.dirname(__file__), "..", "app", "crm", "service.py")
with open(svc_file, "r", encoding="utf-8") as f:
    svc_code = f.read()

target_lock_def = "_sequence_lock = threading.Lock()"
repl_lock_def = """_sequence_lock = threading.Lock()
_sqlite_write_lock = threading.Lock()"""

target_create_lead = """    def create_lead(
        self,
        actor: CurrentUser,
        payload: LeadCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:"""

repl_create_lead = """    def create_lead(
        self,
        actor: CurrentUser,
        payload: LeadCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        is_sqlite = bool(self.db.bind and "sqlite" in str(self.db.bind.url))
        if is_sqlite:
            with _sqlite_write_lock:
                return self._create_lead_impl(actor, payload, request)
        return self._create_lead_impl(actor, payload, request)

    def _create_lead_impl(
        self,
        actor: CurrentUser,
        payload: LeadCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:"""

svc_code_norm = svc_code.replace("\r\n", "\n")
target_lock_norm = target_lock_def.replace("\r\n", "\n")
repl_lock_norm = repl_lock_def.replace("\r\n", "\n")

target_create_norm = target_create_lead.replace("\r\n", "\n")
repl_create_norm = repl_create_lead.replace("\r\n", "\n")

if target_lock_norm in svc_code_norm:
    svc_code_norm = svc_code_norm.replace(target_lock_norm, repl_lock_norm, 1)
    print("Added _sqlite_write_lock!")

if target_create_norm in svc_code_norm:
    svc_code_norm = svc_code_norm.replace(target_create_norm, repl_create_norm, 1)
    print("Added SQLite write serialization to create_lead!")

if "\r\n" in svc_code:
    svc_code_norm = svc_code_norm.replace("\n", "\r\n")

with open(svc_file, "w", encoding="utf-8") as f:
    f.write(svc_code_norm)
print("service.py updated successfully!")

