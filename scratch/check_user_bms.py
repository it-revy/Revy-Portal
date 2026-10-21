import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

import app.models
from app.core.database import SessionLocal, init_db
from app.users.model import User
from app.modules.model import Module, UserModuleMembership
from app.core.dependencies import get_current_user, CurrentUser
from app.core.security import create_access_token
from unittest.mock import MagicMock

db = SessionLocal()

# Create a test user without any roles or memberships
u = User(
    name="Test User No BMS",
    username="test_no_bms",
    email="test_no_bms@example.com",
    password_hash="fakehash",
    status="active"
)
db.add(u)
db.commit()
db.refresh(u)

token = create_access_token({"username": u.username, "userId": u.id})

req = MagicMock()
req.state = MagicMock()
cu = get_current_user(request=req, authorization=f"Bearer {token}", x_role_used=None, db=db)

print("Roles:", cu.roles)
print("Modules:", cu.modules)
print("Active Role:", cu.active_role)
print("Permissions:", cu.permissions)
print("All Permissions:", cu.all_permissions)
print("Is Global Admin:", cu.is_global_admin)

# Check require_module_access("BMS")
from app.core.dependencies import require_module_access
dep = require_module_access("BMS")
try:
    dep(current_user=cu)
    print("require_module_access('BMS') PASSED (NO ERROR)")
except Exception as e:
    print(f"require_module_access('BMS') RAISED: {type(e).__name__}: {e}")

# Clean up
db.delete(u)
db.commit()
