"""Runtime access to audited KB provenance metadata."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text


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


def synchronize_policy_fingerprints(engine, path: Path = MANIFEST_PATH) -> int:
    """Idempotently persist manifest PDF hashes in an existing SQLite DB.

    The repository contains a long-lived SQLite file, so changing seed scripts
    alone does not update deployments created from an older database.  Startup
    calls this migration after table creation and before serving requests.
    """
    manifest = load_dataset_manifest(path)
    updated = 0
    with engine.begin() as connection:
        for source in manifest.get("sources", []):
            result = connection.execute(
                text(
                    """UPDATE policy_version
                          SET file_hash = :sha256
                        WHERE product_id IN (
                              SELECT p.product_id FROM product p
                              JOIN insurer i ON i.insurer_id = p.insurer_id
                              WHERE i.code = :insurer
                        )
                          AND (file_hash IS NULL OR file_hash <> :sha256)"""
                ),
                {"sha256": source["sha256"], "insurer": source["insurer"]},
            )
            updated += result.rowcount or 0
    return updated
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
