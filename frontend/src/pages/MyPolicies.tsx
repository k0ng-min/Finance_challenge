import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type InsurerCoverageOut, type UserPolicyOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { StepFlow } from "../components/StepFlow";
import { Icon3D } from "../components/Icon3D";
import { InsurerPicker } from "../components/InsurerPicker";
import { DateTimeField } from "../components/DateTimeField";
import { INSURERS, shortInsurerName } from "../data/insurers";
import { motion } from "framer-motion";

interface CoverageSelection {
  checked: boolean;
  amount: string;
}


export function MyPolicies() {
  const { userId } = useApp();
  const [searchParams] = useSearchParams();
  const prefillInsurer = INSURERS.find((i) => i.code === searchParams.get("insurer"))?.name;
  const [mode, setMode] = useState<"list" | "add">(searchParams.get("mode") === "add" ? "add" : "list");
  const [policies, setPolicies] = useState<UserPolicyOut[]>([]);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [insurerName, setInsurerName] = useState(prefillInsurer ?? "");
  const [productName, setProductName] = useState("");
  const [policyType, setPolicyType] = useState("직접가입");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [availableCoverages, setAvailableCoverages] = useState<InsurerCoverageOut[]>([]);
  const [coveragesLoading, setCoveragesLoading] = useState(false);
  const [selections, setSelections] = useState<Record<number, CoverageSelection>>({});

  async function refresh() {
    if (!userId) return;
    const list = await api.listPolicies(userId);
    setPolicies(list);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  // 담보명을 자유 입력받으면 사용자가 "이게 뭔지 모르겠다"고 느끼기 쉽고, 오타가 나면
  // 실제 약관과 매칭이 안 될 수 있다. 대신 그 보험사가 실제로 파는 담보 목록을 그대로
  // 보여주고 체크만 하게 해서, 매칭 실패 가능성 자체를 없앤다.
  useEffect(() => {
    const code = INSURERS.find((i) => i.name === insurerName)?.code;
    if (!code) {
      setAvailableCoverages([]);
      return;
    }
    setCoveragesLoading(true);
    api.getInsurerCoverages(code)
      .then((list) => {
        setAvailableCoverages(list);
        setSelections((prev) => {
          const next: Record<number, CoverageSelection> = {};
          for (const c of list) next[c.coverage_id] = prev[c.coverage_id] ?? { checked: false, amount: "" };
          return next;
        });
      })
      .catch(() => setAvailableCoverages([]))
      .finally(() => setCoveragesLoading(false));
  }, [insurerName]);

  function toggleCoverage(coverageId: number) {
    setSelections((prev) => ({
      ...prev,
      [coverageId]: { ...prev[coverageId], checked: !prev[coverageId]?.checked },
    }));
  }

  function setCoverageAmount(coverageId: number, amount: string) {
    setSelections((prev) => ({
      ...prev,
      [coverageId]: { ...prev[coverageId], amount },
    }));
  }

  function resetForm() {
    setStep(0);
    setInsurerName("");
    setProductName("");
    setSelections({});
  }

  async function handleSubmit() {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const chosen = availableCoverages.filter((c) => selections[c.coverage_id]?.checked);
      await api.registerPolicy(userId, {
        insurer_name_raw: insurerName,
        product_name_raw: productName,
        policy_type: policyType,
        period_start: periodStart,
        period_end: periodEnd,
        coverages: chosen.map((c) => ({
          coverage_id: c.coverage_id,
          raw_name: c.raw_name,
          subscribed_amount: selections[c.coverage_id]?.amount || null,
        })),
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
        icon: "umbrella",
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
        icon: "calendar",
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
            <DateTimeField label="보험기간 시작" value={periodStart} onChange={setPeriodStart} mode="date" />
            <DateTimeField label="보험기간 종료" value={periodEnd} onChange={setPeriodEnd} mode="date" />
          </>
        ),
        canNext: !!periodStart && !!periodEnd,
      },
      {
        icon: "puzzle",
        eyebrow: "STEP 3 · 가입 담보",
        title: "가입하신 담보를\n골라주세요",
        subtitle: `${insurerName}이(가) 실제로 판매하는 담보 목록이에요. 가입하신 항목만 체크하고, 가입금액을 알고 있으면 적어주세요.`,
        content: (
          <>
            {coveragesLoading && <p className="muted">담보 목록을 불러오는 중...</p>}
            {!coveragesLoading && availableCoverages.length === 0 && (
              <p className="muted">이 보험사의 담보 정보를 아직 찾지 못했어요. 담보 없이 등록만 진행할게요.</p>
            )}
            {availableCoverages.map((c) => {
              const sel = selections[c.coverage_id];
              return (
                <div className="coverage-pick" key={c.coverage_id}>
                  <label className="checkbox-label coverage-pick__head">
                    <input
                      type="checkbox"
                      checked={!!sel?.checked}
                      onChange={() => toggleCoverage(c.coverage_id)}
                    />
                    <span>
                      <strong>{c.std_name ?? c.raw_name}</strong>
                      {c.limit_amount && <span className="muted"> · {c.limit_amount}</span>}
                    </span>
                  </label>
                  {sel?.checked && (
                    <input
                      className="coverage-pick__amount"
                      placeholder={c.limit_amount ? `가입금액 (한도 ${c.limit_amount})` : "가입금액"}
                      value={sel.amount}
                      onChange={(e) => setCoverageAmount(c.coverage_id, e.target.value)}
                    />
                  )}
                </div>
              );
            })}
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
          eyebrow={current.eyebrow}
          title={current.title}
          subtitle={current.subtitle}
          stepIndex={step}
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
        <Icon3D src="gift" size={56} />
        <div className="home-card__text">
          <strong>새 보험 등록하기</strong>
          <span>3단계면 충분해요</span>
        </div>
        <span className="home-card__arrow">›</span>
      </motion.button>

      {policies.length === 0 && (
        <div className="empty-state">
          <Icon3D src="wallet" size={72} />
          <p className="muted">아직 등록된 보험이 없습니다.</p>
        </div>
      )}
      {policies.map((p) => (
        <div className="card policy-card" key={p.user_policy_id}>
          <div className="policy-card__head">
            <strong>{shortInsurerName(p.matched_insurer_code, p.matched_insurer_name ?? p.insurer_name_raw)} 여행자보험</strong>
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
