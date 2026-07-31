"""
사고유형 사전(incident_type) 시드 — 2단계 고정 분류.

왜 필요한가:
지금까지는 claim_review.py가 담보코드(OVS_INJ_MED / DEATH_INJURY / PERSONAL_EFFECTS)를
직접 하드코딩하고, 키워드·NLU 필드(item_damage_type 등)로 "이 사고에 이 담보가 걸리나"를
그때그때 판단했다. 담보가 늘어날수록 그 분기가 기하급수적으로 늘어난다(하위유형 폭발).

그래서 "무슨 일이 있었나"(사고유형)와 "무슨 담보로 받나"(담보)를 분리한다.
L1은 아래 8개로 **고정**한다 — 새 사고가 생기면 L2로만 늘리고, 절대 L1을 추가하지 않는다.
어디에도 맞지 않는 조항/사고는 SPC_OTHER로 보내 사람이 나중에 재분류한다(조용히 버리지 않음).

수식자(활동/장소/시점/상태/대상)는 이 사전에 넣지 않는다 — 사고유형과 직교하는 축이라
incident.modifiers(JSON)에 따로 담는다. 유형 × 수식자를 곱해서 유형을 만들면 그게 바로
하위유형 폭발이다.
"""
from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401  (모델 등록)
from app.models.kb import IncidentType

Base.metadata.create_all(bind=engine)

# (l1_code, L1 한글명, [(l2_code, L2 한글명), ...])
TAXONOMY: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("INJ", "상해", [
        ("INJ_DEATH_DISABILITY", "상해사망·후유장해"),
        ("INJ_OVERSEAS_TREATMENT", "해외상해치료(외래·입원·수술)"),
        ("INJ_DOMESTIC_TREATMENT", "귀국후 국내치료"),
    ]),
    ("ILL", "질병", [
        ("ILL_DEATH_DISABILITY", "질병사망·고도후유장해"),
        ("ILL_OVERSEAS_TREATMENT", "해외질병치료"),
        ("ILL_DOMESTIC_TREATMENT", "국내질병치료"),
        ("ILL_INFECTIOUS", "감염병·격리"),
    ]),
    ("PROP", "휴대품·재물", [
        ("PROP_THEFT", "도난"),
        ("PROP_DAMAGE", "파손"),
        # 대부분의 휴대품손해 특약이 명시적으로 면책하지만, 그래도 정식 유형으로 둔다.
        # 그래야 "이건 분실이라 대부분 면책입니다"라고 근거(면책 조항)를 달아 답할 수 있다.
        ("PROP_LOSS", "분실"),
        ("PROP_CASH_SECURITIES", "현금·유가증권"),
        ("PROP_PASSPORT_LOSS", "여권분실"),
    ]),
    ("LIA", "배상책임", [
        ("LIA_PERSONAL", "대인배상"),
        ("LIA_PROPERTY", "대물배상"),
        ("LIA_LODGING", "임차물·호텔객실"),
    ]),
    ("TRV", "운송", [
        ("TRV_FLIGHT_DELAY", "항공지연·결항"),
        ("TRV_BAGGAGE_DELAY", "수하물지연"),
        ("TRV_BAGGAGE_LOSS", "수하물분실"),
        ("TRV_HIJACK", "항공기납치"),
    ]),
    ("CHG", "여행변경", [
        ("CHG_CANCELLATION", "여행취소"),
        ("CHG_INTERRUPTION", "여행중단·조기귀국"),
    ]),
    ("EMG", "긴급지원", [
        ("EMG_RESCUE", "수색구조"),
        ("EMG_MEDICAL_TRANSPORT", "의료이송"),
        ("EMG_REPATRIATION", "유해송환"),
        ("EMG_FAMILY_VISIT", "가족방문비용"),
    ]),
    ("SPC", "특수·기타", [
        ("SPC_WAR_TERROR", "전쟁·테러(면책)"),
        ("SPC_NATURAL_DISASTER", "천재지변"),
        ("SPC_PET_CARE", "반려동물돌봄"),
        # catch-all — 어디에도 안 맞는 조항/사고를 버리지 않고 여기로 보낸 뒤 사람이 재분류.
        ("SPC_OTHER", "그 외 미분류"),
    ]),
]


def run():
    db = SessionLocal()
    try:
        existing = {t.l2_code: t for t in db.query(IncidentType).all()}
        added_l1 = added_l2 = 0

        for l1_code, l1_name, children in TAXONOMY:
            root = existing.get(l1_code)
            if root is None:
                root = IncidentType(
                    l1_code=l1_code, l2_code=l1_code, name=l1_name,
                    parent_id=None, is_active=True,
                )
                db.add(root)
                db.flush()
                existing[l1_code] = root
                added_l1 += 1

            for l2_code, l2_name in children:
                if l2_code in existing:
                    continue
                child = IncidentType(
                    l1_code=l1_code, l2_code=l2_code, name=l2_name,
                    parent_id=root.type_id, is_active=True,
                )
                db.add(child)
                db.flush()
                existing[l2_code] = child
                added_l2 += 1

        db.commit()
        total = db.query(IncidentType).count()
        print(
            f"incident_type 시드 완료: L1 {added_l1}건 추가, L2 {added_l2}건 추가 "
            f"(전체 {total}건, 기존 행은 스킵)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
