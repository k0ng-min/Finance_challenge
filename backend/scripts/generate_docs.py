"""문서에 적히는 숫자를 실제 DB·코드에서 세어 다시 쓴다.

왜 필요했나
-----------
같은 숫자가 여러 문서에 손으로 베껴져 있었다. README에는 "가격 데이터는 아직 4개사만
확보", `source_register.md` 표에는 보험사별 term_count가 전부 0, 그리고 "197건이
통과해야 합니다". 셋 다 그때는 맞았고 지금은 틀리다. 사람이 옮겨 적는 숫자는 반드시
낡는다 — 옮겨 적기를 그만두는 것 말고는 방법이 없다.

무엇을 하나
-----------
DB와 코드를 세어 문서의 **표시된 구간만** 다시 쓴다. 문서는 이렇게 표시한다::

    <!-- generated:kb-counts start -->
    (여기는 스크립트가 덮어쓴다)
    <!-- generated:kb-counts end -->

표시 밖의 글은 건드리지 않는다. 사람이 쓴 설명과 판단은 사람 것으로 남고, 세어서 알 수
있는 것만 기계가 맡는다. 이 경계가 흐려지면 "확인하지 않은 것이 확인된 것처럼" 보이게
되는데, `app/kb_manifest.py`가 개수만 갱신하고 검증 상태·known_gap은 손대지 않는 것과
같은 이유다.

    cd backend
    python scripts/generate_docs.py           # 무엇이 달라지는지만 보여준다
    python scripts/generate_docs.py --write   # 실제로 다시 쓴다
    python scripts/generate_docs.py --check   # 낡았으면 1로 끝난다(테스트·CI용)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sqlite3
import subprocess
import sys

BACKEND = pathlib.Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
DB_PATH = BACKEND / "data" / "app.db"
MANIFEST_PATH = BACKEND / "data" / "dataset_manifest.json"

DATA_STATUS = ROOT / "docs" / "data_status.md"
SOURCE_REGISTER = ROOT / "docs" / "compliance" / "source_register.md"
README = ROOT / "README.md"


# --- 세기 ------------------------------------------------------------------

def _one(conn: sqlite3.Connection, sql: str) -> int:
    return conn.execute(sql).fetchone()[0]


def collect(conn: sqlite3.Connection) -> dict:
    """문서에 나가는 모든 숫자를 한 번에 센다. 추정하지 않는다 — 세지 못하면 넣지 않는다."""
    insurers = [r[0] for r in conn.execute("select code from insurer order by code")]
    premium_insurers = [
        r[0] for r in conn.execute(
            "select distinct i.code from insurer_premium p"
            " join insurer i on i.insurer_id = p.insurer_id order by i.code"
        )
    ]
    plan_insurers = [
        r[0] for r in conn.execute(
            "select distinct i.code from insurer_plan_coverage p"
            " join insurer i on i.insurer_id = p.insurer_id order by i.code"
        )
    ]
    origin_rows = list(conn.execute(
        "select value_origin, count(*) from insurer_premium group by 1 order by 2 desc"
    ))
    collected = conn.execute(
        "select min(collected_at), max(collected_at) from insurer_premium"
    ).fetchone()
    standard_map = list(conn.execute(
        "select s.article_no, count(distinct i.code)"
        " from clause_standard_map m"
        " join standard_clause s on s.standard_clause_id = m.standard_clause_id"
        " join clause cl on cl.clause_id = m.clause_id"
        " join policy_version pv on pv.policy_version_id = cl.policy_version_id"
        " join product p on p.product_id = pv.product_id"
        " join insurer i on i.insurer_id = p.insurer_id"
        " group by 1 order by 1"
    ))

    return {
        "insurers": insurers,
        "insurer_count": len(insurers),
        "clause": _one(conn, "select count(*) from clause"),
        "coverage": _one(conn, "select count(*) from coverage"),
        "coverage_std": _one(conn, "select count(*) from coverage_std"),
        "incident_map": _one(conn, "select count(*) from clause_incident_map"),
        "clause_term": _one(conn, "select count(*) from clause_term"),
        "doc_map": _one(conn, "select count(*) from coverage_doc_map"),
        "doc_requirement": _one(conn, "select count(*) from doc_requirement"),
        "overlap_rule": _one(conn, "select count(*) from overlap_rule"),
        "incident_l1": _one(conn, "select count(distinct l1_code) from incident_type"),
        "incident_l2": _one(conn, "select count(*) from incident_type"),
        "standard_clause": _one(conn, "select count(*) from standard_clause"),
        "standard_map": _one(conn, "select count(*) from clause_standard_map"),
        "standard_map_by_article": standard_map,
        "premium_rows": _one(conn, "select count(*) from insurer_premium"),
        "premium_insurers": premium_insurers,
        "premium_origin": origin_rows,
        "premium_collected": collected,
        "plan_coverage_rows": _one(conn, "select count(*) from insurer_plan_coverage"),
        "plan_coverage_insurers": plan_insurers,
        "comparison_metric_rows": _one(conn, "select count(*) from insurer_comparison_metric"),
        "travel_alert": _one(conn, "select count(*) from travel_alert"),
    }


def count_tests() -> int | None:
    """pytest에게 직접 물어본다. 테스트 파일을 세어 짐작하지 않는다 —
    파라미터라이즈 하나가 여러 건으로 늘어나서 눈으로 센 값과 다르다."""
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
            cwd=BACKEND, capture_output=True, text=True, timeout=600,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    hit = re.search(r"(\d+) tests? collected", out)
    return int(hit.group(1)) if hit else None


def count_endpoints() -> tuple[int, int] | None:
    """FastAPI 앱에 실제로 등록된 것을 센다."""
    try:
        sys.path.insert(0, str(BACKEND))
        from app.main import app  # noqa: PLC0415

        pairs = {
            (method, route.path)
            for route in app.routes
            if getattr(route, "include_in_schema", True) and hasattr(route, "methods")
            for method in route.methods
            if method not in ("HEAD", "OPTIONS")
        }
        return len(pairs), len({path for _, path in pairs})
    except Exception:  # noqa: BLE001 — 문서 생성이 앱 기동 문제로 죽지 않게 한다
        return None


# --- 문서 조각 --------------------------------------------------------------

def _fmt(n: int) -> str:
    return f"{n:,}"


def kb_counts_block(c: dict) -> str:
    return "\n".join([
        "| 항목 | 수 | 테이블 |",
        "|---|---:|---|",
        f"| 보험사 | {c['insurer_count']} | `insurer` |",
        f"| 약관 조항 | {_fmt(c['clause'])} | `clause` |",
        f"| 담보 | {_fmt(c['coverage'])} | `coverage` |",
        f"| 표준담보 | {_fmt(c['coverage_std'])} | `coverage_std` |",
        f"| 조항↔사고유형 매핑 | {_fmt(c['incident_map'])} | `clause_incident_map` |",
        f"| 정량조건(용어) | {_fmt(c['clause_term'])} | `clause_term` |",
        f"| 담보↔서류 매핑 | {_fmt(c['doc_map'])} | `coverage_doc_map` |",
        f"| 서류 세부요건 | {_fmt(c['doc_requirement'])} | `doc_requirement` |",
        f"| 중복 판정 규칙 | {_fmt(c['overlap_rule'])} | `overlap_rule` |",
        f"| 사고유형 | L1 {c['incident_l1']} · 전체 {c['incident_l2']} | `incident_type` |",
        f"| 표준약관 조문 | {_fmt(c['standard_clause'])} | `standard_clause` |",
        f"| 표준약관 대조 | {_fmt(c['standard_map'])} | `clause_standard_map` |",
        f"| 여행경보 | {_fmt(c['travel_alert'])} | `travel_alert` |",
    ])


def premium_block(c: dict) -> str:
    lo, hi = c["premium_collected"]
    span = lo if lo == hi else f"{lo} ~ {hi}"
    lines = [
        f"보험료는 {len(c['premium_insurers'])}개사 **{_fmt(c['premium_rows'])}행**"
        f"(수집일 {span}). 약관에서 뽑은 값이 아니라 각 사 다이렉트 화면에서 가져온"
        " 외부 자료라, 행마다 어떤 경로로 만들어진 값인지를 함께 저장한다.",
        "",
        "| value_origin | 행 | 뜻 |",
        "|---|---:|---|",
    ]
    meaning = {
        "DIRECT_QUOTE": "다이렉트 화면에서 그대로 조회한 값",
        "DERIVED": "조회값에서 기간 환산 등으로 유도한 값",
        "IMPUTED": "주변 값으로 메운 값 — 순위 계산에서 제외한다",
        "UNKNOWN": "경로를 알 수 없는 값 — 순위 계산에서 제외한다",
    }
    for origin, rows in c["premium_origin"]:
        lines.append(f"| `{origin}` | {_fmt(rows)} | {meaning.get(origin, '—')} |")
    lines += [
        "",
        f"등급별 담보 가입금액표는 {len(c['plan_coverage_insurers'])}개사"
        f" {_fmt(c['plan_coverage_rows'])}행, 보험사 공통 비교표는"
        f" {_fmt(c['comparison_metric_rows'])}행이다.",
    ]
    return "\n".join(lines)


def source_table_block(manifest: dict) -> str:
    head = ("| insurer | product_name | policy_version | effective_date | source_url |"
            " source_type | downloaded_at | sha256 | verification_status | coverage_count |"
            " clause_count | incident_map_count | term_count | doc_map_count | known_gap |")
    sep = "|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|"
    rows = [head, sep]
    for s in manifest.get("sources", []):
        rows.append(
            f"| {s.get('insurer')} | {s.get('product_name')} | {s.get('policy_version')} "
            f"| {s.get('effective_date') or '미확정'} | {s.get('source_url') or '(공개 URL 없음)'} "
            f"| {s.get('source_type')} | {s.get('downloaded_at')} | `{s.get('sha256')}` "
            f"| {s.get('verification_status')} | {s.get('coverage_count')} | {s.get('clause_count')} "
            f"| {s.get('incident_map_count')} | {s.get('term_count')} | {s.get('doc_map_count')} "
            f"| {s.get('known_gap')} |"
        )
    return "\n".join(rows)


def readme_scale_block(c: dict, tests: int | None, endpoints: tuple[int, int] | None) -> str:
    parts = [
        f"- 보험사 **{c['insurer_count']}개사** — {', '.join(c['insurers'])}",
        f"- 약관 조항 **{_fmt(c['clause'])}개**, 담보 **{_fmt(c['coverage'])}개**,"
        f" 조항↔사고유형 매핑 **{_fmt(c['incident_map'])}건**,"
        f" 정량조건 **{_fmt(c['clause_term'])}건**, 담보↔서류 매핑 **{_fmt(c['doc_map'])}건**",
        f"- 실제 보험료 **{_fmt(c['premium_rows'])}행** ({len(c['premium_insurers'])}개사),"
        f" 등급별 담보 가입금액표 **{_fmt(c['plan_coverage_rows'])}행**"
        f" ({len(c['plan_coverage_insurers'])}개사)",
    ]
    if tests is not None:
        parts.append(f"- 백엔드 테스트 **{_fmt(tests)}건**")
    if endpoints is not None:
        parts.append(f"- API **{endpoints[0]}개**(경로 {endpoints[1]}개)")
    parts.append("")
    parts.append("이 숫자는 `backend/scripts/generate_docs.py`가 DB·코드에서 직접 세어 씁니다."
                 " 자세한 내역은 [`docs/data_status.md`](docs/data_status.md).")
    return "\n".join(parts)


def render_data_status(c: dict, tests: int | None, endpoints: tuple[int, int] | None,
                       manifest: dict) -> str:
    lo, hi = c["premium_collected"]
    lines = [
        "# 지금 이 저장소가 담고 있는 것",
        "",
        "`backend/scripts/generate_docs.py`가 만든다. 손으로 고치지 말고 스크립트를 다시 돌릴 것.",
        "",
        "숫자를 여기 한 곳에 모으는 이유는 단순하다. 같은 값을 README와 등록부와 발표자료에",
        "각각 적어 두면 반드시 어긋난다 — 실제로 어긋나 있었다. 다른 문서는 이 문서를 가리키고,",
        "이 문서는 DB를 가리킨다.",
        "",
        "## 지식베이스",
        "",
        "<!-- generated:kb-counts start -->",
        kb_counts_block(c),
        "<!-- generated:kb-counts end -->",
        "",
        "## 보험료·보장금액 (약관이 아닌 외부 자료)",
        "",
        "<!-- generated:premium start -->",
        premium_block(c),
        "<!-- generated:premium end -->",
        "",
        "## 표준약관 대조",
        "",
        "<!-- generated:standard start -->",
        f"금융감독원 표준약관 조문 {c['standard_clause']}개 가운데 실제로 대조를 마친 것은"
        f" {len(c['standard_map_by_article'])}개 조문이고, 보험사별로 세면"
        f" {c['standard_map']}칸이다({c['insurer_count']}개사 × {c['standard_clause']}조문 = "
        f"{c['insurer_count'] * c['standard_clause']}칸이 전부 채워질 자리다)."
        " 근거를 확보하지 못한 칸은 \"표준과 같다\"고 단정하지 않고 비워 둔다.",
        "",
        "| 표준 조문 | 대조된 보험사 수 |",
        "|---|---:|",
        *[f"| {article} | {n} |" for article, n in c["standard_map_by_article"]],
        "<!-- generated:standard end -->",
        "",
        "## 검증",
        "",
        "<!-- generated:verify start -->",
        " ".join(filter(None, [
            (f"백엔드 테스트 {_fmt(tests)}건." if tests is not None
             else "백엔드 테스트 수를 세지 못했다(pytest 실행 실패)."),
            (f"API {endpoints[0]}개(경로 {endpoints[1]}개)." if endpoints is not None else ""),
        ])),
        "",
        f"KB 지문(`kb_content_sha256`): `{manifest.get('kb_content_sha256')}`",
        f"— 동결 시각 {manifest.get('frozen_at')}, 검증 시각 {manifest.get('verified_at')}.",
        "`cd backend && python scripts/validate_kb.py`가 이 지문과 실제 DB를 대조한다.",
        "<!-- generated:verify end -->",
        "",
        "## 이 문서가 답하지 않는 것",
        "",
        "- 숫자가 **맞는지**는 세어서 알 수 있지만, 그 값이 **충분한지**는 아니다.",
        f"  예를 들어 정량조건 {_fmt(c['clause_term'])}건은 보험사마다 편차가 크다 —",
        "  보험사별 내역은 `docs/compliance/source_register.md`를 볼 것.",
        "- 출처·검증 상태·미완 사항(known_gap)은 사람이 원본을 확인해 적는 값이라",
        "  여기서 자동으로 만들지 않는다.",
        "",
    ]
    return "\n".join(lines)


# --- 표시 구간 치환 ---------------------------------------------------------

def replace_block(text: str, name: str, body: str) -> str:
    start, end = f"<!-- generated:{name} start -->", f"<!-- generated:{name} end -->"
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end), re.DOTALL
    )
    if not pattern.search(text):
        raise RuntimeError(f"표시 구간을 찾지 못했다: {name}")
    return pattern.sub(f"{start}\n{body}\n{end}", text)


def build(conn: sqlite3.Connection) -> dict[pathlib.Path, str]:
    counts = collect(conn)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    tests = count_tests()
    endpoints = count_endpoints()

    out: dict[pathlib.Path, str] = {
        DATA_STATUS: render_data_status(counts, tests, endpoints, manifest),
    }
    if SOURCE_REGISTER.exists():
        out[SOURCE_REGISTER] = replace_block(
            SOURCE_REGISTER.read_text(encoding="utf-8"),
            "source-table", source_table_block(manifest),
        )
    if README.exists():
        out[README] = replace_block(
            README.read_text(encoding="utf-8"),
            "scale", readme_scale_block(counts, tests, endpoints),
        )
    return out


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="실제로 다시 쓴다")
    parser.add_argument("--check", action="store_true", help="낡았으면 1로 끝난다")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    try:
        rendered = build(conn)
    finally:
        conn.close()

    stale = [
        path for path, body in rendered.items()
        if not path.exists() or path.read_text(encoding="utf-8") != body
    ]
    if not stale:
        print("문서가 이미 DB·코드와 맞는다 — 고칠 것이 없다.")
        return 0

    for path in stale:
        print(f"  낡음: {path.relative_to(ROOT)}")
    if args.check:
        print("`cd backend && python scripts/generate_docs.py --write`로 다시 쓸 것.")
        return 1
    if args.write:
        for path in stale:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered[path], encoding="utf-8")
        print(f"{len(stale)}개 문서를 다시 썼다.")
        return 0
    print("--write 없이 실행했으므로 아무것도 쓰지 않았다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
