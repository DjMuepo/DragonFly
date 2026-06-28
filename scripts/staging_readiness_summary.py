from pathlib import Path

root = Path(__file__).resolve().parents[1]
checks = [
    root / "qa" / "BETA_SMOKE_TEST_PLAN.md",
    root / "qa" / "BETA_HARDENING_CHECKLIST.md",
    root / "qa" / "STAGING_VERIFICATION_PASS.md",
    root / "qa" / "GO_NO_GO_TEMPLATE.md",
    root / "deployment" / "DEPLOY_CHECKLIST.md",
    root / "BETA_RELEASE_NOTES.md",
]

print("Staging Readiness Summary")
print("=========================")
for item in checks:
    print(f"{item.relative_to(root)}: {'present' if item.exists() else 'missing'}")
