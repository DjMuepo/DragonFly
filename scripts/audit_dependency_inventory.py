from __future__ import annotations

import argparse
import importlib.metadata
import json
from datetime import datetime, timezone
from pathlib import Path


def inventory(root: Path) -> dict:
    manifests = []
    for relative in ("eye-expo/package.json", "web-landing/package.json", "eye-platform-alpha-geometry-backend/eye-expo/package.json"):
        manifest = json.loads((root / relative).read_text(encoding="utf-8"))
        manifests.append({"path": relative, "dependencies": manifest.get("dependencies", {}), "development_dependencies": manifest.get("devDependencies", {}), "purpose": "Active Expo frontend" if relative == "eye-expo/package.json" else "Separate landing page or legacy duplicate frontend; not the current Render frontend"})
    lock = json.loads((root / "eye-expo/package-lock.json").read_text(encoding="utf-8"))
    packages = []
    for path, package in lock["packages"].items():
        packages.append({
            "path": path or "<root>", "version": package.get("version"),
            "declared_license": package.get("license", "UNVERIFIED"), "integrity": package.get("integrity"),
            "development": package.get("dev", False), "optional": package.get("optional", False),
            "purpose": "Root project" if not path else "Direct/transitive build or runtime dependency; per-package call-path use UNVERIFIED",
            "commercial_restrictions": "Apply exact upstream license/NOTICE and bundled-asset terms; binary/source compliance UNVERIFIED",
            "external_fees": "No package-use fee identified in manifest; commercial services or embedded asset fees UNVERIFIED",
            "independent_alternative": "Pin and mirror reviewed package/artifacts on owner infrastructure; replace noncompliant components",
        })
    python_packages = []
    for distribution in sorted(importlib.metadata.distributions(), key=lambda item: item.metadata.get("Name", "").lower()):
        metadata = distribution.metadata
        declared = metadata.get("License-Expression") or metadata.get("License") or "; ".join(value for value in metadata.get_all("Classifier", []) if "License ::" in value) or "UNVERIFIED"
        python_packages.append({"name": metadata.get("Name"), "version": distribution.version, "declared_license": declared,
                                "purpose": "Installed distribution in audit interpreter; presence is not proof of production use",
                                "commercial_restrictions": "Exact bundled-license and model-weight review remains separate",
                                "external_fees": "No inference or service fee incurred by this inventory",
                                "independent_alternative": "Owner-controlled pinned wheel/source mirror after compliance review"})
    requirement_files = {}
    for relative in ("api/requirements.txt", "eye-platform-alpha-geometry-backend/geometry-backend/requirements.txt", "eye-platform-alpha-geometry-backend/geometry-backend/requirements-ai.txt"):
        requirement_files[relative] = [line.strip() for line in (root / relative).read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "network_requests": 0,
            "evidence_scope": "Declared package metadata, not a complete legal opinion or model-weight SBOM. Interpreter packages differ from production Docker; unpinned dependencies remain unresolved.",
            "manifests": manifests, "requirements": requirement_files, "javascript_lock_packages": packages, "installed_python_distributions": python_packages}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a no-network metadata-only dependency inventory; does not install or execute models.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"javascript_entries": len(result["javascript_lock_packages"]), "python_distributions": len(result["installed_python_distributions"]), "network_requests": 0, "output": str(args.output)}))


if __name__ == "__main__":
    main()