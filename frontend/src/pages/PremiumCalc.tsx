import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { toPng } from "html-to-image";
import {
  api, type PremiumComparisonOut, type NonpaymentRatesOut, type InsurerPlansOut, type InsurerComparisonOut,
} from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { Icon3D } from "../components/Icon3D";
import { PlanCoverageBoard } from "../components/PlanCoverageBoard";
import { Modal } from "../components/Modal";

const INSURERS = [
  { code: "SAMSUNG", label: "삼성화재" },
  { code: "HYUNDAI", label: "현대해상" },
  { code: "MERITZ", label: "메리츠화재" },
  { code: "KB", label: "KB손보" },
  { code: "DB", label: "DB손보" },
  { code: "KAKAOPAY", label: "카카오페이손보" },
];

// backend/app/services/insurer_tiers.py의 TIER_LABELS와 반드시 같은 순서로 둔다.
const PLAN_TIER_LABELS = ["실속", "표준", "고급"];

/** InsurerComparisonMetric의 원문 표기 기준 "이 담보가 있다"고 볼 수 있는 값인지.
 * "-"·"미제공"·"미가입"류는 없는 것으로 본다 — 정확한 조건은 표 상세를 봐야 하므로
 * 이 필터는 "후보를 좁히는 용도"라는 문구를 화면에 같이 둔다. */
function isCoveredValue(value: string | undefined | null): boolean {
  if (!value) return false;
  if (value === "-" || value === "미제공") return false;
  if (value.startsWith("미가입")) return false;
  return true;
}

/**
 * 보험료 비교 — 보험사를 골라 나이·성별에 따른 1일 기준 실제 보험료를 비교한다.
 *
 * 2026-08-19부터 보험다모아 비교공시(표준조건 한 값) 대신, 각 사 다이렉트 사이트에서
 * 직접 조회한 실제 등급(플랜)별 가격을 쓴다. 필터의 "등급" 선택기(실속/표준/고급)로
 * 목록 전체 가격을 한 번에 바꿀 수 있고, 행마다 보험사 이름을 누르면 그 보험사만 다른
 * 등급으로 따로 볼 수도 있다(PlanCoverageBoard 팝업) — 전체로 바꾸면 행별 개별 선택은
 * 초기화된다(둘이 뒤섞이면 헷갈리므로). "N등급 · 6개사 보장금액 한눈에 비교" 버튼은
 * InsurerComparisonMetric(같은 항목끼리 미리 정리해 둔 비교표)을 보여준다.
 *
 * 숫자는 약관에서 뽑은 값이 아니라 각 사 공시 화면에서 가져온 값이라, 무엇을 기준으로
 * 조회한 값인지(며칠치·어떤 조건)를 숫자 옆에 같이 둔다. 다만 우리가 그 값을 언제
 * 수집했는지는 화면에 쓰지 않는다 — 읽는 사람이 판단에 쓰는 정보가 아니라 우리 사정이고,
 * 화면마다 붙으면 정작 봐야 할 가격이 뒤로 밀린다.
 */
