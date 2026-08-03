from app.models.external import ExternalPolicy, ExternalCoverage, OverlapRule


def test_기존보험과_담보를_저장하고_읽어온다(db_session):
    policy = ExternalPolicy(
        user_id=1, source="manual", kind="MEDICAL_INDEMNITY",
        insurer_name_raw="삼성화재", enrolled_ym="2019-05", indemnity_gen=3,
    )
    db_session.add(policy)
    db_session.flush()

    db_session.add(ExternalCoverage(
        external_policy_id=policy.external_policy_id,
        raw_name="질병입원 의료비", amount_source="standard_terms",
    ))
    db_session.commit()

    saved = db_session.query(ExternalPolicy).one()
    assert saved.kind == "MEDICAL_INDEMNITY"
    assert saved.indemnity_gen == 3
    assert len(saved.coverages) == 1
    assert saved.coverages[0].amount_source == "standard_terms"


def test_판정규칙은_담보와_구간별로_저장된다(db_session):
    db_session.add(OverlapRule(
        external_kind="MEDICAL_INDEMNITY", coverage_std_id=8,
        scope="국내 의료기관", relation="PARTIAL", clause_id=77, note="국내 치료 구간은 겹친다",
    ))
    db_session.commit()

    rule = db_session.query(OverlapRule).one()
    assert rule.scope == "국내 의료기관"
    assert rule.clause_id == 77
