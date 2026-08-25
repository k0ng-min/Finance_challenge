# 신한EZ손해보험 추가 — 완료 기록 (2026-08-25)

7번째 보험사로 **신한EZ손해보험 「신한 SOL 처음해외여행보험」**(2026.06.06 시행판, 236쪽)을
추가하는 작업. **1~11번 중 보험료(7번)를 뺀 전부 끝났다.**

## 확보한 자료

| 파일 | 내용 |
|---|---|
| `backend/data/raw_pdfs/shinhan_overseas_sol_20260606.pdf` | 상품약관 원본 236쪽 (gitignore — 로컬에만 있음) |
| `backend/data/source_files/shinhan_sol_product_summary_20260606.pdf` | 상품요약서 7쪽 |
| `backend/data/source_files/shinhan_plan_screenshots/direct_compare_1,2.jpg` | 다이렉트 「보장 비교하기」 캡처 — 등급별 보장금액 근거 |
| `frontend/public/insurers/shinhan.jpg` | 공식 「신한 SOL EZ손보」 앱 아이콘 512x512 |

약관 PDF SHA256: `b3279327a710acb875693eda0c951e9a13ec2f168f7f202db12057015f77f016`

## 약관을 다시 받아야 할 때 (공시 사이트가 JS API라 링크가 없다)

공시 페이지 <https://www.shinhanez.co.kr/static/pub/PUB2000T021.html> 는 화면에 링크를
그리지 않고 자체 API(`POST https://www.shinhanez.co.kr/shezApi`)를 호출한다. 재현 절차:

1. 상품 목록 — 서비스ID `hpgpub0002r`, payload `{"slYn":"1"}`
   → 신한 SOL 처음해외여행보험 = `insKndCdVal: "0045004"`, `prodDclKndCd: "2"`
2. 판매기간 목록 — `hpgpub0014r`, payload `{"insKndCdVal":"0045004","slYn":"1","prodDclKndCd":"2"}`
   → 현행판 `slStrYmdy: "2026.06.06"`, `prodDclAdmNo: 510`
3. 파일 목록 — `hpgpub0014r`, payload
   `{"insKndCdVal":"0045004","prodDclKndCd":"2","slStrYmdy":"20260606","prodDclAdmNo":510,"slYn":"1"}`
   → 현행판 약관 `adxFileId = 676fcd29767b4b81a76782c7d96d5db8_file`, `adxFileSeqno = 1`
4. 내려받기 — `POST https://www.shinhanez.co.kr/cmn/fileDown` (multipart/form-data)
   `lrnkPath=fileDown, dvsnCode=cmn, fileNo=<adxFileId>, fileSeq=<adxFileSeqno>, type=chl`

## 만든 것

시드 스크립트 6개. **실행 순서대로**:

| 스크립트 | 담당 | 결과 |
|---|---|---|
| `app/seed_shinhan_2026_a.py` | p.1-33 보통약관 | Insurer/Product/PolicyVersion + 담보 1 · 조항 5 |
| `app/seed_shinhan_2026_b.py` | p.34-67 특약 16종 | 담보 16 · 조항 75 |
| `app/seed_shinhan_2026_c.py` | p.68-137 실손 3종 | 담보 4 · 조항 18 |
| `app/seed_shinhan_2026_d.py` | p.138-236 나머지+별표 | 담보 8 · 조항 19 |
| `app/seed_shinhan_2026_e.py` | 매핑 | 사고유형 143 · 필요서류 99 |
| `app/seed_shinhan_2026_f.py` | 등급별 보장금액 | 담보표 42 · 비교표 42 |

합계 **담보 29 · 조항 117**. `python -m scripts.verify_clause_grounding`에서 신한 실패 0건
(조항 원문을 손으로 옮기지 않고 추출본에서 조문 경계로 잘라냈다).

각 스크립트 docstring에 "무엇을 넣었고 무엇을 왜 안 넣었는지"가 페이지 번호와 함께 적혀 있다.

## 함께 고친 곳

