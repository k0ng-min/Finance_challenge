"""KB를 의도적으로 고친 뒤 매니페스트를 다시 맞추는 절차(refresh_manifest)를 고정한다.

dataset_manifest.json은 "커밋된 app.db가 무엇을 담고 있어야 하는가"를 적어 둔 기록이고,
validate_kb가 그것과 실제 DB를 대조해 KB가 모르는 사이에 바뀌는 걸 잡는다. 그래서 KB를
일부러 고쳤을 때는 매니페스트도 같이 갱신해야 하는데, 손으로 고치면 숫자를 하나 빠뜨려도
검사만 통과하고 기록은 틀린 상태가 된다.

여기서 확인하는 것은 두 가지다.
  1. 갱신 후 실제 DB와 매니페스트가 어긋나지 않는다.
  2. 갱신이 건드리는 것은 개수와 지문뿐이다 — 출처(source_url·sha256·검증상태)처럼
     사람이 확인해 적어 넣은 값은 그대로 남는다.
"""
import json
import shutil
import sqlite3

from app.kb_manifest import refresh_manifest
from scripts.validate_kb import DEFAULT_DATABASE, DEFAULT_MANIFEST, audit_kb


def _copies(tmp_path):
    db = tmp_path / "app.db"
    manifest = tmp_path / "dataset_manifest.json"
    shutil.copy2(DEFAULT_DATABASE, db)
    shutil.copy2(DEFAULT_MANIFEST, manifest)
    return db, manifest


def test_조항을_더_넣은_뒤_갱신하면_대조_검사가_다시_통과한다(tmp_path):
    db, manifest = _copies(tmp_path)
    with sqlite3.connect(db) as conn:
        pv_id = conn.execute("SELECT policy_version_id FROM policy_version LIMIT 1").fetchone()[0]
        conn.execute(
            "INSERT INTO clause (policy_version_id, clause_type, article_no, text) VALUES (?,?,?,?)",
            (pv_id, "보장정의", "제99조", "테스트로 더 넣은 조항 원문"),
        )
        conn.commit()

    before = audit_kb(db, manifest)
    assert before["error_count"] > 0, "KB를 고쳤으면 갱신 전에는 검사가 걸려야 한다"

    refresh_manifest(db, manifest)

    assert audit_kb(db, manifest)["error_count"] == 0


def test_사람이_적어_넣은_출처_정보는_건드리지_않는다(tmp_path):
    db, manifest = _copies(tmp_path)
    original = json.loads(manifest.read_text(encoding="utf-8"))

    refresh_manifest(db, manifest)
    updated = json.loads(manifest.read_text(encoding="utf-8"))

    keep = ("insurer", "product_name", "policy_version", "source_url", "source_type",
            "sha256", "verification_status", "ranking_eligible", "known_gap")
    for before_src, after_src in zip(original["sources"], updated["sources"]):
        for field in keep:
            assert before_src.get(field) == after_src.get(field), f"{field}이 바뀌었다"


def test_커밋된_KB와_매니페스트는_어긋나지_않는다():
    """저장소에 들어가는 app.db와 dataset_manifest.json은 항상 짝이 맞아야 한다."""
    assert audit_kb(DEFAULT_DATABASE, DEFAULT_MANIFEST)["error_count"] == 0
