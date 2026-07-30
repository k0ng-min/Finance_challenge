import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { api, type IncidentAnalysisOut, type UserPolicyOut, type TripSummaryOut } from "../api";
import { useApp } from "../context/AppContext";
import { shortInsurerName } from "../data/insurers";
import { TopBar } from "../components/TopBar";
import { StepFlow } from "../components/StepFlow";
import { ResultTabs } from "../components/ResultTabs";
import { NextStepCard } from "../components/NextStepCard";
import { DateTimeField } from "../components/DateTimeField";
import { LoadingScreen } from "../components/LoadingScreen";
import { InsurerPicker } from "../components/InsurerPicker";
import { PickerField } from "../components/PickerField";
import { INSURERS } from "../data/insurers";

const QUESTION_ICON: Record<string, string> = {
  diagnosis: "file-text",
  hospitalized: "bell",
  surgery: "shield",
  local_treatment: "map-pin",
  medical_cost: "wallet",
  returned_home: "flag",
};

export function IncidentReport() {
  const { userId, isLoggedIn, setIncidentId, age: profileAge, updateAge } = useApp();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const resultOfParam = searchParams.get("resultOf");
  const resumeIncidentId = resultOfParam ? Number(resultOfParam) : null;
  const [phase, setPhase] = useState<"intro" | "questions" | "result">("intro");
  const [introStep, setIntroStep] = useState(0);
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
  const [trips, setTrips] = useState<TripSummaryOut[]>([]);
  const [selectedTripId, setSelectedTripId] = useState<number | null>(null);
  const [age, setAge] = useState("");

  // 로그인 계정은 프로필에 저장된 나이를 자동으로 채워준다 — 매번 다시 입력할 필요 없게.
  useEffect(() => {
    if (isLoggedIn && profileAge) setAge((prev) => prev || String(profileAge));
  }, [isLoggedIn, profileAge]);

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
      setSelectedTripId((prev) => prev ?? (list.length > 0 ? list[0].trip_id : null));
    }).catch(() => {});
  }, [userId]);

  const selectedTrip = trips.find((t) => t.trip_id === selectedTripId) ?? null;

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
        <LoadingScreen icon="chat-bubble" title="이전 접수 내역을 불러오고 있어요" messages={["예전에 접수했던 사고를 찾고 있어요"]} />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page">
        <TopBar title="사고가 발생했어요" />
        <LoadingScreen
          icon="chat-bubble"
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
      if (isLoggedIn && age && Number(age) !== profileAge) {
        await updateAge(Number(age)).catch(() => {});
      }
      const res = await api.createIncident({
        user_id: userId,
        trip_id: selectedTripId,
        user_policy_id: isLoggedIn ? selectedPolicyId : null,
        insurer_code: isLoggedIn ? null : insurerCode || null,
        free_text: freeText,
        occurred_at: occurredAt ? new Date(occurredAt).toISOString() : null,
      });
      setAnalysis(res);
      setIncidentId(res.incident_id);
      setPhase(res.pending_questions.length > 0 ? "questions" : "result");
    } catch (err) {
      setError(String(err));
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
      setError(String(err));
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
    const icon = QUESTION_ICON[q.target_field] ?? "chat-bubble";
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
            ) : (
              <div className="card" style={{ marginBottom: 14 }}>
                <p className="muted" style={{ marginTop: 0 }}>등록된 보험이 없어요. 먼저 등록하면 어느 보험으로 청구할지 고를 수 있어요.</p>
                <button type="button" className="btn-secondary" onClick={() => navigate("/policies?mode=add")}>
                  내 보험 등록하러 가기
                </button>
              </div>
            )
          ) : (
            <>
              <label style={{ marginBottom: 8 }}>어느 보험사로 청구하시나요?</label>
              <InsurerPicker
                value={INSURERS.find((i) => i.code === insurerCode)?.name ?? ""}
                onChange={(name) => setInsurerCode(INSURERS.find((i) => i.name === name)?.code ?? "")}
              />
            </>
          )}

          {trips.length > 1 && (
            <label style={{ marginTop: 14 }}>
              어느 여행에서 있었던 일인가요?
              <PickerField
                value={String(selectedTripId ?? "")}
                onChange={(v) => setSelectedTripId(Number(v))}
                modalTitle="여행 선택"
                placeholder="여행을 선택하세요"
                options={trips.map((t) => ({
                  value: String(t.trip_id),
                  label: `${t.destination} · ${t.start_date} ~ ${t.end_date}`,
                }))}
              />
            </label>
          )}
        </>
      ),
      canNext: isLoggedIn ? (policies.length === 0 || selectedPolicyId !== null) : !!insurerCode,
    },
    {
      icon: "chat-bubble",
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
      canNext: !!freeText.trim() && !!age,
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
