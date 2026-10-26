import sys
backend_dir = r"e:\IT Development\REVY Portal\Revy-Portal\backend"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import get_engine
from sqlalchemy import text
from app.core.security import create_access_token

engine = get_engine()
with engine.connect() as conn:
    users = conn.execute(text("SELECT id, username, email, name, status FROM users LIMIT 10;")).fetchall()
    print(f"Users found in DB: {len(users)}")
    for u in users:
        print(f"  User: id={u[0]}, username={u[1]}, email={u[2]}, name={u[3]}, status={u[4]}")
        
    roles = conn.execute(text("SELECT id, name, code FROM roles;")).fetchall()
    print(f"\nRoles found: {len(roles)}")
    for r in roles:
        print(f"  Role: id={r[0]}, name={r[1]}, code={r[2]}")

    # Check user_roles
    user_roles = conn.execute(text("SELECT u.username, r.code FROM user_roles ur JOIN users u ON ur.user_id = u.id JOIN roles r ON ur.role_id = r.id;")).fetchall()
    print(f"\nUser roles count: {len(user_roles)}")
    for ur in user_roles[:10]:
        print(f"  {ur[0]} -> {ur[1]}")
