import subprocess
import psutil

print("--- Listening Ports ---")
for conn in psutil.net_connections():
    if conn.status == 'LISTEN':
        print(f"Port {conn.laddr.port} (PID: {conn.pid})")

print("\n--- Processes (node & python) ---")
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        name = p.info['name'].lower()
        if 'node' in name or 'python' in name:
            print(f"PID {p.info['pid']} ({p.info['name']}): {' '.join(p.info['cmdline'] or [])}")
    except Exception:
        pass
