import type { ClauseOut } from "../api";
import { highlightStyle, HIGHLIGHT_COLORS } from "../colors";

export function ClauseCard({ clause }: { clause: ClauseOut }) {
  const meta = HIGHLIGHT_COLORS[clause.highlight_color] ?? HIGHLIGHT_COLORS["회색"];
  return (
    <div className="clause-card" style={highlightStyle(clause.highlight_color)}>
      <div className="clause-card__head">
        <span className="clause-tag" style={{ color: meta.border }}>
          {clause.highlight_color} · {meta.label}
        </span>
        <span className="clause-article">{clause.article_no}</span>
      </div>
      <p className="clause-text">{clause.text}</p>
      {clause.page_ref && <div className="clause-page">원문 위치: {clause.page_ref}</div>}
    </div>
  );
}
