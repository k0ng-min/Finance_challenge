"""Audit policy provenance, evidence links, and the frozen KB dataset.

Run from ``backend``::

    python -m scripts.validate_kb
    python -m scripts.validate_kb --json

The command is read-only unless ``--freeze`` is supplied.  A freeze refreshes
the semantic KB fingerprint and per-insurer entity counts while preserving the
manually reviewed source metadata in ``data/dataset_manifest.json``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = BACKEND_DIR / "data" / "app.db"
DEFAULT_MANIFEST = BACKEND_DIR / "data" / "dataset_manifest.json"

EXPECTED_INSURERS = {"SAMSUNG", "HYUNDAI", "MERITZ", "KB", "DB", "KAKAOPAY", "SHINHAN"}
VERIFICATION_STATUSES = {
    "VERIFIED_CURRENT",
    "VERIFIED_VERSIONED",
    "VERIFIED_ISSUED_FILE",
    "NEEDS_CURRENT_VERSION_CHECK",
    "SECONDARY_SOURCE",
    "EXTRACTION_INCOMPLETE",
}
RANKING_ELIGIBLE_STATUSES = {"VERIFIED_CURRENT", "VERIFIED_VERSIONED", "VERIFIED_ISSUED_FILE"}
RECOGNIZED_RELEVANCE = {"직접", "조건부", "면책", "제한"}
RANKING_RELEVANCE = {"직접", "조건부", "면책"}
REQUIRED_SOURCE_FIELDS = {
    "insurer",
    "product_name",
    "policy_version",
    "effective_date",
    "source_url",
    "source_type",
    "downloaded_at",
    "sha256",
    "verification_status",
    "ranking_eligible",
    "coverage_count",
    "clause_count",
    "incident_map_count",
    "term_count",
    "doc_map_count",
    "known_gap",
}
FINGERPRINT_TABLES = (
    "insurer",
    "product",
    "policy_version",
    "coverage_std",
    "coverage",
    "clause",
    "incident_type",
    "clause_incident_map",
    "clause_term",
    "required_doc_std",
    "coverage_doc_map",
    "overlap_rule",
    "standard_clause",
    "clause_standard_map",
)


def _connect(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _scalar(connection: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> int:
    return int(connection.execute(sql, tuple(params)).fetchone()[0])


def _normalized(value: str | None) -> str:
    return " ".join((value or "").split())


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _check(name: str, error_count: int = 0, warning_count: int = 0, details: Any = None) -> dict[str, Any]:
    return {
        "name": name,
        "status": "FAIL" if error_count else ("WARN" if warning_count else "PASS"),
        "error_count": error_count,
        "warning_count": warning_count,
        "details": details or [],
    }


def compute_kb_fingerprint(connection: sqlite3.Connection) -> str:
    """Hash only semantic KB tables so user activity cannot invalidate a freeze."""
    digest = hashlib.sha256()
    for table in FINGERPRINT_TABLES:
        columns = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
        if not columns:
            raise ValueError(f"missing fingerprint table: {table}")
        names = [column[1] for column in columns]
        # PDF hashes are audited against the manifest separately.  Excluding
        # this one deployment-migrated column keeps a freeze comparable before
        # and after the idempotent startup provenance sync runs.
        if table == "policy_version":
            names = [name for name in names if name != "file_hash"]
        primary_keys = [column[1] for column in sorted(columns, key=lambda row: row[5]) if column[5]]
        order_by = primary_keys or names
        rows = connection.execute(
            f'SELECT * FROM "{table}" ORDER BY ' + ", ".join(f'"{name}"' for name in order_by)
        ).fetchall()
        digest.update(f"{table}\n".encode())
        for row in rows:
            payload = {name: row[name] for name in names}
            digest.update(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())
            digest.update(b"\n")
    return digest.hexdigest()


def build_coverage_matrix(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT i.code AS insurer,
               COUNT(DISTINCT c.coverage_id) AS coverage_count,
               COUNT(DISTINCT cl.clause_id) AS clause_count,
               COUNT(DISTINCT cim.map_id) AS incident_map_count,
               COUNT(DISTINCT ct.term_id) AS term_count,
               COUNT(DISTINCT cdm.coverage_doc_id) AS doc_map_count
          FROM insurer i
          JOIN product p ON p.insurer_id = i.insurer_id
          JOIN policy_version pv ON pv.product_id = p.product_id
          LEFT JOIN coverage c ON c.policy_version_id = pv.policy_version_id
          LEFT JOIN clause cl ON cl.policy_version_id = pv.policy_version_id
          LEFT JOIN clause_incident_map cim ON cim.clause_id = cl.clause_id
          LEFT JOIN clause_term ct ON ct.clause_id = cl.clause_id
          LEFT JOIN coverage_doc_map cdm ON cdm.coverage_id = c.coverage_id
         GROUP BY i.code
         ORDER BY i.code
        """
    ).fetchall()
    # Multi-way joins multiply rows, so calculate each count independently.
    matrix: list[dict[str, Any]] = []
    for row in rows:
        code = row["insurer"]
        matrix.append(
            {
                "insurer": code,
                "coverage_count": _scalar(connection, """SELECT COUNT(*) FROM coverage c JOIN policy_version pv USING(policy_version_id) JOIN product p USING(product_id) JOIN insurer i USING(insurer_id) WHERE i.code=?""", (code,)),
                "clause_count": _scalar(connection, """SELECT COUNT(*) FROM clause cl JOIN policy_version pv USING(policy_version_id) JOIN product p USING(product_id) JOIN insurer i USING(insurer_id) WHERE i.code=?""", (code,)),
                "incident_map_count": _scalar(connection, """SELECT COUNT(*) FROM clause_incident_map m JOIN clause cl USING(clause_id) JOIN policy_version pv USING(policy_version_id) JOIN product p USING(product_id) JOIN insurer i USING(insurer_id) WHERE i.code=?""", (code,)),
                "term_count": _scalar(connection, """SELECT COUNT(*) FROM clause_term t JOIN clause cl USING(clause_id) JOIN policy_version pv USING(policy_version_id) JOIN product p USING(product_id) JOIN insurer i USING(insurer_id) WHERE i.code=?""", (code,)),
                "doc_map_count": _scalar(connection, """SELECT COUNT(*) FROM coverage_doc_map d JOIN coverage c USING(coverage_id) JOIN policy_version pv USING(policy_version_id) JOIN product p USING(product_id) JOIN insurer i USING(insurer_id) WHERE i.code=?""", (code,)),
            }
        )
    return matrix


