import { useState } from "react";
import { api, type ClauseSearchResultOut } from "../api";
import { InsurerPicker } from "./InsurerPicker";
import { ClauseCard } from "./ClauseCard";
import { INSURERS } from "../data/insurers";
import { LoadingScreen } from "./LoadingScreen";
import { usePager, PagerNav } from "./Pager";

const RELEVANCE_LABEL: Record<string, string> = { 직접: "직접 보장", 조건부: "조건부 보장", 면책: "면책(보장 제외)" };
const RELEVANCE_BADGE: Record<string, string> = { 직접: "badge--ok", 조건부: "badge--warn", 면책: "badge--danger" };

/** 보험사가 부지급(면책) 통지서에 적어 둔 조항 번호나 문구로, 그 보험사 약관에서 실제
 * 조항 원문을 찾아 보여준다. 법률 자문이 아니다 — "이 조항이 왜 있는지, 어떤 사고유형에
 * 매핑돼 있는지"까지만 보여주고, 실제 이번 사고에 적용되는지는 사람이 판단해야 한다는
 * 것을 화면에 명시한다.
 *
 * "약관 형광펜"에서 사고를 아직 안 골랐을 때(=사고 연결 조항이 없을 때) 대신 보여준다 —
 * 부지급 통지서는 앱에 접수한 사고와 무관하게 받을 수 있어, 사고 선택을 강제하지 않는다. */
export function RejectionClauseSearch() {
  const [insurerCode, setInsurerCode] = useState<string | null>(null);
  const [keyword, setKeyword] = useState("");
  const [results, setResults] = useState<ClauseSearchResultOut[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const insurerName = INSURERS.find((i) => i.code === insurerCode)?.name;
  const { page, setPage, totalPages, pageItems } = usePager(results ?? [], 3);

  function pickInsurer(name: string) {
    const found = INSURERS.find((i) => i.name === name);
    // 이미 고른 보험사를 다시 누르면 선택을 취소한다(토글) — 다른 보험사를 눌렀을 때만 바꾼다.
    setInsurerCode((prev) => (found && prev === found.code ? null : found?.code ?? null));
  }

  async function handleSearch() {
    if (!insurerCode || keyword.trim().length < 2) {
      setError("보험사를 고르고, 통지서에 적힌 조항 번호나 문구를 2자 이상 입력해주세요.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const r = await api.searchClauses(insurerCode, keyword.trim());
      setResults(r);
    } catch {
      setError("검색 중 문제가 생겼어요. 잠시 후 다시 시도해주세요.");
      setResults(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <p className="muted" style={{ fontSize: "0.85rem", marginTop: 0 }}>
        보험사가 부지급(면책) 통지서에 인용한 조항 번호나 핵심 문구를 입력하면, 그 보험사
        약관 원문에서 실제 조항을 찾아드려요. <strong>법률 자문이 아닙니다</strong> — 조항
        원문과 그 조항이 어떤 사고유형에 어떻게 매핑돼 있는지까지만 보여드리고, 실제 이번
        사고에 적용되는지는 상황마다 다르니 직접 확인이 필요해요. 확실하지 않으면 보험사에
        직접 묻거나 금융감독원 분쟁조정(국번없이 1332)을 신청할 수 있어요.
      </p>

      <div className="card" style={{ marginBottom: 14 }}>
        <p style={{ fontWeight: 700, marginTop: 0, fontSize: "0.9rem" }}>1. 어느 보험사인가요?</p>
        <InsurerPicker value={insurerName ?? ""} onChange={pickInsurer} />

        <label>
          2. 통지서에 적힌 조항 번호나 문구
          <input
            className="clause-search__input"
            placeholder="예: 제4조, 전쟁, 스쿠버다이빙 ..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }}
          />
        </label>
        {error && <div className="error-box" style={{ marginTop: 8 }}>{error}</div>}
        <button type="button" className="btn-primary" style={{ width: "100%", marginTop: 8 }} onClick={handleSearch}>
          조항 찾기
        </button>
      </div>

      {loading && <LoadingScreen icon="notebook" title="약관 원문에서 찾고 있어요" messages={["보험사 약관 원문에서 일치하는 조항을 찾고 있어요"]} />}

      {!loading && results && results.length === 0 && (
        <div className="empty-state">
          <p className="muted">일치하는 조항을 찾지 못했어요. 조항 번호(예: "제4조")로 다시 검색해보세요.</p>
        </div>
      )}

      {!loading && results && results.length > 0 && (
        <div>
          {pageItems.map((r) => (
            <div key={r.clause.clause_id} style={{ marginBottom: 14 }}>
              <ClauseCard clause={r.clause} />
              {r.incident_links.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                  {r.incident_links.map((link, i) => (
                    <span key={i} className={`badge ${RELEVANCE_BADGE[link.relevance] ?? ""}`}>
                      {link.type_name} · {RELEVANCE_LABEL[link.relevance] ?? link.relevance}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          <PagerNav page={page} totalPages={totalPages} onChange={setPage} label="쪽" />
        </div>
      )}
    </div>
  );
}
