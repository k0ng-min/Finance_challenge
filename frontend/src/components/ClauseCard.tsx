import { useNavigate } from "react-router-dom";
import type { ClauseOut } from "../api";
import { highlightStyle, HIGHLIGHT_COLORS } from "../colors";

const SNIPPET_LEN = 70;

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
        </div>
      )}
      <span className="clause-card__link">약관형광펜에서 자세히 보기 →</span>
      {clause.page_ref && <div className="clause-page">원문 위치: {clause.page_ref}</div>}
    </button>
  );
}
