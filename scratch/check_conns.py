import psutil

for pid in [21876, 20496, 17660, 20064, 34356]:
    try:
        p = psutil.Process(pid)
        print(f"Process {pid} ({p.name()}):")
        conns = p.connections()
        for c in conns:
            print(f"  {c.status}: {c.laddr}")
    except Exception as e:
        print(f"Error checking {pid}: {e}")
