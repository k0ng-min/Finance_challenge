from app import config
from app.models.kb import (
    Clause,
    ClauseIncidentMap,
    ClauseTerm,
    Coverage,
    CoverageDocMap,
    IncidentType,
    Insurer,
    PolicyVersion,
    Product,
    RequiredDocStd,
)
from app.services.insurer_ranking import rank_insurers


def _incident(db, code: str) -> IncidentType:
    item = IncidentType(l1_code=code, l2_code=code, name=code)
    db.add(item)
    db.flush()
    return item


def _coverage_with_mapping(
    db,
    *,
    insurer_code: str,
    incident: IncidentType,
    relevance: str,
    with_term: bool = False,
    mandatory_docs: int | None = 1,
):
    insurer = db.query(Insurer).filter(Insurer.code == insurer_code).first()
    if insurer is None:
        insurer = Insurer(code=insurer_code, name=f"{insurer_code} 보험")
        db.add(insurer)
        db.flush()
    product = Product(insurer_id=insurer.insurer_id, name=f"{insurer_code} 상품")
    db.add(product)
    db.flush()
    policy = PolicyVersion(product_id=product.product_id, version_label="테스트 약관")
    db.add(policy)
    db.flush()
    coverage = Coverage(policy_version_id=policy.policy_version_id, raw_name=f"{incident.l1_code} 담보")
    db.add(coverage)
    db.flush()
    clause = Clause(
        policy_version_id=policy.policy_version_id,
        coverage_id=coverage.coverage_id,
        clause_type="면책" if relevance == "면책" else "보장정의",
        article_no="제1조",
        text=f"{incident.l1_code} 사고에 대한 {relevance} 근거와 지급한도 100만원",
        page_ref="1",
    )
    db.add(clause)
    db.flush()
    db.add(ClauseIncidentMap(
        clause_id=clause.clause_id,
        type_id=incident.type_id,
        relevance=relevance,
        mapped_by="human",
        confidence=1.0,
    ))
    if with_term:
        db.add(ClauseTerm(
            clause_id=clause.clause_id,
            term_type="지급한도",
            value_num=1_000_000,
            unit="원",
            raw_text="지급한도 100만원",
            confidence=1.0,
        ))
    if mandatory_docs is not None:
        for index in range(mandatory_docs):
            doc = RequiredDocStd(
                doc_code=f"{insurer_code}_{incident.l1_code}_{index}",
                doc_name=f"필수서류 {index + 1}",
            )
            db.add(doc)
            db.flush()
            db.add(CoverageDocMap(
                coverage_id=coverage.coverage_id,
                required_doc_std_id=doc.required_doc_std_id,
                is_mandatory=True,
                clause_id=clause.clause_id,
            ))
    db.flush()
    return insurer, coverage, clause


def _dimension(item: dict, code: str) -> dict:
    return next(dimension for dimension in item["dimensions"] if dimension["code"] == code)


def test_same_input_is_deterministic(db_session, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)
    prop = _incident(db_session, "PROP")
    _coverage_with_mapping(db_session, insurer_code="A", incident=prop, relevance="직접", with_term=True)
    _coverage_with_mapping(db_session, insurer_code="B", incident=prop, relevance="조건부", with_term=True)
    db_session.commit()

    context = {"coverage_priority": ["PROP"]}
    first = rank_insurers(db_session, "균형형", context)
    second = rank_insurers(db_session, "균형형", context)

    assert first == second
    assert all("score" not in item for item in first)


def test_selected_incident_type_changes_relative_order(db_session, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)
    prop = _incident(db_session, "PROP")
    emg = _incident(db_session, "EMG")
    _coverage_with_mapping(db_session, insurer_code="A", incident=prop, relevance="직접", with_term=True)
    _coverage_with_mapping(db_session, insurer_code="A", incident=emg, relevance="면책")
    _coverage_with_mapping(db_session, insurer_code="B", incident=prop, relevance="면책")
    _coverage_with_mapping(db_session, insurer_code="B", incident=emg, relevance="직접", with_term=True)
    db_session.commit()

    prop_ranking = rank_insurers(db_session, "안정형", {"coverage_priority": ["PROP"]})
    emg_ranking = rank_insurers(db_session, "안정형", {"coverage_priority": ["EMG"]})

    assert prop_ranking[0]["insurer_code"] == "A"
    assert emg_ranking[0]["insurer_code"] == "B"