def build_ranking_completeness_matrix(
    connection: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """Expose annotation coverage without pretending it is product performance.

    These counts are diagnostic only. In particular, a low term/map count must not
    be converted to a low insurer score; the ranking service reports that axis as
    UNKNOWN until an explicit review-complete marker exists.
    """
    result: list[dict[str, Any]] = []
    for code in sorted(row[0] for row in connection.execute("SELECT code FROM insurer")):
        mapped_l1_count = _scalar(connection, """
            SELECT COUNT(DISTINCT it.l1_code)
              FROM clause_incident_map m
              JOIN incident_type it ON it.type_id=m.type_id
              JOIN clause cl ON cl.clause_id=m.clause_id
              JOIN policy_version pv ON pv.policy_version_id=cl.policy_version_id
              JOIN product p ON p.product_id=pv.product_id
              JOIN insurer i ON i.insurer_id=p.insurer_id
             WHERE i.code=? AND m.relevance IN ('직접', '조건부', '면책')
        """, (code,))
        supported_coverage_count = _scalar(connection, """
            SELECT COUNT(DISTINCT cl.coverage_id)
              FROM clause_incident_map m
              JOIN clause cl ON cl.clause_id=m.clause_id
              JOIN policy_version pv ON pv.policy_version_id=cl.policy_version_id
              JOIN product p ON p.product_id=pv.product_id
              JOIN insurer i ON i.insurer_id=p.insurer_id
             WHERE i.code=? AND m.relevance IN ('직접', '조건부')
               AND cl.coverage_id IS NOT NULL
        """, (code,))
        term_coverage_count = _scalar(connection, """
            SELECT COUNT(DISTINCT supported.coverage_id)
              FROM (
                    SELECT DISTINCT cl.coverage_id
                      FROM clause_incident_map m
                      JOIN clause cl ON cl.clause_id=m.clause_id
                      JOIN policy_version pv ON pv.policy_version_id=cl.policy_version_id
                      JOIN product p ON p.product_id=pv.product_id
                      JOIN insurer i ON i.insurer_id=p.insurer_id
                     WHERE i.code=? AND m.relevance IN ('직접', '조건부')
                       AND cl.coverage_id IS NOT NULL
                   ) supported
             WHERE EXISTS (
                    SELECT 1 FROM clause term_clause
                    JOIN clause_term term ON term.clause_id=term_clause.clause_id
                    WHERE term_clause.coverage_id=supported.coverage_id
                   )
        """, (code,))
        doc_coverage_count = _scalar(connection, """
            SELECT COUNT(DISTINCT supported.coverage_id)
              FROM (
                    SELECT DISTINCT cl.coverage_id
                      FROM clause_incident_map m
                      JOIN clause cl ON cl.clause_id=m.clause_id
                      JOIN policy_version pv ON pv.policy_version_id=cl.policy_version_id
                      JOIN product p ON p.product_id=pv.product_id
                      JOIN insurer i ON i.insurer_id=p.insurer_id
                     WHERE i.code=? AND m.relevance IN ('직접', '조건부')
                       AND cl.coverage_id IS NOT NULL
                   ) supported
             WHERE EXISTS (
                    SELECT 1 FROM coverage_doc_map doc
                    WHERE doc.coverage_id=supported.coverage_id
                   )
        """, (code,))
        result.append({
            "insurer": code,
            "mapped_l1_count": mapped_l1_count,
            "mapped_l1_total": len({"INJ", "ILL", "PROP", "LIA", "TRV", "CHG", "EMG", "SPC"}),
            "supported_coverage_count": supported_coverage_count,
            "term_coverage_count": term_coverage_count,
            "doc_coverage_count": doc_coverage_count,
            "condition_clarity_state": (
                "AVAILABLE"
                if supported_coverage_count > 0 and term_coverage_count == supported_coverage_count
                else "UNKNOWN"
            ),
            "claim_simplicity_state": "UNKNOWN",
            # The schema has positive restriction annotations but no explicit
            # review-complete/no-restriction marker.
            "restrictions_state": "UNKNOWN",
        })
    return result


def audit_kb(database: Path | str = DEFAULT_DATABASE, manifest_path: Path | str = DEFAULT_MANIFEST) -> dict[str, Any]:
    database = Path(database)
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    with _connect(database) as connection:
        db_insurers = {row[0] for row in connection.execute("SELECT code FROM insurer")}
        checks.append(_check("expected_insurers", len(EXPECTED_INSURERS - db_insurers), details=sorted(db_insurers)))

        graph_errors = {
            "clause_missing_policy": _scalar(connection, "SELECT COUNT(*) FROM clause cl LEFT JOIN policy_version pv ON pv.policy_version_id=cl.policy_version_id WHERE pv.policy_version_id IS NULL"),
            "coverage_missing_policy": _scalar(connection, "SELECT COUNT(*) FROM coverage c LEFT JOIN policy_version pv ON pv.policy_version_id=c.policy_version_id WHERE pv.policy_version_id IS NULL"),
            "clause_coverage_version_mismatch": _scalar(connection, "SELECT COUNT(*) FROM clause cl JOIN coverage c ON c.coverage_id=cl.coverage_id WHERE c.policy_version_id<>cl.policy_version_id"),
        }
        checks.append(_check("clause_coverage_policy_traceability", sum(graph_errors.values()), details=graph_errors))

        evidence_errors = {
            "incident_map_missing_clause": _scalar(connection, "SELECT COUNT(*) FROM clause_incident_map m LEFT JOIN clause cl ON cl.clause_id=m.clause_id WHERE cl.clause_id IS NULL"),
            "incident_map_missing_type": _scalar(connection, "SELECT COUNT(*) FROM clause_incident_map m LEFT JOIN incident_type t ON t.type_id=m.type_id WHERE t.type_id IS NULL"),
            "term_missing_clause": _scalar(connection, "SELECT COUNT(*) FROM clause_term t LEFT JOIN clause cl ON cl.clause_id=t.clause_id WHERE cl.clause_id IS NULL"),
            "doc_map_missing_coverage": _scalar(connection, "SELECT COUNT(*) FROM coverage_doc_map d LEFT JOIN coverage c ON c.coverage_id=d.coverage_id WHERE c.coverage_id IS NULL"),
            "doc_map_missing_required_doc": _scalar(connection, "SELECT COUNT(*) FROM coverage_doc_map d LEFT JOIN required_doc_std s ON s.required_doc_std_id=d.required_doc_std_id WHERE s.required_doc_std_id IS NULL"),
            "doc_map_missing_clause": _scalar(connection, "SELECT COUNT(*) FROM coverage_doc_map d LEFT JOIN clause cl ON cl.clause_id=d.clause_id WHERE d.clause_id IS NOT NULL AND cl.clause_id IS NULL"),
            "overlap_rule_missing_clause": _scalar(connection, "SELECT COUNT(*) FROM overlap_rule r LEFT JOIN clause cl ON cl.clause_id=r.clause_id WHERE r.clause_id IS NOT NULL AND cl.clause_id IS NULL"),
            "standard_map_missing_standard_clause": _scalar(connection, "SELECT COUNT(*) FROM clause_standard_map m LEFT JOIN standard_clause sc ON sc.standard_clause_id=m.standard_clause_id WHERE sc.standard_clause_id IS NULL"),
            "standard_map_missing_insurer": _scalar(connection, "SELECT COUNT(*) FROM clause_standard_map m LEFT JOIN insurer i ON i.insurer_id=m.insurer_id WHERE i.insurer_id IS NULL"),
            "standard_map_missing_clause": _scalar(connection, "SELECT COUNT(*) FROM clause_standard_map m LEFT JOIN clause cl ON cl.clause_id=m.clause_id WHERE m.clause_id IS NOT NULL AND cl.clause_id IS NULL"),
            "standard_map_relation_clause_mismatch": _scalar(
                connection,
                """SELECT COUNT(*) FROM clause_standard_map
                    WHERE (relation = 'MISSING_IN_INSURER' AND (clause_id IS NOT NULL OR anchor_phrase_insurer IS NOT NULL))
                       OR (relation != 'MISSING_IN_INSURER' AND clause_id IS NULL)""",
            ),
        }
        checks.append(_check("ranking_evidence_references", sum(evidence_errors.values()), details=evidence_errors))

        relevance_rows = connection.execute("SELECT relevance, COUNT(*) AS count FROM clause_incident_map GROUP BY relevance").fetchall()
        relevance_counts = {row["relevance"]: row["count"] for row in relevance_rows}
        unknown_relevance = sum(count for value, count in relevance_counts.items() if value not in RECOGNIZED_RELEVANCE)
        ranking_excluded = sum(count for value, count in relevance_counts.items() if value not in RANKING_RELEVANCE)
        checks.append(_check("incident_map_relevance", unknown_relevance, ranking_excluded, relevance_counts))

        premium_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(insurer_premium)")
        }
        required_premium_columns = {
            "value_origin", "source_value", "source_period_days", "transformation",
            "transformation_reason", "source_reference", "collected_at",
        }
        if required_premium_columns <= premium_columns:
            premium_errors = {
                "invalid_origin": _scalar(connection, """
                    SELECT COUNT(*) FROM insurer_premium
                     WHERE value_origin NOT IN ('DIRECT_QUOTE', 'DERIVED', 'IMPUTED', 'UNKNOWN')
                """),
                "direct_missing_source": _scalar(connection, """
                    SELECT COUNT(*) FROM insurer_premium
                     WHERE value_origin='DIRECT_QUOTE'
                       AND (source_value IS NULL OR source_period_days IS NULL OR source_reference IS NULL)
                """),
                "derived_missing_transformation": _scalar(connection, """
                    SELECT COUNT(*) FROM insurer_premium
                     WHERE value_origin='DERIVED'
                       AND (source_value IS NULL OR source_period_days IS NULL
                            OR transformation IS NULL OR transformation_reason IS NULL
                            OR source_reference IS NULL)
                """),
                "imputed_missing_reason": _scalar(connection, """
                    SELECT COUNT(*) FROM insurer_premium
                     WHERE value_origin='IMPUTED'
                       AND (transformation IS NULL OR transformation_reason IS NULL
                            OR source_reference IS NULL)
                """),
                "missing_collected_at": _scalar(connection, """
                    SELECT COUNT(*) FROM insurer_premium WHERE collected_at IS NULL
                """),
            }
            unknown_premiums = _scalar(
                connection, "SELECT COUNT(*) FROM insurer_premium WHERE value_origin='UNKNOWN'"
            )
            origin_counts = {
                row["value_origin"]: row["count"]
                for row in connection.execute(
                    "SELECT value_origin, COUNT(*) AS count FROM insurer_premium GROUP BY value_origin"
                )
            }
            checks.append(_check(
                "premium_provenance",
                sum(premium_errors.values()),
                unknown_premiums,
                {"errors": premium_errors, "origin_counts": origin_counts},
            ))
        else:
            checks.append(_check(
                "premium_provenance",
                error_count=len(required_premium_columns - premium_columns),
                details={"missing_columns": sorted(required_premium_columns - premium_columns)},
            ))

        term_rows = connection.execute("SELECT t.term_id, t.raw_text, cl.text FROM clause_term t JOIN clause cl ON cl.clause_id=t.clause_id").fetchall()
        ungrounded_terms = [row["term_id"] for row in term_rows if _normalized(row["raw_text"]) not in _normalized(row["text"])]
        anchor_rows = connection.execute("SELECT r.rule_id, r.anchor_phrase, cl.text FROM overlap_rule r JOIN clause cl ON cl.clause_id=r.clause_id WHERE r.anchor_phrase IS NOT NULL AND trim(r.anchor_phrase)<>''").fetchall()
        ungrounded_anchors = [row["rule_id"] for row in anchor_rows if _normalized(row["anchor_phrase"]) not in _normalized(row["text"])]
        standard_anchor_rows = connection.execute(
            "SELECT m.map_id, m.anchor_phrase_standard, sc.text FROM clause_standard_map m JOIN standard_clause sc ON sc.standard_clause_id=m.standard_clause_id"
        ).fetchall()
        ungrounded_standard_anchors = [
            row["map_id"] for row in standard_anchor_rows
            if _normalized(row["anchor_phrase_standard"]) not in _normalized(row["text"])
        ]
        insurer_anchor_rows = connection.execute(
            "SELECT m.map_id, m.anchor_phrase_insurer, cl.text FROM clause_standard_map m JOIN clause cl ON cl.clause_id=m.clause_id WHERE m.anchor_phrase_insurer IS NOT NULL"
        ).fetchall()
        ungrounded_insurer_anchors = [
            row["map_id"] for row in insurer_anchor_rows
            if _normalized(row["anchor_phrase_insurer"]) not in _normalized(row["text"])
        ]
        grounding_errors = (
            len(ungrounded_terms) + len(ungrounded_anchors)
            + len(ungrounded_standard_anchors) + len(ungrounded_insurer_anchors)
        )
        checks.append(_check("evidence_text_grounding", grounding_errors, details={
            "term_ids": ungrounded_terms,
            "overlap_rule_ids": ungrounded_anchors,
            "clause_standard_map_standard_side": ungrounded_standard_anchors,
            "clause_standard_map_insurer_side": ungrounded_insurer_anchors,
        }))

        sources = manifest.get("sources", [])
        source_codes = {source.get("insurer") for source in sources}
        schema_details: list[str] = []
        for source in sources:
            missing = sorted(REQUIRED_SOURCE_FIELDS - set(source))
            if missing:
                schema_details.append(f"{source.get('insurer', '<unknown>')}: missing {', '.join(missing)}")
            if source.get("verification_status") not in VERIFICATION_STATUSES:
                schema_details.append(f"{source.get('insurer', '<unknown>')}: invalid verification_status")
            if not _valid_sha256(source.get("sha256")):
                schema_details.append(f"{source.get('insurer', '<unknown>')}: invalid sha256")
            expected_gate = source.get("verification_status") in RANKING_ELIGIBLE_STATUSES
            if source.get("ranking_eligible") is not expected_gate:
                schema_details.append(f"{source.get('insurer', '<unknown>')}: ranking_eligible does not match status")
        missing_sources = EXPECTED_INSURERS - source_codes
        if missing_sources:
            schema_details.append(f"missing insurers: {', '.join(sorted(missing_sources))}")
        checks.append(_check("manifest_source_schema", len(schema_details), details=schema_details))

        matrix = build_coverage_matrix(connection)
        matrix_by_code = {row["insurer"]: row for row in matrix}
        db_source_rows = connection.execute(
            """SELECT i.code AS insurer, p.name AS product_name, pv.version_label AS policy_version,
                      pv.effective_date, pv.source_url, pv.file_hash AS sha256
                 FROM policy_version pv JOIN product p USING(product_id) JOIN insurer i USING(insurer_id)"""
        ).fetchall()
        db_sources = {row["insurer"]: dict(row) for row in db_source_rows}
        source_mismatches: list[str] = []
        source_alignment_warnings: list[str] = []
        freshness_warnings: list[str] = []
        for source in sources:
            code = source.get("insurer")
            db_source = db_sources.get(code)
            if not db_source:
                source_mismatches.append(f"{code}: policy version missing in database")
                continue
            for field in ("product_name", "policy_version", "effective_date", "source_url", "sha256"):
                if field == "sha256" and not db_source.get(field):
                    source_alignment_warnings.append(f"{code}: sha256 awaits startup provenance sync")
                elif source.get(field) != db_source.get(field):
                    source_mismatches.append(f"{code}: {field} differs from database")
            for field in ("coverage_count", "clause_count", "incident_map_count", "term_count", "doc_map_count"):
                if source.get(field) != matrix_by_code.get(code, {}).get(field):
                    source_mismatches.append(f"{code}: {field} differs from database")
            if not source.get("effective_date"):
                freshness_warnings.append(f"{code}: effective_date is not identified")
            if not source.get("ranking_eligible"):
                freshness_warnings.append(f"{code}: excluded from ranking ({source.get('verification_status')})")
        checks.append(_check("manifest_database_alignment", len(source_mismatches), len(source_alignment_warnings), details=source_mismatches + source_alignment_warnings))
        checks.append(_check("source_freshness_and_ranking_gate", warning_count=len(freshness_warnings), details=freshness_warnings))

        comparison_completeness = build_ranking_completeness_matrix(connection)

        actual_fingerprint = compute_kb_fingerprint(connection)
        expected_fingerprint = manifest.get("kb_content_sha256")
        checks.append(_check("dataset_freeze", int(actual_fingerprint != expected_fingerprint), details={"expected": expected_fingerprint, "actual": actual_fingerprint}))

    error_count = sum(check["error_count"] for check in checks)
    warning_count = sum(check["warning_count"] for check in checks)
    return {
        "dataset_version": manifest.get("dataset_version"),
        "frozen_at": manifest.get("frozen_at"),
        "database": str(database),
        "manifest": str(manifest_path),
        "status": "FAIL" if error_count else ("WARN" if warning_count else "PASS"),
        "error_count": error_count,
        "warning_count": warning_count,
        "checks": checks,
        "coverage_matrix": matrix,
        "ranking_completeness": comparison_completeness,
    }


