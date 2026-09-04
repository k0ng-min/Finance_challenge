"""기존보험 수집 인터페이스.

수집 방식(직접 입력 / 시연용 목 / CODEF 실연동)이 무엇이든 같은 DTO를 돌려주게 만들어,
저장·진단·화면이 수집 방식을 구분하지 않게 한다. 나중에 CODEF를 붙일 때 CodefProvider만
채우면 되고 나머지 코드는 건드리지 않는다.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# external_policy.kind로 허용하는 값
VALID_KINDS = {
    "MEDICAL_INDEMNITY",  # 실손의료비
    "ACCIDENT",           # 상해보험
    "DAILY_LIABILITY",    # 일상생활배상책임
    "DRIVER",             # 운전자보험
    "OTHER",
}


@dataclass
class ExternalCoverageDTO:
    raw_name: str
    coverage_std_code: str | None = None
    subscribed_amount: str | None = None
    amount_source: str = "unknown"


@dataclass
class ExternalPolicyDTO:
    source: str
    kind: str
    insurer_name_raw: str | None = None
    product_name_raw: str | None = None
    enrolled_ym: str | None = None
    indemnity_gen: int | None = None
    coverages: list[ExternalCoverageDTO] = field(default_factory=list)
    raw_payload: dict | None = None


class ExternalPolicyProvider(ABC):
    #: 화면과 API에서 이 구현체를 가리키는 이름
    name: str
    #: 사용자에게 보여줄 한국어 이름
    label: str
    #: 외부 서비스 인증이 필요한가. False면 게스트도 쓸 수 있다.
    requires_login: bool
    #: fetch()가 실제로 동작하는가. 자리만 잡아둔 구현체는 False로 두고,
    #: registry가 사용가능 목록에서 빼고 설정에 들어 있으면 기동 때 막는다.
    #: 껍데기만 있는 연동이 켜져 있는 것처럼 보이는 일을 막기 위한 표시다.
    implemented: bool = True
    #: 결과가 실제 조회가 아니라 미리 정해 둔 예시 데이터인가.
    #: True면 화면은 반드시 notice를 함께 보여줘 실제 조회 결과와 구분해야 한다.
    is_demo: bool = False
    #: 시연용일 때 화면에 함께 띄울 안내 문구.
    notice: str | None = None

    @abstractmethod
    def fetch(self, *, user, credentials: dict) -> list[ExternalPolicyDTO]:
        """기존보험 목록을 가져온다. 실패는 예외로 알리고, 빈 목록으로 뭉개지 않는다."""
        raise NotImplementedError
