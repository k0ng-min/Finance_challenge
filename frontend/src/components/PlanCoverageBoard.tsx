import { useEffect, useState } from "react";
import { api, type InsurerPlanCoverageOut, type InsurerPlansOut } from "../api";

/**
 * 보험사 한 곳의 등급(플랜)을 고르고, 그 등급의 담보 가입금액표를 스크롤로 훑어보는 카드.
 *
 * 순위 상세(가입 전 등급 비교) · 보험 등록(어느 등급인지 기록) · 사고 접수(청구 전 한도
 * 참고) · 보험료 비교 세부설정, 네 곳에서 같은 컴포넌트를 그대로 쓴다 — 등급·담보한도
 * 데이터가 InsurerPremium·InsurerPlanCoverage 두 테이블뿐이라 화면마다 새로 만들 이유가
 * 없다. 담보한도는 보험사 다이렉트 사이트에서 직접 조회한 값이라 실제 약관 문구는 아니다
 * (UserCoverage와는 성격이 다르다) — 그래서 항상 출처를 같이 보여준다.
 */
export function PlanCoverageBoard({
  insurerCode, age, sex, selectedPlan, onSelectPlan, compact, onPlansLoaded,
}: {
  insurerCode: string;
  age?: number | null;
  sex?: "M" | "F" | null;
  selectedPlan: string | null;
  onSelectPlan: (planName: string) => void;
  compact?: boolean;
  /** 이 보험사의 등급별 가격을 불러오면 상위 화면에도 알려준다 — 목록 행의 대표 가격을
   * 고른 등급 가격으로 바꿔 보여주는 등, 이 카드 밖에서도 쓸 수 있게 하기 위함이다. */
  onPlansLoaded?: (plans: InsurerPlansOut | null) => void;
}) {
  const [plans, setPlans] = useState<InsurerPlansOut | null>(null);
  const [coverage, setCoverage] = useState<InsurerPlanCoverageOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setNotFound(false);
    Promise.all([
      api.getInsurerPlans(insurerCode, age ?? undefined, sex ?? undefined).catch(() => null),
      api.getInsurerPlanCoverage(insurerCode).catch(() => null),
    ]).then(([p, c]) => {
      if (cancelled) return;
      setPlans(p);
      setCoverage(c);
      onPlansLoaded?.(p);
      if (!p && !c) {
        setNotFound(true);
      } else {
        // 가격 자료가 있으면 그 등급 순서(가격순)를 기준으로, 없으면 담보한도표 순서로 기본
        // 선택한다 — 아무 등급도 안 골라져 있으면 목록이 비어 보이기 때문.
        const names = p && !p.price_unavailable
          ? p.plans.map((x) => x.plan_name)
          : c?.plan_names ?? [];
        if (names.length > 0 && !names.includes(selectedPlan ?? "")) {
          const standard = p?.plans.find((x) => x.is_standard_tier)?.plan_name;
          onSelectPlan(standard ?? names[0]);
        }
      }
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [insurerCode, age, sex]);

  if (loading) {
    return <p className="muted" style={{ fontSize: "0.82rem" }}>등급·담보한도를 불러오는 중...</p>;
  }
  if (notFound) {
    return <p className="muted" style={{ fontSize: "0.82rem" }}>이 보험사의 등급·담보한도 자료가 아직 없어요.</p>;
  }

  const planNames = plans && !plans.price_unavailable
    ? plans.plans.map((p) => p.plan_name)
    : coverage?.plan_names ?? [];
  const priceByPlan = new Map((plans?.plans ?? []).map((p) => [p.plan_name, p.premium]));
  const rows = (coverage?.rows ?? []).filter((r) => r.plan_name === selectedPlan);

  return (
    <div className={`plan-board${compact ? " plan-board--compact" : ""}`}>
      {planNames.length > 0 && (
        <div className="calc-chips" style={{ marginBottom: 10 }}>
          {planNames.map((name) => (
            <button
              key={name}
              type="button"
              className={`premium-chip${selectedPlan === name ? " premium-chip--on" : ""}`}
              onClick={() => onSelectPlan(name)}
            >
              {name}
              {priceByPlan.has(name) && (
                <> · {priceByPlan.get(name)!.toLocaleString()}원{plans?.premium_period_days ?? 1}일</>
              )}
            </button>
          ))}
        </div>
      )}

      {rows.length > 0 ? (
        <>
          <div className="plan-board__scroll">
            <table className="coverage-table">
              <thead>
                <tr>
                  <th>담보</th>
                  <th>가입금액</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.coverage_label}>
                    <td>{r.coverage_label}</td>
                    <td>{/^\d+$/.test(r.amount_text) ? `${Number(r.amount_text).toLocaleString()}${r.unit}` : r.amount_text}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted plan-board__source">
            {coverage?.source}에서 직접 조회{coverage?.collected_at ? ` (${coverage.collected_at})` : ""} — 실제
            가입 시 금액은 달라질 수 있어요.
          </p>
        </>
      ) : (
        <p className="muted" style={{ fontSize: "0.82rem" }}>담보한도 자료가 없어요.</p>
      )}
    </div>
  );
}