def freeze_manifest(database: Path, manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with _connect(database) as connection:
        matrix = {row["insurer"]: row for row in build_coverage_matrix(connection)}
        for source in manifest["sources"]:
            counts = matrix[source["insurer"]]
            source.update({key: value for key, value in counts.items() if key != "insurer"})
        manifest["kb_content_sha256"] = compute_kb_fingerprint(connection)
    manifest["frozen_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _print_human(report: dict[str, Any]) -> None:
    print(f"KB audit: {report['status']} ({report['error_count']} errors, {report['warning_count']} warnings)")
    for check in report["checks"]:
        print(f"[{check['status']}] {check['name']}: {check['error_count']} errors, {check['warning_count']} warnings")
    print("\nCoverage matrix")
    print("insurer | coverage | clause | incident_map | term | doc_map")
    for row in report["coverage_matrix"]:
        print(f"{row['insurer']} | {row['coverage_count']} | {row['clause_count']} | {row['incident_map_count']} | {row['term_count']} | {row['doc_map_count']}")
    print("\nRanking evidence completeness (diagnostic; never a product score)")
    print("insurer | mapped L1 | supported coverage | term coverage | doc coverage | clarity | claim | restrictions")
    for row in report["ranking_completeness"]:
        print(
            f"{row['insurer']} | {row['mapped_l1_count']}/{row['mapped_l1_total']} | "
            f"{row['supported_coverage_count']} | {row['term_coverage_count']} | "
            f"{row['doc_coverage_count']} | {row['condition_clarity_state']} | "
            f"{row['claim_simplicity_state']} | "
            f"{row['restrictions_state']}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true", help="print the complete audit report as JSON")
    parser.add_argument("--freeze", action="store_true", help="refresh counts and the semantic KB fingerprint")
    args = parser.parse_args(argv)
    if args.freeze:
        freeze_manifest(args.database, args.manifest)
    report = audit_kb(args.database, args.manifest)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human(report)
    return 1 if report["error_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
