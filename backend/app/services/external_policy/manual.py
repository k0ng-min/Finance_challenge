"""사용자가 화면에서 직접 고른 기존보험을 DTO로 옮긴다.

실손만 담보를 자동으로 채울 수 있다 — 2009년 표준화 이후 보장구조가 보험사별로 같기 때문.
나머지 종류는 표준약관이 없어 회사·상품마다 담보가 달라, 종류만 저장하고 금액은 비워 둔다.
중복 판정 자체는 종류만으로 되므로 진단 기능은 정상 동작한다(금액 계산만 못 한다).
"""
from __future__ import annotations

from app.services.external_policy.base import (
    VALID_KINDS, ExternalPolicyDTO, ExternalPolicyProvider,
)
from app.services.external_policy.indemnity import resolve_indemnity_generation


class ManualProvider(ExternalPolicyProvider):
    name = "manual"
    requires_login = False

    def fetch(self, *, user, credentials: dict) -> list[ExternalPolicyDTO]:
        items = credentials.get("items") or []
        result: list[ExternalPolicyDTO] = []
        for item in items:
            kind = item.get("kind")
            if kind not in VALID_KINDS:
                raise ValueError(f"알 수 없는 보험 종류: {kind}")

            enrolled_ym = item.get("enrolled_ym")
            generation = (
                resolve_indemnity_generation(enrolled_ym)
                if kind == "MEDICAL_INDEMNITY" else None
            )
            result.append(ExternalPolicyDTO(
                source="manual",
                kind=kind,
                insurer_name_raw=item.get("insurer_name_raw"),
                product_name_raw=item.get("product_name_raw"),
                enrolled_ym=enrolled_ym,
                indemnity_gen=generation,
                # 담보 자동채움은 세대별 표준 보장구조를 시드한 뒤에 붙인다.
                # 금융감독원 표준약관 원문과 대조하기 전에는 숫자를 넣지 않는다.
                coverages=[],
            ))
        return result
