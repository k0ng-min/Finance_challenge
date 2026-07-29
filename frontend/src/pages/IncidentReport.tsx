import { useEffect, useState } from "react";
import { api, type IncidentAnalysisOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { StepFlow } from "../components/StepFlow";
import { ResultTabs } from "../components/ResultTabs";
import { NextStepCard } from "../components/NextStepCard";

const QUESTION_ICON: Record<string, { icon: string; bg: string }> = {
  diagnosis: { icon: "file-text", bg: "var(--mint-soft)" },
  hospitalized: { icon: "bell", bg: "var(--yellow-soft)" },
  surgery: { icon: "shield", bg: "var(--orange-soft)" },
  local_treatment: { icon: "map-pin", bg: "var(--cream-deep)" },
  medical_cost: { icon: "wallet", bg: "var(--orange-soft)" },
  returned_home: { icon: "flag", bg: "var(--mint-soft)" },
};

export function IncidentReport() {
  const { userId, incidentId, setIncidentId } = useApp();
  const [phase, setPhase] = useState<"intro" | "questions" | "result">("intro");
  const [freeText, setFreeText] = useState("");
  const [occurredAt, setOccurredAt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<IncidentAnalysisOut | null>(null);
  const [answerText, setAnswerText] = useState("");

  useEffect(() => {
    if (incidentId) {
      api.getIncident(incidentId).then((res) => {
        setAnalysis(res);
        setPhase(res.pending_questions.length > 0 ? "questions" : "result");
      }).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleStart() {
    if (!userId || !freeText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.createIncident({
        user_id: userId,
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
          {analysis.findings.length === 0 && (
            <p className="muted">등록된 보험 중 이번 사고와 관련된 담보를 찾지 못했습니다.</p>
          )}
          <ResultTabs groups={groups} />
          <NextStepCard
            to="/checklist"
            icon="file-text"
            iconBg="var(--mint-soft)"
            label="다음 단계"
            title="필요 서류 체크하러 가기"
          />
        </div>
      </div>
    );
  }

  if (phase === "questions" && analysis && analysis.pending_questions.length > 0) {
    const q = analysis.pending_questions[0];
    const meta = QUESTION_ICON[q.target_field] ?? { icon: "chat-bubble", bg: "var(--yellow-soft)" };
    return (
      <div className="page">
        <TopBar title="사고가 발생했어요" />
        <StepFlow
          icon={meta.icon}
          iconBg={meta.bg}
          eyebrow={`추가 확인 ${analysis.pending_questions.length}건 남음`}
          title={q.question_text}
          stepIndex={0}
          stepCount={1}
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

  return (
    <div className="page">
      <TopBar title="사고가 발생했어요" />
      <StepFlow
        icon="chat-bubble"
        iconBg="var(--yellow-soft)"
        eyebrow="INCIDENT"
        title={"당황하지 마세요,\n하나씩 도와드릴게요"}
        subtitle="사고 상황을 자유롭게 적어주시면 등록된 보험을 통합 분석해 드려요."
        stepIndex={0}
        stepCount={1}
        onNext={handleStart}
        nextLabel="사고 분석 요청"
        nextDisabled={!freeText.trim() || loading}
        loading={loading}
      >
        <label>
          사고 상황 (자유롭게 작성)
          <textarea
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            rows={5}
            placeholder="예: 스위스에서 트레킹 중 미끄러져 발목을 다쳐서 현지 병원에서 입원 치료를 받았습니다."
            autoFocus
          />
        </label>
        <label>
          사고 일시 (알고 있으면 입력)
          <input type="datetime-local" value={occurredAt} onChange={(e) => setOccurredAt(e.target.value)} />
        </label>
        {error && <div className="error-box">{error}</div>}
      </StepFlow>
    </div>
  );
}
