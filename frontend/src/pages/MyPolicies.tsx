import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, type UserPolicyOut, type ExternalPolicyOut, type OverlapReportOut, userMessage } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { StepFlow } from "../components/StepFlow";
import { Icon3D } from "../components/Icon3D";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { InsurerPicker } from "../components/InsurerPicker";
import { PlanCoverageBoard } from "../components/PlanCoverageBoard";
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
          {policy.plan_name && <span className="policy-card__plan">{policy.plan_name}</span>}
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
  const { userId, isLoggedIn, age: profileAge, sex: profileSex, updateAge } = useApp();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const prefillInsurer = INSURERS.find((i) => i.code === searchParams.get("insurer"))?.name;
  const [mode, setMode] = useState<"list" | "add">(searchParams.get("mode") === "add" ? "add" : "list");
  const [policies, setPolicies] = useState<UserPolicyOut[]>([]);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [insurerName, setInsurerName] = useState(prefillInsurer ?? "");
  const [productName, setProductName] = useState("");
  const [planName, setPlanName] = useState<string | null>(null);
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
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, isLoggedIn]);

  // 진단 기준 보험: 사용자가 카드를 펼쳤으면 그 보험 기준으로, 아니면 가장 최근에 등록한
  // 보험 기준으로 본다. list_policies에는 ORDER BY가 없어 목록 순서가 등록 순서를
  // 보장하지 않으므로, 여기서 user_policy_id가 가장 큰(가장 나중에 등록된) 보험을 직접 고른다
  // — 예전에는 항상 list[0](가장 먼저 등록한 보험) 기준으로 진단해서, 이번 여행용으로 새
  // 보험을 등록해도 옛 보험 기준 결과가 나오는 문제가 있었다.
  const basisPolicy =
    policies.length === 0
      ? null
      : (expandedId != null && policies.find((p) => p.user_policy_id === expandedId)) ||
        policies.reduce((latest, p) => (p.user_policy_id > latest.user_policy_id ? p : latest), policies[0]);

  useEffect(() => {
    if (!userId || !basisPolicy) {
      // 보험이 하나도 없으면(전부 삭제 등) 낡은 진단 결과가 화면에 남지 않게 한다.
      setOverlap(null);
      return;
    }
    let cancelled = false;
    api.getCoverageOverlap(userId, { userPolicyId: basisPolicy.user_policy_id })
      .then((r) => { if (!cancelled) setOverlap(r); })
      .catch(() => { if (!cancelled) setOverlap(null); });
    return () => { cancelled = true; };
    // external도 의존성에 넣는다 — 기존보험을 새로 등록/삭제해도(user_policy는 그대로여도)
    // 진단 대상이 바뀌므로 다시 조회해야 한다. refresh()가 매번 새 배열을 만들어 넘기므로
    // 참조 비교로 충분히 재실행된다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, basisPolicy?.user_policy_id, external]);

  // 프로필에 저장된 나이를 자동으로 채워준다 — 이미 다른 화면에서 한 번 입력했다면 여기서도 다시 안 물어봄.
  useEffect(() => {
    if (mode === "add" && profileAge) setAge((prev) => prev || String(profileAge));
  }, [mode, profileAge]);

  function resetForm() {
    setStep(0);
    setInsurerName("");
    setProductName("");
    setPlanName(null);
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
        plan_name: planName,
        subscriber_age: age ? Number(age) : null,
        period_start: periodStart,
        period_end: periodEnd,
      });
      await refresh();
      resetForm();
      setMode("list");
    } catch (err) {
      setError(userMessage(err));
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
      setError(userMessage(err));
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
            <InsurerPicker
              value={insurerName}
              onChange={(name) => {
                setInsurerName(name);
                setPlanName(null);
              }}
            />
            <label style={{ marginTop: 16 }}>
              상품명 (알고 있으면)
              <input value={productName} onChange={(e) => setProductName(e.target.value)} placeholder="예: 해외여행보험" />
            </label>
          </>
        ),
        canNext: insurerName.trim().length > 0,
      },
      {
        icon: "shield",
        eyebrow: "STEP 2 · 등급",
        title: "어느 등급으로\n가입하셨나요?",
        content: (
          <PlanCoverageBoard
            insurerCode={INSURERS.find((i) => i.name === insurerName)?.code ?? ""}
            age={Number(age) || profileAge}
            sex={profileSex === "F" ? "F" : profileSex === "M" ? "M" : null}
            selectedPlan={planName}
            onSelectPlan={setPlanName}
          />
        ),
        // 몰라도 건너뛸 수 있다 — 담보한도 자료가 없는 보험사도 등록은 막지 않는다.
        canNext: true,
      },
      {
        icon: "calendar",
        eyebrow: "STEP 3 · 가입 정보",
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
        가입한 보험을 등록하면 보험사·상품명을 보유한 약관 자료와 대조해 매칭 가능한 담보를 불러와요.
        자료에서 확인된 담보만 사고 후 청구 검토 대상으로 사용합니다.
      </p>

      {/* 두 버튼은 성격이 같다 — "보험을 들이는 일"과 "얼마인지 보는 일". 세로로 쌓으면
          목록(보험 카드)이 화면 아래로 밀려나므로 한 줄에 나란히 둔다.
          보험료 비교가 여기 있는 이유: 홈의 작은 칸은 4개를 넘기지 않고, 비로그인
          상태에서는 이 화면 자체를 못 보므로 그때만 홈 첫 칸이 보험료 비교로 바뀐다. */}
      <div className="policy-actions">
        <motion.button
          type="button"
          className="home-card home-card--compact"
          whileTap={{ scale: 0.98 }}
          onClick={() => setMode("add")}
        >
          <Icon3D src="gift" size={44} />
          <div className="home-card__text">
            <strong>새 보험 등록하기</strong>
            <span>보험사·등급·가입정보를 간단히 알려주세요</span>
          </div>
          <span className="home-card__arrow">›</span>
        </motion.button>

        <motion.button
          type="button"
          className="home-card home-card--compact"
          whileTap={{ scale: 0.98 }}
          onClick={() => navigate("/premium")}
        >
          <Icon3D src="wallet" size={44} />
          <div className="home-card__text">
            <strong>보험료 비교</strong>
            <span>직접조회·환산·추정값을 구분해요</span>
          </div>
          <span className="home-card__arrow">›</span>
        </motion.button>
      </div>

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

      <section className="ext-section">
        <h2 className="ext-section__title">기존에 들고 계신 보험</h2>
        <p className="page-desc">
          실손·상해·일상생활배상책임 같은 기존보험을 등록하면, 이번 여행자보험과 겹치는 담보와
          비는 담보를 약관 원문 근거와 함께 알려드려요.
        </p>

        {external.map((e) => {
          // source가 manual이면 사용자가 직접 고른 것이다. 그 밖의 출처(시연용 mock 등)는
          // 실제 조회 결과가 아닌데 카드 모양이 똑같아서 구분이 안 된다. 그래서 출처가
          // 직접 입력이 아닐 때만 표식과 한 줄 안내를 붙인다 — 평소 화면(직접 입력)은
          // 그대로 두고, 예시 데이터일 때만 반드시 그렇게 말하게 하는 방식이다.
          const isDemo = e.source !== "manual";
          return (
            <div className="card ext-card" key={e.external_policy_id}>
              <div className="ext-card__body">
                <div className="ext-card__kind">
                  {KIND_LABELS[e.kind]}
                  {isDemo && (
                    <span
                      style={{
                        marginLeft: 8, fontSize: "0.72rem", fontWeight: 700,
                        color: "var(--orange)", border: "1px solid var(--orange)",
                        borderRadius: 999, padding: "2px 8px", verticalAlign: "middle",
                      }}
                    >
                      시연용 예시
                    </span>
                  )}
                </div>
                <div className="ext-card__meta">
                  {e.insurer_name_raw ?? "보험사 미상"}
                  {e.indemnity_gen ? ` · ${e.indemnity_gen}세대 실손` : ""}
                  {e.enrolled_ym ? ` · ${e.enrolled_ym} 가입` : ""}
                </div>
                {isDemo && (
                  <div className="ext-card__meta" style={{ color: "var(--orange)" }}>
                    실제 보험 조회 결과가 아니라, 화면 흐름을 보여주기 위해 넣어 둔 예시
                    데이터예요.
                  </div>
                )}
              </div>
              <button type="button" className="history-card__delete" title="삭제"
                onClick={() => handleDeleteExternal(e.external_policy_id)}>🗑</button>
            </div>
          );
        })}

        {picking ? (
          <div className="card">
            <ExternalPolicyPicker value={picked} onChange={setPicked} />
            {error && <div className="error-box">{error}</div>}
            <div className="ext-actions">
              <button type="button" className="btn-primary" disabled={picked.length === 0 || loading}
                onClick={handleLinkExternal}>등록</button>
              <button type="button" className="btn-secondary"
                onClick={() => { setPicking(false); setPicked([]); setError(null); }}>취소</button>
            </div>
          </div>
        ) : (
          <button type="button" className="btn-primary" onClick={() => setPicking(true)}>
            기존보험 등록하기
          </button>
        )}
      </section>

      {/* 진단은 등록 폼과 성격이 다른 결과물이라 섹션을 따로 세운다 — 등록 카드 안에 넣으면
          "등록하는 중"과 "진단 결과"가 한 덩어리로 읽힌다. */}
      {overlap && external.length > 0 && basisPolicy && (
        <section className="ext-section">
          <h2 className="ext-section__title">중복·공백 진단</h2>
          <span className="ext-section__basis">
            {shortInsurerName(basisPolicy.matched_insurer_code, basisPolicy.matched_insurer_name ?? basisPolicy.insurer_name_raw)} 여행자보험 기준
          </span>
          <OverlapReportView report={overlap} />
        </section>
      )}

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
