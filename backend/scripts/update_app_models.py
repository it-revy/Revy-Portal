import os

models_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "models.py")
with open(models_path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace("\r\n", "\n")
c = c.replace("Milestone\n)", "Milestone,\n    LeadNurturingProcess,\n    NurturingActivity\n)")
c = c.replace('"Milestone"\n]', '"Milestone",\n    "LeadNurturingProcess",\n    "NurturingActivity"\n]')

with open(models_path, "w", encoding="utf-8") as f:
    f.write(c)
print("Updated app/models.py successfully")

