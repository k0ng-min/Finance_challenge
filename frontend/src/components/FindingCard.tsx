import type { FindingOut } from "../api";
import { ClauseCard } from "./ClauseCard";

const TYPE_LABEL: Record<string, string> = {
  추천담보: "추천 담보",
  제한조건: "제한조건 주의",
  보장공백: "보장 공백",
  필요서류: "필요 서류",
};

export function FindingCard({ finding, incidentId }: { finding: FindingOut; incidentId?: number }) {
  return (
    <div className="finding-card">
      <div className="finding-card__head">
        <span className="finding-type">{TYPE_LABEL[finding.finding_type] ?? finding.finding_type}</span>
        <span className="finding-status">{finding.status}</span>
        {finding.insurer_name && <span className="finding-insurer">{finding.insurer_name}</span>}
      </div>
      {finding.target_ref && <div className="finding-target">{finding.target_ref}</div>}
      <p className="finding-desc">{finding.description}</p>
      {finding.coverage_amount && (
        <div className="finding-amount">
          <span className="finding-amount__label">보장금액</span>
          <span className="finding-amount__value">{finding.coverage_amount}</span>
        </div>
      )}
      {finding.clauses.length > 0 && (
        <div className="finding-clauses">
          {finding.clauses.map((c) => (
            <ClauseCard key={c.clause_id} clause={c} incidentId={incidentId} />
          ))}
        </div>
      )}
    </div>
  );
}
