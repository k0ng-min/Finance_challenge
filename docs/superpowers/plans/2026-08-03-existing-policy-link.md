# 기존보험 연결·중복보장 진단 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사용자가 이미 가진 보험(실손·상해·일상생활배상책임 등)을 등록하면, 이번 여행자보험 담보와 겹치는 지점·비는 지점을 약관 원문 근거와 함께 보여준다.

**Architecture:** 기존보험 수집은 `ExternalPolicyProvider` 추상 인터페이스 뒤에 숨기고 manual/mock/codef 세 구현체를 둔다. 중복 판정은 코드가 아니라 `overlap_rule` 테이블에 행마다 근거 `clause_id`를 물려 시드하고, 진단 엔진은 조회 시점에 그 규칙을 조합해 결과를 만든다(저장하지 않는다).

**Tech Stack:** FastAPI, SQLAlchemy 2.0, SQLite, Pydantic 2, pytest, React 19 + TypeScript + Vite

## Global Constraints

- **근거 없는 결과를 내지 않는다.** `overlap_rule.relation`이 `UNKNOWN`이 아닌 모든 행은 유효한 `clause_id`를 가져야 한다. 근거가 없으면 행을 만들지 말고 진단에서 "확인불가"로 떨어뜨린다.
- **인용문은 원문의 부분 문자열이어야 한다.** 진단 결과가 담는 원문 조각은 반드시 해당 `clause.text`의 부분 문자열이어야 하며, 아니면 반환하지 않는다.
- **실손 세대별 자기부담률·한도 수치는 이번 계획에서 시드하지 않는다.** 금융감독원 「금융상품 표준약관」(https://www.fss.or.kr/fss/bbs/B0000115/list.do?menuNo=200504) 원문과 대조하기 전에는 숫자를 넣지 않는다. 세대 판정(1~4)까지만 한다.
- **CODEF는 실제 호출하지 않는다.** 내보험다보여 회원가입에 주민등록번호가 필요하고, 개인정보보호법 제24조의2상 법령 근거 없이는 처리할 수 없다. `CodefProvider`는 스키마와 필드 매핑만 두고 `fetch()`는 `NotImplementedError`를 던진다.
- **주석은 한국어로, "무엇"이 아니라 "왜"를 쓴다.** 기존 코드 스타일을 따른다.
- **새 테이블은 `Base.metadata.create_all`이 자동 생성한다.** 기존 테이블에 컬럼을 추가할 때만 `main.py`의 `_add_missing_columns`를 쓴다. 이 계획은 기존 테이블을 건드리지 않는다.
- 작업 디렉터리는 `backend/`이며 파이썬은 `backend/.venv/Scripts/python.exe`다.

## 범위 분리

스펙 §7(혜택·할인 크롤러)은 이 계획에 포함하지 않는다. 크롤 성공 여부에 결과가 좌우되는 독립 하위 시스템이라, 묶으면 핵심 기능까지 발이 묶인다. 이 계획을 끝낸 뒤 `docs/superpowers/plans/`에 별도 계획으로 작성한다.

## 파일 구조

| 파일 | 책임 |
|---|---|
| `backend/tests/conftest.py` (신규) | 인메모리 SQLite 세션 fixture |
| `backend/app/models/external.py` (신규) | `ExternalPolicy` / `ExternalCoverage` / `OverlapRule` |
| `backend/app/services/external_policy/indemnity.py` (신규) | 실손 가입시기 → 세대 판정 |
| `backend/app/services/external_policy/base.py` (신규) | DTO + `ExternalPolicyProvider` ABC |
| `backend/app/services/external_policy/manual.py` (신규) | 체크리스트 → DTO |
| `backend/app/services/external_policy/mock.py` (신규) | CODEF 형태 고정 샘플 |
| `backend/app/services/external_policy/codef.py` (신규) | 스키마·필드매핑만, 호출부 미구현 |
| `backend/app/services/external_policy/registry.py` (신규) | Provider 선택 |
| `backend/app/seed_overlap_rules.py` (신규) | 근거 조항 물린 판정 규칙 시드 |
| `backend/app/services/coverage_overlap.py` (신규) | 진단 엔진 |
| `backend/app/routers/external_policies.py` (신규) | API |
| `backend/app/schemas.py` (수정) | 요청·응답 스키마 추가 |
| `backend/app/main.py` (수정) | 라우터 등록 |
| `frontend/src/api.ts` (수정) | 클라이언트 함수·타입 |
| `frontend/src/components/ExternalPolicyPicker.tsx` (신규) | 기존보험 선택 UI (3화면 공용) |
| `frontend/src/components/OverlapReport.tsx` (신규) | 진단 결과 표시 (3화면 공용) |
| `frontend/src/pages/MyPolicies.tsx` (수정) | 기존보험 섹션 |
| `frontend/src/pages/TripPrep.tsx` (수정) | 마지막 단계 통합 |
| `frontend/src/pages/IncidentReport.tsx` (수정) | 최종 단계 통합 |

---

### Task 1: 테스트 환경과 기존보험 모델

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/app/models/external.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_external_models.py`

**Interfaces:**
- Consumes: `app.database.Base`
- Produces: `ExternalPolicy`, `ExternalCoverage`, `OverlapRule` ORM 클래스. `db_session` pytest fixture.

- [ ] **Step 1: pytest 의존성 추가**

`backend/requirements.txt` 끝에 추가:

```
# 테스트 — 진단 규칙이 근거 조항을 실제로 갖고 있는지 검증하는 데 쓴다
pytest==8.3.3
```

설치: `.venv\Scripts\python.exe -m pip install pytest==8.3.3`

- [ ] **Step 2: 테스트 fixture 작성**

`backend/tests/__init__.py` — 빈 파일.

`backend/tests/conftest.py`:

```python
"""테스트는 운영 DB(data/app.db)를 절대 건드리지 않는다 — 인메모리 SQLite를 새로 만들어 쓴다."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app import models  # noqa: F401  (모델 등록을 위해 import)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # 인메모리 DB는 연결이 끊기면 사라지므로 연결을 하나로 고정한다
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
```

- [ ] **Step 3: 실패하는 테스트 작성**

`backend/tests/test_external_models.py`:

```python
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
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_external_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.external'`

- [ ] **Step 5: 모델 작성**

`backend/app/models/external.py`:

```python
"""기존보험 도메인 — 사용자가 이 서비스 밖에서 이미 들고 있는 보험.

UserPolicy(이번 여행에 든 여행자보험)와는 성격이 달라 테이블을 나눈다. UserPolicy는
우리가 약관을 분석해 둔 6개사 상품에 매칭되지만, 기존보험은 그 밖의 상품이라 매칭 대상이
아니고, 담보도 우리 약관 DB에서 끌어올 수 없다.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ExternalPolicy(Base):
    __tablename__ = "external_policy"

    external_policy_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("app_user.user_id"), nullable=False)
    # manual(사용자가 직접 고름) / mock(연동 시연용) / codef(실연동)
    source = Column(String, nullable=False)
    # MEDICAL_INDEMNITY 실손 / ACCIDENT 상해 / DAILY_LIABILITY 일상생활배상책임 /
    # DRIVER 운전자 / OTHER 그 외
    kind = Column(String, nullable=False)
    # 사용자가 자기 보험사·상품명을 모르는 경우가 흔하다 — 몰라도 등록은 되게 둔다.
    insurer_name_raw = Column(String, nullable=True)
    product_name_raw = Column(String, nullable=True)
    # "YYYY-MM". 실손은 이 값 하나로 세대가 갈리고 세대가 보장구조를 결정한다.
    enrolled_ym = Column(String, nullable=True)
    indemnity_gen = Column(Integer, nullable=True)  # 1~4, 실손만
    # CODEF 원본 응답. 나중에 매핑 규칙이 바뀌어도 재해석할 수 있게 원본을 남긴다.
    raw_payload = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    coverages = relationship(
        "ExternalCoverage", back_populates="external_policy", cascade="all, delete-orphan"
    )


class ExternalCoverage(Base):
    __tablename__ = "external_coverage"

    external_coverage_id = Column(Integer, primary_key=True)
    external_policy_id = Column(
        Integer, ForeignKey("external_policy.external_policy_id"), nullable=False
    )
    coverage_std_id = Column(Integer, ForeignKey("coverage_std.coverage_std_id"), nullable=True)
    raw_name = Column(String)
    subscribed_amount = Column(String, nullable=True)
    # standard_terms(표준약관에서 자동) / user_input / codef / unknown
    # 화면에서 "자동 입력"과 "사용자가 직접 입력"을 구분해 보여줘야 신뢰도를 정직하게 전달할 수 있다.
    amount_source = Column(String, nullable=False, default="unknown")

    external_policy = relationship("ExternalPolicy", back_populates="coverages")
    coverage_std = relationship("CoverageStd")


