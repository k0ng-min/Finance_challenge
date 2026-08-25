"""구 KB 삭제 범위 테스트.

이 스크립트는 되돌릴 수 없으므로, 지우는 테이블과 남기는 테이블을 테스트로 고정한다.
"""
from app.reset_kb import DELETE_ORDER, KEEP_TABLES


def test_delete_order_covers_kb_and_user_data():
    for table in (
        "clause_incident_map", "clause_term", "coverage_doc_map", "doc_requirement",
        "overlap_rule", "clause_standard_map", "clause", "coverage",
        "policy_version", "product",
        "app_user", "user_policy", "user_coverage", "trip", "incident", "evidence",
        "analysis_run", "analysis_finding", "finding_evidence_link",
        "validation_result", "user_question_log", "eval_log",
    ):
        assert table in DELETE_ORDER, f"{table}이 삭제 목록에 없다"


def test_reference_data_is_kept():
    for table in (
        "insurer", "coverage_std", "incident_type", "required_doc_std", "standard_clause",
        "insurer_premium", "travel_alert", "nonpayment_rate", "flight_delay_stat",
        "country_language", "onsite_phrase_i18n", "question_bank",
        "simulation_scenario", "validation_rule",
    ):
        assert table in KEEP_TABLES, f"{table}은 남겨야 한다"
        assert table not in DELETE_ORDER, f"{table}이 삭제 목록에 들어 있다"


def test_children_are_deleted_before_parents():
    """외래키 역순이 아니면 SQLite가 참조 오류를 낸다."""
    assert DELETE_ORDER.index("finding_evidence_link") < DELETE_ORDER.index("analysis_finding")
    assert DELETE_ORDER.index("analysis_finding") < DELETE_ORDER.index("analysis_run")
    assert DELETE_ORDER.index("clause_incident_map") < DELETE_ORDER.index("clause")
    assert DELETE_ORDER.index("clause") < DELETE_ORDER.index("coverage")
    assert DELETE_ORDER.index("coverage") < DELETE_ORDER.index("policy_version")
    assert DELETE_ORDER.index("user_coverage") < DELETE_ORDER.index("user_policy")
    assert DELETE_ORDER.index("user_policy") < DELETE_ORDER.index("app_user")
