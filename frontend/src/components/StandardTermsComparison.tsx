import { useEffect, useState } from "react";
import { api, type InsurerStandardComparisonOut } from "../api";
import { LoadingScreen } from "./LoadingScreen";
import { usePager, PagerNav } from "./Pager";

const RELATION_LABEL: Record<string, string> = {
  SAME: "표준과 동일",
  BROADER: "표준보다 넓게 보장",
  NARROWER: "표준보다 좁게 보장",
  MISSING_IN_INSURER: "이 회사 약관에 대응 조항 없음",
};
const RELATION_BADGE: Record<string, string> = {
  SAME: "badge--ok",
  BROADER: "badge--ok",
  NARROWER: "badge--warn",
  MISSING_IN_INSURER: "badge--danger",
};

function highlight(text: string, anchor: string) {
  const idx = text.indexOf(anchor);
  if (idx === -1 || !anchor) return text;
  return (
    <>
      {text.slice(0, idx)}
      <span className="clause-relevant-mark">{text.slice(idx, idx + anchor.length)}</span>
      {text.slice(idx + anchor.length)}
    </>
  );
}

/** 이 보험사 약관을 금융감독원 표준약관(해외여행 실손의료보험)과 조문 단위로 대조한다.
 * 대응 조항을 못 찾은 표준 조문은 목록에서 조용히 빠진다 — 근거 없이 "표준과 같다"고
 * 단정하지 않기 위함이다. 매핑이 아직 없는 조문이 있을 수 있어 부분적인 비교표다. */
export function StandardTermsComparison({ insurerCode }: { insurerCode: string }) {
  const [data, setData] = useState<InsurerStandardComparisonOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const { page, setPage, totalPages, pageItems } = usePager(data?.items ?? [], 2);

  useEffect(() => {
    setLoading(true);
    setError(false);
    api.getInsurerStandardComparison(insurerCode)
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [insurerCode]);

  if (loading) {
    return <LoadingScreen icon="highlighter" title="표준약관과 대조하고 있어요" messages={["금융감독원 표준약관 조문과 실제 약관 원문을 나란히 대조하고 있어요"]} />;
  }

  if (error || !data || data.items.length === 0) {
    return (
      <div className="empty-state">
        <p className="muted">
          아직 이 보험사의 표준약관 대조 데이터가 없어요. 현재는 해외여행 실손의료보험
          표준약관 제1~9조(보장·면책·청구 관련 핵심 조문)만 대조 대상입니다.
        </p>
      </div>
    );
  }

  return (
    <div>
      <p className="muted" style={{ fontSize: "0.85rem", marginTop: 0, marginBottom: 12 }}>
        금융감독원 표준약관(<a href={data.source_url} target="_blank" rel="noreferrer">원문</a>
        {data.amended_at ? ` · ${data.amended_at} 개정` : ""})과 {data.insurer_name} 실제 약관을
        조문 단위로 대조했어요. 대조는 보상 여부를 판정하는 근거가 아니라 참고 정보입니다 —
        표준과 다르게 쓰여 있는 조문이 보이면 원문을 확인하고 보험사에 직접 물어보세요.
      </p>
      {pageItems.map((item) => (
        <div className="card" key={item.standard_clause_id} style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
            <strong>{item.article_no}({item.title})</strong>
            <span className={`badge ${RELATION_BADGE[item.relation] ?? ""}`}>
              {RELATION_LABEL[item.relation] ?? item.relation}
            </span>
          </div>

          <div style={{ marginTop: 10 }}>
            <div className="muted" style={{ fontSize: "0.75rem", marginBottom: 2 }}>표준약관 원문</div>
            <p style={{ fontSize: "0.85rem", margin: 0 }}>
              {highlight(item.standard_text, item.anchor_phrase_standard)}
            </p>
          </div>

          {item.relation === "MISSING_IN_INSURER" ? (
            <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
              <p className="muted" style={{ fontSize: "0.85rem", margin: 0 }}>
                {data.insurer_name} 약관에서 이 조문에 대응하는 조항을 찾지 못했어요.
              </p>
            </div>
          ) : (
            <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
              <div className="muted" style={{ fontSize: "0.75rem", marginBottom: 2 }}>
                {data.insurer_name} 약관 원문{item.insurer_article_no ? ` (${item.insurer_article_no})` : ""}
              </div>
              <p style={{ fontSize: "0.85rem", margin: 0 }}>
                {item.insurer_text && item.anchor_phrase_insurer
                  ? highlight(item.insurer_text, item.anchor_phrase_insurer)
                  : item.insurer_text}
              </p>
            </div>
          )}

          {item.note && (
            <p className="muted" style={{ fontSize: "0.78rem", marginTop: 8, marginBottom: 0 }}>
              {item.note}
            </p>
          )}
        </div>
      ))}
      <PagerNav page={page} totalPages={totalPages} onChange={setPage} label="쪽" />
    </div>
  );
}
