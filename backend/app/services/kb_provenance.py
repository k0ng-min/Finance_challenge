"""Runtime access to audited KB provenance metadata."""

from __future__ import annotations

import json
from pathlib import Path


MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "dataset_manifest.json"
RANKING_ELIGIBLE_STATUSES = {"VERIFIED_CURRENT", "VERIFIED_VERSIONED"}


def load_dataset_manifest(path: Path = MANIFEST_PATH) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        # Ranking must fail closed: silently using unverified data would defeat
        # the provenance gate this manifest provides.
        raise RuntimeError(f"KB provenance manifest is unavailable or invalid: {path}") from exc


def ranking_eligible_insurer_codes(path: Path = MANIFEST_PATH) -> set[str]:
    manifest = load_dataset_manifest(path)
    eligible: set[str] = set()
    for source in manifest.get("sources", []):
        status_allows = source.get("verification_status") in RANKING_ELIGIBLE_STATUSES
        explicitly_allowed = source.get("ranking_eligible") is True
        if status_allows and explicitly_allowed:
            eligible.add(source["insurer"])
    return eligible
