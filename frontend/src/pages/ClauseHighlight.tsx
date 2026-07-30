import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { api, type ClauseOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { Icon3D } from "../components/Icon3D";
import { IncidentPicker } from "../components/IncidentPicker";
import { LoadingScreen } from "../components/LoadingScreen";

/** 조항 하나를 그 사고 상황과 대조해서, 직접 관련된 부분만 노란색으로 표시한다.
 * 여러 색으로 나누지 않고 "이 사고와 관련 있는지"만 본다. 관련도 계산은 목록 정렬을 위해
 * 한 번만 미리 해두고(useEffect에서 병렬 조회), 여기서는 그 결과를 그대로 그려주기만 한다
 * (같은 조항·사고에 대해 Gemini를 두 번 부르지 않기 위함). */
function ClauseRelevanceText({
  segments,
  fallbackText,
}: {
  segments: { text: string; highlighted: boolean }[] | null;
  fallbackText: string;
}) {
  if (!segments) {
    return <p className="clause-reader__text">{fallbackText}</p>;
  }

  return (
    <p className="clause-reader__text clause-reader__text--inline">
      {segments.map((s, i) =>
        s.highlighted ? (
          <span key={i} className="clause-relevant-mark">{s.text}</span>
        ) : (
          <span key={i}>{s.text}</span>
        )
      )}
    </p>
  );
}

/** "쉬운 말로 보기"는 이제 버튼을 누른 순간이 아니라, 조항 목록을 불러올 때 이미 다 준비해
 * 둔 결과를 그대로 보여주기만 한다(그래서 버튼을 누르면 로딩 없이 바로 뜬다). */
function ClausePlainText({ text, supported }: { text: string | null; supported: boolean }) {
  if (!supported || !text) return <p className="clause-plain muted">지금은 쉬운말 설명을 만들 수 없어요.</p>;
  return <p className="clause-plain">{text}</p>;
}

interface ClauseWithContext {
  clause: ClauseOut;
  targetRef: string | null;
  insurerName: string | null;
  findingType: string;
  relevantChars: number;
  segments: { text: string; highlighted: boolean }[] | null;
  plainText: string | null;
  plainSupported: boolean;
}

/** 검색어가 포함된 부분을 표시해서 왜 이 조항이 검색됐는지 한눈에 보이게 한다. */
function HighlightedSnippet({ text, query }: { text: string; query: string }) {
  const idx = text.indexOf(query);
  if (idx === -1) return <>{text}</>;
  const contextStart = Math.max(0, idx - 30);
  const contextEnd = Math.min(text.length, idx + query.length + 40);
  return (
    <>
      {contextStart > 0 && "…"}
      {text.slice(contextStart, idx)}
      <mark className="clause-search__mark">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length, contextEnd)}
      {contextEnd < text.length && "…"}
    </>
  );
}

