import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { api, type PremiumComparisonOut, type NonpaymentRatesOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { Icon3D } from "../components/Icon3D";

const INSURERS = [
  { code: "SAMSUNG", label: "삼성화재" },
  { code: "HYUNDAI", label: "현대해상" },
  { code: "MERITZ", label: "메리츠화재" },
  { code: "KB", label: "KB손보" },
  { code: "DB", label: "DB손보" },
  { code: "KAKAOPAY", label: "카카오페이손보" },
];

/**
 * 보험료 비교공시 — 보험사를 골라 나이·성별에 따른 7일 표준조건 공시값을 비교한다.
 *
 * 숫자는 약관에서 뽑은 값이 아니라 보험다모아 비교공시에서 수집한 값이라, 산출 전제와
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
          setError("이 나이는 6개사 모두 가입연령 범위 밖이라 비교공시에 보험료가 없어요.");
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
  // 고른 보험사 중 이 나이·성별로는 상품이 없는 곳 — 조용히 빼지 않고 이유를 밝힌다.
  const missing = useMemo(() => {
    const present = new Set((data?.items ?? []).map((i) => i.insurer_code));
    return INSURERS.filter((i) => selected.includes(i.code) && !present.has(i.code));
  }, [data, selected]);

  return (
    <div className="page">
      <TopBar title="비교공시 보험료" />
      <PageHero
        icon="wallet"
        eyebrow="PREMIUM"
        title={"7일 표준조건\n보험료를 비교해요"}
        subtitle="보험다모아에 공시된 동일 기준의 보험료를 보험사별로 비교해 드려요."
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

        <div className="calc-grid calc-grid--single">
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

        <div className="calc-row">
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

      {loading && <p className="muted" style={{ fontSize: "0.82rem" }}>공시 자료를 불러오는 중...</p>}
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
            {rows.map((item, i) => (
              <motion.li
                key={item.insurer_code}
                className="premium-row"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <span className="premium-row__rank">{i + 1}</span>
                <span className="premium-row__name">
                  {item.insurer_name}
                  {item.product_name && <em>{item.product_name}</em>}
                </span>
                <span className="premium-row__amount">
                  <span className="premium-row__cost">{item.published_premium.toLocaleString()}원</span>
                  <small>1일 기준</small>
                </span>
              </motion.li>
            ))}
          </ul>

          {missing.length > 0 && (
            <p className="muted premium-basis">
              {missing.map((m) => m.label).join(", ")} — 만 {age}세 {sex === "M" ? "남성" : "여성"}은
              가입연령 범위 밖이라 비교공시에 상품이 나오지 않아요.
            </p>
          )}

          <p className="premium-basis">
            <strong>{data.premium_period_days}일 표준조건 비교공시 보험료입니다.</strong>
            <br />
            {data.basis}
            <br />
            실제 가입 보험료는 여행기간, 담보구성, 가입금액 등 계약조건에 따라 달라질 수 있습니다.{" "}
            {data.source_url && (
              <a href={data.source_url} target="_blank" rel="noreferrer">
                {data.source} ({data.collected_at} 수집)에서 실제 가입조건 보험료 확인 →
              </a>
            )}
          </p>
        </>
      )}

      {selected.length > 0 && nonpayment && (
        <div className="card" style={{ marginTop: 16 }}>
          <p className="section-label" style={{ marginBottom: 8 }}>보험금 부지급률(손보협회 공시)</p>
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
        </div>
      )}
    </div>
  );
}
