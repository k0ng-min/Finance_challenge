import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type IncidentAnalysisOut, type UserPolicyOut, type TripSummaryOut, type OverlapReportOut, userMessage } from "../api";
import { useApp } from "../context/AppContext";
import { shortInsurerName } from "../data/insurers";
import { TopBar } from "../components/TopBar";
import { StepFlow } from "../components/StepFlow";
import { ResultTabs } from "../components/ResultTabs";
import { NextStepCard } from "../components/NextStepCard";
import { DateRangeField, DateTimeField } from "../components/DateTimeField";
import { LoadingScreen } from "../components/LoadingScreen";
import { InsurerPicker } from "../components/InsurerPicker";
import { PlanCoverageBoard } from "../components/PlanCoverageBoard";
import { Modal } from "../components/Modal";
import { PickerField } from "../components/PickerField";
import { ExternalPolicyPicker, type PickedPolicy } from "../components/ExternalPolicyPicker";
import { OverlapReportView } from "../components/OverlapReport";
import { INSURERS } from "../data/insurers";
import { COUNTRIES } from "../data/countries";

const QUESTION_ICON: Record<string, string> = {
  diagnosis: "file-text",
  hospitalized: "bell",
  surgery: "shield",
  local_treatment: "map-pin",
  medical_cost: "wallet",
  returned_home: "flag",
};

