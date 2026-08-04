import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type UserPolicyOut, type ExternalPolicyOut, type OverlapReportOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { StepFlow } from "../components/StepFlow";
import { Icon3D } from "../components/Icon3D";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { InsurerPicker } from "../components/InsurerPicker";
import { DateTimeField } from "../components/DateTimeField";
import { ExternalPolicyPicker, KIND_LABELS, type PickedPolicy } from "../components/ExternalPolicyPicker";
import { OverlapReportView } from "../components/OverlapReport";
import { INSURERS, shortInsurerName } from "../data/insurers";
import { motion } from "framer-motion";
import { usePager, PagerNav } from "../components/Pager";

/** 보험 카드 하나. 담보 표가 길어질 수 있어(펼쳤을 때) 스크롤 대신 페이지로 나눠 보여준다.
 * 훅(usePager)을 목록 map() 콜백 안에서 바로 못 쓰기 때문에 별도 컴포넌트로 뺐다. */
function PolicyCard({
  policy, isOpen, onToggle, onDelete,
}: {
  policy: UserPolicyOut;
  isOpen: boolean;
  onToggle: () => void;
  onDelete: () => void;
}) {
  const { page, setPage, totalPages, pageItems } = usePager(policy.coverages, 5);

  return (
    <div className="card policy-card">
      <div className="policy-card__head">
        <button
          type="button"
          onClick={onToggle}
          style={{ background: "none", border: "none", padding: 0, cursor: "pointer", display: "flex", alignItems: "baseline", gap: 8, flex: 1, textAlign: "left" }}
        >
          <span className="policy-card__chevron" style={{ transform: isOpen ? "rotate(90deg)" : undefined, transition: "transform 0.15s", display: "inline-block" }}>
            ›
          </span>
          <strong>{shortInsurerName(policy.matched_insurer_code, policy.matched_insurer_name ?? policy.insurer_name_raw)} 여행자보험</strong>
        </button>
        <button type="button" className="history-card__delete" title="삭제" onClick={onDelete}>
          🗑
        </button>
      </div>
      <div className="muted" style={{ fontSize: "0.85rem" }}>
        {policy.period_start} ~ {policy.period_end}{policy.subscriber_age ? ` · 만 ${policy.subscriber_age}세` : ""}
        {" · "}담보 {policy.coverages.length}건
      </div>
      {isOpen && (
        policy.coverages.length > 0 ? (
          <>
            <table className="coverage-table">
              <thead>
                <tr>
                  <th>담보</th>
                  <th>보장금액</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.map((c) => (
                  <tr key={c.user_coverage_id}>
                    <td>{c.matched_std_name ?? c.raw_name}</td>
                    <td>{c.subscribed_amount ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <PagerNav page={page} totalPages={totalPages} onChange={setPage} label="쪽" />
          </>
        ) : (
          <p className="muted" style={{ fontSize: "0.82rem" }}>이 보험사의 담보 정보를 아직 찾지 못했어요.</p>
        )
      )}
    </div>
  );
}

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
  // 담보 표가 길어서 카드마다 다 펼쳐두면 화면이 너무 길어진다 — 기본은 접어두고
  // 보험 카드를 누르면 그 카드만 펼쳐서 담보 표를 보여준다.
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [external, setExternal] = useState<ExternalPolicyOut[]>([]);
  const [picking, setPicking] = useState(false);
  const [picked, setPicked] = useState<PickedPolicy[]>([]);
  const [overlap, setOverlap] = useState<OverlapReportOut | null>(null);

  async function refresh() {
    if (!userId || !isLoggedIn) return;
    const list = await api.listPolicies(userId);
    setPolicies(list);
    setExternal(await api.listExternalPolicies(userId));
    if (list.length > 0) {
      setOverlap(await api.getCoverageOverlap(userId, { userPolicyId: list[0].user_policy_id }));
    }
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

  async function handleLinkExternal() {
    if (!userId || picked.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      await api.linkExternalPolicies(userId, { provider: "manual", items: picked });
      setPicked([]);
      setPicking(false);
      await refresh();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteExternal(id: number) {
    if (!userId) return;
    await api.deleteExternalPolicy(userId, id);
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
        <PolicyCard
          key={p.user_policy_id}
          policy={p}
          isOpen={expandedId === p.user_policy_id}
          onToggle={() => setExpandedId(expandedId === p.user_policy_id ? null : p.user_policy_id)}
          onDelete={() => setConfirmDeleteId(p.user_policy_id)}
        />
      ))}

      <section style={{ marginTop: 28 }}>
        <h2 style={{ fontSize: "1.05rem" }}>기존에 들고 계신 보험</h2>
        <p className="page-desc">
          실손·상해·일상생활배상책임 같은 기존보험을 등록하면, 이번 여행자보험과 겹치는 담보와
          비는 담보를 약관 원문 근거와 함께 알려드려요.
        </p>

        {external.map((e) => (
          <div className="card" key={e.external_policy_id} style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <strong>{KIND_LABELS[e.kind]}</strong>
              <button type="button" className="history-card__delete" title="삭제"
                onClick={() => handleDeleteExternal(e.external_policy_id)}>🗑</button>
            </div>
            <div className="muted" style={{ fontSize: "0.85rem" }}>
              {e.insurer_name_raw ?? "보험사 미상"}
              {e.indemnity_gen ? ` · ${e.indemnity_gen}세대 실손` : ""}
              {e.enrolled_ym ? ` · ${e.enrolled_ym} 가입` : ""}
            </div>
          </div>
        ))}

        {picking ? (
          <div className="card">
            <ExternalPolicyPicker value={picked} onChange={setPicked} />
            {error && <div className="error-box">{error}</div>}
            <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
              <button type="button" className="btn-primary" disabled={picked.length === 0 || loading}
                onClick={handleLinkExternal}>등록</button>
              <button type="button" onClick={() => { setPicking(false); setPicked([]); }}>취소</button>
            </div>
          </div>
        ) : (
          <button type="button" className="btn-primary" onClick={() => setPicking(true)}>
            기존보험 등록하기
          </button>
        )}

        {overlap && external.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <h2 style={{ fontSize: "1.05rem" }}>중복·공백 진단</h2>
            <OverlapReportView report={overlap} />
          </div>
        )}
      </section>

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
