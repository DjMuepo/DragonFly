from pathlib import Path

root = Path(__file__).resolve().parents[1]
phase = root / "PHASE_STATUS.md"
docs = [
    root / "deployment" / "DEPLOY_CHECKLIST.md",
    root / "qa" / "BETA_SMOKE_TEST_PLAN.md",
    root / "qa" / "BETA_HARDENING_CHECKLIST.md",
    root / "api" / "CLOUD_DB_AND_WORKER_PLAN.md",
]

print("Beta Readiness Summary")
print("======================")
print(f"Phase status file present: {phase.exists()}")
for d in docs:
    print(f"{d.relative_to(root)} present: {d.exists()}")
