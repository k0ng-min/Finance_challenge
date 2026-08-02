"""보험다모아(손해보험협회 온라인 보험슈퍼마켓)에서 해외여행자보험 나이·성별별 보험료를 수집한다.

수집 대상은 이 프로젝트가 약관을 분석해 둔 6개사뿐이다. 페이지가 제공하는 보험료는
"상해1급(사무직 종사자 등) / 보험기간 7일 / 일시납" 표준보장 담보 기준이며, 실제 가입
조건(여행지·기간·담보 구성)에 따라 달라진다 — 이 전제는 수집 결과에 그대로 기록해서
화면에서도 함께 안내한다(근거 없는 숫자를 내놓지 않는다는 원칙).

사이트에 부담을 주지 않도록 요청 간 간격을 두고 순차적으로만 조회한다.

    python -m app.crawl_premiums              # 만 0~80세 × 남/녀
    python -m app.crawl_premiums --ages 20,30 # 일부 나이만
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import date
from pathlib import Path

import httpx

BASE = "http://203.229.168.79"
LIST_URL = f"{BASE}/tripIns/tripInsList.knia"
LIST_REFERER = f"{LIST_URL}?prdtSmlClsCd=H001"

# 요청 간격(초). 협회 서버에 부담을 주지 않기 위한 값이라 낮추지 말 것.
REQUEST_INTERVAL = 1.2
TIMEOUT = 40.0
MAX_RETRY = 3

# 보험료 산출 전제 — 페이지 상단 "가입 기준"에 명시된 문구를 그대로 옮긴다.
PREMIUM_BASIS = "상해1급(사무직 종사자 등) / 보험기간 7일 / 일시납, 표준보장 담보 기준"

# 보험다모아 표기명 → 이 프로젝트 DB의 insurer.code
COMPANY_TO_CODE = {
    "삼성화재": "SAMSUNG",
    "현대해상": "HYUNDAI",
    "메리츠화재": "MERITZ",
    "KB손보": "KB",
    "DB손보": "DB",
    "카카오페이손해보험": "KAKAOPAY",
}

ROW_RE = re.compile(r'<tr data-prdt-cd="([^"]+)"[^>]*>(.*?)</tr>', re.S)
COMPANY_RE = re.compile(r'<img src="/img/company/[^"]+"\s+alt="([^"]*)"')
PRODUCT_RE = re.compile(r'word-break:keep-all;">(.*?)</span>', re.S)
COST_RE = re.compile(r'<td class="total_cost">([\d,]+)</td>')
AGE_RANGE_RE = re.compile(r'<td class="total_cost">[\d,]+</td>\s*<td>([^<]*)</td>', re.S)
TOTAL_RE = re.compile(r"총\s*<strong>(\d+)</strong>\s*건")


def parse_rows(html: str) -> list[dict]:
    """결과 HTML에서 상품 행을 뽑는다. 6개사에 해당하는 행만 남긴다."""
    rows = []
    for prdt_cd, body in ROW_RE.findall(html):
        comp = COMPANY_RE.search(body)
        if not comp:
            continue
        company = comp.group(1).strip()
        code = COMPANY_TO_CODE.get(company)
        if code is None:
            continue
        prod = PRODUCT_RE.search(body)
        cost = COST_RE.search(body)
        arange = AGE_RANGE_RE.search(body)
        if not cost:
            continue
        rows.append({
            "insurer_code": code,
            "company_label": company,
            "prdt_cd": prdt_cd,
            "product_name": re.sub(r"\s+", " ", prod.group(1)).strip() if prod else None,
            "premium": int(cost.group(1).replace(",", "")),
            "age_range": arange.group(1).strip() if arange else None,
        })
    return rows


def fetch(client: httpx.Client, sex: str, age: int) -> str:
    """나이·성별 하나에 대한 비교 결과 HTML을 가져온다."""
    data = {
        "prdtSmlClsCd": "H001", "enterType": "A", "prdtCd": "", "prdtNm": "",
        "sex": sex, "sexType": sex, "sexDiv": "", "insrCmpyNm": "",
        "page": "1", "startDt": "", "age": str(age), "ordering": "ASC",
    }
    last_err: Exception | None = None
    for attempt in range(MAX_RETRY):
        try:
            r = client.post(LIST_URL, data=data)
            r.raise_for_status()
            return r.text
        except Exception as exc:  # 일시적 네트워크 오류는 물러섰다가 다시 시도한다
            last_err = exc
            time.sleep(REQUEST_INTERVAL * (attempt + 2))
    raise RuntimeError(f"조회 실패 sex={sex} age={age}: {last_err}")


def crawl(ages: list[int], sexes: list[str], out_path: Path) -> dict:
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"),
        "Referer": LIST_REFERER,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    records: list[dict] = []
    missing: list[dict] = []
    with httpx.Client(headers=headers, timeout=TIMEOUT, follow_redirects=True) as client:
        client.get(LIST_REFERER)  # 세션 쿠키 확보
        total = len(ages) * len(sexes)
        done = 0
        for sex in sexes:
            for age in ages:
                html = fetch(client, sex, age)
                rows = parse_rows(html)
                for row in rows:
                    records.append({**row, "sex": sex, "age": age})
                found = {r["insurer_code"] for r in rows}
                for code in COMPANY_TO_CODE.values():
                    if code not in found:
                        # 해당 나이가 가입연령 범위 밖이면 목록에 아예 안 나온다 — 이것도 정보다.
                        missing.append({"insurer_code": code, "sex": sex, "age": age})
                done += 1
                print(f"[{done}/{total}] sex={sex} age={age} → {len(rows)}건", flush=True)
                time.sleep(REQUEST_INTERVAL)

    payload = {
        "source": "보험다모아(손해보험협회 온라인 보험슈퍼마켓)",
        "source_url": LIST_REFERER,
        "collected_at": date.today().isoformat(),
        "premium_basis": PREMIUM_BASIS,
        "note": ("표준보장 담보 기준 예시 보험료로, 실제 가입조건(여행지·기간·담보 구성)에 따라 "
                 "달라질 수 있습니다. 목록에 나오지 않는 나이는 해당 상품의 가입연령 범위 밖입니다."),
        "records": records,
        "unavailable": missing,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ages", default="0-80", help="예: 0-80 또는 20,30,40")
    ap.add_argument("--sexes", default="M,F")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "data" / "premiums.json"))
    args = ap.parse_args()

    if "-" in args.ages and "," not in args.ages:
        lo, hi = args.ages.split("-")
        ages = list(range(int(lo), int(hi) + 1))
    else:
        ages = [int(a) for a in args.ages.split(",") if a.strip()]
    sexes = [s.strip() for s in args.sexes.split(",") if s.strip()]

    payload = crawl(ages, sexes, Path(args.out))
    print(f"\n수집 완료: {len(payload['records'])}건 → {args.out}")


if __name__ == "__main__":
    main()
