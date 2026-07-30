import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ClauseOut } from "../api";
import { highlightStyle, HIGHLIGHT_COLORS } from "../colors";

const SNIPPET_LEN = 70;

/** 조항 원문을 통째로 보여주지 않고 짧게 미리보기만 보여준다.
 * incidentId가 있으면 눌렀을 때 약관형광펜으로 이동해서 그 조항을 바로 펼쳐 보여주고,
 * 없으면(사고와 무관한 화면) 제자리에서 펼쳐 보여준다. */
export function ClauseCard({ clause, incidentId }: { clause: ClauseOut; incidentId?: number }) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const meta = HIGHLIGHT_COLORS[clause.highlight_color] ?? HIGHLIGHT_COLORS["회색"];
  const isLong = clause.text.length > SNIPPET_LEN;
  const snippet = isLong ? `${clause.text.slice(0, SNIPPET_LEN)}…` : clause.text;

  function handleClick() {
    if (incidentId) {
      navigate(`/highlights?incidentId=${incidentId}&clauseId=${clause.clause_id}`);
    } else {
      setExpanded((v) => !v);
    }
  }

  return (
    <button type="button" className="clause-card clause-card--compact" style={highlightStyle(clause.highlight_color)} onClick={handleClick}>
      <div className="clause-card__head">
        <span className="clause-tag" style={{ color: meta.border }}>
          {clause.highlight_color} · {meta.label}
        </span>
        <span className="clause-article">{clause.article_no}</span>
      </div>
      <p className="clause-text">{expanded ? clause.text : snippet}</p>
      <span className="clause-card__link">
        {incidentId ? "약관형광펜에서 자세히 보기 →" : (isLong ? (expanded ? "접기" : "더보기") : "")}
      </span>
      {clause.page_ref && <div className="clause-page">원문 위치: {clause.page_ref}</div>}
    </button>
  );
}