def test_every_exposed_evidence_reference_exists(db_session, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)
    prop = _incident(db_session, "PROP")
    _coverage_with_mapping(
        db_session, insurer_code="A", incident=prop, relevance="직접", with_term=True, mandatory_docs=2
    )
    db_session.commit()

    item = rank_insurers(db_session, "균형형", {"coverage_priority": ["PROP"]})[0]
    model_by_kind = {"clause": Clause, "term": ClauseTerm, "document": CoverageDocMap}
    evidence = [reference for dimension in item["dimensions"] for reference in dimension["evidence"]]

    assert evidence
    for reference in evidence:
        model = model_by_kind[reference["kind"]]
        assert db_session.get(model, reference["source_id"]) is not None


def test_missing_clause_term_is_unknown_and_does_not_lower_rank(db_session, monkeypatch):
    """Case A: 동일 보장인데 한 보험사만 미구축이어도 0점 감점하지 않는다."""
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)
    prop = _incident(db_session, "PROP")
    _coverage_with_mapping(db_session, insurer_code="A", incident=prop, relevance="직접", with_term=False)
    _coverage_with_mapping(db_session, insurer_code="B", incident=prop, relevance="직접", with_term=True)
    db_session.commit()

    ranking = rank_insurers(db_session, "최대보장형", {"coverage_priority": ["PROP"]})
    dimensions = {
        item["insurer_code"]: _dimension(item, "condition_clarity")
        for item in ranking
    }

    assert [item["insurer_code"] for item in ranking] == ["A", "B"]
    assert dimensions["A"]["comparison_state"] == "UNKNOWN"
    assert dimensions["B"]["comparison_state"] == "UNKNOWN"
    assert dimensions["A"]["available"] is False
    assert dimensions["B"]["available"] is False
    assert dimensions["A"]["level"] == dimensions["B"]["level"] == 0
    assert dimensions["A"]["completeness_rate"] == 0.0
    assert dimensions["B"]["completeness_rate"] == 100.0


def test_unmapped_incident_is_unknown_not_noncoverage(db_session, monkeypatch):
    prop = _incident(db_session, "PROP")
    _incident(db_session, "EMG")
    _coverage_with_mapping(db_session, insurer_code="A", incident=prop, relevance="직접")
    db_session.commit()

    item = rank_insurers(
        db_session, "균형형", {"coverage_priority": ["PROP", "EMG"]}
    )[0]
    coverage_fit = _dimension(item, "coverage_fit")

    assert coverage_fit["comparison_state"] == "UNKNOWN"
    assert coverage_fit["available"] is False
    assert coverage_fit["known_count"] == 1
    assert coverage_fit["total_count"] == 2


def test_restrictions_are_excluded_without_negative_review_marker(db_session, monkeypatch):
    prop = _incident(db_session, "PROP")
    _coverage_with_mapping(db_session, insurer_code="A", incident=prop, relevance="조건부")
    db_session.commit()

    item = rank_insurers(db_session, "안정형", {"coverage_priority": ["PROP"]})[0]
    restrictions = _dimension(item, "restrictions")

    assert restrictions["comparison_state"] == "UNKNOWN"
    assert restrictions["available"] is False
    assert restrictions["level"] == 0


def test_missing_document_mapping_is_not_treated_as_easy_claim(db_session, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)
    prop = _incident(db_session, "PROP")
    _coverage_with_mapping(
        db_session, insurer_code="A", incident=prop, relevance="직접", mandatory_docs=None
    )
    _coverage_with_mapping(
        db_session, insurer_code="B", incident=prop, relevance="직접", mandatory_docs=1
    )
    db_session.commit()

    ranking = rank_insurers(db_session, "간편청구형", {"coverage_priority": ["PROP"]})
    item_a = next(item for item in ranking if item["insurer_code"] == "A")
    simplicity = _dimension(item_a, "claim_simplicity")

    assert simplicity["level"] == 0
    assert simplicity["status"] == "근거 부족"
