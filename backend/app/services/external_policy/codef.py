"""CODEF 실연동 자리 — 지금은 스키마와 매핑 규칙만 두고 호출하지 않는다.

왜 미구현인가:
  신용정보원 '내보험다보여' 회원가입에는 주민등록번호가 필요하다. 개인정보보호법 제24조의2는
  주민등록번호를 법령에 구체적 근거가 있을 때만 처리하도록 하고, 정보주체 동의로 갈음할 수
  없다. 이 서비스에는 그 근거가 없다. 운영 주체가 법적 요건을 갖춘 뒤 fetch()를 채우고
  implemented=True로 바꾼 다음에야 EXTERNAL_POLICY_PROVIDERS에 codef를 넣어 활성화할 수
  있다 — 구현 없이 환경변수만 켜면 기동할 때 오류로 막힌다
  (registry.validate_configured_providers).

어느 서비스를 쓰는가:
  CODEF 보험 카테고리에는 신용정보원 '내보험다보여'(/insurance/each/credit4u/*)와
  생명보험협회 '내보험찾아줌'(/insurance/each/cont/find)이 있다. 담보별 중복 판정에는
  보장 상세를 주는 '내보험다보여'만 쓸 수 있다 — '내보험찾아줌'은 계약 상태만 주고
  보장내역을 주지 않는다.

  '내보험다보여'는 아이디/비밀번호 회원제라 CODEF가 회원가입 신청·아이디찾기·비밀번호변경
  API까지 함께 제공한다. 연동 시 가입 → 자격증명 보관 → 계약정보 조회 순서가 된다.
"""
from __future__ import annotations

from app.services.external_policy.base import ExternalPolicyDTO, ExternalPolicyProvider

#: CODEF 계약정보 응답 → ExternalPolicyDTO 필드 매핑. 실연동 시 이 표대로 옮긴다.
FIELD_MAP = {
    "resCompanyNm": "insurer_name_raw",
    "resInsuranceName": "product_name_raw",
    "resContractDate": "enrolled_ym",
}


class CodefProvider(ExternalPolicyProvider):
    name = "codef"
    label = "내보험다보여(CODEF) 연동"
    requires_login = True
    # fetch()가 비어 있는 자리표시자라는 표시. registry가 이 표시를 보고 사용가능 목록에서
    # 빼고, EXTERNAL_POLICY_PROVIDERS에 codef가 들어 있으면 기동 때 오류로 막는다.
    # 환경변수만 켜서 "연동된 것처럼" 보이게 만드는 길을 없애기 위한 장치다.
    implemented = False
    notice = "CODEF 연동은 아직 구현되지 않았습니다."

    def fetch(self, *, user, credentials: dict) -> list[ExternalPolicyDTO]:
        raise NotImplementedError(
            "CODEF 연동은 아직 설정되지 않았습니다. "
            "주민등록번호 처리 근거(개인정보보호법 제24조의2)를 갖춘 뒤 활성화하세요."
        )
