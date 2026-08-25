import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ClauseOut } from "../api";
import { highlightStyle, HIGHLIGHT_COLORS } from "../colors";
import { loadFlightDelayStats, internationalAvgDelayMinutes } from "../flightDelayBaseline";

const SNIPPET_LEN = 70;

/** 지연기준시간(시간 단위) 옆에 한국공항공사 실제 평균 지연시간을 참고로 붙인다.
 * 확률·발동 가능성은 주장하지 않고 크기 비교까지만 한다(원본에 총 운항편수가 없어
 * 발생 확률을 계산할 근거가 없기 때문 — flightDelayBaseline.ts 참고). */
function DelayBaselineNote({ hours }: { hours: number }) {
  const [avgMinutes, setAvgMinutes] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    loadFlightDelayStats().then((stats) => {
      if (alive) setAvgMinutes(internationalAvgDelayMinutes(stats));
    });
    return () => { alive = false; };
  }, []);

  if (avgMinutes == null) return null;
  const thresholdMinutes = hours * 60;
  const ratio = Math.round((thresholdMinutes / avgMinutes) * 10) / 10;

  return (
    <div className="muted" style={{ fontSize: "0.72rem", marginTop: 2 }}>
      참고: 한국공항공사 통계상 국제선 평균 지연시간은 약 {avgMinutes}분 — 이 기준({thresholdMinutes}분)은
      평균의 약 {ratio}배{ratio >= 1 ? " 길어요" : " 짧아요"}. (지연 발생 확률이 아닌 크기 비교입니다)
    </div>
  );
}

/** 조항 원문을 통째로 보여주지 않고 짧게 미리보기만 보여준다. 눌리면 항상 약관형광펜으로
 * 이동해서 그 조항을 바로 열어 보여준다 — incidentId가 있으면 그 사고 기준 관련도로,
 * 없으면(가입 전 추천처럼 사고와 무관한 화면) 조항 원문만 보여주는 모드로 연다. */
export function ClauseCard({ clause, incidentId }: { clause: ClauseOut; incidentId?: number }) {
  const navigate = useNavigate();
  const meta = HIGHLIGHT_COLORS[clause.highlight_color] ?? HIGHLIGHT_COLORS["회색"];
  const isLong = clause.text.length > SNIPPET_LEN;
  const snippet = isLong ? `${clause.text.slice(0, SNIPPET_LEN)}…` : clause.text;

  function handleClick() {
    const params = new URLSearchParams({ clauseId: String(clause.clause_id) });
    if (incidentId) params.set("incidentId", String(incidentId));
    navigate(`/highlights?${params.toString()}`);
  }

  const terms = clause.terms ?? [];

  return (
    <button type="button" className="clause-card clause-card--compact" style={highlightStyle(clause.highlight_color)} onClick={handleClick}>
      <div className="clause-card__head">
        <span className="clause-tag" style={{ color: meta.border }}>
          {clause.highlight_color} · {meta.label}
        </span>
        <span className="clause-article">{clause.article_no}</span>
      </div>
      <p className="clause-text">{snippet}</p>
      {terms.length > 0 && (
        <div className="clause-terms">
          {terms.map((t, i) => (
            <span key={i} className="clause-term-badge">
              {t.term_type}
              {t.value_num != null && `: ${t.value_num.toLocaleString()}${t.unit ?? ""}`}
              {t.basis && ` (${t.basis})`}
            </span>
          ))}
          {terms
            .filter((t) => t.term_type === "지연기준시간" && t.unit === "시간" && t.value_num != null)
            .slice(0, 1)
            .map((t, i) => <DelayBaselineNote key={i} hours={t.value_num as number} />)}
        </div>
      )}
      <span className="clause-card__link">약관형광펜에서 자세히 보기 →</span>
      {clause.page_ref && <div className="clause-page">원문 위치: {clause.page_ref}</div>}
    </button>
  );
}