export function PremiumCalc() {
  const { age: profileAge, sex: profileSex, userId, isLoggedIn } = useApp();
  // 처음엔 아무것도 고르지 않은 상태로 시작한다 — 전부 켜둔 채로 열면 "내가 고른 것"이
  // 아니라 "일단 다 나온 것"으로 보여서, 비교하려고 고르는 행동 자체가 흐려진다.
  const [selected, setSelected] = useState<string[]>([]);
  const [age, setAge] = useState<number>(profileAge ?? 30);
  const [sex, setSex] = useState<"M" | "F">(profileSex === "F" ? "F" : "M");
  const [order, setOrder] = useState<"asc" | "desc">("asc");
  const [data, setData] = useState<PremiumComparisonOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [nonpayment, setNonpayment] = useState<NonpaymentRatesOut | null>(null);
  // 행마다 등급 칩·담보한도표가 처음부터 펼쳐져 있다(표준 등급으로 고정하지 않고
  // 자유롭게 등급을 바꿔볼 수 있게). 고른 등급과 그 등급의 실시간 가격을 보험사별로 기억한다.
  const [planByInsurer, setPlanByInsurer] = useState<Record<string, string>>({});
  const [plansByInsurer, setPlansByInsurer] = useState<Record<string, InsurerPlansOut | null>>({});
  // 행 오른쪽 화살표를 누르면 "이 보험사 비교에서 빼기" 메뉴가 나온다 — 한 번에 하나만 연다.
  const [menuOpenFor, setMenuOpenFor] = useState<string | null>(null);
  // 보험사 이름을 누르면 등급·담보한도 팝업이 뜬다.
  const [planModalFor, setPlanModalFor] = useState<string | null>(null);
  // 부지급률 표는 기본으로 접어 둔다 — 누르면 펼쳐진다.
  const [showNonpayment, setShowNonpayment] = useState(false);
  // 전체 등급(실속/표준/고급) — 고르면 목록 전체 가격이 그 등급으로 다시 계산된다.
  // 행마다 따로 고른 등급(planByInsurer)은 여기서 비워서, 전체 등급 선택이 우선하게 한다.
  const [planTierRank, setPlanTierRank] = useState(1);
  const [showComparison, setShowComparison] = useState(false);
  const [comparison, setComparison] = useState<InsurerComparisonOut | null>(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  // 필터 카드가 나이 하나만으로 시작해 한눈에 보이게 하고, 나머지(등급·성별·정렬·담보
  // 유형·가격대)는 눌러서 펼쳐야 나온다 — 전부 펼쳐 두면 스크롤이 길어지고 화면이 복잡해진다.
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  // 담보 유형 필터 — "category|||metric_label"로 인코딩해 고른다. 안 고르면(null) 필터 없음.
  const [coverageFilterKey, setCoverageFilterKey] = useState<string | null>(null);
  // 가격대 필터 — 빈 문자열이면 그쪽 경계 없음.
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  // 비교 결과 공유 카드
  const [showShareCard, setShowShareCard] = useState(false);
  const [shareCardBusy, setShareCardBusy] = useState(false);
  const [shareCardError, setShareCardError] = useState(false);
  const shareCardRef = useRef<HTMLDivElement>(null);
  // 로그인 계정의 비교함(찜하기) — 처음 불러오기 전까지는 저장하지 않는다(안 그러면
  // 빈 목록으로 시작하는 첫 렌더가 곧바로 서버 저장을 덮어써 버린다).
  const skipWatchlistSaveRef = useRef(false);
  const [watchlistSaved, setWatchlistSaved] = useState(false);

  useEffect(() => {
    if (profileAge != null) setAge(profileAge);
  }, [profileAge]);

  useEffect(() => {
    api.getNonpaymentRates().then(setNonpayment).catch(() => setNonpayment(null));
  }, []);

  useEffect(() => {
    if (!isLoggedIn || !userId) return;
    skipWatchlistSaveRef.current = true;
    api.getPremiumWatchlist(userId)
      .then((res) => {
        const codes = res.insurer_codes.filter((c) => INSURERS.some((i) => i.code === c));
        if (codes.length > 0) setSelected(codes);
      })
      .catch(() => {
        skipWatchlistSaveRef.current = false;
      });
  }, [isLoggedIn, userId]);

  useEffect(() => {
    if (!isLoggedIn || !userId) return;
    if (skipWatchlistSaveRef.current) {
      skipWatchlistSaveRef.current = false;
      return;
    }
    api.setPremiumWatchlist(userId, selected)
      .then(() => {
        setWatchlistSaved(true);
        setTimeout(() => setWatchlistSaved(false), 1500);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, isLoggedIn, userId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getPremiumComparison(age, sex, order, planTierRank)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch(() => {
        if (!cancelled) {
          setData(null);
          setError("이 나이는 가격을 확보한 보험사 전부의 가입연령 범위 밖이라 비교할 보험료가 없어요.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [age, sex, order, planTierRank]);

  // 전체 등급을 바꾸면 행마다 따로 골라 둔 등급은 비운다 — 안 그러면 방금 고른 전체
  // 등급과 예전에 개별로 고른 등급이 뒤섞여 헷갈린다.
  useEffect(() => {
    setPlanByInsurer({});
    setPlansByInsurer({});
  }, [planTierRank]);

  // 비교표 팝업뿐 아니라 담보 유형 필터의 목록·판정에도 같은 자료가 필요해서, 팝업을
  // 열었을 때만이 아니라 등급이 바뀔 때마다 미리 불러와 둔다.
  useEffect(() => {
    setComparisonLoading(true);
    api.getInsurerComparisonMetrics(planTierRank)
      .then(setComparison)
      .catch(() => setComparison(null))
      .finally(() => setComparisonLoading(false));
  }, [planTierRank]);

  function toggle(code: string) {
    setSelected((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  }

  // 담보 유형 필터 드롭다운에 쓸 목록 — 카테고리별로 묶어 <optgroup>으로 보여준다.
  const coverageOptions = useMemo(() => {
    if (!comparison) return [];
    return comparison.categories.map((cat) => ({
      category: cat.category,
      items: cat.metrics.map((m) => ({ key: `${cat.category}|||${m.metric_label}`, label: m.metric_label })),
    }));
  }, [comparison]);

  // 고른 담보 유형을 "가지고 있다"고 볼 수 있는 보험사 코드 집합. 못 고르면(null) 필터 없음.
  const coveredCodes = useMemo(() => {
    if (!coverageFilterKey || !comparison) return null;
    const [category, metricLabel] = coverageFilterKey.split("|||");
    const metric = comparison.categories
      .find((c) => c.category === category)
      ?.metrics.find((m) => m.metric_label === metricLabel);
    if (!metric) return null;
    return new Set(metric.values.filter((v) => isCoveredValue(v.value_text)).map((v) => v.insurer_code));
  }, [coverageFilterKey, comparison]);

  const priceBounds = useMemo(() => {
    const min = minPrice.trim() ? Number(minPrice) : null;
    const max = maxPrice.trim() ? Number(maxPrice) : null;
    return {
      min: min != null && !Number.isNaN(min) ? min : null,
      max: max != null && !Number.isNaN(max) ? max : null,
    };
  }, [minPrice, maxPrice]);

  const hasExtraFilter = coveredCodes != null || priceBounds.min != null || priceBounds.max != null;

  const rows = useMemo(() => {
    let list = (data?.items ?? []).filter((i) => selected.includes(i.insurer_code));
    if (coveredCodes) list = list.filter((i) => coveredCodes.has(i.insurer_code));
    if (priceBounds.min != null) list = list.filter((i) => i.published_premium >= priceBounds.min!);
    if (priceBounds.max != null) list = list.filter((i) => i.published_premium <= priceBounds.max!);
    return list;
  }, [data, selected, coveredCodes, priceBounds]);
  // 고른 보험사 중 목록에 안 나온 곳 — 조용히 빼지 않고 이유를 밝힌다. 이유가 둘로
  // 갈린다: (1) 이 나이만 가입연령 범위 밖 (2) 나이와 무관하게 가격 자체를 아직
  // 못 구함(DB·메리츠) — 서버가 내려주는 no_data_insurer_codes로 구분한다. 하나로
  // 뭉뚱그리면 "아직 못 구함"을 "가입 안 되는 나이"로 잘못 전달하게 된다.
  const missing = useMemo(() => {
    const present = new Set((data?.items ?? []).map((i) => i.insurer_code));
    const noDataCodes = new Set(data?.no_data_insurer_codes ?? []);
    const notShown = INSURERS.filter((i) => selected.includes(i.code) && !present.has(i.code));
    return {
      ageOutOfRange: notShown.filter((i) => !noDataCodes.has(i.code)),
      noDataYet: notShown.filter((i) => noDataCodes.has(i.code)),
    };
  }, [data, selected]);

  return (
    <div className="page">
      <TopBar title="보험료 비교" />
      <PageHero
        icon="wallet"
        eyebrow="PREMIUM"
        title={"1일 기준\n실제 보험료를 비교해요"}
        subtitle="각 보험사 다이렉트 사이트에서 직접 조회한 등급별 가격을 비교해 드려요."
      />

      <div className="card">
        <p className="section-label" style={{ marginBottom: 8 }}>비교할 보험사</p>
        <div className="calc-chips">
          {INSURERS.map((i) => (
            <button
              key={i.code}
              type="button"
              className={`premium-chip${selected.includes(i.code) ? " premium-chip--on" : ""}`}
              onClick={() => toggle(i.code)}
            >
              {i.label}
            </button>
          ))}
        </div>
        {isLoggedIn ? (
          <p className="muted calc-watchlist-hint">
            {watchlistSaved ? "✓ 비교함에 저장했어요" : "고른 보험사는 비교함에 저장돼요 — 나중에 다시 와도 그대로예요."}
          </p>
        ) : (
          <p className="muted calc-watchlist-hint">로그인하면 고른 보험사 목록이 비교함에 저장돼요.</p>
        )}

        <div className="calc-filter-group">
          <label>
            나이 (만)
            <input
              type="number"
              min={0}
              max={80}
              value={age}
              onChange={(e) => setAge(Number(e.target.value))}
            />
          </label>
        </div>

        <button
          type="button"
          className="calc-more-toggle"
          onClick={() => setFiltersExpanded((v) => !v)}
        >
          {filtersExpanded ? "접기 ▴" : "더보기 ▾"}
        </button>
        {!filtersExpanded && (
          <p className="muted calc-filter-summary">
            {PLAN_TIER_LABELS[planTierRank]} 등급 · {sex === "M" ? "남자" : "여자"} ·{" "}
            {order === "asc" ? "낮은 가격순" : "높은 가격순"}
            {hasExtraFilter && " · 필터 적용중"}
          </p>
        )}

        {filtersExpanded && (
          <>
            <div className="calc-filter-group">
              <span className="calc-filter-group__label">등급</span>
              <div className="calc-seg">
                {PLAN_TIER_LABELS.map((label, rank) => (
                  <button
                    key={label}
                    type="button"
                    className={`premium-chip${planTierRank === rank ? " premium-chip--on" : ""}`}
                    onClick={() => setPlanTierRank(rank)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div className="calc-filter-group">
              <span className="calc-filter-group__label">성별</span>
              <div className="calc-seg">
                {(["M", "F"] as const).map((s) => (
                  <button
                    key={s}
                    type="button"
                    className={`premium-chip${sex === s ? " premium-chip--on" : ""}`}
                    onClick={() => setSex(s)}
                  >
                    {s === "M" ? "남자" : "여자"}
                  </button>
                ))}
              </div>
            </div>

            <div className="calc-filter-group">
              <span className="calc-filter-group__label">정렬</span>
              <div className="calc-seg">
                <button
                  type="button"
                  className={`premium-chip${order === "asc" ? " premium-chip--on" : ""}`}
                  onClick={() => setOrder("asc")}
                >
                  낮은 가격순
                </button>
                <button
                  type="button"
                  className={`premium-chip${order === "desc" ? " premium-chip--on" : ""}`}
                  onClick={() => setOrder("desc")}
                >
                  높은 가격순
                </button>
              </div>
            </div>

            <div className="calc-filter-group">
              <span className="calc-filter-group__label">담보 유형</span>
              <select
                value={coverageFilterKey ?? ""}
                onChange={(e) => setCoverageFilterKey(e.target.value || null)}
              >
                <option value="">전체 보기</option>
                {coverageOptions.map((group) => (
                  <optgroup key={group.category} label={group.category}>
                    {group.items.map((opt) => (
                      <option key={opt.key} value={opt.key}>{opt.label}</option>
                    ))}
                  </optgroup>
                ))}
              </select>
              {coverageFilterKey && (
                <p className="muted calc-filter-note">
                  {PLAN_TIER_LABELS[planTierRank]} 등급 기준으로 이 담보가 있는 곳만 보여드려요(정확한 조건은
                  담보 상세표를 확인해 주세요).
                </p>
              )}
            </div>

            <div className="calc-filter-group">
              <span className="calc-filter-group__label">가격대 (1일 기준, 원)</span>
              <div className="calc-filter-group__row">
                <input
                  type="number"
                  min={0}
                  placeholder="최소"
                  value={minPrice}
                  onChange={(e) => setMinPrice(e.target.value)}
                />
                <span className="calc-filter-group__tilde">~</span>
                <input
                  type="number"
                  min={0}
                  placeholder="최대"
                  value={maxPrice}
                  onChange={(e) => setMaxPrice(e.target.value)}
                />
              </div>
            </div>
          </>
        )}
      </div>

      {loading && <p className="muted" style={{ fontSize: "0.82rem" }}>보험료 자료를 불러오는 중...</p>}
      {!loading && error && <div className="error-box">{error}</div>}

      {!loading && !error && selected.length === 0 && (
        <div className="empty-state">
          <Icon3D src="wallet" size={56} />
          <p className="muted">비교할 보험사를 한 곳 이상 골라주세요.</p>
        </div>
      )}

      {!loading && !error && selected.length > 0 && rows.length === 0 && hasExtraFilter && (
        <div className="empty-state">
          <Icon3D src="wallet" size={56} />
          <p className="muted">필터 조건에 맞는 보험사가 없어요.</p>
          <button
            type="button"
            className="premium-chip"
            onClick={() => { setCoverageFilterKey(null); setMinPrice(""); setMaxPrice(""); }}
          >
            필터 초기화
          </button>
        </div>
      )}

      {!loading && data && selected.length > 0 && rows.length > 0 && (
        <>
          <ul className="premium-list">
            {rows.map((item, i) => {
              const chosenPlan = planByInsurer[item.insurer_code];
              const livePlans = plansByInsurer[item.insurer_code];
              const chosenPremium = livePlans?.plans.find((p) => p.plan_name === chosenPlan)?.premium
                ?? item.published_premium;
              const chosenLabel = chosenPlan ?? item.product_name;
              const menuOpen = menuOpenFor === item.insurer_code;
              return (
                <motion.li
                  key={item.insurer_code}
                  className="premium-row"
                  style={{ flexDirection: "column", alignItems: "stretch" }}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                >
                  <div className="premium-row__head">
                    <span className="premium-row__rank">{i + 1}</span>
                    <button
                      type="button"
                      className="premium-row__name premium-row__name--clickable"
                      onClick={() => setPlanModalFor(item.insurer_code)}
                    >
                      {item.insurer_name}
                      {chosenLabel && <em>{chosenLabel}</em>}
                    </button>
                    <span className="premium-row__amount">
                      <span className="premium-row__cost">{chosenPremium.toLocaleString()}원</span>
                      <small>1일 기준</small>
                    </span>
                    <button
                      type="button"
                      className="premium-row__menu-btn"
                      aria-label="더보기"
                      onClick={() => setMenuOpenFor(menuOpen ? null : item.insurer_code)}
                    >
                      ⋮
                    </button>
                  </div>
                  {menuOpen && (
                    <div className="premium-row__menu">
                      <button
                        type="button"
                        className="premium-row__menu-item"
                        onClick={() => {
                          toggle(item.insurer_code);
                          setMenuOpenFor(null);
                        }}
                      >
                        🗑 이 보험사 비교에서 빼기
                      </button>
                    </div>
                  )}
                </motion.li>
              );
            })}
          </ul>

          {rows.map((item) => (
            <Modal
              key={item.insurer_code}
              open={planModalFor === item.insurer_code}
              onClose={() => setPlanModalFor(null)}
              title={`${item.insurer_name} 등급·담보한도`}
            >
              <PlanCoverageBoard
                insurerCode={item.insurer_code}
                age={age}
                sex={sex}
                selectedPlan={planByInsurer[item.insurer_code] ?? null}
                onSelectPlan={(plan) =>
                  setPlanByInsurer((prev) => ({ ...prev, [item.insurer_code]: plan }))
                }
                onPlansLoaded={(p) =>
                  setPlansByInsurer((prev) => ({ ...prev, [item.insurer_code]: p }))
                }
              />
            </Modal>
          ))}
        </>
      )}

      {!loading && data && selected.length > 0 && (missing.ageOutOfRange.length > 0 || missing.noDataYet.length > 0) && (
        <>
          {missing.ageOutOfRange.length > 0 && (
            <p className="muted premium-basis">
              {missing.ageOutOfRange.map((m) => m.label).join(", ")} — 만 {age}세 {sex === "M" ? "남성" : "여성"}은
              가입연령 범위 밖이라 상품이 나오지 않아요.
            </p>
          )}
          {missing.noDataYet.length > 0 && (
            <p className="muted premium-basis">
              {missing.noDataYet.map((m) => m.label).join(", ")} — 아직 실제 보험료를 확보하지 못해
              비교에서 빠졌어요(나이·성별과는 무관해요).
            </p>
          )}
        </>
      )}

      {!loading && data && selected.length > 0 && rows.length > 0 && (
        <p className="premium-basis">
          <strong>{data.premium_period_days}일 기준으로 조회한 실제 보험료입니다.</strong>
        </p>
      )}

      {selected.length > 0 && nonpayment && (
        <div className="card" style={{ marginTop: 16 }}>
          <button
            type="button"
            className="calc-more-toggle calc-more-toggle--plain"
            onClick={() => setShowNonpayment((v) => !v)}
          >
            <span className="section-label">보험금 부지급률(손보협회 공시)</span>
            <span>{showNonpayment ? "접기 ▴" : "펼치기 ▾"}</span>
          </button>
          {showNonpayment && (
          <>
          <table className="coverage-table">
            <thead>
              <tr>
                <th>보험사</th>
                <th>부지급률</th>
                <th>청구이후 해지율</th>
              </tr>
            </thead>
            <tbody>
              {nonpayment.items
                .filter((r) => r.insurer_code && selected.includes(r.insurer_code))
                .map((r) => (
                  <tr key={r.insurer_code}>
                    <td>{r.company_name}</td>
                    <td>{r.unpaid_rate.toFixed(2)}%</td>
                    <td>{r.post_claim_cancel_rate != null ? `${r.post_claim_cancel_rate.toFixed(2)}%` : "-"}</td>
                  </tr>
                ))}
              {nonpayment.industry_average && (
                <tr className="muted">
                  <td>업계평균</td>
                  <td>{nonpayment.industry_average.unpaid_rate.toFixed(2)}%</td>
                  <td>
                    {nonpayment.industry_average.post_claim_cancel_rate != null
                      ? `${nonpayment.industry_average.post_claim_cancel_rate.toFixed(2)}%`
                      : "-"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          </>
          )}
        </div>
      )}

      {/* 보장금액 비교표와 공유 카드는 "가격을 다 본 뒤에 더 파고들 때" 쓰는 도구다.
          목록 위에 있으면 정작 비교하려고 들어온 가격표보다 먼저 눈에 걸린다 — 화면 맨
          아래로 내려서 가격 → 안내 문구 → 더 보기 순서로 읽히게 한다. */}
      <button
        type="button"
        className="rank-compare-trigger"
        onClick={() => setShowComparison(true)}
      >
        <span>📊 {PLAN_TIER_LABELS[planTierRank]} 등급 · 6개사 보장금액 한눈에 비교</span>
        <span className="rank-compare-trigger__arrow">›</span>
      </button>
      <Modal
        open={showComparison}
        onClose={() => setShowComparison(false)}
        title={`${PLAN_TIER_LABELS[planTierRank]} 등급 · 보장금액 비교`}
        className="modal-card--wide"
      >
        {comparisonLoading && <p className="muted" style={{ fontSize: "0.82rem" }}>불러오는 중...</p>}
        {!comparisonLoading && comparison && (
          <>
            {comparison.categories.map((cat) => (
              <div key={cat.category} className="compare-category">
                <p className="compare-category__title">{cat.category}</p>
                <div className="compare-table-scroll">
                  <table className="coverage-table compare-table">
                    <thead>
                      <tr>
                        <th>담보</th>
                        {INSURERS.map((i) => (
                          <th key={i.code}>{i.label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {cat.metrics.map((m) => {
                        const valueByCode = new Map(m.values.map((v) => [v.insurer_code, v.value_text]));
                        return (
                          <tr key={m.metric_label}>
                            <td>{m.metric_label}</td>
                            {INSURERS.map((i) => {
                              const raw = valueByCode.get(i.code);
                              const display = raw == null
                                ? "-"
                                : /^\d+$/.test(raw) ? `${Number(raw).toLocaleString()}${m.unit}` : raw;
                              return <td key={i.code}>{display}</td>;
                            })}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
            <p className="muted plan-board__source">
              {comparison.source}에서 직접 조회한 값이며 — 실제
              가입 시 금액은 달라질 수 있어요.
            </p>
          </>
        )}
      </Modal>

      {selected.length > 0 && (
        <button
          type="button"
          className="rank-compare-trigger"
          onClick={() => { setShareCardError(false); setShowShareCard(true); }}
        >
          <span>🖼 비교 결과 공유 카드 만들기</span>
          <span className="rank-compare-trigger__arrow">›</span>
        </button>
      )}
      <Modal
        open={showShareCard}
        onClose={() => setShowShareCard(false)}
        title="비교 결과 공유 카드"
        className="modal-card--wide"
      >
        {rows.length === 0 ? (
          <p className="muted" style={{ fontSize: "0.82rem" }}>
            카드로 만들 보험사가 없어요. 필터를 조정해 주세요.
          </p>
        ) : (
          <>
            <div ref={shareCardRef} className="share-card">
              <p className="share-card__eyebrow">TRAVEL INSURANCE</p>
              <h3 className="share-card__title">
                만 {age}세 {sex === "M" ? "남성" : "여성"} · {PLAN_TIER_LABELS[planTierRank]} 등급 보험료 비교
              </h3>
              <p className="share-card__subtitle">1일 기준 실제 보험료</p>
              <div className="share-card__list">
                {rows.map((item, i) => (
                  <div key={item.insurer_code} className="share-card__row">
                    <span className="share-card__name">{i + 1}. {item.insurer_name}</span>
                    <span className="share-card__price">{item.published_premium.toLocaleString()}원</span>
                  </div>
                ))}
              </div>
              <p className="share-card__footnote">
                각 보험사 다이렉트 사이트에서 직접 조회한 값이며, 실제 가입조건에 따라 달라질 수 있어요.
              </p>
            </div>
            <button
              type="button"
              className="btn-primary share-card__download-btn"
              disabled={shareCardBusy}
              onClick={async () => {
                if (!shareCardRef.current) return;
                setShareCardBusy(true);
                setShareCardError(false);
                try {
                  const dataUrl = await toPng(shareCardRef.current, { pixelRatio: 2, cacheBust: true });
                  const a = document.createElement("a");
                  a.href = dataUrl;
                  a.download = `보험료비교_${age}세_${PLAN_TIER_LABELS[planTierRank]}등급.png`;
                  a.click();
                } catch {
                  setShareCardError(true);
                } finally {
                  setShareCardBusy(false);
                }
              }}
            >
              {shareCardBusy ? "이미지 만드는 중..." : "이미지로 다운로드"}
            </button>
            {shareCardError && (
              <p className="error-box" style={{ marginTop: 8 }}>이미지 생성에 실패했어요. 다시 시도해 주세요.</p>
            )}
          </>
        )}
      </Modal>
    </div>
  );
}
