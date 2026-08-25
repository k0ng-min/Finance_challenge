"""커밋된 여행경보 스냅샷을 실제로 읽어, 인기 여행지에 출국권고가 뜨지 않는지 고정한다.

이 기능이 틀리는 방식은 "안 뜨는 것"이 아니라 "엉뚱한 데 뜨는 것"이다. 국가별 최고 단계를
대표로 쓰면 일본이 3단계(후쿠시마 원전 30km), 필리핀이 4단계(민다나오 일부)가 되어
도쿄·세부 여행자에게 여행금지가 뜬다. 3·4단계 72개국 중 52개국이 일부 지역 경보라
예외가 아니라 다수다.

그래서 합성 데이터가 아니라 **실제 스냅샷**으로 검증한다. 누가 baseline 판정을 되돌리거나
외교부가 문구를 크게 바꾸면 여기서 잡힌다.
"""
import json
from collections import defaultdict
from pathlib import Path

import pytest

from app.models.kb import TravelAlert
from app.services.travel_alert import CLAUSE_FROM_LEVEL, BASIS_LOCAL, _pick_baseline

SNAPSHOT = Path(__file__).resolve().parents[1] / "data" / "travel_alerts.json"


@pytest.fixture(scope="module")
def by_country() -> dict[str, list[TravelAlert]]:
    assert SNAPSHOT.exists(), (
        f"{SNAPSHOT.name}이 없습니다. 이 스냅샷은 premiums.json처럼 저장소에 커밋해 두는 "
        "자료입니다(python -m app.crawl_travel_alerts, 인증키 필요)."
    )
    payload = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    grouped: dict[str, list[TravelAlert]] = defaultdict(list)
    for row in payload["alerts"]:
        grouped[row["country_name"]].append(TravelAlert(
            country_name=row["country_name"], level=int(row["level"]),
            region_type=row.get("region_type"), note=row.get("note"),
        ))
    return grouped


def _baseline_level(rows: list[TravelAlert]) -> int | None:
    base, _basis = _pick_baseline(rows)
    return base.level if base else None


def test_스냅샷이_지역_행을_접지_않고_담고_있다(by_country):
    """국가당 1건으로 접으면 어느 지역이 위험한지 알 수 없어 방문 여부를 물을 수 없다."""
    total_rows = sum(len(v) for v in by_country.values())
    assert total_rows > len(by_country), "국가 수보다 행이 많아야 합니다(지역별 경보 보존)"


@pytest.mark.parametrize(
    "country",
    ["일본", "태국", "필리핀", "인도", "멕시코", "캄보디아", "러시아", "이집트", "사우디아라비아", "요르단"],
)
def test_인기_여행지에_면책조항이_자동으로_붙지_않는다(by_country, country):
    """모두 3·4단계 지역경보를 가졌지만, 그건 특정 지역 이야기다.
    사용자가 그 지역에 간다고 체크하기 전에는 면책 조항을 꺼내지 않는다."""
    rows = by_country.get(country)
    assert rows, f"{country}가 스냅샷에 없습니다"
    assert max(r.level for r in rows) >= CLAUSE_FROM_LEVEL, (
        f"{country}에 3단계 이상 지역경보가 있다는 전제가 깨졌습니다 — 테스트를 다시 보세요"
    )

    level = _baseline_level(rows)
    assert level is None or level < CLAUSE_FROM_LEVEL, (
        f"{country}의 기본단계가 {level}로 잡혔습니다. 일부 지역 경보를 국가 전체로 "
        f"넓혀 말하고 있습니다: {[(r.level, r.note) for r in rows]}"
    )


@pytest.mark.parametrize(
    "country", ["시리아", "우크라이나", "이라크", "아프가니스탄", "예멘", "이란", "니제르", "수단"],
)
def test_실제로_위험한_나라는_체크_없이_면책조항이_붙는다(by_country, country):
    rows = by_country.get(country)
    assert rows, f"{country}가 스냅샷에 없습니다"

    level = _baseline_level(rows)
    assert level is not None and level >= CLAUSE_FROM_LEVEL, (
        f"{country}의 기본단계가 {level}입니다. 전국이 위험한 나라인데 경고가 빠집니다: "
        f"{[(r.level, r.region_type, r.note) for r in rows]}"
    )


def test_시리아는_괄호_속_제외에_끌려가지_않는다(by_country):
    """시리아 3단계는 "골란고원 일부(…지역 제외)"다. '제외'라는 글자만 보면 이 행이
    나머지 전역으로 잡혀 기본단계가 4가 아니라 3이 된다."""
    assert _baseline_level(by_country["시리아"]) == 4


def test_일본은_후쿠시마_지역경보로만_잡힌다(by_country):
    """가장 흔한 목적지이자, 예전 규칙에서 가장 크게 틀렸던 나라."""
    base, basis = _pick_baseline(by_country["일본"])

    assert base is None and basis == BASIS_LOCAL
    notes = " ".join(r.note or "" for r in by_country["일본"])
    assert "후쿠시마" in notes


def test_지역_설명에_HTML_엔티티가_남아_있지_않다(by_country):
    """응답에 &middot; &bull; 같은 엔티티가 섞여 온다. React가 이스케이프하므로 그대로 두면
    화면에 "로스토프&middot;벨고로드"로 보인다."""
    남은것 = [
        (c, r.note) for c, rows in by_country.items() for r in rows
        if r.note and "&" in r.note and ";" in r.note
    ]
    assert not 남은것, f"HTML 엔티티가 남았습니다: {남은것[:3]}"


def test_대부분의_나라는_기본단계를_판정할_수_있다(by_country):
    """휴리스틱이 '제외' 문구에 기대므로, 판정 불가가 많아지면 경고가 통째로 빠진다.
    외교부가 문구를 바꿨을 때 조용히 무력화되는 것을 여기서 잡는다."""
    local = [c for c, rows in by_country.items() if _pick_baseline(rows)[1] == BASIS_LOCAL]

    assert len(local) < len(by_country) * 0.2, (
        f"기본단계를 못 정한 나라가 {len(local)}/{len(by_country)}개국입니다. "
        f"'제외' 문구 휴리스틱을 다시 봐야 합니다: {sorted(local)}"
    )
