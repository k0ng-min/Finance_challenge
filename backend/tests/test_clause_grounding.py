"""조항 원문이 실제 PDF 추출본에 있는지 대조하는 검증 스크립트 테스트."""
import json
import sqlite3

from scripts.verify_clause_grounding import check, normalize


def _make_db(path, clause_text):
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE insurer (insurer_id INTEGER PRIMARY KEY, code TEXT);
        CREATE TABLE product (product_id INTEGER PRIMARY KEY, insurer_id INTEGER, name TEXT);
        CREATE TABLE policy_version (policy_version_id INTEGER PRIMARY KEY, product_id INTEGER);
        CREATE TABLE clause (
            clause_id INTEGER PRIMARY KEY, policy_version_id INTEGER,
            article_no TEXT, text TEXT, page_ref TEXT
        );
        INSERT INTO insurer VALUES (1, 'SAMSUNG');
        INSERT INTO product VALUES (1, 1, '해외여행보험');
        INSERT INTO policy_version VALUES (1, 1);
        """
    )
    connection.execute(
        "INSERT INTO clause VALUES (1, 1, '제3조', ?, 'p.80')", (clause_text,)
    )
    connection.commit()
    connection.close()


def _make_sources(tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "samsung_full_text.txt").write_text(
        "\n\n===PAGE 80===\n회사는 피보험자가 여행 도중에 상해를\n입은 경우 보험금을 지급합니다.\n",
        encoding="utf-8",
    )
    catalog = tmp_path / "source_files.json"
    catalog.write_text(
        json.dumps(
            {"SAMSUNG": [{"page_ref_prefix": None, "pdf": "samsung.pdf",
                          "text": "samsung_full_text.txt", "pages": 307, "sha256": "x"}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return catalog, processed


def test_normalize_drops_all_whitespace():
    assert normalize("회사는  피보험자가\n여행 도중에") == "회사는피보험자가여행도중에"


def test_grounded_clause_passes(tmp_path):
    catalog, processed = _make_sources(tmp_path)
    db_path = tmp_path / "app.db"
    _make_db(db_path, "회사는 피보험자가 여행 도중에 상해를 입은 경우 보험금을 지급합니다.")
    assert check(db_path, catalog, processed) == []


def test_invented_clause_is_reported(tmp_path):
    catalog, processed = _make_sources(tmp_path)
    db_path = tmp_path / "app.db"
    _make_db(db_path, "회사는 피보험자가 여행 도중에 질병에 걸린 경우 보험금을 지급합니다.")
    failures = check(db_path, catalog, processed)
    assert len(failures) == 1
    assert failures[0]["insurer"] == "SAMSUNG"
    assert failures[0]["clause_id"] == 1
    assert failures[0]["article_no"] == "제3조"
