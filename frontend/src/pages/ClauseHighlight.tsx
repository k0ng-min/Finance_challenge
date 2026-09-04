import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { api, type ClauseOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { IncidentPicker } from "../components/IncidentPicker";
import { LoadingScreen } from "../components/LoadingScreen";
import { TripContextBadge } from "../components/TripContextBadge";
import { EvidenceStats } from "../components/EvidenceStats";
import { RejectionClauseSearch } from "../components/RejectionClauseSearch";

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
function ClausePlainText(
  { text, supported, ready }: { text: string | null; supported: boolean; ready: boolean }
) {
  // "아직 안 만들어졌다"와 "만들 수 없다"는 다른 말이다. 조항 원문을 먼저 보여주고 설명은
  // 뒤따라 채우는 구조라, 준비가 안 끝났을 뿐인데 "만들 수 없어요"라고 하면 거짓말이 된다.
  if (!ready) return <p className="clause-plain muted">쉬운말 설명을 준비하고 있어요...</p>;
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
  /** 형광펜 표시·쉬운말 설명 조회가 이 조항까지 끝났는지. 원문은 처음부터 있다. */
  enriched: boolean;
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
  const [tripContext, setTripContext] = useState<{
    tripDestination: string | null; tripStartDate: string | null; tripEndDate: string | null; incidentCountry: string | null;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  /** 원문은 이미 떴고, 형광펜 표시·쉬운말 설명을 뒤에서 채우는 중인지. */
  const [enriching, setEnriching] = useState(false);
  /** 관련도 순 정렬이 실제로 적용됐는지 — 적용 전에 "관련도 순"이라고 적으면 거짓말이 된다. */
  const [sortedByRelevance, setSortedByRelevance] = useState(false);
  const [index, setIndex] = useState(0);
  const [showPlain, setShowPlain] = useState(false);
  /** 사용자가 조항을 넘겼는지. 읽고 있는 도중에 목록을 재배열하면 보던 조항이 사라진다. */
  const userMovedRef = useRef(false);
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
      setTripContext(null);
      return;
    }
    // 사고를 바꾸면 앞 사고의 조회가 아직 돌고 있다. 이 표시가 없으면 그 결과가 뒤늦게
    // 도착해 새 사고의 목록 위에 덧칠된다.
    let cancelled = false;
    userMovedRef.current = false;
    setLoading(true);
    setSortedByRelevance(false);
    api.getIncident(activeIncidentId)
      .then(async (r) => {
        if (cancelled) return;
        setTripContext({
          tripDestination: r.trip_destination, tripStartDate: r.trip_start_date,
          tripEndDate: r.trip_end_date, incidentCountry: r.incident_country,
        });
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
                enriched: false,
              });
            }
          })
        );
        const list = [...byId.values()];

        // 조항 원문은 이미 손에 있다. 조항마다 Gemini를 2번씩(관련도+쉬운말) 부르는 건
        // 형광펜 표시와 쉬운말 설명 때문인데, 그걸 다 기다렸다가 화면을 그리면 조항이 많은
        // 사고에서 그 앞에 한참 묶인다 — 이 자리에 "보통 3~6개"라고 적혀 있었지만, 실제
        // 상해 사고 한 건에서 31개가 나왔다(호출 62번을 순서대로 기다린다는 뜻이다).
        // 그래서 원문부터 바로 보여주고, 표시는 준비되는 대로 그 자리에 채워 넣는다.
        // 순차 조회 자체는 그대로 둔다 — 한꺼번에 쏘면 무료 티어의 분당 한도를 넘어서
        // 두 번째 조항부터 조용히 실패한다(폴백: 하이라이트 없음).
        setItems(list);
        setShowPlain(false);
        // ?clauseId=가 있으면 그 조항의 위치로 바로 이동한다
        // (예: 청구검토 결과 카드에서 조항을 눌러 들어온 경우).
        const linkedPos = linkedClauseId
          ? list.findIndex((it) => it.clause.clause_id === Number(linkedClauseId))
          : -1;
        setIndex(linkedPos !== -1 ? linkedPos : 0);
        setLoading(false);
        setEnriching(true);

        for (const it of list) {
          if (cancelled) return;
          const [relevance, plain] = await Promise.all([
            api.getClauseRelevance(it.clause.clause_id, activeIncidentId).catch(() => null),
            api.getClausePlainText(it.clause.clause_id, activeIncidentId).catch(() => null),
          ]);
          if (cancelled) return;
          setItems((prev) =>
            prev.map((p) =>
              p.clause.clause_id === it.clause.clause_id
                ? {
                    ...p,
                    relevantChars: relevance?.relevant_chars ?? 0,
                    segments: relevance?.segments ?? null,
                    plainText: plain?.plain_text ?? null,
                    plainSupported: plain?.supported ?? false,
                    enriched: true,
                  }
                : p
            )
          );
        }
        if (cancelled) return;
        setEnriching(false);

        // 관련도 순 정렬은 전부 준비된 뒤에 한 번만 한다. 그것도 사용자가 아직 첫 조항에서
        // 움직이지 않았을 때만 — 읽는 중에 목록이 재배열되면 보던 조항이 눈앞에서 바뀐다.
        // 조항을 지정해 들어온 경우(?clauseId=)도 그 위치가 흐트러지므로 건드리지 않는다.
        if (!userMovedRef.current && linkedPos === -1) {
          setItems((prev) => [...prev].sort((a, b) => b.relevantChars - a.relevantChars));
          setSortedByRelevance(true);
        }
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
        setEnriching(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeIncidentId, linkedClauseId]);

  if (soloLoading) {
    return (
      <div className="page">
        <TopBar title="약관 형광펜" />
        <LoadingScreen icon="highlighter" title="조항을 불러오고 있어요" />
      </div>
    );
  }

  if (soloClause) {
    return (
      <div className="page">
        <TopBar title="약관 형광펜" />
        <PageHero
          icon="highlighter"
          eyebrow="CLAUSE"
          title={"이 조항의 실제 원문이에요"}
          subtitle="특정 사고와 대조한 게 아니라, 조항 자체의 원문과 쉬운말 설명이에요."
        />
        <div className="clause-reader__doc">
          <div className="clause-reader__head">
            <div className="clause-reader__target">{soloClause.article_no}</div>
          </div>
          <p className="clause-reader__text">{soloClause.text}</p>
          {soloPlain && (
            <ClausePlainText text={soloPlain.text} supported={soloPlain.supported} ready />
          )}
          {soloClause.page_ref && <div className="clause-page">원문 위치: {soloClause.page_ref}</div>}
        </div>
      </div>
    );
  }

  if (!activeIncidentId) {
    // 사고를 아직 안 골랐어도 이 화면을 막다른 길로 두지 않는다 — 부지급 통지서는 앱에
    // 접수한 사고와 무관하게 받을 수 있으므로, 보험사·조항 번호로 직접 찾아보게 한다.
    return (
      <div className="page">
        <TopBar title="약관 형광펜" />
        <PageHero
          icon="highlighter"
          eyebrow="CLAUSE HIGHLIGHT"
          title={"약관 원문을\n직접 찾아볼 수 있어요"}
          subtitle={'"사고가 발생했어요"에서 사고를 분석하면 관련 조항이 형광펜으로 여기 모여요. 아직 없다면 보험사와 조항 번호로 직접 찾아볼 수 있어요.'}
        />
        <RejectionClauseSearch />
        <EvidenceStats />
      </div>
    );
  }

  const activeItem = items[Math.min(index, items.length - 1)];

  function goToIndex(next: number) {
    userMovedRef.current = true;
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
        icon="highlighter"
        eyebrow="CLAUSE HIGHLIGHT"
        title={"이 사고와 관련해 찾은 부분,\n노란색으로 한눈에"}
        subtitle="이번 사고유형과 연결된 실제 약관 원문을 노랗게 표시했어요. 표시가 다 준비되면 관련도가 높은 순서로 정렬해 드려요."
      />
      <IncidentPicker userId={userId} value={activeIncidentId} onChange={setActiveIncidentId} />
      {tripContext && (
        <TripContextBadge
          tripDestination={tripContext.tripDestination}
          tripStartDate={tripContext.tripStartDate}
          tripEndDate={tripContext.tripEndDate}
          incidentCountry={tripContext.incidentCountry}
        />
      )}

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
        <LoadingScreen icon="highlighter" title="이 사고와 관련된 부분을 찾고 있어요" messages={["실제 약관 원문과 사고 상황을 대조하고 있어요"]} />
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
              <span className="clause-reader__count">
                {index + 1} / {items.length}
                {sortedByRelevance ? " (관련도 순)" : ""}
              </span>
              <button
                type="button"
                className="clause-reader__navbtn"
                onClick={() => goToIndex(Math.min(items.length - 1, index + 1))}
                disabled={index === items.length - 1}
              >
                다음 조항 →
              </button>
            </div>

            {enriching && (
              <p className="clause-reader__progress muted">
                형광펜 표시를 준비하고 있어요 · {items.filter((it) => it.enriched).length}/{items.length}
                <span className="clause-reader__progress-hint">
                  준비되는 대로 이 자리에 노란색이 채워져요. 원문은 지금 바로 읽으실 수 있어요.
                </span>
              </p>
            )}

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
                  <ClausePlainText
                    text={activeItem.plainText}
                    supported={activeItem.plainSupported}
                    ready={activeItem.enriched}
                  />
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
