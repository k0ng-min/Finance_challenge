import { useEffect, useState } from "react";
import { api, type UserPolicyOut } from "../api";
import { useApp } from "../context/AppContext";
import { PageHero } from "../components/PageHero";
import { Icon3D } from "../components/Icon3D";

interface CoverageDraft {
  raw_name: string;
  subscribed_amount: string;
}

export function MyPolicies() {
  const { userId } = useApp();
  const [policies, setPolicies] = useState<UserPolicyOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [insurerName, setInsurerName] = useState("삼성화재");
  const [productName, setProductName] = useState("해외여행보험");
  const [policyType, setPolicyType] = useState("직접가입");
  const [periodStart, setPeriodStart] = useState("2026-08-10");
  const [periodEnd, setPeriodEnd] = useState("2026-08-20");
  const [coverages, setCoverages] = useState<CoverageDraft[]>([
    { raw_name: "상해사망후유장해", subscribed_amount: "" },
  ]);

  async function refresh() {
    if (!userId) return;
    const list = await api.listPolicies(userId);
    setPolicies(list);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  function updateCoverage(i: number, field: keyof CoverageDraft, value: string) {
    setCoverages((prev) => prev.map((c, idx) => (idx === i ? { ...c, [field]: value } : c)));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      await api.registerPolicy(userId, {
        insurer_name_raw: insurerName,
        product_name_raw: productName,
        policy_type: policyType,
        period_start: periodStart,
        period_end: periodEnd,
        coverages: coverages.filter((c) => c.raw_name.trim()),
      });
      await refresh();
      setCoverages([{ raw_name: "", subscribed_amount: "" }]);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <PageHero
        icon="umbrella"
        iconBg="var(--orange-soft)"
        eyebrow="MY POLICIES"
        title={"내 보험,\n한 곳에 안전하게"}
        subtitle="가입한 보험을 등록하면 보험사명·담보명을 실제 약관과 자동으로 매칭해 보관해 드려요."
      />

      <form className="card form" onSubmit={handleSubmit}>
        <div className="form-row">
          <label>
            보험사명
            <input value={insurerName} onChange={(e) => setInsurerName(e.target.value)} required />
          </label>
          <label>
            상품명
            <input value={productName} onChange={(e) => setProductName(e.target.value)} />
          </label>
        </div>
        <div className="form-row">
          <label>
            가입 유형
            <select value={policyType} onChange={(e) => setPolicyType(e.target.value)}>
              <option value="직접가입">직접가입</option>
              <option value="카드부가">카드부가</option>
              <option value="단체">단체</option>
            </select>
          </label>
        </div>
        <div className="form-row">
          <label>
            보험기간 시작
            <input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} required />
          </label>
          <label>
            보험기간 종료
            <input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} required />
          </label>
        </div>

        <div className="coverage-list">
          <div className="coverage-list__label">가입 담보</div>
          {coverages.map((c, i) => (
            <div className="form-row" key={i}>
              <input
                placeholder="담보명 (예: 해외의료비)"
                value={c.raw_name}
                onChange={(e) => updateCoverage(i, "raw_name", e.target.value)}
              />
              <input
                placeholder="가입금액 (예: 1억원)"
                value={c.subscribed_amount}
                onChange={(e) => updateCoverage(i, "subscribed_amount", e.target.value)}
              />
            </div>
          ))}
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setCoverages((prev) => [...prev, { raw_name: "", subscribed_amount: "" }])}
          >
            + 담보 추가
          </button>
        </div>

        <button type="submit" disabled={loading || !userId}>
          {loading ? "등록 중..." : "보험 등록"}
        </button>
        {error && <div className="error-box">{error}</div>}
      </form>

      <h2>등록된 보험</h2>
      {policies.length === 0 && (
        <div className="empty-state">
          <Icon3D src="wallet" size={72} bg="var(--cream-deep)" rounded="34%" />
          <p className="muted">아직 등록된 보험이 없습니다. 위 양식으로 첫 보험을 등록해보세요.</p>
        </div>
      )}
      {policies.map((p) => (
        <div className="card policy-card" key={p.user_policy_id}>
          <div className="policy-card__head">
            <strong>{p.matched_insurer_name ?? p.insurer_name_raw}</strong>
            <span className="muted">{p.matched_product_name ?? p.product_name_raw}</span>
          </div>
          <div className="muted">{p.period_start} ~ {p.period_end} · {p.policy_type}</div>
          <table className="coverage-table">
            <thead>
              <tr>
                <th>입력한 담보명</th>
                <th>KB 매칭 결과</th>
                <th>가입금액</th>
              </tr>
            </thead>
            <tbody>
              {p.coverages.map((c) => (
                <tr key={c.user_coverage_id}>
                  <td>{c.raw_name}</td>
                  <td>
                    {c.matched_std_name ? (
                      <span className="match-ok">✓ {c.matched_std_name}</span>
                    ) : (
                      <span className="match-none">매칭 안 됨 (KB에 없는 담보)</span>
                    )}
                  </td>
                  <td>{c.subscribed_amount ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
