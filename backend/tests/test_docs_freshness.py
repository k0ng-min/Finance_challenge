"""문서에 적힌 숫자가 실제 DB·코드와 어긋나면 여기서 걸린다.

왜 필요한가
-----------
같은 숫자가 여러 문서에 손으로 베껴져 있었고, 전부 낡아 있었다.

  · README: "가격 데이터는 아직 4개사만 확보" — 실제로는 7개사 전부 있었다.
  · README: "197건이 통과해야 합니다" — 실제 테스트는 그보다 훨씬 많았다.
  · source_register 표: 보험사 여섯 곳의 term_count가 전부 0 — 실제로는 12~67건.
  · dataset_manifest known_gap: 신한EZ "실제 보험료 미확보" — 이미 확보한 뒤였다.

문서를 한 번 고치는 것으로는 같은 일이 또 생긴다. 낡으면 빨간불이 켜지게 해야 한다.
`scripts/generate_docs.py --check`가 그 일을 하고, 이 테스트가 그것을 CI에 묶는다.

고치는 법::

    cd backend && python scripts/generate_docs.py --write
"""
import json
import pathlib
import re
import sqlite3

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
DB_PATH = BACKEND / "data" / "app.db"
MANIFEST_PATH = BACKEND / "data" / "dataset_manifest.json"


@pytest.fixture(scope="module")
def conn():
    if not DB_PATH.exists():
        pytest.skip("약관 KB(data/app.db)가 없어 건너뜁니다")
    connection = sqlite3.connect(DB_PATH)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# --- 생성된 구간이 최신인가 -------------------------------------------------

def test_생성된_문서_구간이_DB와_맞는다(conn):
    """`generate_docs.py --check`와 같은 판정을 테스트에서 한다.

    이 테스트가 깨졌다면 문서가 틀렸다는 뜻이지 코드가 틀렸다는 뜻이 아니다.
    `cd backend && python scripts/generate_docs.py --write`로 고친다."""
    import sys

    sys.path.insert(0, str(BACKEND))
    from scripts.generate_docs import build  # noqa: PLC0415

    rendered = build(conn)
    stale = [
        path.relative_to(ROOT).as_posix()
        for path, body in rendered.items()
        if not path.exists() or path.read_text(encoding="utf-8") != body
    ]
    assert not stale, (
        "문서가 DB·코드와 어긋납니다: " + ", ".join(stale)
        + " — cd backend && python scripts/generate_docs.py --write"
    )


# --- 매니페스트의 known_gap이 자기 숫자와 모순되지 않는가 -------------------

def _db_count(conn, table: str) -> int:
    return conn.execute(f"select count(*) from {table}").fetchone()[0]


@pytest.mark.parametrize("phrase,table", [
    ("clause_standard_map", "clause_standard_map"),
    ("overlap_rule", "overlap_rule"),
    ("doc_requirement", "doc_requirement"),
])
def test_known_gap이_적어_둔_개수가_실제와_같다(manifest, conn, phrase, table):
    """known_gap은 사람이 쓰는 글이라 자동으로 덮어쓰지 않는다(그건 확인하지 않은 것을
    확인한 것처럼 만든다). 대신 그 안에 적힌 '무엇이 N건'이 실제와 어긋나면 여기서 잡는다.

    실제로 표준약관 대조가 9건에서 11건으로 늘어난 뒤에도 known_gap에는 9건이 남아 있었다.
    """
    actual = _db_count(conn, table)
    pattern = re.compile(re.escape(phrase) + r"[^0-9]{0,20}?(\d+)건")
    for source in manifest["sources"]:
        for written in pattern.findall(source.get("known_gap") or ""):
            assert int(written) == actual, (
                f"{source['insurer']}의 known_gap이 {phrase} {written}건이라고 적었지만 "
                f"실제 DB는 {actual}건입니다"
            )


def test_보험료를_확보한_보험사를_미확보라고_적어_두지_않았다(manifest, conn):
    """신한EZ가 그랬다 — 보험료를 넣은 뒤에도 known_gap에는 '아직 확보하지 못해'가
    남아 있었고, 그 문장이 등록부 문서로 그대로 흘러갔다."""
    priced = {
        row[0] for row in conn.execute(
            "select distinct i.code from insurer_premium p"
            " join insurer i on i.insurer_id = p.insurer_id"
        )
    }
    for source in manifest["sources"]:
        gap = source.get("known_gap") or ""
        if source["insurer"] in priced:
            assert "실제 보험료를 아직 확보하지 못해" not in gap, (
                f"{source['insurer']}는 보험료가 이미 있는데 known_gap이 미확보라고 적고 있습니다"
            )


# --- 매니페스트 개수가 DB와 맞는가(등록부 표의 출처) ------------------------

def test_매니페스트_개수가_실제_DB와_같다(manifest, conn):
    """등록부 문서의 표는 이 매니페스트에서 만들어진다. 매니페스트가 낡으면 문서도
    같이 낡으므로, 여기가 첫 관문이다.

    어긋나면 `cd backend && python -m app.kb_manifest --confirm`으로 맞춘다."""
    rows = {
        row[0]: row for row in conn.execute(
            """
            select i.code,
                   (select count(*) from coverage c
                      join policy_version pv on pv.policy_version_id = c.policy_version_id
                      join product p on p.product_id = pv.product_id
                     where p.insurer_id = i.insurer_id),
                   (select count(*) from clause cl
                      join policy_version pv on pv.policy_version_id = cl.policy_version_id
                      join product p on p.product_id = pv.product_id
                     where p.insurer_id = i.insurer_id)
              from insurer i
            """
        )
    }
    for source in manifest["sources"]:
        code = source["insurer"]
        assert code in rows, f"매니페스트에 있는 {code}가 DB에 없습니다"
        _, coverage, clause = rows[code]
        assert source["coverage_count"] == coverage, (
            f"{code}.coverage_count: 매니페스트 {source['coverage_count']} vs DB {coverage}"
        )
        assert source["clause_count"] == clause, (
            f"{code}.clause_count: 매니페스트 {source['clause_count']} vs DB {clause}"
        )


def test_매니페스트가_DB의_모든_보험사를_담는다(manifest, conn):
    """보험사를 하나 더 넣고 등록부에 적는 걸 잊으면, 출처를 밝히지 않은 보험사가
    순위에 끼게 된다."""
    in_db = {row[0] for row in conn.execute("select code from insurer")}
    in_manifest = {s["insurer"] for s in manifest["sources"]}
    assert in_db == in_manifest, (
        f"DB에만 있는 보험사: {in_db - in_manifest}, 매니페스트에만 있는 보험사: {in_manifest - in_db}"
    )
