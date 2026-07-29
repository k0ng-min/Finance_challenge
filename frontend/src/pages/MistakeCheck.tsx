import { useEffect, useState } from "react";
import { api, type ValidationResultOut } from "../api";
import { useApp } from "../context/AppContext";

const SEVERITY_LABEL: Record<string, string> = { 오류: "오류", 경고: "경고", 확인: "확인 필요" };

export function MistakeCheck() {
  const { incidentId } = useApp();
  const [results, setResults] = useState<ValidationResultOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!incidentId) return;
    setLoading(true);
    Promise.all([api.getIncident(incidentId), api.getChecklist(incidentId)])
      .then(([incident, checklist]) => {
        const byCode = new Map<string, ValidationResultOut>();
        incident.validation_results.forEach((r) => byCode.set(r.rule_code, r));
        checklist.validation_results.forEach((r) => byCode.set(r.rule_code, r));
        setResults([...byCode.values()]);
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [incidentId]);

  if (!incidentId) {
    return (
      <div className="page">
        <h1>실수 방지 점검</h1>
        <p className="muted">먼저 "사고가 발생했어요" 메뉴에서 사고를 등록해주세요.</p>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>실수 방지 점검</h1>
      <p className="page-desc">
        보험기간 불일치, 사고정보 누락, 입력 모순, 서류 미확보를 규칙 기반으로 점검합니다. 이 화면은
        지급 여부를 판단하지 않으며, 청구 전에 다시 확인할 항목만 안내합니다.
      </p>
      {loading && <p className="muted">불러오는 중...</p>}
      {error && <div className="error-box">{error}</div>}

      {results.length === 0 && !loading && <p className="muted">점검할 항목이 아직 없습니다.</p>}

      {results.map((r) => (
        <div className={`card alert alert--${r.passed ? "ok" : "warn"}`} key={r.rule_code}>
          <div className="alert__head">
            <strong>{r.rule_name}</strong>
            <span className={`severity-tag severity-tag--${r.severity}`}>
              {SEVERITY_LABEL[r.severity] ?? r.severity}
            </span>
            <span className="alert__status">{r.passed ? "이상 없음" : "확인 필요"}</span>
          </div>
          <p>{r.detail}</p>
        </div>
      ))}
    </div>
  );
}
