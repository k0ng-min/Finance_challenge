import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { api, type PremiumComparisonOut, type NonpaymentRatesOut, type InsurerPlansOut } from "../api";
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

/**
 * 보험료 비교 — 보험사를 골라 나이·성별에 따른 1일 기준 실제 보험료를 비교한다.
 *
 * 2026-08-19부터 보험다모아 비교공시(표준조건 한 값) 대신, 각 사 다이렉트 사이트에서
 * 직접 조회한 실제 등급(플랜)별 가격을 쓴다. 목록 행에는 표준 등급 가격만 보이고,
 * 보험사 이름을 누르면 등급 칩·담보 가입금액표(스크롤)를 팝업으로 볼 수 있다
 * (PlanCoverageBoard) — 목록을 담보 표로 길게 늘리지 않으면서도 등급은 자유롭게
 * 바꿔볼 수 있다. 팝업에서 등급을 바꾸면 목록 행의 가격도 그 등급 가격으로 바뀐다.
 *
 * 숫자는 약관에서 뽑은 값이 아니라 각 사 공시 화면에서 가져온 값이라, 산출 전제와
 * 출처·수집일을 항상 같이 보여준다(숫자만 떼어 보여주지 않는다).
 */
export function PremiumCalc() {
  const { age: profileAge, sex: profileSex } = useApp();
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

  useEffect(() => {
    if (profileAge != null) setAge(profileAge);
  }, [profileAge]);

  useEffect(() => {
    api.getNonpaymentRates().then(setNonpayment).catch(() => setNonpayment(null));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getPremiumComparison(age, sex, order)
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
  }, [age, sex, order]);

  function toggle(code: string) {
    setSelected((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  }

  const rows = useMemo(
    () => (data?.items ?? []).filter((i) => selected.includes(i.insurer_code)),
    [data, selected]
  );
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
      </div>

      {loading && <p className="muted" style={{ fontSize: "0.82rem" }}>보험료 자료를 불러오는 중...</p>}
      {!loading && error && <div className="error-box">{error}</div>}

      {!loading && !error && selected.length === 0 && (
        <div className="empty-state">
          <Icon3D src="wallet" size={56} />
          <p className="muted">비교할 보험사를 한 곳 이상 골라주세요.</p>
        </div>
      )}

      {!loading && data && selected.length > 0 && (
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
                      ⌄
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

          <p className="premium-basis">
            <strong>{data.premium_period_days}일 기준으로 조회한 실제 보험료입니다.</strong>
            <br />
            {data.basis}
            <br />
            여행기간, 담보구성, 가입금액 등 실제 계약조건에 따라 보험료는 달라질 수 있습니다.{" "}
            {data.source && `(출처: ${data.source}, ${data.collected_at} 조회)`}
            {data.source_url && (
              <a href={data.source_url} target="_blank" rel="noreferrer">
                {" "}실제 가입조건 보험료 확인 →
              </a>
            )}
          </p>
        </>
      )}

      {selected.length > 0 && nonpayment && (
        <div className="card" style={{ marginTop: 16 }}>
          <button
            type="button"
            className="premium-row__detail-toggle"
            style={{ marginTop: 0, fontSize: "0.85rem" }}
            onClick={() => setShowNonpayment((v) => !v)}
          >
            {showNonpayment ? "보험금 부지급률(손보협회 공시) 접기 ⌃" : "보험금 부지급률(손보협회 공시) 보기 ⌄"}
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
          <p className="premium-basis" style={{ marginTop: 8 }}>
            {nonpayment.period} 공시 · {nonpayment.scope_note}{" "}
            <a href={nonpayment.source_url} target="_blank" rel="noreferrer">
              {nonpayment.source}({nonpayment.collected_at} 수집) 원문 확인 →
            </a>
          </p>
          </>
          )}
        </div>
      )}
    </div>
  );
}
