import { useEffect, useState } from "react";
import { api, type IncidentTypeOut, type InsurerIncidentCoverageOut } from "../api";
import { LoadingScreen } from "./LoadingScreen";
import { usePager, PagerNav } from "./Pager";

const RELEVANCE_LABEL: Record<string, string> = { 직접: "직접 보장", 조건부: "조건부 보장", 면책: "면책(보장 제외)" };
const RELEVANCE_BADGE: Record<string, string> = { 직접: "badge--ok", 조건부: "badge--warn", 면책: "badge--danger" };

/** 가입 전 보험사 상세화면에서, 여행 준비 때 고른 "걱정되는 사고유형"별로 버튼을 보여주고
 * 누르면 그 보험사가 실제로 그 사고유형을 어떤 담보·조항으로 다루는지 그대로 나열한다.
 * 여행위험도 기반 자동추천(추천담보/제한조건/보장공백)과 달리, 사용자가 직접 고른 사고유형
 * 기준으로 그 보험사의 실제 약관 원문을 바로 보여주는 방식이다. */
export function InsurerIncidentClauses({ insurerCode, typeCodes }: { insurerCode: string; typeCodes: string[] }) {
  const [types, setTypes] = useState<IncidentTypeOut[]>([]);
  const [activeTypeId, setActiveTypeId] = useState<number | null>(null);
  const [coverages, setCoverages] = useState<InsurerIncidentCoverageOut[]>([]);
  const [loading, setLoading] = useState(false);
  const { page, setPage, totalPages, pageItems } = usePager(coverages, 2);

  useEffect(() => {
    api.getIncidentTypes()
      .then((all) => {
        const filtered = all.filter((t) => typeCodes.includes(t.l1_code));
        setTypes(filtered);
        setActiveTypeId((prev) => prev ?? (filtered.length > 0 ? filtered[0].type_id : null));
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typeCodes.join(",")]);

  useEffect(() => {
    if (!activeTypeId) return;
    setLoading(true);
    api.getInsurerIncidentCoverages(insurerCode, activeTypeId)
      .then(setCoverages)
      .catch(() => setCoverages([]))
      .finally(() => setLoading(false));
  }, [insurerCode, activeTypeId]);

  if (types.length === 0) {
    return (
      <div className="empty-state">
        <p className="muted">
          여행 준비 단계에서 걱정되는 사고유형을 고르지 않으셨어요. "내 여행"을 다시 준비하며
          사고유형을 고르면, 여기서 이 보험사가 그 사고를 어떻게 보상하는지 바로 보여드려요.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="tabs" style={{ marginBottom: 14, flexWrap: "wrap" }}>
        {types.map((t) => (
          <button
            key={t.type_id}
            type="button"
            className={`tab${activeTypeId === t.type_id ? " tab--active" : ""}`}
            onClick={() => setActiveTypeId(t.type_id)}
          >
            {t.name}
          </button>
        ))}
      </div>

      {loading && <LoadingScreen icon="highlighter" title="관련 약관을 찾고 있어요" messages={["실제 약관 원문에서 이 사고유형과 관련된 조항을 찾고 있어요"]} />}

      {!loading && coverages.length === 0 && (
        <div className="empty-state">
          <p className="muted">이 보험사에서 이 사고유형에 매핑된 약관을 아직 찾지 못했어요.</p>
        </div>
      )}

      {!loading && pageItems.map((cov) => (
        <div className="card" key={cov.coverage_id} style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
            <strong>{cov.coverage_name}</strong>
            <span className={`badge ${RELEVANCE_BADGE[cov.relevance] ?? ""}`}>
              {RELEVANCE_LABEL[cov.relevance] ?? cov.relevance}
            </span>
          </div>
          {cov.limit_amount && (
            <div className="muted" style={{ fontSize: "0.85rem", marginTop: 4 }}>보장한도: {cov.limit_amount}</div>
          )}
          {cov.clauses.map((c) => (
            <div key={c.clause_id} style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
              <div className="clause-article">{c.article_no}</div>
              <p style={{ fontSize: "0.85rem", margin: "4px 0 0" }}>{c.text}</p>
            </div>
          ))}
        </div>
      ))}
      {!loading && <PagerNav page={page} totalPages={totalPages} onChange={setPage} label="쪽" />}
    </div>
  );
}
