import { useEffect, useState } from "react";
import { api, type ValidationResultOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { Icon3D } from "../components/Icon3D";
import { NextStepCard } from "../components/NextStepCard";
import { IncidentPicker } from "../components/IncidentPicker";
import { LoadingScreen } from "../components/LoadingScreen";
import { TripContextBadge } from "../components/TripContextBadge";
import type { IncidentAnalysisOut } from "../api";

const SEVERITY_LABEL: Record<string, string> = { 오류: "오류", 경고: "경고", 확인: "확인 필요" };

export function MistakeCheck() {
  const { userId, incidentId } = useApp();
  const [activeIncidentId, setActiveIncidentId] = useState<number | null>(incidentId);
  const [incident, setIncident] = useState<IncidentAnalysisOut | null>(null);
  const [results, setResults] = useState<ValidationResultOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setActiveIncidentId(incidentId);
  }, [incidentId]);

  useEffect(() => {
    if (!activeIncidentId) return;
    setLoading(true);
    Promise.all([api.getIncident(activeIncidentId), api.getChecklist(activeIncidentId)])
      .then(([inc, checklist]) => {
        const byCode = new Map<string, ValidationResultOut>();
        inc.validation_results.forEach((r) => byCode.set(r.rule_code, r));
        checklist.validation_results.forEach((r) => byCode.set(r.rule_code, r));
        setResults([...byCode.values()]);
        setIncident(inc);
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [activeIncidentId]);

  if (!activeIncidentId) {
    return (
      <div className="page">
        <TopBar title="실수 방지 점검" />
        <div className="empty-state">
          <Icon3D src="shield" size={72} />
          <p className="muted">먼저 "사고가 발생했어요" 메뉴에서 사고를 등록해주세요.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <TopBar title="실수 방지 점검" />
      <PageHero
        icon="shield"
        eyebrow="MISTAKE CHECK"
        title={"놓친 건 없는지,\n한번 더 확인해요"}
        subtitle="보험기간 불일치, 정보 누락, 입력 모순, 서류 미확보를 점검합니다. 지급 여부를 판단하지는 않아요."
      />
      <IncidentPicker userId={userId} value={activeIncidentId} onChange={setActiveIncidentId} />
      {incident && (
        <TripContextBadge
          tripDestination={incident.trip_destination}
          tripStartDate={incident.trip_start_date}
          tripEndDate={incident.trip_end_date}
          incidentCountry={incident.incident_country}
        />
      )}
      {loading && <LoadingScreen icon="shield" title="놓친 부분이 없는지 점검하고 있어요" messages={["입력 내용과 서류 현황을 대조하고 있어요"]} />}
      {error && <div className="error-box">{error}</div>}

      {!loading && results.length === 0 && (
        <div className="empty-state">
          <Icon3D src="tick" size={64} />
          <p className="muted">점검할 항목이 아직 없습니다.</p>
        </div>
      )}

      {!loading && results.map((r) => (
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

      <NextStepCard
        to="/highlights"
        icon="notebook"
        label="다음 단계"
        title="근거 약관 확인하러 가기"
      />
    </div>
  );
}
