"""연동 UX 전체(버튼 → 로딩 → 결과)를 실제 CODEF 없이 시연하기 위한 고정 샘플.

여기서 나오는 보험사·상품명은 전부 만들어 둔 예시다. 실제 조회 결과가 아니므로 배포
기본값(config.EXTERNAL_POLICY_PROVIDERS)에는 들어 있지 않고, 시연·테스트 환경에서
EXTERNAL_POLICY_PROVIDERS에 mock을 넣었을 때만 켜진다. 켜지더라도 is_demo/notice가
API 응답에 함께 실려, 화면이 이 결과를 실제 조회처럼 보여줄 수 없게 한다.

raw_payload는 CODEF 응답을 흉내 낸 형태로 담아둔다 — 나중에 CodefProvider를 채울 때
이 구조를 그대로 매핑 대상으로 삼는다.
"""
from __future__ import annotations

from app.services.external_policy.base import ExternalPolicyDTO, ExternalPolicyProvider

_SAMPLES = [
    {
        "kind": "MEDICAL_INDEMNITY",
        "insurer_name_raw": "삼성화재해상보험",
        "product_name_raw": "무배당 삼성화재 실손의료비보험",
        "enrolled_ym": "2019-05",
        "indemnity_gen": 3,
    },
    {
        "kind": "DAILY_LIABILITY",
        "insurer_name_raw": "현대해상화재보험",
        "product_name_raw": "가족일상생활배상책임 특약",
        "enrolled_ym": "2022-03",
        "indemnity_gen": None,
    },
    {
        "kind": "ACCIDENT",
        "insurer_name_raw": "메리츠화재해상보험",
        "product_name_raw": "무배당 메리츠 상해보험",
        "enrolled_ym": "2015-11",
        "indemnity_gen": None,
    },
]


class MockProvider(ExternalPolicyProvider):
    name = "mock"
    label = "시연용 예시 데이터"
    requires_login = True
    is_demo = True
    notice = "화면 흐름을 보여주기 위한 시연용 예시 데이터입니다. 실제 보험 조회 결과가 아닙니다."

    def fetch(self, *, user, credentials: dict) -> list[ExternalPolicyDTO]:
        return [
            ExternalPolicyDTO(
                source="mock",
                kind=s["kind"],
                insurer_name_raw=s["insurer_name_raw"],
                product_name_raw=s["product_name_raw"],
                enrolled_ym=s["enrolled_ym"],
                indemnity_gen=s["indemnity_gen"],
                coverages=[],
                raw_payload=dict(s),
            )
            for s in _SAMPLES
        ]
