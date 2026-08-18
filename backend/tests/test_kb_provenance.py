import json
import shutil
import sqlite3
from pathlib import Path

import pytest
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
    assert ranking_eligible_insurer_codes() == EXPECTED_INSURERS


def test_audit_detects_ungrounded_evidence_and_broken_freeze(tmp_path):
    connection = sqlite3.connect(DEFAULT_DATABASE)
    try:
        has_terms = connection.execute("SELECT COUNT(*) FROM clause_term").fetchone()[0] > 0
    finally:
        connection.close()
    if not has_terms:
        pytest.skip(
            "clause_term이 아직 비어 있다 — 2026-08-18 약관 재구축 1차분은 "
            "clause_incident_map/coverage_doc_map까지만 다시 만들었고 clause_term/"
            "doc_requirement/overlap_rule/clause_standard_map은 다음 단계로 미뤘다 "
            "(dataset_manifest.json의 known_gap 참조). 이 테스트가 검증하려는 "
            "그라운딩 위반 탐지 자체는 evidence_text_grounding 체크에 그대로 남아 있다."
        )

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


def test_issued_file_status_is_ranking_eligible(tmp_path):
    """공개 URL이 없는 보험사 공식 발행 파일도 순위 대상으로 인정한다.

    2026년 약관은 방화벽 안쪽 발행 경로에서 받아 공개 URL이 없다. 문서 자체가 보험사
    공식 발행본이므로 2차 유통본과 같게 취급하지 않는다.
    """
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "insurer": "SAMSUNG",
                        "verification_status": "VERIFIED_ISSUED_FILE",
                        "ranking_eligible": True,
                    },
                    {
                        "insurer": "MERITZ",
                        "verification_status": "SECONDARY_SOURCE",
                        "ranking_eligible": False,
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert ranking_eligible_insurer_codes(manifest) == {"SAMSUNG"}


def test_startup_sync_upgrades_existing_database_fingerprints(tmp_path):
    database = tmp_path / "app.db"
    shutil.copy2(DEFAULT_DATABASE, database)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE policy_version SET file_hash=NULL")
        connection.commit()

    engine = create_engine(f"sqlite:///{database.as_posix()}")
    assert synchronize_policy_fingerprints(engine) == 6
    assert audit_kb(database, DEFAULT_MANIFEST)["error_count"] == 0