export function ClauseHighlight() {
  const { userId, incidentId } = useApp();
  const [searchParams] = useSearchParams();
  const linkedIncidentId = searchParams.get("incidentId");
  const linkedClauseId = searchParams.get("clauseId");
  const [activeIncidentId, setActiveIncidentId] = useState<number | null>(
    linkedIncidentId ? Number(linkedIncidentId) : incidentId
  );
  const [items, setItems] = useState<ClauseWithContext[]>([]);
  const [loading, setLoading] = useState(false);
  const [index, setIndex] = useState(0);
  const [showPlain, setShowPlain] = useState(false);
  const [query, setQuery] = useState("");

  // 사고와 무관하게(가입 전 추천 화면 등에서) 조항 하나만 보러 들어온 경우 — 관련도 하이라이트
  // 없이 원문 + 쉬운말 설명만 보여주는 훨씬 단순한 모드.
  const [soloClause, setSoloClause] = useState<ClauseOut | null>(null);
  const [soloPlain, setSoloPlain] = useState<{ text: string | null; supported: boolean } | null>(null);
  const [soloLoading, setSoloLoading] = useState(false);

  useEffect(() => {
    if (!linkedIncidentId) setActiveIncidentId(incidentId);
  }, [incidentId, linkedIncidentId]);

  useEffect(() => {
    if (!linkedClauseId || activeIncidentId) {
      setSoloClause(null);
      return;
    }
    const id = Number(linkedClauseId);
    setSoloLoading(true);
    Promise.all([api.getClause(id), api.getClausePlainText(id)])
      .then(([clause, plain]) => {
        setSoloClause(clause);
        setSoloPlain({ text: plain.plain_text, supported: plain.supported });
      })
      .catch(() => setSoloClause(null))
      .finally(() => setSoloLoading(false));
  }, [linkedClauseId, activeIncidentId]);

  useEffect(() => {
    if (!activeIncidentId) {
      setItems([]);
      return;
    }
    setLoading(true);
    api.getIncident(activeIncidentId)
      .then(async (r) => {
        const byId = new Map<number, ClauseWithContext>();
        r.findings.forEach((f) =>
          f.clauses.forEach((c) => {
            if (!byId.has(c.clause_id)) {
              byId.set(c.clause_id, {
                clause: c,
                targetRef: f.target_ref,
                insurerName: f.insurer_name,
                findingType: f.finding_type,
                relevantChars: 0,
                segments: null,
                plainText: null,
                plainSupported: true,
              });
            }
          })
        );
        const list = [...byId.values()];

        // 이 사고와 얼마나 관련 있는지(노란 글자 수)와 쉬운말 설명을 전부 미리 계산해서,
        // "쉬운 말로 보기"를 눌렀을 때 다시 기다리지 않게 한다. 조항 개수가 적어(보통 3~6개)
        // 한꺼번에 병렬 조회해도 괜찮다.
        const withRelevance = await Promise.all(
          list.map(async (it) => {
            const [relevance, plain] = await Promise.all([
              api.getClauseRelevance(it.clause.clause_id, activeIncidentId).catch(() => null),
              api.getClausePlainText(it.clause.clause_id, activeIncidentId).catch(() => null),
            ]);
            return {
              ...it,
              relevantChars: relevance?.relevant_chars ?? 0,
              segments: relevance?.segments ?? null,
              plainText: plain?.plain_text ?? null,
              plainSupported: plain?.supported ?? false,
            };
          })
        );
        withRelevance.sort((a, b) => b.relevantChars - a.relevantChars);

        setItems(withRelevance);
        setIndex(0);
        setShowPlain(false);

        // ?clauseId=가 있으면 그 조항의 위치로 바로 이동한다
        // (예: 청구검토 결과 카드에서 조항을 눌러 들어온 경우).
        if (linkedClauseId) {
          const pos = withRelevance.findIndex((it) => it.clause.clause_id === Number(linkedClauseId));
          if (pos !== -1) setIndex(pos);
        }
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeIncidentId, linkedClauseId]);

  if (soloLoading) {
    return (
      <div className="page">
        <TopBar title="약관 형광펜" />
        <LoadingScreen icon="notebook" title="조항을 불러오고 있어요" />
      </div>
    );
  }

  if (soloClause) {
    return (
      <div className="page">
        <TopBar title="약관 형광펜" />
        <PageHero
          icon="notebook"
          eyebrow="CLAUSE"
          title={"이 조항의 실제 원문이에요"}
          subtitle="특정 사고와 대조한 게 아니라, 조항 자체의 원문과 쉬운말 설명이에요."
        />
        <div className="clause-reader__doc">
          <div className="clause-reader__head">
            <div className="clause-reader__target">{soloClause.article_no}</div>
          </div>
          <p className="clause-reader__text">{soloClause.text}</p>
          {soloPlain && <ClausePlainText text={soloPlain.text} supported={soloPlain.supported} />}
          {soloClause.page_ref && <div className="clause-page">원문 위치: {soloClause.page_ref}</div>}
        </div>
      </div>
    );
  }

  if (!activeIncidentId) {
    return (
      <div className="page">
        <TopBar title="약관 형광펜" />
        <div className="empty-state">
          <Icon3D src="star" size={72} />
          <p className="muted">
            "사고가 발생했어요"에서 사고를 분석하면, 그 근거가 된 실제 약관 조항이 여기 모입니다.
          </p>
        </div>
      </div>
    );
  }

  const activeItem = items[Math.min(index, items.length - 1)];

  function goToIndex(next: number) {
    setIndex(next);
    setShowPlain(false);
  }

  function jumpToItem(item: ClauseWithContext) {
    const pos = items.findIndex((it) => it.clause.clause_id === item.clause.clause_id);
    if (pos !== -1) goToIndex(pos);
    setQuery("");
  }

  const trimmedQuery = query.trim();
  const searchMatches = trimmedQuery
    ? items.filter((it) => it.clause.text.includes(trimmedQuery))
    : [];

  return (
    <div className="page">
      <TopBar title="약관 형광펜" />
      <PageHero
        icon="notebook"
        eyebrow="CLAUSE HIGHLIGHT"
        title={"이 사고와 관련된 부분,\n노란색으로 한눈에"}
        subtitle="이번 사고와 직접 관련된 실제 약관 원문만 노랗게 표시했어요. 관련도가 높은 조항부터 보여드려요."
      />
      <IncidentPicker userId={userId} value={activeIncidentId} onChange={setActiveIncidentId} />

      {!loading && items.length > 0 && (
        <div className="clause-search">
          <input
            className="clause-search__input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="약관에서 찾아보기 (예: 스쿠버다이빙, 자기부담금, 14일)"
          />
        </div>
      )}

      {!loading && trimmedQuery && (
        <div className="clause-search__results">
          {searchMatches.length === 0 && (
            <p className="muted" style={{ fontSize: "0.85rem" }}>"{trimmedQuery}"에 해당하는 조항을 찾지 못했어요.</p>
          )}
          {searchMatches.map((it) => (
            <button
              type="button"
              key={it.clause.clause_id}
              className="clause-search__result"
              onClick={() => jumpToItem(it)}
            >
              <div className="clause-search__result-head">
                <span>{it.targetRef ?? "약관 조항"}</span>
                <span className="clause-article">{it.clause.article_no}</span>
              </div>
              <p className="clause-search__result-text">
                <HighlightedSnippet text={it.clause.text} query={trimmedQuery} />
              </p>
            </button>
          ))}
        </div>
      )}

      {loading && (
        <LoadingScreen icon="notebook" title="이 사고와 관련된 부분을 찾고 있어요" messages={["실제 약관 원문과 사고 상황을 대조하고 있어요"]} />
      )}

      {!loading && !trimmedQuery && items.length > 0 && (
        <>
          <div className="clause-reader">
            <div className="clause-reader__nav">
              <button
                type="button"
                className="clause-reader__navbtn"
                onClick={() => goToIndex(Math.max(0, index - 1))}
                disabled={index === 0}
              >
                ← 이전 조항
              </button>
              <span className="clause-reader__count">{index + 1} / {items.length} (관련도 순)</span>
              <button
                type="button"
                className="clause-reader__navbtn"
                onClick={() => goToIndex(Math.min(items.length - 1, index + 1))}
                disabled={index === items.length - 1}
              >
                다음 조항 →
              </button>
            </div>

            <AnimatePresence mode="wait">
              <motion.div
                key={activeItem.clause.clause_id}
                className="clause-reader__doc"
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -12 }}
                transition={{ duration: 0.2 }}
              >
                <div className="clause-reader__head">
                  <div>
                    <div className="clause-reader__target">{activeItem.targetRef ?? "약관 조항"}</div>
                    {activeItem.insurerName && <div className="clause-reader__insurer">{activeItem.insurerName}</div>}
                  </div>
                  <span className="clause-article">{activeItem.clause.article_no}</span>
                </div>
                <ClauseRelevanceText
                  segments={activeItem.segments}
                  fallbackText={activeItem.clause.text}
                />
                <button
                  type="button"
                  className="clause-plain-toggle"
                  onClick={() => setShowPlain((v) => !v)}
                >
                  {showPlain ? "원문으로 접기" : "💬 쉬운 말로 보기"}
                </button>
                {showPlain && (
                  <ClausePlainText text={activeItem.plainText} supported={activeItem.plainSupported} />
                )}
                {activeItem.clause.page_ref && (
                  <div className="clause-page">원문 위치: {activeItem.clause.page_ref}</div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        </>
      )}
    </div>
  );
}
