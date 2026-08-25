"""여행에 연결되지 않은 현지 대응 팩 — 나라만 고르면 볼 수 있다.

여행을 등록하지 않은 사람도(게스트 포함) 이 화면이 필요하다. 사고는 여행 등록 여부와
무관하게 나고, 현지에서 서류를 못 챙기면 되돌릴 수 없기 때문이다. 사고 접수 화면이
"연결된 여행이 없으면 국가만이라도 직접 입력"을 허용하는 것과 같은 이유다.

여행에 연결된 팩은 /trips/{trip_id}/onsite에 있다. 조립은 양쪽 다 services/onsite.py의
같은 함수가 하고, 라우터는 입력만 다르게 넘긴다.
"""
from dataclasses import asdict

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.schemas import OnsitePackOut
from app.services.onsite import build_onsite_pack

router = APIRouter(prefix="/onsite", tags=["onsite"])


@router.get("", response_model=OnsitePackOut)
@limiter.limit("30/minute")
def get_onsite_pack(
    request: Request, country: str | None = None, db: Session = Depends(get_db),
):
    """나라 기준 현지 대응 팩. 약관 KB에서만 나오는 내용이라 로그인 없이 볼 수 있다.

    번역이 캐시에 없으면 Gemini를 부를 수 있어 빈도 제한을 둔다. 두 번째 사용자부터는
    캐시를 타므로 실제 호출은 나라별로 한 번뿐이다.
    """
    pack = build_onsite_pack(db, country=country)
    return OnsitePackOut(**asdict(pack))
