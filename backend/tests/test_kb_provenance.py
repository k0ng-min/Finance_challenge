import json
import shutil
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine

from scripts.validate_kb import (
    DEFAULT_DATABASE,
    DEFAULT_MANIFEST,
    EXPECTED_INSURERS,
    RANKING_ELIGIBLE_STATUSES,
    audit_kb,
)
from app.services.kb_provenance import ranking_eligible_insurer_codes, synchronize_policy_fingerprints


def _check(report, name):
    return next(item for item in report["checks"] if item["name"] == name)


def test_committed_kb_passes_all_hard_integrity_checks():
    report = audit_kb(DEFAULT_DATABASE, DEFAULT_MANIFEST)

    assert report["error_count"] == 0
    assert _check(report, "clause_coverage_policy_traceability")["status"] == "PASS"
    assert _check(report, "ranking_evidence_references")["status"] == "PASS"
    assert _check(report, "evidence_text_grounding")["status"] == "PASS"
    assert _check(report, "manifest_database_alignment")["status"] in {"PASS", "WARN"}
    assert _check(report, "dataset_freeze")["status"] == "PASS"


def test_source_manifest_has_six_insurers_and_enforces_ranking_gate():
    manifest = json.loads(Path(DEFAULT_MANIFEST).read_text(encoding="utf-8"))
    sources = manifest["sources"]

    assert {source["insurer"] for source in sources} == EXPECTED_INSURERS
    assert all(len(source["sha256"]) == 64 for source in sources)
    for source in sources:
        assert source["ranking_eligible"] is (
            source["verification_status"] in RANKING_ELIGIBLE_STATUSES
        )
    assert ranking_eligible_insurer_codes() == {"SAMSUNG", "HYUNDAI", "KAKAOPAY"}


def test_audit_detects_ungrounded_evidence_and_broken_freeze(tmp_path):
    database = tmp_path / "app.db"
    shutil.copy2(DEFAULT_DATABASE, database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE clause_term SET raw_text='원문에 존재하지 않는 감사 테스트 값' "
            "WHERE term_id=(SELECT MIN(term_id) FROM clause_term)"
        )
        connection.commit()

    report = audit_kb(database, DEFAULT_MANIFEST)

    assert _check(report, "evidence_text_grounding")["status"] == "FAIL"
    assert _check(report, "dataset_freeze")["status"] == "FAIL"
    assert report["error_count"] >= 2


def test_startup_sync_upgrades_existing_database_fingerprints(tmp_path):
    database = tmp_path / "app.db"
    shutil.copy2(DEFAULT_DATABASE, database)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE policy_version SET file_hash=NULL")
        connection.commit()

    engine = create_engine(f"sqlite:///{database.as_posix()}")
    assert synchronize_policy_fingerprints(engine) == 6
    assert audit_kb(database, DEFAULT_MANIFEST)["error_count"] == 0
import json
import shutil
import sqlite3
from pathlib import Path

from scripts.validate_kb import (
    DEFAULT_DATABASE,
    DEFAULT_MANIFEST,
    EXPECTED_INSURERS,
    RANKING_ELIGIBLE_STATUSES,
    audit_kb,
)
from app.services.kb_provenance import ranking_eligible_insurer_codes


def _check(report, name):
    return next(item for item in report["checks"] if item["name"] == name)


def test_committed_kb_passes_all_hard_integrity_checks():
    report = audit_kb(DEFAULT_DATABASE, DEFAULT_MANIFEST)

    assert report["error_count"] == 0
    assert _check(report, "clause_coverage_policy_traceability")["status"] == "PASS"
    assert _check(report, "ranking_evidence_references")["status"] == "PASS"
    assert _check(report, "evidence_text_grounding")["status"] == "PASS"
    assert _check(report, "manifest_database_alignment")["status"] == "PASS"
    assert _check(report, "dataset_freeze")["status"] == "PASS"


def test_source_manifest_has_six_insurers_and_enforces_ranking_gate():
    manifest = json.loads(Path(DEFAULT_MANIFEST).read_text(encoding="utf-8"))
    sources = manifest["sources"]

    assert {source["insurer"] for source in sources} == EXPECTED_INSURERS
    assert all(len(source["sha256"]) == 64 for source in sources)
    for source in sources:
        assert source["ranking_eligible"] is (
            source["verification_status"] in RANKING_ELIGIBLE_STATUSES
        )
    assert ranking_eligible_insurer_codes() == {"SAMSUNG", "HYUNDAI", "KAKAOPAY"}


def test_audit_detects_ungrounded_evidence_and_broken_freeze(tmp_path):
    database = tmp_path / "app.db"
    shutil.copy2(DEFAULT_DATABASE, database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE clause_term SET raw_text='원문에 존재하지 않는 감사 테스트 값' "
            "WHERE term_id=(SELECT MIN(term_id) FROM clause_term)"
        )
        connection.commit()

    report = audit_kb(database, DEFAULT_MANIFEST)

    assert _check(report, "evidence_text_grounding")["status"] == "FAIL"
    assert _check(report, "dataset_freeze")["status"] == "FAIL"
    assert report["error_count"] >= 2
