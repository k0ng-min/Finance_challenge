import { useEffect, useState } from "react";
import { api, type UserPolicyOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { StepFlow } from "../components/StepFlow";
import { Icon3D } from "../components/Icon3D";
import { InsurerPicker } from "../components/InsurerPicker";
import { motion } from "framer-motion";

interface CoverageDraft {
  raw_name: string;
  subscribed_amount: string;
}

const STEP_COUNT = 3;

export function MyPolicies() {
  const { userId } = useApp();
  const [mode, setMode] = useState<"list" | "add">("list");
  const [policies, setPolicies] = useState<UserPolicyOut[]>([]);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [insurerName, setInsurerName] = useState("삼성화재");
  const [productName, setProductName] = useState("해외여행보험");
  const [policyType, setPolicyType] = useState("직접가입");
  const [periodStart, setPeriodStart] = useState("2026-08-10");
  const [periodEnd, setPeriodEnd] = useState("2026-08-20");
  const [coverages, setCoverages] = useState<CoverageDraft[]>([{ raw_name: "", subscribed_amount: "" }]);

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

  function resetForm() {
    setStep(0);
    setInsurerName("");
    setProductName("");
    setCoverages([{ raw_name: "", subscribed_amount: "" }]);
  }

  async function handleSubmit() {
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
      resetForm();
      setMode("list");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  if (mode === "add") {
    const steps = [
      {
        icon: "umbrella", iconBg: "var(--orange-soft)",
        eyebrow: "STEP 1 · 보험사",
        title: "어느 보험사에\n가입하셨나요?",
        content: (
          <>
            <InsurerPicker value={insurerName} onChange={setInsurerName} />
            <label style={{ marginTop: 16 }}>
              상품명
              <input value={productName} onChange={(e) => setProductName(e.target.value)} placeholder="예: 해외여행보험" />
            </label>
          </>
        ),
        canNext: insurerName.trim().length > 0,
      },
      {
        icon: "calendar", iconBg: "var(--yellow-soft)",
        eyebrow: "STEP 2 · 가입 정보",
        title: "가입 유형과\n보험기간을 알려주세요",
        content: (
          <>
            <label>
              가입 유형
              <select value={policyType} onChange={(e) => setPolicyType(e.target.value)}>
                <option value="직접가입">직접가입</option>
                <option value="카드부가">카드부가</option>
                <option value="단체">단체</option>
              </select>
            </label>
            <label>
              보험기간 시작
              <input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} />
            </label>
            <label>
              보험기간 종료
              <input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} />
            </label>
          </>
        ),
        canNext: true,
      },
      {
        icon: "puzzle", iconBg: "var(--mint-soft)",
        eyebrow: "STEP 3 · 가입 담보",
        title: "가입하신 담보를\n알려주세요",
        subtitle: "증권에 적힌 이름 그대로 입력하시면 실제 약관과 자동으로 매칭해 드려요.",
        content: (
          <>
            {coverages.map((c, i) => (
              <div className="form-row" key={i}>
                <input
                  placeholder="담보명 (예: 해외의료비)"
                  value={c.raw_name}
                  onChange={(e) => updateCoverage(i, "raw_name", e.target.value)}
                />
                <input
                  placeholder="가입금액"
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
            {error && <div className="error-box">{error}</div>}
          </>
        ),
        canNext: true,
      },
    ];

    const current = steps[step];
    const isLast = step === steps.length - 1;

    return (
      <div className="page">
        <TopBar title="보험 등록" />
        <StepFlow
          icon={current.icon}
          iconBg={current.iconBg}
          eyebrow={current.eyebrow}
          title={current.title}
          subtitle={current.subtitle}
          stepIndex={step}
          stepCount={STEP_COUNT}
          onBack={() => (step > 0 ? setStep((s) => s - 1) : setMode("list"))}
          onNext={isLast ? handleSubmit : () => setStep((s) => s + 1)}
          nextLabel={isLast ? "등록 완료" : "다음"}
          nextDisabled={!current.canNext || loading}
          loading={loading}
        >
          {current.content}
        </StepFlow>
      </div>
    );
  }

  return (
    <div className="page">
      <TopBar title="내 보험 보관함" />
      <p className="page-desc">
        가입한 보험을 등록하면 보험사명·담보명을 실제 약관과 자동으로 매칭해요. 매칭된 담보만 사고 후
        청구 검토 대상이 됩니다.
      </p>

      <motion.button
        type="button"
        className="home-card"
        style={{ marginBottom: 16 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => setMode("add")}
      >
        <Icon3D src="gift" size={56} bg="var(--yellow-soft)" rounded="30%" />
        <div className="home-card__text">
          <strong>새 보험 등록하기</strong>
          <span>3단계면 충분해요</span>
        </div>
        <span className="home-card__arrow">›</span>
      </motion.button>

      {policies.length === 0 && (
        <div className="empty-state">
          <Icon3D src="wallet" size={72} bg="var(--tan)" rounded="34%" />
          <p className="muted">아직 등록된 보험이 없습니다.</p>
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