class OverlapRule(Base):
    """중복 판정 규칙. 판정을 코드에 숨기지 않고 행마다 근거 조항을 물려 시드한다 —
    근거 없는 판정이 구조적으로 불가능해진다."""

    __tablename__ = "overlap_rule"

    rule_id = Column(Integer, primary_key=True)
    external_kind = Column(String, nullable=False)
    coverage_std_id = Column(
        Integer, ForeignKey("coverage_std.coverage_std_id"), nullable=False
    )
    # 같은 담보 안에서도 구간에 따라 판정이 갈린다. 예: 해외발생 질병의료비는 해외 의료기관
    # 구간에선 기존 실손과 안 겹치지만, 국내 의료기관 구간에선 겹친다.
    scope = Column(String, nullable=False, default="전체")
    # NO_OVERLAP / DUPLICATE_PRORATA / DUPLICATE_FIXED / PARTIAL / UNKNOWN
    relation = Column(String, nullable=False)
    # UNKNOWN이 아니면 반드시 있어야 한다(seed_overlap_rules.py가 검증한다).
    clause_id = Column(Integer, ForeignKey("clause.clause_id"), nullable=True)
    note = Column(Text)

    coverage_std = relationship("CoverageStd")
    clause = relationship("Clause")
```

`backend/app/models/__init__.py` 끝에 추가:

```python
from app.models.external import ExternalPolicy, ExternalCoverage, OverlapRule  # noqa: F401
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_external_models.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: 커밋**

```bash
git add backend/requirements.txt backend/tests backend/app/models/external.py backend/app/models/__init__.py
git commit -m "기존보험 모델(external_policy/external_coverage/overlap_rule)과 pytest 환경 추가"
```

---

### Task 2: 실손 세대 판정

**Files:**
- Create: `backend/app/services/external_policy/__init__.py`
- Create: `backend/app/services/external_policy/indemnity.py`
- Test: `backend/tests/test_indemnity.py`

**Interfaces:**
- Produces: `resolve_indemnity_generation(enrolled_ym: str | None) -> int | None`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_indemnity.py`:

```python
import pytest

from app.services.external_policy.indemnity import resolve_indemnity_generation


@pytest.mark.parametrize("ym,expected", [
    ("2005-01", 1),
    ("2009-09", 1),   # 1세대 마지막 달
    ("2009-10", 2),   # 2세대 첫 달
    ("2017-03", 2),   # 2세대 마지막 달
    ("2017-04", 3),   # 3세대 첫 달
    ("2021-06", 3),   # 3세대 마지막 달
    ("2021-07", 4),   # 4세대 첫 달
    ("2026-08", 4),
])
def test_가입시기로_세대를_판정한다(ym, expected):
    assert resolve_indemnity_generation(ym) == expected


@pytest.mark.parametrize("ym", [None, "", "몰라요", "2021", "2021-13", "202107"])
def test_알수없는_가입시기는_None을_돌려준다(ym):
    """세대를 모르면 추측하지 않는다 — 담보 자동채움을 건너뛰고 종류만 저장한다."""
    assert resolve_indemnity_generation(ym) is None
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_indemnity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.external_policy'`

- [ ] **Step 3: 구현 작성**

`backend/app/services/external_policy/__init__.py` — 빈 파일.

`backend/app/services/external_policy/indemnity.py`:

