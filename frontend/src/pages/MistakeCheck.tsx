import { useEffect, useState } from "react";
import { api, type ValidationResultOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { Icon3D } from "../components/Icon3D";
import { NextStepCard } from "../components/NextStepCard";

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
        <TopBar title="실수 방지 점검" />
        <div className="empty-state">
          <Icon3D src="shield" size={72} bg="var(--orange-soft)" rounded="34%" />
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
        iconBg="var(--orange-soft)"
        eyebrow="MISTAKE CHECK"
        title={"놓친 건 없는지,\n한번 더 확인해요"}
        subtitle="보험기간 불일치, 정보 누락, 입력 모순, 서류 미확보를 점검합니다. 지급 여부를 판단하지는 않아요."
      />
      {loading && <p className="muted">불러오는 중...</p>}
      {error && <div className="error-box">{error}</div>}

      {results.length === 0 && !loading && (
        <div className="empty-state">
          <Icon3D src="tick" size={64} bg="var(--mint-soft)" rounded="34%" />
          <p className="muted">점검할 항목이 아직 없습니다.</p>
        </div>
      )}

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

      <NextStepCard
        to="/highlights"
        icon="notebook"
        iconBg="var(--tan)"
        label="다음 단계"
        title="근거 약관 확인하러 가기"
      />
    </div>
  );
}
