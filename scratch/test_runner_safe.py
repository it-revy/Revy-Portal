import os
import sys
import shutil
import subprocess

backend_dir = os.path.abspath("backend")
test_db_path = os.path.join(backend_dir, "test_isolated_suite.db")

# Ensure test db is clean
if os.path.exists(test_db_path):
    os.remove(test_db_path)

env = os.environ.copy()
env["TESTING"] = "1"
env["DATABASE_URL"] = f"sqlite:///{test_db_path.replace(chr(92), '/')}"
env["RUN_SEED"] = "1"

test_args = sys.argv[1:] if len(sys.argv) > 1 else ["tests", "--ignore=tests/verify_neon_full.py"]

print(f"Running safe test suite for '{test_args}' against: {env['DATABASE_URL']}")

cmd = [
    os.path.abspath(".venv/Scripts/python.exe"),
    "-m", "pytest"
] + test_args + ["-v"]

res = subprocess.run(cmd, cwd=backend_dir, env=env, capture_output=True, text=True)
print("Exit code:", res.returncode)
print("STDOUT:\n", res.stdout)
if res.stderr:
    print("STDERR:\n", res.stderr)

# Clean up
if os.path.exists(test_db_path):
    os.remove(test_db_path)
    print("Cleaned up test db")
