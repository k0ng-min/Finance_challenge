"""국가 → 현지 서류 창구에서 통하는 언어 매핑.

앱이 실제로 고르게 하는 나라(frontend/src/data/countries.ts) 전부를 담는다. 여기 없는
나라는 추측하지 않고 영어로 떨어진다(services/onsite_i18n.DEFAULT_LANG).

언어 선택 기준은 "그 나라 공용어"가 아니라 **병원·경찰서 문서 창구에서 실제로 통할
가능성**이다. 그래서 인도·말레이시아·케냐처럼 공용어가 여럿이어도 행정·의료 문서가
영어로 오가는 나라는 영어로 둔다. 모로코는 행정·의료 문서에서 프랑스어가 널리 쓰인다.

한국어는 화면에 항상 병기되므로(services/onsite.py), 언어를 하나 잘못 골라도 정보가
사라지지는 않는다 — 여기서의 오차는 "덜 편한" 수준이지 "틀린" 수준이 아니다.
"""
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.kb import CountryLanguage

LANG_NAMES = {
    "en": "영어", "ja": "일본어", "zh": "중국어", "th": "태국어", "vi": "베트남어",
    "es": "스페인어", "fr": "프랑스어", "de": "독일어", "id": "인도네시아어",
    "km": "크메르어", "lo": "라오어", "my": "미얀마어", "mn": "몽골어", "ne": "네팔어",
    "pt": "포르투갈어", "it": "이탈리아어", "nl": "네덜란드어", "el": "그리스어",
    "cs": "체코어", "hu": "헝가리어", "pl": "폴란드어", "sv": "스웨덴어", "no": "노르웨이어",
    "fi": "핀란드어", "da": "덴마크어", "is": "아이슬란드어", "hr": "크로아티아어",
    "tr": "튀르키예어", "ru": "러시아어", "uk": "우크라이나어", "ar": "아랍어", "he": "히브리어",
}

COUNTRY_LANG = {
    # 아시아
    "일본": "ja", "중국": "zh", "대만": "zh", "홍콩": "zh", "마카오": "zh",
    "태국": "th", "베트남": "vi", "필리핀": "en", "말레이시아": "en", "싱가포르": "en",
    "인도네시아": "id", "캄보디아": "km", "라오스": "lo", "미얀마": "my", "몽골": "mn",
    "인도": "en", "네팔": "ne", "스리랑카": "en",
    # 북중미
    "미국": "en", "캐나다": "en", "멕시코": "es", "쿠바": "es", "괌": "en", "사이판": "en",
    # 남미
    "브라질": "pt", "아르헨티나": "es", "칠레": "es", "페루": "es", "콜롬비아": "es",
    # 유럽
    "영국": "en", "프랑스": "fr", "독일": "de", "이탈리아": "it", "스페인": "es",
    "포르투갈": "pt", "스위스": "de", "오스트리아": "de", "네덜란드": "nl", "벨기에": "fr",
    "그리스": "el", "체코": "cs", "헝가리": "hu", "폴란드": "pl", "스웨덴": "sv",
    "노르웨이": "no", "핀란드": "fi", "덴마크": "da", "아이슬란드": "is", "아일랜드": "en",
    "크로아티아": "hr", "튀르키예": "tr", "러시아": "ru", "우크라이나": "uk",
    # 오세아니아
    "호주": "en", "뉴질랜드": "en", "피지": "en",
    # 중동·아프리카
    "아랍에미리트": "ar", "카타르": "ar", "사우디아라비아": "ar", "이스라엘": "he",
    "요르단": "ar", "이집트": "ar", "모로코": "fr",
    "남아프리카공화국": "en", "케냐": "en", "탄자니아": "en",
}


def seed(db: Session) -> int:
    existing = {row.country_name for row in db.query(CountryLanguage).all()}
    added = 0
    for country, lang in COUNTRY_LANG.items():
        if country in existing:
            continue
        name = LANG_NAMES.get(lang)
        if not name:
            raise ValueError(f"LANG_NAMES에 '{lang}'({country})의 한국어 이름이 없습니다.")
        db.add(CountryLanguage(
            country_name=country, lang_code=lang, lang_name_ko=name, is_primary=True,
        ))
        added += 1
    return added


if __name__ == "__main__":
    session = SessionLocal()
    try:
        count = seed(session)
        session.commit()
        print(f"country_language {count}건 추가 (전체 {len(COUNTRY_LANG)}개국)")
    finally:
        session.close()