- `scripts/extract_raw_pdf_text.py` — `FILES`에 SHINHAN 추가
- `scripts/validate_kb.py` — `EXPECTED_INSURERS`에 SHINHAN
- `data/dataset_manifest.json` — SHINHAN 출처 + 개수·지문 갱신 (`python -m app.kb_manifest --confirm`)
- `docs/compliance/source_register.md` — SHINHAN 행
- `app/services/insurer_tiers.py` — `["실속케어", "안심케어", None]`
- `app/seed_clause_incident_map.py` / `app/seed_coverage_doc_map.py` — GOLF_EQUIPMENT 규칙
- `app/services/insurer_ranking_gemini.py` / `_score_gemini.py` — 프롬프트의 "6개 보험사"를 실제 개수로
- `app/routers/insurers.py` — 제외 안내 문구의 은/는 조사 처리(`_subject_particle`)
- `analysis/export_ranking_inputs.py` + `ranking_weights.R` 재실행 → `ranking_weights.json`
- `frontend/src/data/insurers.ts` — SHINHAN + `INSURER_COUNT`(문구에 숫자를 박지 않기 위함)
- 프론트 문구 8개 파일, README, 제출문서 HTML·PDF

## 이번에 내린 판단 (근거는 각 파일 주석에)

1. **골프용품손해 → 새 표준담보 `GOLF_EQUIPMENT`** (45종 → 46종).
   신한이 독립 특약으로 팔고 보험의 목적이 휴대품과 따로 정의돼 있어 흡수하지 않았다.
2. **항공기 및 수하물 지연비용 → 담보 하나(`TRV_BAGGAGE_DELAY`)**.
   신한은 항공지연·결항과 수하물 지연·손실을 한 조문에 담았다. 6개사도 같은 처리이고
   비교표도 "수하물/항공편 지연" 한 항목으로 합쳐 쓴다. 빠지는 절반은
   `seed_shinhan_2026_e.py`의 EXTRA_RULES로 TRV_FLIGHT_DELAY에 보충했다.
3. **실손 조문을 보장종목별로 쪼개지 않았다**. 표 레이아웃 때문에 경계가 연속 구간으로
   떨어지지 않아, 쪼개면 원문 대조가 깨진다. 대신 EXTRA_RULES로 질병 쪽 사고유형을 보충했다.
4. **실속케어=실속, 안심케어=표준**. 해외 실손 3,000만/5,000만원이라 다른 회사의
   실속·표준 구간과 맞는다. 고급 자리는 비웠다.

## 남은 것

1. **보험료** — 사용자가 나중에 준다. 받으면 `insurer_premiums_2026-08.xlsx`에 시트를 추가하고
   `app/seed_premiums_actual.py`의 `_SHEET_CONFIG`·`_BASIS`에 한 줄씩 더한 뒤 다시 돌린다.
   그 다음 `analysis/export_ranking_inputs.py` → `ranking_weights.R`을 재실행하면
   `priced_insurers`에 SHINHAN이 자동으로 들어간다(손으로 넣지 말 것).
   **지금은 신한만 가격 축을 빼고 재정규화하는 경로를 타는 유일한 보험사다** —
   그 경로가 실제로 도는 걸 이번에 처음 눈으로 확인했다(순위 조회 시 "아직 실제 보험료를
   확보하지 못했어요"가 뜬다).
2. **clause_term(정량조건)** — 신한은 0건이다. 지급한도·자기부담금·지연기준시간을 조항
   원문에서 뽑아 `raw_text`로 앵커링하는 별도 작업이라 미뤘다(6개사도 재구축 1차분에서
   일부만 만들었다). `raw_text`는 반드시 `clause.text`의 부분 문자열이어야 한다.
3. **표준약관 대조(`clause_standard_map`)** — 신한은 아직 대상이 아니다.
4. **매핑 규칙표의 빈칸** — `(담보, '조건')`·`(담보, '공통')` 조합에 규칙이 없어 매핑이
   안 붙는 조항이 신한 33건 있다. 기존 6개사도 같은 자리가 비어 있어(메리츠 29건 등)
   신한만의 결함은 아니지만, 규칙표를 채우면 7개사 전부 다시 돌려야 한다.

## 검증 상태 (2026-08-25 기준)

- `cd backend && .venv/Scripts/python.exe -m pytest` → **274건 통과**
- `python -m scripts.validate_kb` → 0 errors (warning 4건은 effective_date 미확정 등 기존 항목)
- `python -m scripts.verify_clause_grounding` → 신한 0건 실패
  (전체 94건은 신한 추가 이전부터 있던 6개사분 드리프트 — 이번 작업과 무관)
- `cd frontend && npx tsc --noEmit` → 통과
