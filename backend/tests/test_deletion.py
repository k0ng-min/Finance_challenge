"""탈퇴·게스트승격 시 기존보험(external_policy/external_coverage)까지 함께 지워지는지 확인한다.

user_id는 AUTOINCREMENT가 아니라 탈퇴 후 rowid가 재사용될 수 있다 — 지우지 않으면 다음
사용자가 같은 user_id를 받았을 때 탈퇴자의 기존보험 정보를 그대로 물려받는다."""
from app.models.external import ExternalCoverage, ExternalPolicy
from app.models.user import AppUser
from app.services.deletion import delete_user_cascade, wipe_user_data


def _make_user_with_external_policy(db_session) -> AppUser:
    user = AppUser(nickname="테스터", auth_provider="guest")
    db_session.add(user)
    db_session.flush()

    policy = ExternalPolicy(
        user_id=user.user_id, source="manual", kind="MEDICAL_INDEMNITY",
        insurer_name_raw="삼성화재", enrolled_ym="2019-05", indemnity_gen=3,
    )
    db_session.add(policy)
    db_session.flush()
    db_session.add(ExternalCoverage(
        external_policy_id=policy.external_policy_id,
        raw_name="질병입원 의료비", amount_source="standard_terms",
    ))
    db_session.commit()
    return user


def test_회원탈퇴시_기존보험도_함께_지워진다(db_session):
    user = _make_user_with_external_policy(db_session)
    user_id = user.user_id

    delete_user_cascade(db_session, user)
    db_session.commit()

    assert db_session.query(ExternalPolicy).filter(ExternalPolicy.user_id == user_id).count() == 0
    assert db_session.query(ExternalCoverage).count() == 0
    assert db_session.get(AppUser, user_id) is None


def test_게스트승격시_wipe_user_data가_기존보험도_지운다(db_session):
    """로그인·회원가입 시 계정은 남기고 게스트 시절 기록만 지운다 — 기존보험도 예외가 아니다."""
    user = _make_user_with_external_policy(db_session)
    user_id = user.user_id

    wipe_user_data(db_session, user_id)
    db_session.commit()

    assert db_session.query(ExternalPolicy).filter(ExternalPolicy.user_id == user_id).count() == 0
    assert db_session.query(ExternalCoverage).count() == 0
    # 계정 자체는 살아있어야 한다 (wipe_user_data는 계정을 지우지 않는다)
    assert db_session.get(AppUser, user_id) is not None


def test_user_id_재사용시_탈퇴자의_기존보험을_물려받지_않는다(db_session):
    """rowid 재사용 시나리오를 직접 재현한다: 탈퇴자와 같은 user_id를 가진 신규 사용자를
    만들었을 때, 탈퇴자의 external_policy 행이 남아있으면 안 된다."""
    user = _make_user_with_external_policy(db_session)
    user_id = user.user_id

    delete_user_cascade(db_session, user)
    db_session.commit()

    # 같은 user_id로 새 사용자가 들어온 상황을 흉내낸다 (SQLite rowid 재사용과 동일한 효과).
    new_user = AppUser(user_id=user_id, nickname="새사용자", auth_provider="guest")
    db_session.add(new_user)
    db_session.commit()

    remaining = db_session.query(ExternalPolicy).filter(ExternalPolicy.user_id == user_id).all()
    assert remaining == []
