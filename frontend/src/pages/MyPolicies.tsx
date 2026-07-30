import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type UserPolicyOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { StepFlow } from "../components/StepFlow";
import { Icon3D } from "../components/Icon3D";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { InsurerPicker } from "../components/InsurerPicker";
import { DateTimeField } from "../components/DateTimeField";
import { INSURERS, shortInsurerName } from "../data/insurers";
import { motion } from "framer-motion";

export function MyPolicies() {
  const { userId, isLoggedIn, age: profileAge, updateAge } = useApp();
  const [searchParams] = useSearchParams();
  const prefillInsurer = INSURERS.find((i) => i.code === searchParams.get("insurer"))?.name;
  const [mode, setMode] = useState<"list" | "add">(searchParams.get("mode") === "add" ? "add" : "list");
  const [policies, setPolicies] = useState<UserPolicyOut[]>([]);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [insurerName, setInsurerName] = useState(prefillInsurer ?? "");
  const [productName, setProductName] = useState("");
  const [age, setAge] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  async function refresh() {
    if (!userId || !isLoggedIn) return;
    const list = await api.listPolicies(userId);
    setPolicies(list);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, isLoggedIn]);

  // 프로필에 저장된 나이를 자동으로 채워준다 — 이미 다른 화면에서 한 번 입력했다면 여기서도 다시 안 물어봄.
  useEffect(() => {
    if (mode === "add" && profileAge) setAge((prev) => prev || String(profileAge));
  }, [mode, profileAge]);

  function resetForm() {
    setStep(0);
    setInsurerName("");
    setProductName("");
    setAge("");
    setPeriodStart("");
    setPeriodEnd("");
  }

  async function handleSubmit() {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      if (age && Number(age) !== profileAge) {
        await updateAge(Number(age)).catch(() => {});
      }
      await api.registerPolicy(userId, {
        insurer_name_raw: insurerName,
        product_name_raw: productName || null,
        subscriber_age: age ? Number(age) : null,
        period_start: periodStart,
        period_end: periodEnd,
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

  async function handleDelete(policyId: number) {
    if (!userId) return;
    await api.deletePolicy(userId, policyId);
    setConfirmDeleteId(null);
    await refresh();
  }

  // 보험 등록·관리는 로그인 계정에서만 — 게스트는 브라우저를 새로 열 때마다 데이터가
  // 사실상 새로 시작돼서, 여러 번 다시 찾아와 관리하는 "내 보험" 개념과 맞지 않는다.
  if (!isLoggedIn) {
    return (
      <div className="page">
        <TopBar title="내 보험 보관함" />
        <div className="empty-state">
          <Icon3D src="lock" size={72} />
          <p className="muted">로그인하면 보험을 등록하고 관리할 수 있어요.</p>
          <a href="/account" className="btn-primary" style={{ textDecoration: "none", display: "inline-block", padding: "13px 22px" }}>
            로그인하러 가기
          </a>
        </div>
      </div>
    );
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
              상품명 (알고 있으면)
              <input value={productName} onChange={(e) => setProductName(e.target.value)} placeholder="예: 해외여행보험" />
            </label>
          </>
        ),
        canNext: insurerName.trim().length > 0,
      },
      {
        icon: "calendar",
        eyebrow: "STEP 2 · 가입 정보",
        title: "나이와 보험기간을\n알려주세요",
        content: (
          <>
            <label>
              나이
              <input
                type="number"
                min={0}
                max={120}
                value={age}
                onChange={(e) => setAge(e.target.value)}
                placeholder="예: 30"
              />
            </label>
            <DateTimeField label="보험기간 시작" value={periodStart} onChange={setPeriodStart} mode="date" />
            <DateTimeField label="보험기간 종료" value={periodEnd} onChange={setPeriodEnd} mode="date" minDate={periodStart || undefined} />
            {error && <div className="error-box">{error}</div>}
          </>
        ),
        canNext: !!periodStart && !!periodEnd,
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
        가입한 보험을 등록하면 보험사명을 실제 약관과 자동으로 매칭해서, 그 상품이 실제로 파는 담보를 그대로
        불러와요. 매칭된 담보만 사고 후 청구 검토 대상이 됩니다.
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
          <span>2단계면 충분해요</span>
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
            <button
              type="button"
              className="history-card__delete"
              title="삭제"
              style={{ marginLeft: "auto" }}
              onClick={() => setConfirmDeleteId(p.user_policy_id)}
            >
              🗑
            </button>
          </div>
          <div className="muted">
            {p.period_start} ~ {p.period_end}{p.subscriber_age ? ` · 만 ${p.subscriber_age}세` : ""}
          </div>
          {p.coverages.length > 0 ? (
            <table className="coverage-table">
              <thead>
                <tr>
                  <th>담보</th>
                  <th>보장금액</th>
                </tr>
              </thead>
              <tbody>
                {p.coverages.map((c) => (
                  <tr key={c.user_coverage_id}>
                    <td>{c.matched_std_name ?? c.raw_name}</td>
                    <td>{c.subscribed_amount ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted" style={{ fontSize: "0.82rem" }}>이 보험사의 담보 정보를 아직 찾지 못했어요.</p>
          )}
        </div>
      ))}

      <ConfirmDialog
        open={confirmDeleteId !== null}
        title="보험 삭제"
        message="이 보험을 삭제할까요? 연결된 사고 접수 이력에서도 이 보험 연결이 풀려요."
        onConfirm={() => confirmDeleteId !== null && handleDelete(confirmDeleteId)}
        onCancel={() => setConfirmDeleteId(null)}
      />
    </div>
  );
}
