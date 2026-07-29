import { useEffect, useState } from "react";
import { api, type IncidentAnalysisOut } from "../api";
import { useApp } from "../context/AppContext";
import { FindingCard } from "../components/FindingCard";

export function IncidentReport() {
  const { userId, incidentId, setIncidentId } = useApp();
  const [freeText, setFreeText] = useState("");
  const [occurredAt, setOccurredAt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<IncidentAnalysisOut | null>(null);
  const [answerDrafts, setAnswerDrafts] = useState<Record<number, string>>({});

  useEffect(() => {
    if (incidentId) {
      api.getIncident(incidentId).then(setAnalysis).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!userId) return;
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
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleAnswer(questionId: number) {
    if (!analysis) return;
    const text = answerDrafts[questionId];
    if (!text?.trim()) return;
    setLoading(true);
    try {
      const res = await api.answerQuestion(analysis.incident_id, questionId, text);
      setAnalysis(res);
      setAnswerDrafts((prev) => {
        const next = { ...prev };
        delete next[questionId];
        return next;
      });
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <h1>사고가 발생했어요</h1>
      <p className="page-desc">
        사고 상황을 자유롭게 적어주세요. 등록하신 보험을 통합 분석해 청구 검토 대상 담보와 필요 서류를
        찾아드리고, 부족한 정보는 하나씩 다시 물어봅니다.
      </p>

      {!analysis && (
        <form className="card form" onSubmit={handleSubmit}>
          <label>
            사고 상황 (자유롭게 작성)
            <textarea
              value={freeText}
              onChange={(e) => setFreeText(e.target.value)}
              rows={5}
              placeholder="예: 스위스에서 트레킹 중 미끄러져 발목을 다쳐서 현지 병원에서 입원 치료를 받았습니다."
              required
            />
          </label>
          <label>
            사고 일시 (알고 있으면 입력)
            <input type="datetime-local" value={occurredAt} onChange={(e) => setOccurredAt(e.target.value)} />
          </label>
          <button type="submit" disabled={loading || !userId}>
            {loading ? "분석 중..." : "사고 분석 요청"}
          </button>
          {error && <div className="error-box">{error}</div>}
        </form>
      )}

      {analysis && (
        <div className="result-section">
          {analysis.pending_questions.length > 0 && (
            <>
              <h2>추가로 확인이 필요해요</h2>
              {analysis.pending_questions.map((q) => (
                <div className="card question-card" key={q.question_id}>
                  <div className="question-text">{q.question_text}</div>
                  <div className="question-answer-row">
                    <input
                      value={answerDrafts[q.question_id] ?? ""}
                      onChange={(e) =>
                        setAnswerDrafts((prev) => ({ ...prev, [q.question_id]: e.target.value }))
                      }
                      placeholder="답변 입력"
                    />
                    <button
                      className="btn-secondary"
                      disabled={loading}
                      onClick={() => handleAnswer(q.question_id)}
                    >
                      답변
                    </button>
                  </div>
                </div>
              ))}
            </>
          )}

          <h2>청구 검토 결과</h2>
          {analysis.findings.length === 0 && (
            <p className="muted">등록된 보험 중 이번 사고와 관련된 담보를 찾지 못했습니다.</p>
          )}
          {analysis.findings.map((f) => (
            <FindingCard key={f.finding_id} finding={f} />
          ))}

          <button className="btn-secondary" onClick={() => setAnalysis(null)}>
            새 사고 입력하기
          </button>
        </div>
      )}
    </div>
  );
}