```python
"""실손의료보험 세대 판정.

실손은 2009년 표준화 이후 보험사별 보장내용이 동일하다. 그래서 "언제 가입했는지"만 알면
보장구조가 결정된다 — 사용자가 자기 가입금액을 몰라도 담보를 채울 수 있는 근거가 이것이다.
(보험다모아: "4세대 실손의료보험은 보험회사별 보장내용은 모두 표준화되어있지만,
보험료는 사업비 구조, 적용위험률 등에 따라 다를 수 있습니다")

세대별 자기부담률·한도 수치는 여기서 다루지 않는다. 금융감독원 표준약관 원문과 대조하기
전에는 숫자를 넣지 않는다.
"""
from __future__ import annotations

import re

_YM_RE = re.compile(r"^(\d{4})-(\d{2})$")

# (경계 년월, 그 년월까지의 세대). 위에서부터 순서대로 비교한다.
_BOUNDARIES = [
    ("2009-09", 1),
    ("2017-03", 2),
    ("2021-06", 3),
]
_LATEST_GENERATION = 4


def resolve_indemnity_generation(enrolled_ym: str | None) -> int | None:
    """가입 년월("YYYY-MM")로 실손 세대(1~4)를 정한다. 판정할 수 없으면 None.

    None을 돌려주는 경우 호출부는 담보 자동채움을 건너뛰고 보험 종류만 저장해야 한다.
    모르는 값을 그럴듯한 세대로 추측하면 근거 없는 진단이 나간다.
    """
    if not enrolled_ym:
        return None
    m = _YM_RE.match(enrolled_ym.strip())
    if not m:
        return None
    month = int(m.group(2))
    if not 1 <= month <= 12:
        return None

    for boundary, generation in _BOUNDARIES:
        if enrolled_ym <= boundary:  # "YYYY-MM"은 사전순 비교가 곧 시간순 비교다
            return generation
    return _LATEST_GENERATION
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_indemnity.py -v`
Expected: PASS (14 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/external_policy backend/tests/test_indemnity.py
git commit -m "실손 가입시기로 세대(1~4) 판정하는 유틸 추가"
```

---

### Task 3: Provider 인터페이스와 ManualProvider

**Files:**
- Create: `backend/app/services/external_policy/base.py`
- Create: `backend/app/services/external_policy/manual.py`
- Test: `backend/tests/test_manual_provider.py`

**Interfaces:**
- Consumes: `resolve_indemnity_generation` (Task 2)
- Produces: `ExternalCoverageDTO`, `ExternalPolicyDTO`, `ExternalPolicyProvider` (ABC), `ManualProvider`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_manual_provider.py`:

```python
import pytest

from app.services.external_policy.manual import ManualProvider


def test_게스트도_쓸_수_있다():
    """수동입력은 외부 인증이 필요 없으므로 로그인 없이 허용한다."""
    assert ManualProvider().requires_login is False


def test_실손은_가입시기로_세대를_채운다():
    result = ManualProvider().fetch(user=None, credentials={
        "items": [{"kind": "MEDICAL_INDEMNITY", "insurer_name_raw": "삼성화재", "enrolled_ym": "2019-05"}]
    })
    assert len(result) == 1
    assert result[0].kind == "MEDICAL_INDEMNITY"
    assert result[0].indemnity_gen == 3
    assert result[0].source == "manual"


def test_가입시기를_모르면_세대를_비워둔다():
    result = ManualProvider().fetch(user=None, credentials={
        "items": [{"kind": "MEDICAL_INDEMNITY", "enrolled_ym": None}]
    })
    assert result[0].indemnity_gen is None
    assert result[0].coverages == []


def test_실손_외_종류는_금액을_모르는_상태로_담는다():
    """상해·일상생활배상책임·운전자보험은 표준약관이 없어 회사·상품마다 담보가 다르다.
    종류만 저장하고 금액은 unknown으로 둔다 — 중복 판정 자체는 종류만으로 가능하다."""
    result = ManualProvider().fetch(user=None, credentials={
        "items": [{"kind": "DAILY_LIABILITY", "insurer_name_raw": "현대해상"}]
    })
    assert result[0].indemnity_gen is None
    assert result[0].coverages == []


def test_알수없는_종류는_거부한다():
    with pytest.raises(ValueError, match="알 수 없는 보험 종류"):
        ManualProvider().fetch(user=None, credentials={"items": [{"kind": "NOT_A_KIND"}]})
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_manual_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.external_policy.manual'`

- [ ] **Step 3: 베이스 인터페이스 작성**

`backend/app/services/external_policy/base.py`:

```python
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
    #: 외부 서비스 인증이 필요한가. False면 게스트도 쓸 수 있다.
    requires_login: bool

    @abstractmethod
    def fetch(self, *, user, credentials: dict) -> list[ExternalPolicyDTO]:
        """기존보험 목록을 가져온다. 실패는 예외로 알리고, 빈 목록으로 뭉개지 않는다."""
        raise NotImplementedError
```

- [ ] **Step 4: ManualProvider 작성**

`backend/app/services/external_policy/manual.py`:

```python
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
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_manual_provider.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/services/external_policy/base.py backend/app/services/external_policy/manual.py backend/tests/test_manual_provider.py
git commit -m "기존보험 수집 Provider 인터페이스와 수동입력 구현체 추가"
```

---

### Task 4: MockProvider, CodefProvider 스텁, registry

**Files:**
- Create: `backend/app/services/external_policy/mock.py`
- Create: `backend/app/services/external_policy/codef.py`
- Create: `backend/app/services/external_policy/registry.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_provider_registry.py`

**Interfaces:**
- Consumes: `ExternalPolicyProvider`, `ExternalPolicyDTO` (Task 3)
- Produces: `MockProvider`, `CodefProvider`, `get_provider(name) -> ExternalPolicyProvider`, `list_available_providers() -> list[ExternalPolicyProvider]`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_provider_registry.py`:

```python
import pytest

from app.services.external_policy.base import ExternalPolicyDTO
from app.services.external_policy.registry import get_provider, list_available_providers


def test_이름으로_구현체를_고른다():
    assert get_provider("manual").name == "manual"
    assert get_provider("mock").name == "mock"


def test_등록되지_않은_이름은_거부한다():
    with pytest.raises(ValueError, match="지원하지 않는 수집 방식"):
        get_provider("없는provider")


def test_기본_사용가능_목록에_codef는_없다():
    """CODEF는 주민등록번호 처리 요건을 갖추기 전까지 꺼둔다."""
    names = [p.name for p in list_available_providers()]
    assert "manual" in names
    assert "mock" in names
    assert "codef" not in names


def test_mock은_CODEF_형태의_샘플을_돌려준다():
    result = get_provider("mock").fetch(user=None, credentials={})
    assert len(result) >= 2
    assert all(isinstance(p, ExternalPolicyDTO) for p in result)
    assert all(p.source == "mock" for p in result)
    # 실연동 전환 시 스키마가 그대로 쓰이도록 원본 payload를 함께 담는다
    assert all(p.raw_payload is not None for p in result)


def test_codef는_아직_호출할_수_없다():
    with pytest.raises(NotImplementedError, match="CODEF 연동"):
        get_provider("codef").fetch(user=None, credentials={})


def test_세_구현체가_모두_같은_DTO_형태를_돌려준다():
    """수집 방식이 달라도 저장·진단·화면이 구분하지 않게 하려면 반환 형태가 같아야 한다."""
    manual = get_provider("manual").fetch(
        user=None, credentials={"items": [{"kind": "ACCIDENT"}]}
    )
    mock = get_provider("mock").fetch(user=None, credentials={})
    for dto in manual + mock:
        assert isinstance(dto, ExternalPolicyDTO)
        assert isinstance(dto.coverages, list)
        assert dto.kind
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_provider_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.external_policy.registry'`

- [ ] **Step 3: MockProvider 작성**

`backend/app/services/external_policy/mock.py`:

```python
"""연동 UX 전체(버튼 → 로딩 → 결과)를 실제 CODEF 없이 시연하기 위한 고정 샘플.

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
    requires_login = True

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
```

- [ ] **Step 4: CodefProvider 스텁 작성**

`backend/app/services/external_policy/codef.py`:

```python
"""CODEF 실연동 자리 — 지금은 스키마와 매핑 규칙만 두고 호출하지 않는다.

왜 미구현인가:
  신용정보원 '내보험다보여' 회원가입에는 주민등록번호가 필요하다. 개인정보보호법 제24조의2는
  주민등록번호를 법령에 구체적 근거가 있을 때만 처리하도록 하고, 정보주체 동의로 갈음할 수
  없다. 이 서비스에는 그 근거가 없다. 운영 주체가 법적 요건을 갖춘 뒤 fetch()를 채우고
  EXTERNAL_POLICY_PROVIDERS에 codef를 넣어 활성화한다.

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
    requires_login = True

    def fetch(self, *, user, credentials: dict) -> list[ExternalPolicyDTO]:
        raise NotImplementedError(
            "CODEF 연동은 아직 설정되지 않았습니다. "
            "주민등록번호 처리 근거(개인정보보호법 제24조의2)를 갖춘 뒤 활성화하세요."
        )
```

- [ ] **Step 5: registry와 설정 작성**

`backend/app/config.py` 끝에 추가:

```python
# 기존보험 수집에 쓸 방식. codef는 주민등록번호 처리 요건을 갖춘 뒤에만 켠다.
EXTERNAL_POLICY_PROVIDERS = [
    p.strip() for p in os.getenv("EXTERNAL_POLICY_PROVIDERS", "manual,mock").split(",")
    if p.strip()
]
```

`backend/app/services/external_policy/registry.py`:

```python
"""활성 Provider 관리.

프론트는 list_available_providers() 결과로 버튼을 그린다 — 그래서 CODEF가 꺼져 있으면
버튼 자체가 안 보이고, 환경변수만 켜면 나타난다. 프론트 코드를 고칠 필요가 없다.
"""
from __future__ import annotations

from app import config
from app.services.external_policy.base import ExternalPolicyProvider
from app.services.external_policy.codef import CodefProvider
from app.services.external_policy.manual import ManualProvider
from app.services.external_policy.mock import MockProvider

_ALL: dict[str, ExternalPolicyProvider] = {
    p.name: p for p in (ManualProvider(), MockProvider(), CodefProvider())
}


def get_provider(name: str) -> ExternalPolicyProvider:
    provider = _ALL.get(name)
    if provider is None:
        raise ValueError(f"지원하지 않는 수집 방식: {name}")
    return provider


def list_available_providers() -> list[ExternalPolicyProvider]:
    """설정으로 켜 둔 것만 돌려준다. 순서는 설정에 적은 순서를 따른다."""
    return [_ALL[n] for n in config.EXTERNAL_POLICY_PROVIDERS if n in _ALL]
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_provider_registry.py -v`
Expected: PASS (6 passed)

- [ ] **Step 7: 커밋**

```bash
git add backend/app/services/external_policy backend/app/config.py backend/tests/test_provider_registry.py
git commit -m "Mock·CODEF 스텁 Provider와 registry 추가 — 환경변수로 수집 방식 전환"
```

---

### Task 5: 중복 판정 규칙 시드

**Files:**
- Create: `backend/app/seed_overlap_rules.py`
- Test: `backend/tests/test_overlap_rules_seed.py`

**Interfaces:**
- Consumes: `OverlapRule` (Task 1)
- Produces: `seed_overlap_rules(db) -> int` (삽입한 행 수), `RULE_SPECS` 상수

**배경:** clause_id를 상수로 박으면 약관을 재시드할 때 어긋난다. 보험사명 + 조항 제목 조각으로 조회해 붙이고, 못 찾으면 조용히 넘어가지 않고 예외를 던진다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_overlap_rules_seed.py`:

```python
from app.models.external import OverlapRule
from app.seed_overlap_rules import RULE_SPECS


def test_UNKNOWN이_아닌_규칙은_모두_근거조항_조회조건을_갖는다():
    """근거 없는 판정을 구조적으로 막는다 — 이 테스트가 그 계약을 강제한다."""
    for spec in RULE_SPECS:
        if spec["relation"] != "UNKNOWN":
            assert spec.get("clause_lookup"), f"근거 없는 규칙: {spec}"


def test_같은_담보_구간_조합이_중복되지_않는다():
    seen = set()
    for spec in RULE_SPECS:
        key = (spec["external_kind"], spec["coverage_std_code"], spec["scope"])
        assert key not in seen, f"중복된 규칙 키: {key}"
        seen.add(key)


def test_relation은_정의된_값만_쓴다():
    allowed = {"NO_OVERLAP", "DUPLICATE_PRORATA", "DUPLICATE_FIXED", "PARTIAL", "UNKNOWN"}
    for spec in RULE_SPECS:
        assert spec["relation"] in allowed


def test_실손과_해외의료비는_겹치지_않는다고_판정한다():
    """기존 실손은 국내 의료기관만 보상한다 — '실손 있으니 해외의료비를 빼라'는 조언은 틀렸다."""
    specs = [
        s for s in RULE_SPECS
        if s["external_kind"] == "MEDICAL_INDEMNITY"
        and s["coverage_std_code"] == "OVS_INJ_MED"
    ]
    assert len(specs) == 1
    assert specs[0]["relation"] == "NO_OVERLAP"


def test_질병의료비는_구간에_따라_판정이_갈린다():
    specs = {
        s["scope"]: s["relation"] for s in RULE_SPECS
        if s["external_kind"] == "MEDICAL_INDEMNITY"
        and s["coverage_std_code"] == "OVS_ILL_MED"
    }
    assert specs["해외 의료기관"] == "NO_OVERLAP"
    assert specs["국내 의료기관"] == "PARTIAL"


def test_시드는_빈_DB에서도_돌고_결과를_남긴다(db_session):
    """근거 조항이 없는 테스트 DB에서는 아무 행도 넣지 않되 예외도 내지 않는다
    (운영 DB 시드는 별도로 조항 존재를 검증한다)."""
    from app.seed_overlap_rules import seed_overlap_rules
    inserted = seed_overlap_rules(db_session, strict=False)
    assert inserted == 0
    assert db_session.query(OverlapRule).count() == 0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_overlap_rules_seed.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.seed_overlap_rules'`

- [ ] **Step 3: 시드 스크립트 작성**

`backend/app/seed_overlap_rules.py`:

```python
"""기존보험 × 여행자보험 담보의 중복 판정 규칙을 시드한다.

판정을 코드에 숨기지 않고 데이터로 두는 이유: 행마다 근거 조항을 물려야 근거 없는 판정이
구조적으로 불가능해진다. relation이 UNKNOWN이 아닌 규칙은 반드시 실제 clause를 찾아 붙이고,
못 찾으면(strict=True) 예외를 던진다 — 조용히 빠뜨리면 근거 없이 단정하는 결과가 나간다.

clause_id를 상수로 박지 않는 이유: 약관을 재시드하면 id가 어긋난다. 보험사명과 조항 제목
조각으로 조회한다.

    python -m app.seed_overlap_rules
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.external import OverlapRule
from app.models.kb import Clause, Coverage, CoverageStd, Insurer, PolicyVersion, Product

#: 각 규칙의 근거 조항은 (보험사명 조각, 조항 제목 조각)으로 찾는다.
RULE_SPECS: list[dict] = [
    {
        "external_kind": "MEDICAL_INDEMNITY",
        "coverage_std_code": "OVS_INJ_MED",
        "scope": "해외 의료기관",
        "relation": "NO_OVERLAP",
        "clause_lookup": ("삼성화재", "(1)상해-해외의료비"),
        "note": "기존 실손의료보험은 국내 의료기관 진료만 보상한다. 해외 현지에서 쓴 상해 치료비는 "
                "여행자보험에서만 나오므로 이 담보는 여전히 필요하다.",
    },
    {
        "external_kind": "MEDICAL_INDEMNITY",
        "coverage_std_code": "OVS_ILL_MED",
        "scope": "해외 의료기관",
        "relation": "NO_OVERLAP",
        "clause_lookup": ("삼성화재", "(2)질병의료비-해외"),
        "note": "해외 현지 질병 치료비도 기존 실손으로는 보상받지 못한다.",
    },
    {
        "external_kind": "MEDICAL_INDEMNITY",
        "coverage_std_code": "OVS_ILL_MED",
        "scope": "국내 의료기관",
        "relation": "PARTIAL",
        "clause_lookup": ("삼성화재", "국내 의료기관 의료비"),
        "note": "귀국 후 국내에서 이어 받는 치료는 기존 실손과 겹친다. 실제 부담한 금액을 넘겨 "
                "이중으로 받지는 못한다.",
    },
    {
        "external_kind": "DAILY_LIABILITY",
        "coverage_std_code": "LIABILITY",
        "scope": "전체",
        "relation": "DUPLICATE_PRORATA",
        "clause_lookup": ("삼성화재", "의무보험과의 관계"),
        "note": "기존 일상생활배상책임 특약과 겹친다. 초과액만 보상하므로 두 개를 들어도 "
                "받는 총액이 늘지 않는다.",
    },
    {
        "external_kind": "ACCIDENT",
        "coverage_std_code": "DEATH_INJURY",
        "scope": "전체",
        "relation": "DUPLICATE_FIXED",
        "clause_lookup": ("삼성화재", "상해사망"),
        "note": "정액 지급 담보라 기존 상해보험과 겹쳐도 각각 다 받는다. 실손형과 달리 "
                "중복가입이 손해가 아니다.",
    },
    {
        "external_kind": "OTHER",
        "coverage_std_code": "PASSPORT_LOSS",
        "scope": "전체",
        "relation": "DUPLICATE_PRORATA",
        "clause_lookup": ("삼성화재", "여권분실"),
        "note": "보험금을 지급할 다른 계약이 있으면 비율에 따라 나눠 지급한다.",
    },
    {
        "external_kind": "OTHER",
        "coverage_std_code": "HIJACK",
        "scope": "전체",
        "relation": "DUPLICATE_PRORATA",
        "clause_lookup": ("현대해상", "다른 보험과의 관계"),
        "note": "유사한 다수 계약이 있으면 그중 하나에서만 보상하고, 나머지 계약의 보험료는 "
                "돌려받는다.",
    },
]


def _find_clause(db: Session, insurer_frag: str, article_frag: str) -> Clause | None:
    """보험사명·조항 제목 조각으로 근거 조항을 찾는다. 여러 개면 가장 앞선 것을 쓴다."""
    return (
        db.query(Clause)
        .join(PolicyVersion, PolicyVersion.policy_version_id == Clause.policy_version_id)
        .join(Product, Product.product_id == PolicyVersion.product_id)
        .join(Insurer, Insurer.insurer_id == Product.insurer_id)
        .filter(Insurer.name.like(f"%{insurer_frag}%"))
        .filter(Clause.article_no.like(f"%{article_frag}%"))
        .order_by(Clause.clause_id)
        .first()
    )


def seed_overlap_rules(db: Session, *, strict: bool = True) -> int:
    """규칙을 다시 심는다. 기존 행은 지우고 새로 넣는다(멱등).

    strict=True면 근거 조항을 못 찾은 규칙에서 예외를 던진다. 운영 시드는 반드시 strict로
    돌린다 — 근거를 못 찾았는데 넘어가면 판정만 남고 근거가 사라진다.
    """
    db.query(OverlapRule).delete()

    inserted = 0
    missing: list[str] = []
    for spec in RULE_SPECS:
        std = (
            db.query(CoverageStd)
            .filter(CoverageStd.std_code == spec["coverage_std_code"])
            .first()
        )
        if std is None:
            missing.append(f"표준담보 없음: {spec['coverage_std_code']}")
            continue

        clause = None
        if spec["relation"] != "UNKNOWN":
            clause = _find_clause(db, *spec["clause_lookup"])
            if clause is None:
                missing.append(
                    f"근거 조항 없음: {spec['coverage_std_code']} / {spec['clause_lookup']}"
                )
                continue

        db.add(OverlapRule(
            external_kind=spec["external_kind"],
            coverage_std_id=std.coverage_std_id,
            scope=spec["scope"],
            relation=spec["relation"],
            clause_id=clause.clause_id if clause else None,
            note=spec["note"],
        ))
        inserted += 1

    if missing and strict:
        db.rollback()
        raise RuntimeError("근거를 찾지 못한 규칙이 있습니다:\n  " + "\n  ".join(missing))

    db.commit()
    return inserted


def main() -> None:
    db = SessionLocal()
    try:
        count = seed_overlap_rules(db)
        print(f"중복 판정 규칙 {count}건 시드 완료")
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_overlap_rules_seed.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: 실제 DB에 시드하고 근거가 다 붙었는지 확인**

Run: `cd backend && .venv\Scripts\python.exe -m app.seed_overlap_rules`
Expected: `중복 판정 규칙 7건 시드 완료`

7건이 아니거나 `RuntimeError`가 나면 **멈추고 보고한다.** 조회 조각(`clause_lookup`)이 실제 `article_no`와 안 맞는다는 뜻이므로, DB에서 실제 조항 제목을 확인해 조각을 고친 뒤 다시 돌린다. 근거를 못 찾은 규칙을 지우고 넘어가지 않는다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/seed_overlap_rules.py backend/tests/test_overlap_rules_seed.py
git commit -m "중복 판정 규칙 시드 추가 — 규칙마다 약관 근거 조항을 조회해 물린다"
```

---

### Task 6: 진단 엔진

**Files:**
- Create: `backend/app/services/coverage_overlap.py`
- Test: `backend/tests/test_coverage_overlap.py`

**Interfaces:**
- Consumes: `OverlapRule`, `ExternalPolicy` (Task 1)
- Produces: `diagnose(db, *, external_policies, target_coverage_std_ids) -> OverlapReport`, 데이터클래스 `OverlapFinding`, `OverlapReport`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_coverage_overlap.py`:

```python
import pytest

from app.models.external import ExternalPolicy, OverlapRule
from app.models.kb import Clause, CoverageStd
from app.services.coverage_overlap import diagnose


@pytest.fixture
def seeded(db_session):
    db_session.add(CoverageStd(
        coverage_std_id=2, std_code="OVS_INJ_MED", std_name="해외발생 상해의료비",
        category="의료", is_base=0,
    ))
    db_session.add(CoverageStd(
        coverage_std_id=6, std_code="LIABILITY", std_name="배상책임",
        category="배상책임", is_base=0,
    ))
    db_session.add(Clause(
        clause_id=901, policy_version_id=1, article_no="제3조",
        clause_type="보장정의",
        text="회사는 보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다.",
    ))
    db_session.add(OverlapRule(
        external_kind="MEDICAL_INDEMNITY", coverage_std_id=2, scope="해외 의료기관",
        relation="NO_OVERLAP", clause_id=901, note="해외 진료는 기존 실손으로 보상되지 않는다",
    ))
    db_session.add(OverlapRule(
        external_kind="DAILY_LIABILITY", coverage_std_id=6, scope="전체",
        relation="DUPLICATE_PRORATA", clause_id=901, note="초과액만 보상한다",
    ))
    db_session.commit()
    return db_session


def test_기존보험이_없으면_모두_확인대상에서_빠진다(seeded):
    report = diagnose(seeded, external_policies=[], target_coverage_std_ids=[2, 6])
    assert report.duplicates == []
    assert report.gaps == []
    assert report.fixed_ok == []


def test_실손이_있으면_해외의료비는_공백으로_잡힌다(seeded):
    policy = ExternalPolicy(user_id=1, source="manual", kind="MEDICAL_INDEMNITY")
    seeded.add(policy)
    seeded.commit()

    report = diagnose(seeded, external_policies=[policy], target_coverage_std_ids=[2])
    assert len(report.gaps) == 1
    finding = report.gaps[0]
    assert finding.coverage_std_code == "OVS_INJ_MED"
    assert finding.relation == "NO_OVERLAP"
    assert finding.clause_id == 901


def test_일상배상책임이_있으면_배상책임은_중복으로_잡힌다(seeded):
    policy = ExternalPolicy(user_id=1, source="manual", kind="DAILY_LIABILITY")
    seeded.add(policy)
    seeded.commit()

    report = diagnose(seeded, external_policies=[policy], target_coverage_std_ids=[6])
    assert len(report.duplicates) == 1
    assert report.duplicates[0].relation == "DUPLICATE_PRORATA"


def test_규칙이_없는_조합은_확인불가로_남는다(seeded):
    """근거가 없으면 단정하지 않는다."""
    policy = ExternalPolicy(user_id=1, source="manual", kind="DRIVER")
    seeded.add(policy)
    seeded.commit()

    report = diagnose(seeded, external_policies=[policy], target_coverage_std_ids=[2, 6])
    assert len(report.unknown) == 2
    assert all(f.relation == "UNKNOWN" for f in report.unknown)
    assert all(f.clause_id is None for f in report.unknown)


def test_인용문은_조항_원문의_부분_문자열이다(seeded):
    policy = ExternalPolicy(user_id=1, source="manual", kind="MEDICAL_INDEMNITY")
    seeded.add(policy)
    seeded.commit()

    report = diagnose(seeded, external_policies=[policy], target_coverage_std_ids=[2])
    clause = seeded.query(Clause).filter(Clause.clause_id == 901).one()
    quote = report.gaps[0].clause_quote
    assert quote
    assert quote in clause.text
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_coverage_overlap.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.coverage_overlap'`

- [ ] **Step 3: 진단 엔진 작성**

`backend/app/services/coverage_overlap.py`:

```python
"""기존보험과 이번 여행자보험 담보의 겹침·공백을 진단한다.

조회할 때마다 계산하고 저장하지 않는다 — 약관 DB가 갱신되면 결과도 자동으로 따라오고,
데이터가 작아(담보 수십 개) 성능 문제가 없다. 저장하면 약관이 바뀌었을 때 낡은 결과가 남는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.external import ExternalPolicy, OverlapRule
from app.models.kb import Clause, CoverageStd

#: 인용문 최대 길이. 화면에 넣기 좋은 만큼만 자른다.
_QUOTE_LIMIT = 200


@dataclass
class OverlapFinding:
    coverage_std_id: int
    coverage_std_code: str
    coverage_std_name: str
    external_kind: str
    scope: str
    relation: str
    note: str | None = None
    clause_id: int | None = None
    clause_article_no: str | None = None
    #: 근거 조항 원문의 부분 문자열. 원문에 없는 글자는 절대 담지 않는다.
    clause_quote: str | None = None


@dataclass
class OverlapReport:
    duplicates: list[OverlapFinding] = field(default_factory=list)
    gaps: list[OverlapFinding] = field(default_factory=list)
    fixed_ok: list[OverlapFinding] = field(default_factory=list)
    unknown: list[OverlapFinding] = field(default_factory=list)


def _quote(clause: Clause | None) -> str | None:
    """조항 원문 앞부분을 인용용으로 자른다. 자르기만 하므로 결과는 항상 원문의 부분 문자열이다."""
    if clause is None or not clause.text:
        return None
    text = clause.text.strip()
    return text[:_QUOTE_LIMIT] if len(text) > _QUOTE_LIMIT else text


def diagnose(
    db: Session, *, external_policies: list[ExternalPolicy], target_coverage_std_ids: list[int]
) -> OverlapReport:
    """기존보험 목록과 검토할 담보 목록을 받아 진단 결과를 만든다.

    기존보험이 하나도 없으면 비교 대상이 없으므로 빈 보고서를 돌려준다.
    """
    report = OverlapReport()
    if not external_policies or not target_coverage_std_ids:
        return report

    kinds = {p.kind for p in external_policies}

    stds = {
        s.coverage_std_id: s
        for s in db.query(CoverageStd)
        .filter(CoverageStd.coverage_std_id.in_(target_coverage_std_ids))
        .all()
    }
    rules = (
        db.query(OverlapRule)
        .filter(OverlapRule.external_kind.in_(kinds))
        .filter(OverlapRule.coverage_std_id.in_(target_coverage_std_ids))
        .all()
    )
    clauses = {
        c.clause_id: c
        for c in db.query(Clause)
        .filter(Clause.clause_id.in_([r.clause_id for r in rules if r.clause_id]))
        .all()
    } if rules else {}

    matched_std_ids = set()
    for rule in rules:
        std = stds.get(rule.coverage_std_id)
        if std is None:
            continue
        matched_std_ids.add(rule.coverage_std_id)
        clause = clauses.get(rule.clause_id) if rule.clause_id else None
        finding = OverlapFinding(
            coverage_std_id=std.coverage_std_id,
            coverage_std_code=std.std_code,
            coverage_std_name=std.std_name,
            external_kind=rule.external_kind,
            scope=rule.scope,
            relation=rule.relation,
            note=rule.note,
            clause_id=rule.clause_id,
            clause_article_no=clause.article_no if clause else None,
            clause_quote=_quote(clause),
        )
        if rule.relation in ("DUPLICATE_PRORATA", "PARTIAL"):
            report.duplicates.append(finding)
        elif rule.relation == "DUPLICATE_FIXED":
            report.fixed_ok.append(finding)
        elif rule.relation == "NO_OVERLAP":
            report.gaps.append(finding)
        else:
            report.unknown.append(finding)

    # 규칙이 없는 조합은 조용히 빠뜨리지 않고 "확인불가"로 남긴다 — 근거가 없다는 사실 자체가
    # 사용자에게 전달돼야 할 정보다.
    for std_id in target_coverage_std_ids:
        if std_id in matched_std_ids:
            continue
        std = stds.get(std_id)
        if std is None:
            continue
        report.unknown.append(OverlapFinding(
            coverage_std_id=std.coverage_std_id,
            coverage_std_code=std.std_code,
            coverage_std_name=std.std_name,
            external_kind=",".join(sorted(kinds)),
            scope="전체",
            relation="UNKNOWN",
            note="이 조합에 대한 약관 근거를 찾지 못했습니다.",
        ))

    return report
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_coverage_overlap.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/coverage_overlap.py backend/tests/test_coverage_overlap.py
git commit -m "기존보험 대비 중복·공백 진단 엔진 추가 — 조회 시점 계산, 근거 원문 동봉"
```

---

### Task 7: API

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `backend/app/routers/external_policies.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_external_policies_api.py`

**Interfaces:**
- Consumes: `get_provider`, `list_available_providers` (Task 4), `diagnose` (Task 6)
- Produces: 라우터 `external_policies.router`, prefix `/users/{user_id}/external-policies`

- [ ] **Step 1: 스키마 추가**

`backend/app/schemas.py` 끝에 추가:

```python
class ExternalPolicyLinkItem(BaseModel):
    kind: str
    insurer_name_raw: Optional[str] = None
    product_name_raw: Optional[str] = None
    enrolled_ym: Optional[str] = None


class ExternalPolicyLinkRequest(BaseModel):
    """등록 진입점은 수집 방식과 무관하게 하나다 — 수동입력도 provider='manual'로 들어온다."""
    provider: str = "manual"
    items: list[ExternalPolicyLinkItem] = []


class ExternalCoverageOut(BaseModel):
    external_coverage_id: int
    raw_name: Optional[str] = None
    subscribed_amount: Optional[str] = None
    amount_source: str

    class Config:
        from_attributes = True


class ExternalPolicyOut(BaseModel):
    external_policy_id: int
    source: str
    kind: str
    insurer_name_raw: Optional[str] = None
    product_name_raw: Optional[str] = None
    enrolled_ym: Optional[str] = None
    indemnity_gen: Optional[int] = None
    coverages: list[ExternalCoverageOut] = []

    class Config:
        from_attributes = True


class ProviderOut(BaseModel):
    name: str
    requires_login: bool


class OverlapFindingOut(BaseModel):
    coverage_std_code: str
    coverage_std_name: str
    external_kind: str
    scope: str
    relation: str
    note: Optional[str] = None
    clause_id: Optional[int] = None
    clause_article_no: Optional[str] = None
    clause_quote: Optional[str] = None


class OverlapReportOut(BaseModel):
    duplicates: list[OverlapFindingOut] = []
    gaps: list[OverlapFindingOut] = []
    fixed_ok: list[OverlapFindingOut] = []
    unknown: list[OverlapFindingOut] = []
```

- [ ] **Step 2: 실패하는 테스트 작성**

`backend/tests/test_external_policies_api.py`:

```python
from app.services.external_policy.registry import get_provider, list_available_providers


def test_사용가능한_수집방식에_codef는_빠져있다():
    payload = [{"name": p.name, "requires_login": p.requires_login}
               for p in list_available_providers()]
    names = [p["name"] for p in payload]
    assert "manual" in names
    assert "codef" not in names


def test_게스트가_로그인필요_provider를_쓰면_막아야_한다():
    """라우터가 이 플래그를 보고 401을 낸다 — 플래그 자체가 계약이다."""
    assert get_provider("mock").requires_login is True
    assert get_provider("manual").requires_login is False
```

- [ ] **Step 3: 테스트 실행**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_external_policies_api.py -v`
Expected: PASS (2 passed) — Task 4에서 만든 registry로 이미 통과한다. 라우터가 이 계약을 지키는지는 Step 5 수동 확인으로 검증한다.

- [ ] **Step 4: 라우터 작성**

`backend/app/routers/external_policies.py`:

```python
"""기존보험 등록·조회와 중복보장 진단 API."""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.external import ExternalCoverage, ExternalPolicy
from app.models.kb import Coverage, CoverageStd
from app.models.user import AppUser, Trip, UserPolicy
from app.routers.auth import get_current_user_optional, verify_owner
from app.schemas import (
    ExternalPolicyLinkRequest, ExternalPolicyOut, OverlapReportOut, ProviderOut,
)
from app.services.coverage_overlap import diagnose
from app.services.external_policy.registry import get_provider, list_available_providers

router = APIRouter(prefix="/users/{user_id}/external-policies", tags=["external-policies"])


@router.get("/providers", response_model=list[ProviderOut])
def list_providers(user_id: int):
    """프론트는 이 목록으로 버튼을 그린다 — CODEF가 꺼져 있으면 버튼 자체가 안 보인다."""
    return [ProviderOut(name=p.name, requires_login=p.requires_login)
            for p in list_available_providers()]


@router.get("", response_model=list[ExternalPolicyOut])
def list_external_policies(
    user_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    verify_owner(user_id, current)
    return db.query(ExternalPolicy).filter(ExternalPolicy.user_id == user_id).all()


@router.post("/link", response_model=list[ExternalPolicyOut])
def link_external_policies(
    user_id: int, payload: ExternalPolicyLinkRequest, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """등록 진입점 하나로 모든 수집 방식을 받는다 — 방식이 늘어도 라우터는 바뀌지 않는다."""
    verify_owner(user_id, current)
    if not db.get(AppUser, user_id):
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    try:
        provider = get_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    available = {p.name for p in list_available_providers()}
    if provider.name not in available:
        raise HTTPException(status_code=400, detail=f"'{provider.name}' 연동은 아직 사용할 수 없습니다.")

    # 외부 인증이 필요한 방식은 로그인 계정에서만 — 게스트는 자격증명을 안전하게 보관할 곳이 없다.
    if provider.requires_login and (current is None or current.auth_provider == "guest"):
        raise HTTPException(status_code=401, detail="이 연동은 로그인 후 이용할 수 있습니다.")

    credentials = {"items": [i.model_dump() for i in payload.items]}
    try:
        dtos = provider.fetch(user=current, credentials=credentials)
    except NotImplementedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    created = []
    for dto in dtos:
        policy = ExternalPolicy(
            user_id=user_id, source=dto.source, kind=dto.kind,
            insurer_name_raw=dto.insurer_name_raw, product_name_raw=dto.product_name_raw,
            enrolled_ym=dto.enrolled_ym, indemnity_gen=dto.indemnity_gen,
            raw_payload=json.dumps(dto.raw_payload, ensure_ascii=False) if dto.raw_payload else None,
        )
        db.add(policy)
        db.flush()
        for cov in dto.coverages:
            std = (
                db.query(CoverageStd)
                .filter(CoverageStd.std_code == cov.coverage_std_code).first()
                if cov.coverage_std_code else None
            )
            db.add(ExternalCoverage(
                external_policy_id=policy.external_policy_id,
                coverage_std_id=std.coverage_std_id if std else None,
                raw_name=cov.raw_name, subscribed_amount=cov.subscribed_amount,
                amount_source=cov.amount_source,
            ))
        created.append(policy)

    db.commit()
    for p in created:
        db.refresh(p)
    return created


@router.delete("/{external_policy_id}")
def delete_external_policy(
    user_id: int, external_policy_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    verify_owner(user_id, current)
    policy = db.get(ExternalPolicy, external_policy_id)
    if not policy or policy.user_id != user_id:
        raise HTTPException(status_code=404, detail="기존보험 정보를 찾을 수 없습니다.")
    db.delete(policy)
    db.commit()
    return {"status": "deleted"}
```

`backend/app/routers/external_policies.py` 끝에 진단 라우터를 별도 prefix로 추가:

```python
overlap_router = APIRouter(prefix="/users/{user_id}", tags=["external-policies"])


@overlap_router.get("/coverage-overlap", response_model=OverlapReportOut)
def coverage_overlap(
    user_id: int,
    trip_id: int | None = Query(default=None),
    user_policy_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """검토 대상 담보는 등록된 여행자보험에서 가져온다. trip_id를 주면 그 여행에 묶인 보험을 쓴다."""
    verify_owner(user_id, current)

    if user_policy_id is None and trip_id is not None:
        trip = db.get(Trip, trip_id)
        if trip and trip.user_id == user_id:
            user_policy_id = trip.user_policy_id

    target_ids: list[int] = []
    if user_policy_id is not None:
        policy = db.get(UserPolicy, user_policy_id)
        if policy and policy.user_id == user_id and policy.policy_version_id:
            target_ids = [
                c.coverage_std_id
                for c in db.query(Coverage)
                .filter(Coverage.policy_version_id == policy.policy_version_id).all()
                if c.coverage_std_id
            ]

    external = db.query(ExternalPolicy).filter(ExternalPolicy.user_id == user_id).all()
    report = diagnose(db, external_policies=external, target_coverage_std_ids=sorted(set(target_ids)))
    return OverlapReportOut(
        duplicates=[f.__dict__ for f in report.duplicates],
        gaps=[f.__dict__ for f in report.gaps],
        fixed_ok=[f.__dict__ for f in report.fixed_ok],
        unknown=[f.__dict__ for f in report.unknown],
    )
```

`backend/app/main.py`의 import 줄에 `external_policies`를 추가하고, 라우터 등록부에 추가:

```python
from app.routers import users, trips, policies, incidents, insurers, auth, clauses, external_policies
...
app.include_router(external_policies.router)
app.include_router(external_policies.overlap_router)
```

- [ ] **Step 5: 서버를 띄워 실제로 확인**

Run: `cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000`

http://127.0.0.1:8000/docs 에서 확인:
1. `GET /users/1/external-policies/providers` → `manual`, `mock` 두 개가 나오고 `codef`는 없다
2. `POST /users/1/external-policies/link` 에 `{"provider":"manual","items":[{"kind":"MEDICAL_INDEMNITY","enrolled_ym":"2019-05"}]}` → `indemnity_gen: 3`으로 저장된다
3. `GET /users/1/external-policies` → 방금 등록한 것이 나온다
4. `GET /users/1/coverage-overlap` → 200이 나온다(여행자보험이 없으면 전부 빈 배열)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/schemas.py backend/app/routers/external_policies.py backend/app/main.py backend/tests/test_external_policies_api.py
git commit -m "기존보험 등록·조회·진단 API 추가 — 등록 진입점은 provider 무관하게 /link 하나"
```

---

### Task 8: 프론트 공용 컴포넌트와 내 보험 화면

**Files:**
- Modify: `frontend/src/api.ts`
- Create: `frontend/src/components/ExternalPolicyPicker.tsx`
- Create: `frontend/src/components/OverlapReport.tsx`
- Modify: `frontend/src/pages/MyPolicies.tsx`

**Interfaces:**
- Consumes: Task 7의 API
- Produces: `api.listProviders`, `api.listExternalPolicies`, `api.linkExternalPolicies`, `api.deleteExternalPolicy`, `api.getCoverageOverlap`; 컴포넌트 `<ExternalPolicyPicker>`, `<OverlapReportView>`

- [ ] **Step 1: API 클라이언트에 타입과 함수 추가**

`frontend/src/api.ts`에 타입을 추가한다(기존 타입 정의부 끝):

```typescript
export type ExternalPolicyKind =
  | "MEDICAL_INDEMNITY" | "ACCIDENT" | "DAILY_LIABILITY" | "DRIVER" | "OTHER";

export interface ExternalPolicyOut {
  external_policy_id: number;
  source: string;
  kind: ExternalPolicyKind;
  insurer_name_raw: string | null;
  product_name_raw: string | null;
  enrolled_ym: string | null;
  indemnity_gen: number | null;
  coverages: { external_coverage_id: number; raw_name: string | null; subscribed_amount: string | null; amount_source: string }[];
}

export interface ProviderOut {
  name: string;
  requires_login: boolean;
}

export interface OverlapFindingOut {
  coverage_std_code: string;
  coverage_std_name: string;
  external_kind: string;
  scope: string;
  relation: "NO_OVERLAP" | "DUPLICATE_PRORATA" | "DUPLICATE_FIXED" | "PARTIAL" | "UNKNOWN";
  note: string | null;
  clause_id: number | null;
  clause_article_no: string | null;
  clause_quote: string | null;
}

export interface OverlapReportOut {
  duplicates: OverlapFindingOut[];
  gaps: OverlapFindingOut[];
  fixed_ok: OverlapFindingOut[];
  unknown: OverlapFindingOut[];
}
```

`api` 객체 안에 함수를 추가한다:

```typescript
  listProviders: (userId: number) =>
    request<ProviderOut[]>(`/users/${userId}/external-policies/providers`),

  listExternalPolicies: (userId: number) =>
    request<ExternalPolicyOut[]>(`/users/${userId}/external-policies`),

  linkExternalPolicies: (
    userId: number,
    body: { provider: string; items: { kind: string; insurer_name_raw?: string | null; enrolled_ym?: string | null }[] },
  ) =>
    request<ExternalPolicyOut[]>(`/users/${userId}/external-policies/link`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteExternalPolicy: (userId: number, id: number) =>
    request<{ status: string }>(`/users/${userId}/external-policies/${id}`, { method: "DELETE" }),

  getCoverageOverlap: (userId: number, params: { tripId?: number; userPolicyId?: number }) => {
    const q = new URLSearchParams();
    if (params.tripId) q.set("trip_id", String(params.tripId));
    if (params.userPolicyId) q.set("user_policy_id", String(params.userPolicyId));
    return request<OverlapReportOut>(`/users/${userId}/coverage-overlap?${q.toString()}`);
  },
```

- [ ] **Step 2: 기존보험 선택 컴포넌트 작성**

`frontend/src/components/ExternalPolicyPicker.tsx`:

```tsx
import { useState } from "react";
import type { ExternalPolicyKind } from "../api";
import { InsurerPicker } from "./InsurerPicker";

/** 기존보험 선택 UI. 내 보험·여행 준비·사고 접수 세 화면이 같이 쓴다. */

export const KIND_LABELS: Record<ExternalPolicyKind, string> = {
  MEDICAL_INDEMNITY: "실손의료비(실비)",
  ACCIDENT: "상해보험",
  DAILY_LIABILITY: "일상생활배상책임",
  DRIVER: "운전자보험",
  OTHER: "그 외",
};

export interface PickedPolicy {
  kind: ExternalPolicyKind;
  insurer_name_raw?: string | null;
  enrolled_ym?: string | null;
}

export function ExternalPolicyPicker({
  value, onChange,
}: {
  value: PickedPolicy[];
  onChange: (next: PickedPolicy[]) => void;
}) {
  const [insurer, setInsurer] = useState("");

  function toggle(kind: ExternalPolicyKind) {
    const exists = value.find((v) => v.kind === kind);
    if (exists) {
      onChange(value.filter((v) => v.kind !== kind));
    } else {
      onChange([...value, { kind, insurer_name_raw: insurer || null, enrolled_ym: null }]);
    }
  }

  function setYm(kind: ExternalPolicyKind, ym: string) {
    onChange(value.map((v) => (v.kind === kind ? { ...v, enrolled_ym: ym || null } : v)));
  }

  const indemnity = value.find((v) => v.kind === "MEDICAL_INDEMNITY");

  return (
    <>
      <p className="muted" style={{ fontSize: "0.85rem" }}>
        이미 들고 계신 보험을 골라주세요. 겹치는 담보와 비는 담보를 약관 근거와 함께 알려드려요.
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
        {(Object.keys(KIND_LABELS) as ExternalPolicyKind[]).map((kind) => {
          const on = value.some((v) => v.kind === kind);
          return (
            <button
              key={kind}
              type="button"
              className={on ? "chip chip--on" : "chip"}
              onClick={() => toggle(kind)}
            >
              {KIND_LABELS[kind]}
            </button>
          );
        })}
      </div>

      {/* 실손만 가입시기를 묻는다 — 실손은 2009년 표준화 이후 보장구조가 보험사별로 같아서
          가입시기 하나로 세대(1~4세대)가 정해지고, 세대가 보장구조를 결정한다. */}
      {indemnity && (
        <label style={{ marginTop: 16, display: "block" }}>
          실손 가입시기 (모르면 비워두세요)
          <input
            type="month"
            value={indemnity.enrolled_ym ?? ""}
            onChange={(e) => setYm("MEDICAL_INDEMNITY", e.target.value)}
          />
        </label>
      )}

      <label style={{ marginTop: 16, display: "block" }}>
        보험사 (모르면 비워두세요)
        <InsurerPicker value={insurer} onChange={setInsurer} />
      </label>
    </>
  );
}
```

- [ ] **Step 3: 진단 결과 컴포넌트 작성**

`frontend/src/components/OverlapReport.tsx`:

```tsx
import type { OverlapFindingOut, OverlapReportOut } from "../api";

/** 진단 결과 표시. 근거 조항 원문을 그대로 붙이고, 근거가 없으면 "확인불가"라고 밝힌다. */

function Finding({ f }: { f: OverlapFindingOut }) {
  return (
    <div className="card" style={{ marginBottom: 10 }}>
      <strong>{f.coverage_std_name}</strong>
      {f.scope !== "전체" && <span className="muted"> · {f.scope}</span>}
      {f.note && <p style={{ margin: "6px 0 0", fontSize: "0.9rem" }}>{f.note}</p>}
      {f.clause_quote ? (
        <blockquote style={{ margin: "10px 0 0", padding: "8px 12px", borderLeft: "3px solid var(--accent, #888)", fontSize: "0.82rem" }}>
          {f.clause_quote}
          <div className="muted" style={{ marginTop: 4 }}>— {f.clause_article_no}</div>
        </blockquote>
      ) : (
        <p className="muted" style={{ margin: "8px 0 0", fontSize: "0.82rem" }}>
          약관 근거를 찾지 못해 확인불가입니다.
        </p>
      )}
    </div>
  );
}

export function OverlapReportView({ report }: { report: OverlapReportOut }) {
  const empty =
    report.duplicates.length === 0 && report.gaps.length === 0 &&
    report.fixed_ok.length === 0 && report.unknown.length === 0;

  if (empty) {
    return <p className="muted">진단할 내용이 없어요. 기존보험과 여행자보험을 모두 등록하면 결과가 나옵니다.</p>;
  }

  return (
    <>
      {report.gaps.length > 0 && (
        <section>
          <h3>기존보험으로 커버되지 않아요</h3>
          {report.gaps.map((f) => <Finding key={`${f.coverage_std_code}-${f.scope}`} f={f} />)}
        </section>
      )}
      {report.duplicates.length > 0 && (
        <section>
          <h3>겹쳐요 — 두 개 들어도 더 받지 못합니다</h3>
          {report.duplicates.map((f) => <Finding key={`${f.coverage_std_code}-${f.scope}`} f={f} />)}
        </section>
      )}
      {report.fixed_ok.length > 0 && (
        <section>
          <h3>겹치지만 각각 다 받아요</h3>
          {report.fixed_ok.map((f) => <Finding key={`${f.coverage_std_code}-${f.scope}`} f={f} />)}
        </section>
      )}
      {report.unknown.length > 0 && (
        <section>
          <h3>확인불가</h3>
          {report.unknown.map((f) => <Finding key={`${f.coverage_std_code}-${f.scope}`} f={f} />)}
        </section>
      )}
    </>
  );
}
```

- [ ] **Step 4: 내 보험 화면에 섹션 추가**

`frontend/src/pages/MyPolicies.tsx`의 import에 추가:

```tsx
import { api, type UserPolicyOut, type ExternalPolicyOut, type OverlapReportOut } from "../api";
import { ExternalPolicyPicker, KIND_LABELS, type PickedPolicy } from "../components/ExternalPolicyPicker";
import { OverlapReportView } from "../components/OverlapReport";
```

`MyPolicies` 함수 안, 기존 `useState` 선언들 아래에 추가:

```tsx
  const [external, setExternal] = useState<ExternalPolicyOut[]>([]);
  const [picking, setPicking] = useState(false);
  const [picked, setPicked] = useState<PickedPolicy[]>([]);
  const [overlap, setOverlap] = useState<OverlapReportOut | null>(null);
```

`refresh` 함수 안 `setPolicies(list);` 다음 줄에 추가:

```tsx
    setExternal(await api.listExternalPolicies(userId));
    if (list.length > 0) {
      setOverlap(await api.getCoverageOverlap(userId, { userPolicyId: list[0].user_policy_id }));
    }
```

`handleDelete` 함수 아래에 추가:

```tsx
  async function handleLinkExternal() {
    if (!userId || picked.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      await api.linkExternalPolicies(userId, { provider: "manual", items: picked });
      setPicked([]);
      setPicking(false);
      await refresh();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteExternal(id: number) {
    if (!userId) return;
    await api.deleteExternalPolicy(userId, id);
    await refresh();
  }
```

목록 화면의 `<ConfirmDialog ... />` 바로 위에 섹션을 추가:

```tsx
      <section style={{ marginTop: 28 }}>
        <h2 style={{ fontSize: "1.05rem" }}>기존에 들고 계신 보험</h2>
        <p className="page-desc">
          실손·상해·일상생활배상책임 같은 기존보험을 등록하면, 이번 여행자보험과 겹치는 담보와
          비는 담보를 약관 원문 근거와 함께 알려드려요.
        </p>

        {external.map((e) => (
          <div className="card" key={e.external_policy_id} style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <strong>{KIND_LABELS[e.kind]}</strong>
              <button type="button" className="history-card__delete" title="삭제"
                onClick={() => handleDeleteExternal(e.external_policy_id)}>🗑</button>
            </div>
            <div className="muted" style={{ fontSize: "0.85rem" }}>
              {e.insurer_name_raw ?? "보험사 미상"}
              {e.indemnity_gen ? ` · ${e.indemnity_gen}세대 실손` : ""}
              {e.enrolled_ym ? ` · ${e.enrolled_ym} 가입` : ""}
            </div>
          </div>
        ))}

        {picking ? (
          <div className="card">
            <ExternalPolicyPicker value={picked} onChange={setPicked} />
            {error && <div className="error-box">{error}</div>}
            <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
              <button type="button" className="btn-primary" disabled={picked.length === 0 || loading}
                onClick={handleLinkExternal}>등록</button>
              <button type="button" onClick={() => { setPicking(false); setPicked([]); }}>취소</button>
            </div>
          </div>
        ) : (
          <button type="button" className="btn-primary" onClick={() => setPicking(true)}>
            기존보험 등록하기
          </button>
        )}

        {overlap && external.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <h2 style={{ fontSize: "1.05rem" }}>중복·공백 진단</h2>
            <OverlapReportView report={overlap} />
          </div>
        )}
      </section>
```

- [ ] **Step 5: 타입 검사와 화면 확인**

Run: `cd frontend && npx tsc -b`
Expected: 오류 없음

Run: `cd frontend && npm run dev` (백엔드도 함께 띄워둔다)

http://localhost:5173/policies 에서 확인:
1. 로그인 후 "기존보험 등록하기" 버튼이 보인다
2. 실손을 고르면 가입시기 입력칸이 나타난다
3. 등록하면 카드에 "3세대 실손"처럼 세대가 표시된다
4. 여행자보험도 등록돼 있으면 "중복·공백 진단"에 근거 조항 원문이 붙어 나온다

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/api.ts frontend/src/components/ExternalPolicyPicker.tsx frontend/src/components/OverlapReport.tsx frontend/src/pages/MyPolicies.tsx
git commit -m "내 보험 화면에 기존보험 등록과 중복·공백 진단 표시 추가"
```

---

### Task 9: 여행 준비·사고 접수 화면 통합

**Files:**
- Modify: `frontend/src/pages/TripPrep.tsx`
- Modify: `frontend/src/pages/IncidentReport.tsx`

**Interfaces:**
- Consumes: `<ExternalPolicyPicker>`, `<OverlapReportView>`, `api.linkExternalPolicies`, `api.getCoverageOverlap` (Task 8)

**배경:** 두 화면 모두 단계 배열(`steps` / `introSteps`)의 **마지막 항목이 제출 버튼을 띄우는 단계**이고, 그 항목의 `canNext`가 입력값 검증을 맡고 있다. 새 단계를 배열 끝에 붙이면 검증이 새 항목의 `canNext: true`로 밀려나 필수값 없이 제출된다. **그래서 마지막 항목 바로 앞에 끼워 넣는다.**

게스트도 `provider: "manual"`은 쓸 수 있으므로 로그인 여부로 막지 않는다.

- [ ] **Step 1: 여행 준비 화면에 단계 추가**

`frontend/src/pages/TripPrep.tsx` import에 추가:

```tsx
import { ExternalPolicyPicker, type PickedPolicy } from "../components/ExternalPolicyPicker";
```

`useApp()` 호출(25행) 아래 상태 선언부에 추가:

```tsx
  // 기존보험은 선택 항목이다 — 건너뛰어도 여행 준비는 끝까지 진행된다.
  const [picked, setPicked] = useState<PickedPolicy[]>([]);
```

`const steps = [`(147행) 배열에서 **마지막 항목인 `eyebrow: "STEP 6 · 확인"` 객체 바로 앞에** 새 항목을 끼워 넣는다:

```tsx
      {
        icon: "umbrella",
        eyebrow: "STEP 6 · 기존보험",
        title: "이미 들고 계신\n보험이 있나요?",
        content: <ExternalPolicyPicker value={picked} onChange={setPicked} />,
        canNext: true,  // 선택 항목이라 아무것도 안 골라도 넘어간다
      },
```

그리고 뒤로 밀린 확인 단계의 `eyebrow`를 `"STEP 6 · 확인"` → `"STEP 7 · 확인"`으로 고친다.

`handleSubmit`(75행) 안 `setTripId(res.trip_id);`(95행) 바로 다음 줄에 추가:

```tsx
      // 기존보험을 골랐으면 같이 저장한다. 여행 생성은 이미 끝났으므로 이 저장이 실패해도
      // 흐름을 막지 않는다 — 기존보험은 나중에 내 보험 화면에서 다시 등록할 수 있다.
      if (picked.length > 0) {
        await api.linkExternalPolicies(userId, { provider: "manual", items: picked }).catch(() => {});
      }
```

- [ ] **Step 2: 사고 접수 화면에 단계 추가**

`frontend/src/pages/IncidentReport.tsx` import에 추가:

```tsx
import { ExternalPolicyPicker, type PickedPolicy } from "../components/ExternalPolicyPicker";
```

`const [introStep, setIntroStep] = useState(0);`(41행) 아래에 추가:

```tsx
  const [picked, setPicked] = useState<PickedPolicy[]>([]);
```

`const introSteps = [`(253행) 배열에서 **마지막 항목(401행의 `canNext: !!freeText.trim() && ...`를 가진 객체) 바로 앞에** 끼워 넣는다:

```tsx
      {
        icon: "umbrella",
        eyebrow: "선택 · 기존보험",
        title: "이미 들고 계신\n보험이 있나요?",
        content: <ExternalPolicyPicker value={picked} onChange={setPicked} />,
        canNext: true,
      },
```

`handleStart`(135행) 안 `setIncidentId(res.incident_id);`(158행) 바로 다음 줄에 추가:

```tsx
      if (picked.length > 0) {
        await api.linkExternalPolicies(userId, { provider: "manual", items: picked }).catch(() => {});
      }
```

- [ ] **Step 3: 타입 검사**

Run: `cd frontend && npx tsc -b`
Expected: 오류 없음

- [ ] **Step 4: 게스트 흐름 확인**

백엔드와 프론트를 모두 띄우고, 브라우저 시크릿 창(게스트 상태)에서 확인:

1. http://localhost:5173/trip — 마지막 단계에 "이미 들고 계신 보험이 있나요?"가 나온다
2. 아무것도 안 고르고 넘어가도 여행 등록이 정상 완료된다
3. 실손을 고르고 완료하면 오류 없이 끝난다
4. http://localhost:5173/incident — 최종 단계에 같은 선택이 나온다

- [ ] **Step 5: 전체 테스트 실행**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/ -v`
Expected: 전부 PASS

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/pages/TripPrep.tsx frontend/src/pages/IncidentReport.tsx
git commit -m "여행 준비·사고 접수 마지막 단계에 기존보험 선택 추가 — 게스트도 등록 가능"
```

---

## 완료 기준

- `cd backend && .venv\Scripts\python.exe -m pytest tests/ -v` 전부 통과
- `cd frontend && npx tsc -b` 오류 없음
- `python -m app.seed_overlap_rules`가 7건을 심고, 모든 행에 `clause_id`가 붙어 있다
- `/policies`에서 기존보험을 등록하면 진단 결과에 약관 원문 인용이 나온다
- `/trip`, `/incident` 마지막 단계에서 게스트도 기존보험을 고를 수 있다

## 후속 작업 (별도 계획)

1. **혜택·할인 크롤러** — 스펙 §7. 보험다모아·각사 공식 안내에서 수집, `insurer_discount` 테이블, 출처 등록대장 기록.
2. **실손 세대별 담보 자동채움** — 금융감독원 표준약관 원문과 대조 후 세대별 자기부담률·한도 시드. `ManualProvider`의 `coverages=[]`를 채운다.
3. **약관 PDF 재추출** — `data/raw_pdfs/` 확보 후 "다른 보험과의 관계"·"보험금의 분담" 조항을 추가 추출해 `overlap_rule`의 `UNKNOWN` 조합을 줄인다.