export function IncidentReport() {
  const { userId, isLoggedIn, setIncidentId, age: profileAge, updateAge, sex: profileSex, updateSex } = useApp();
  const [searchParams] = useSearchParams();
  const resultOfParam = searchParams.get("resultOf");
  const resumeIncidentId = resultOfParam ? Number(resultOfParam) : null;
  const [phase, setPhase] = useState<"intro" | "questions" | "result">("intro");
  const [introStep, setIntroStep] = useState(0);
  const [picked, setPicked] = useState<PickedPolicy[]>([]);
  const [freeText, setFreeText] = useState("");
  const [occurredAt, setOccurredAt] = useState("");
  const [loading, setLoading] = useState(false);
  const [resuming, setResuming] = useState(!!resumeIncidentId);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<IncidentAnalysisOut | null>(null);
  const [answerText, setAnswerText] = useState("");
  const [policies, setPolicies] = useState<UserPolicyOut[]>([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState<number | null>(null);
  const [insurerCode, setInsurerCode] = useState("");
  // 등록된 보험이 없을 때 보험사만 고르는 경우, 그 보험사의 어느 등급으로 청구할지도
  // 같이 받는다(참고용 — 담보한도를 보고 청구 전에 감을 잡게 해준다).
  const [incidentPlanName, setIncidentPlanName] = useState<string | null>(null);
  const [showIncidentPlanModal, setShowIncidentPlanModal] = useState(false);
  const [trips, setTrips] = useState<TripSummaryOut[]>([]);
  const [selectedTripId, setSelectedTripId] = useState<number | null>(null);
  const [age, setAge] = useState("");
  const [sex, setSex] = useState<"M" | "F" | "">("");
  // 이번 사고를 어느 여행에 붙일지. 등록된 여행 중에서 고르거나(selectedTripId), 이
  // 자리에서 새 여행을 만들어 붙일 수 있다(newTrip).
  //
  // 예전에는 등록된 여행이 딱 하나면 선택기 자체를 안 띄우고 그 여행으로 못박았다.
  // 그래서 지난달 유럽 여행이 하나 남아 있으면, 이번 홍콩에서 난 사고까지 유럽 여행
  // 기록에 들어갔다 — 여행이 하나뿐일 때가 오히려 "새 여행"일 확률이 높은데도.
  // 이제는 여행이 몇 개든 항상 고르게 하고, 그 옆에 새 여행을 만드는 팝업을 둔다.
  const [newTrip, setNewTrip] = useState<{ destination: string; start: string; end: string } | null>(null);
  const [showNewTripModal, setShowNewTripModal] = useState(false);
  const [draftDestination, setDraftDestination] = useState("");
  const [draftStart, setDraftStart] = useState("");
  const [draftEnd, setDraftEnd] = useState("");
  // 이번 접수에서 기존보험을 골랐을 때만 중복·공백 진단을 시도한다(안 골랐으면 빈 결과만
  // 온다). linkExternalPolicies는 fire-and-forget이라 저장이 실제로 끝났는지 알 수 없는데,
  // 진단은 그 저장이 끝난 뒤 DB에서 다시 읽어야 의미가 있다 — 그래서 그 Promise를 들고
  // 있다가 진단 조회 직전에 기다린다(핸들러 자체는 여전히 안 기다리고 화면을 바로 넘긴다).
  const [hasPickedExternal, setHasPickedExternal] = useState(false);
  const externalLinkReadyRef = useRef<Promise<unknown>>(Promise.resolve());
  const [overlap, setOverlap] = useState<OverlapReportOut | null>(null);

  // 한 번 입력한 나이·성별은 자동으로 채워준다 — 매번 다시 입력할 필요 없게.
  useEffect(() => {
    if (profileAge) setAge((prev) => prev || String(profileAge));
  }, [profileAge]);
  useEffect(() => {
    if (profileSex === "M" || profileSex === "F") setSex((prev) => prev || profileSex);
  }, [profileSex]);

  // 로그인 계정: 등록된 보험 중 이번 사고를 어느 보험으로 청구할지 고를 수 있게 목록을 준비한다.
  // 게스트: "내 보험"을 쓸 수 없으니 6개 보험사 중 하나를 바로 고르게 한다(아래 InsurerPicker).
  useEffect(() => {
    if (!userId || !isLoggedIn) return;
    api.listPolicies(userId).then((list) => {
      setPolicies(list);
      setSelectedPolicyId((prev) => prev ?? (list.length > 0 ? list[0].user_policy_id : null));
    }).catch(() => {});
  }, [userId, isLoggedIn]);

  // 사고 일시를 여행 기간 안에서만 고를 수 있도록, 여행 기록도 함께 불러온다.
  useEffect(() => {
    if (!userId) return;
    api.listTrips(userId).then((list) => {
      setTrips(list);
      // 자동으로 첫 여행을 고르지 않는다 — 사용자가 직접 고르거나 새로 만들게 한다.
      setSelectedTripId((prev) => (prev != null && list.some((t) => t.trip_id === prev) ? prev : null));
    }).catch(() => {});
  }, [userId]);

  // 사고 일시의 선택 범위·안내 문구는 "고른 기존 여행"이든 "방금 만든 새 여행"이든
  // 똑같이 필요하다 — 두 경우를 같은 모양으로 맞춰 아래에서 한 번만 다룬다.
  const selectedTrip = newTrip
    ? { destination: newTrip.destination, start_date: newTrip.start, end_date: newTrip.end }
    : trips.find((t) => t.trip_id === selectedTripId) ?? null;
  const hasTripContext = newTrip !== null || selectedTripId !== null;

  // 결과 화면에 진입했고, 이번에 기존보험을 골랐을 때만 중복·공백 진단을 조회한다.
  // (기존보험 저장을 기다렸다가 조회 — 위 externalLinkReadyRef 주석 참고.)
  useEffect(() => {
    if (phase !== "result" || !analysis || !userId || !hasPickedExternal || !analysis.trip_id) return;
    let cancelled = false;
    externalLinkReadyRef.current
      .then(() => api.getCoverageOverlap(userId, { tripId: analysis.trip_id! }))
      .then((r) => { if (!cancelled) setOverlap(r); })
      .catch(() => { if (!cancelled) setOverlap(null); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, analysis?.incident_id, hasPickedExternal, userId]);

  // ?resultOf=<id>로 명시적으로 지정된 경우에만 과거 사고 접수 결과를 불러온다.
  // (context의 incidentId를 그대로 fallback으로 쓰면, 로그인 상태에서 이전에 접수한
  //  사고가 남아있을 때 "사고가 발생했어요"를 눌러도 새 접수 화면 대신 예전 결과로
  //  바로 넘어가버리는 버그가 생긴다.)
  useEffect(() => {
    if (resumeIncidentId) {
      setResuming(true);
      setIncidentId(resumeIncidentId);
      api.getIncident(resumeIncidentId).then((res) => {
        setAnalysis(res);
        setPhase(res.pending_questions.length > 0 ? "questions" : "result");
      }).catch(() => {}).finally(() => setResuming(false));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resumeIncidentId]);

  if (resuming) {
    return (
      <div className="page">
        <TopBar title="사고가 발생했어요" />
        <LoadingScreen icon="collision" title="이전 접수 내역을 불러오고 있어요" messages={["예전에 접수했던 사고를 찾고 있어요"]} />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page">
        <TopBar title="사고가 발생했어요" />
        <LoadingScreen
          icon="collision"
          title="사고 내용을 분석하고 있어요"
          messages={[
            "입력하신 사고 상황을 정리하고 있어요",
            "등록된 보험 약관과 대조하고 있어요",
            "청구에 필요한 서류를 확인하고 있어요",
          ]}
        />
      </div>
    );
  }

  async function handleStart() {
    if (!userId || !freeText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      if (age && Number(age) !== profileAge) await updateAge(Number(age)).catch(() => {});
      if (sex && sex !== profileSex) await updateSex(sex).catch(() => {});
      const res = await api.createIncident({
        user_id: userId,
        trip_id: newTrip ? null : selectedTripId,
        // 등록된 보험을 골랐으면 그걸 쓰고, 없으면(비로그인이거나 등록 전이거나) 고른
        // 보험사 코드로 검토한다 — 백엔드는 user_policy_id가 없을 때 insurer_code를 본다.
        user_policy_id: selectedPolicyId,
        insurer_code: selectedPolicyId ? null : insurerCode || null,
        plan_name: selectedPolicyId ? null : incidentPlanName,
        free_text: freeText,
        occurred_at: occurredAt ? new Date(occurredAt).toISOString() : null,
        country: newTrip ? newTrip.destination : null,
        // 새 여행을 고른 경우 백엔드가 이 값들로 여행을 만들어 사고에 붙인다
        // (trip_id를 비워 보내야 이 경로가 탄다).
        new_trip_destination: newTrip ? newTrip.destination : null,
        new_trip_start_date: newTrip ? newTrip.start : null,
        new_trip_end_date: newTrip ? newTrip.end : null,
      });
      setAnalysis(res);
      setIncidentId(res.incident_id);
      // 결과값을 쓰지 않고 에러도 버리므로 화면 전환 자체는 이 저장을 기다리지 않는다 —
      // 사고 등록은 이미 끝났고, 여기서 기다리면 "흐름을 막지 않는다"는 의도와 어긋난다.
      // 다만 진단(overlap) 조회는 이 저장이 끝난 뒤에만 의미가 있으므로, Promise를 남겨뒀다가
      // 결과 화면에 진입할 때 그 Promise를 기다린 뒤에 조회한다(아래 useEffect 참고).
      if (picked.length > 0) {
        externalLinkReadyRef.current = api
          .linkExternalPolicies(userId, { provider: "manual", items: picked })
          .catch(() => {});
        setHasPickedExternal(true);
      } else {
        setHasPickedExternal(false);
        setOverlap(null);
      }
      setPhase(res.pending_questions.length > 0 ? "questions" : "result");
    } catch (err) {
      setError(userMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleAnswer() {
    if (!analysis || !answerText.trim()) return;
    const question = analysis.pending_questions[0];
    setLoading(true);
    try {
      const res = await api.answerQuestion(analysis.incident_id, question.question_id, answerText);
      setAnalysis(res);
      setAnswerText("");
      setPhase(res.pending_questions.length > 0 ? "questions" : "result");
    } catch (err) {
      setError(userMessage(err));
    } finally {
      setLoading(false);
    }
  }

  if (phase === "result" && analysis) {
    const groups = [
      { key: "추천담보", label: "청구검토 담보", items: analysis.findings.filter((f) => f.finding_type === "추천담보") },
      { key: "필요서류", label: "필요 서류", items: analysis.findings.filter((f) => f.finding_type === "필요서류") },
      { key: "보장공백", label: "보장 공백", items: analysis.findings.filter((f) => f.finding_type === "보장공백") },
    ];
    return (
      <div className="page">
        <TopBar title="청구 검토 결과" />
        <div className="result-section">
          {analysis.linked_insurer_name && (
            <p className="muted" style={{ marginTop: -4 }}>
              {shortInsurerName(analysis.linked_insurer_code, analysis.linked_insurer_name)} 여행자보험 기준으로 검토했어요.
            </p>
          )}
          {analysis.findings.length === 0 && (
            <p className="muted">등록된 보험 중 이번 사고와 관련된 담보를 찾지 못했습니다.</p>
          )}
          <ResultTabs groups={groups} incidentId={analysis.incident_id} />
          {overlap && (
            <section style={{ marginTop: 24 }}>
              <h2 style={{ fontSize: "1.05rem" }}>기존보험과 겹치거나 비는 담보</h2>
              <OverlapReportView report={overlap} />
            </section>
          )}
          <a
            className="price-link"
            href="https://www.fss.or.kr/fss/job/fncCnflCase/list.do?menuNo=201195"
            target="_blank"
            rel="noreferrer"
          >
            ⚖️ 비슷한 사고의 실제 분쟁조정사례가 궁금하신가요? 금융감독원 분쟁조정사례에서
            직접 검색해볼 수 있어요 →
          </a>
          <NextStepCard
            to="/checklist"
            icon="file-text"
            label="다음 단계"
            title="필요 서류 체크하러 가기"
          />
        </div>
      </div>
    );
  }

  if (phase === "questions" && analysis && analysis.pending_questions.length > 0) {
    const q = analysis.pending_questions[0];
    const icon = QUESTION_ICON[q.target_field] ?? "collision";
    return (
      <div className="page">
        <TopBar title="사고가 발생했어요" />
        <StepFlow
          icon={icon}
          eyebrow={`추가 확인 ${analysis.pending_questions.length}건 남음`}
          title={q.question_text}
          stepIndex={0}
          onNext={handleAnswer}
          nextLabel="답변하고 계속하기"
          nextDisabled={!answerText.trim()}
          loading={loading}
        >
          <label>
            답변
            <input
              value={answerText}
              onChange={(e) => setAnswerText(e.target.value)}
              placeholder="편하게 답변해주세요"
              autoFocus
            />
          </label>
          {error && <div className="error-box">{error}</div>}
        </StepFlow>
      </div>
    );
  }

  // 게스트는 보험사 그리드(6개)까지 한 화면에 다 넣으면 카드 안에서 스크롤이 생겨버려서,
  // "어느 보험으로/여행인가" 고르는 화면과 "사고 상황을 적는" 화면 두 스텝으로 나눈다.
  const introSteps = [
    {
      icon: "umbrella",
      eyebrow: "STEP 1 · 보험",
      title: "어느 보험으로\n청구하시나요?",
      content: (
        <>
          {isLoggedIn ? (
            policies.length > 0 ? (
              <>
                <label>
                  어느 보험으로 청구하시나요?
                  <PickerField
                    value={String(selectedPolicyId ?? "")}
                    onChange={(v) => setSelectedPolicyId(Number(v))}
                    modalTitle="청구할 보험"
                    placeholder="보험을 선택하세요"
                    options={policies.map((p) => ({
                      value: String(p.user_policy_id),
                      label: `${shortInsurerName(p.matched_insurer_code, p.matched_insurer_name ?? p.insurer_name_raw)} 여행자보험`,
                    }))}
                  />
                </label>
                {(() => {
                  const chosen = policies.find((p) => p.user_policy_id === selectedPolicyId);
                  return chosen?.matched_insurer_code ? (
                    <button
                      type="button"
                      className="rank-compare-trigger"
                      style={{ marginTop: 12 }}
                      onClick={() => setShowIncidentPlanModal(true)}
                    >
                      <span>📋 이 보험의 등급·담보한도 보기 (참고용)</span>
                      <span className="rank-compare-trigger__arrow">›</span>
                    </button>
                  ) : null;
                })()}
              </>
            ) : (
              // 등록된 보험이 없어도 여기서 흐름을 끊지 않는다. 예전에는 "내 보험 등록하러
              // 가기"로 내보내서 사고 접수가 통째로 중단됐다. 보험사만 고르면 그 회사 약관으로
              // 대조할 수 있고(백엔드는 insurer_code만으로도 검토한다), 그마저 건너뛰어도 된다.
              <>
                <label style={{ marginBottom: 8 }}>어느 보험사로 청구하시나요?</label>
                <InsurerPicker
                  value={INSURERS.find((i) => i.code === insurerCode)?.name ?? ""}
                  onChange={(name) => {
                    setInsurerCode(INSURERS.find((i) => i.name === name)?.code ?? "");
                    setIncidentPlanName(null);
                  }}
                />
                <p className="step-note">
                  아직 등록한 보험이 없네요. 보험사만 골라두면 그 회사 약관으로 맞춰 볼게요.
                  <br />
                  지금 모르겠으면 그냥 넘어가도 괜찮아요.
                </p>
                {insurerCode && (
                  <button
                    type="button"
                    className="rank-compare-trigger"
                    style={{ marginTop: 12 }}
                    onClick={() => setShowIncidentPlanModal(true)}
                  >
                    <span>📋 어느 등급인가요? (알고 있으면, 담보한도 참고용)</span>
                    <span className="rank-compare-trigger__arrow">›</span>
                  </button>
                )}
              </>
            )
          ) : (
            <>
              <label style={{ marginBottom: 8 }}>어느 보험사로 청구하시나요?</label>
              <InsurerPicker
                value={INSURERS.find((i) => i.code === insurerCode)?.name ?? ""}
                onChange={(name) => {
                  setInsurerCode(INSURERS.find((i) => i.name === name)?.code ?? "");
                  setIncidentPlanName(null);
                }}
              />
              {insurerCode && (
                <button
                  type="button"
                  className="rank-compare-trigger"
                  style={{ marginTop: 12 }}
                  onClick={() => setShowIncidentPlanModal(true)}
                >
                  <span>📋 어느 등급인가요? (알고 있으면, 담보한도 참고용)</span>
                  <span className="rank-compare-trigger__arrow">›</span>
                </button>
              )}
            </>
          )}
          {(() => {
            const chosenPolicy = policies.length > 0
              ? policies.find((p) => p.user_policy_id === selectedPolicyId)
              : null;
            const activeInsurerCode = chosenPolicy?.matched_insurer_code ?? (insurerCode || null);
            if (!activeInsurerCode) return null;
            return (
              <Modal
                open={showIncidentPlanModal}
                onClose={() => setShowIncidentPlanModal(false)}
                title="등급·담보한도"
              >
                <PlanCoverageBoard
                  insurerCode={activeInsurerCode}
                  age={Number(age) || profileAge}
                  sex={(sex || profileSex) === "F" ? "F" : (sex || profileSex) === "M" ? "M" : null}
                  selectedPlan={incidentPlanName ?? chosenPolicy?.plan_name ?? null}
                  onSelectPlan={setIncidentPlanName}
                />
              </Modal>
            );
          })()}

          {/* 어느 여행에서 난 사고인지는 서류체크·실수방지·약관형광펜까지 따라다니는
              맥락이라 반드시 정하고 넘어간다. 등록된 여행이 없거나, 있어도 이번 사고가
              그중 어느 것도 아닐 수 있으므로 새 여행을 만드는 길을 항상 같이 둔다. */}
          <label style={{ marginTop: 14 }}>어느 여행에서 있었던 일인가요?</label>
          {trips.length > 0 && (
            <PickerField
              value={newTrip ? "" : String(selectedTripId ?? "")}
              onChange={(v) => { setNewTrip(null); setSelectedTripId(Number(v)); }}
              modalTitle="여행 선택"
              placeholder="여행을 선택하세요"
              options={trips.map((t) => ({
                value: String(t.trip_id),
                label: `${t.destination} · ${t.start_date} ~ ${t.end_date}`,
              }))}
            />
          )}
          {newTrip && (
            <div className="new-trip-chip">
              <span>
                <strong>새 여행 · {newTrip.destination}</strong>
                <em>{newTrip.start} ~ {newTrip.end}</em>
              </span>
              <button type="button" onClick={() => setNewTrip(null)} aria-label="새 여행 취소">✕</button>
            </div>
          )}
          <button
            type="button"
            className="rank-compare-trigger"
            style={{ marginTop: 10 }}
            onClick={() => {
              setDraftDestination(newTrip?.destination ?? "");
              setDraftStart(newTrip?.start ?? "");
              setDraftEnd(newTrip?.end ?? "");
              setShowNewTripModal(true);
            }}
          >
            <span>＋ 목록에 없어요 · 새 여행 등록하기</span>
            <span className="rank-compare-trigger__arrow">›</span>
          </button>

          <Modal
            open={showNewTripModal}
            onClose={() => setShowNewTripModal(false)}
            title="새 여행 등록"
          >
            <label>
              여행 국가
              <PickerField
                value={draftDestination}
                onChange={setDraftDestination}
                placeholder="국가를 선택하세요"
                modalTitle="여행 국가"
                options={COUNTRIES.map((c) => ({ value: c, label: c }))}
              />
            </label>
            <DateRangeField
              label="여행 기간"
              start={draftStart}
              end={draftEnd}
              onChange={(s, e) => { setDraftStart(s); setDraftEnd(e); }}
            />
            <p className="muted" style={{ fontSize: "0.76rem" }}>
              이 사고와 함께 여행도 새로 등록해 드려요. 나중에 계정 화면에서 고칠 수 있어요.
            </p>
            <button
              type="button"
              className="btn-primary"
              style={{ width: "100%" }}
              disabled={!draftDestination || !draftStart || !draftEnd || draftEnd <= draftStart}
              onClick={() => {
                setNewTrip({ destination: draftDestination, start: draftStart, end: draftEnd });
                setSelectedTripId(null);
                setOccurredAt("");
                setShowNewTripModal(false);
              }}
            >
              이 여행으로 등록하기
            </button>
          </Modal>
        </>
      ),
      // 등록된 보험이 있으면 그중 하나를 골라야 하고, 없으면 보험사 선택은 선택사항이다
      // (사고 상황부터 적고 나중에 보험을 붙여도 되게 둔다).
      canNext:
        hasTripContext &&
        (policies.length > 0 ? selectedPolicyId !== null : (isLoggedIn ? true : !!insurerCode)),
    },
    {
      icon: "umbrella",
      eyebrow: "선택 · 기존보험",
      title: "이미 들고 계신\n보험이 있나요?",
      content: <ExternalPolicyPicker value={picked} onChange={setPicked} />,
      canNext: true,
    },
    {
      icon: "collision",
      eyebrow: "STEP 2 · 사고 내용",
      title: "당황하지 마세요,\n하나씩 도와드릴게요",
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
              autoFocus
            />
          </label>
          {/* 나이·성별은 담보 판단과 보험료 안내에 모두 쓰이므로 사고 접수 때도 같이 받는다. */}
          <label style={{ marginBottom: 10 }}>성별</label>
          <div className="tabs">
            {([["M", "남자"], ["F", "여자"]] as const).map(([v, label]) => (
              <button
                key={v}
                type="button"
                className={`tab${sex === v ? " tab--active" : ""}`}
                onClick={() => setSex(v)}
              >
                {label}
              </button>
            ))}
          </div>
          <label>
            사고 상황 (자유롭게 작성)
            <textarea
              value={freeText}
              onChange={(e) => setFreeText(e.target.value)}
              rows={5}
              placeholder="예: 스위스에서 트레킹 중 미끄러져 발목을 다쳐서 현지 병원에서 입원 치료를 받았습니다."
            />
          </label>
          <DateTimeField
            label="사고 일시 (알고 있으면 입력)"
            value={occurredAt}
            onChange={setOccurredAt}
            mode="datetime"
            placeholder="탭해서 날짜와 시간을 선택하세요"
            minDate={selectedTrip?.start_date ?? undefined}
            maxDate={selectedTrip?.end_date ?? undefined}
          />
          {selectedTrip && (
            <p className="muted" style={{ fontSize: "0.76rem", marginTop: -8 }}>
              {selectedTrip.destination} 여행 기간({selectedTrip.start_date} ~ {selectedTrip.end_date}) 안에서만 고를 수 있어요.
            </p>
          )}
          {error && <div className="error-box">{error}</div>}
        </>
      ),
      canNext: !!freeText.trim() && !!age && !!sex,
    },
  ];

  const currentIntro = introSteps[introStep];
  const isLastIntro = introStep === introSteps.length - 1;

  return (
    <div className="page">
      <TopBar title="사고가 발생했어요" />
      <StepFlow
        icon={currentIntro.icon}
        eyebrow={currentIntro.eyebrow}
        title={currentIntro.title}
        stepIndex={introStep}
        onBack={introStep > 0 ? () => setIntroStep((s) => s - 1) : undefined}
        onNext={isLastIntro ? handleStart : () => setIntroStep((s) => s + 1)}
        nextLabel={isLastIntro ? "사고 분석 요청" : "다음"}
        nextDisabled={!currentIntro.canNext || loading}
        loading={loading}
      >
        {currentIntro.content}
      </StepFlow>
    </div>
  );
}
