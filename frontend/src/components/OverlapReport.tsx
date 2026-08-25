import type { OverlapFindingOut, OverlapReportOut } from "../api";

/** 진단 결과 표시. 근거 조항 원문을 그대로 붙이고, 근거가 없으면 "확인불가"라고 밝힌다. */

type Tone = "gap" | "dup" | "ok" | "unknown";

function Finding({ f, tone }: { f: OverlapFindingOut; tone: Tone }) {
  return (
    <div className={`card overlap-card overlap-card--${tone}`}>
      <div className="overlap-card__head">
        {f.coverage_std_name}
        {f.scope !== "전체" && <span className="overlap-card__scope"> · {f.scope}</span>}
      </div>
      {f.note && <p className="overlap-card__note">{f.note}</p>}
      {f.clause_quote ? (
        <blockquote className="overlap-quote">
          {f.clause_quote}
          <cite className="overlap-quote__source">— {f.clause_article_no}</cite>
        </blockquote>
      ) : (
        <p className="overlap-nobasis">약관 근거를 찾지 못해 확인불가입니다.</p>
      )}
    </div>
  );
}

function Group({ title, items, tone }: { title: string; items: OverlapFindingOut[]; tone: Tone }) {
  if (items.length === 0) return null;
  return (
    <section className="overlap-group">
      <h3 className="overlap-group__title">
        {title}
        <span className="overlap-group__count">{items.length}</span>
      </h3>
      {items.map((f) => (
        <Finding key={`${f.coverage_std_code}-${f.scope}-${f.external_kind}`} f={f} tone={tone} />
      ))}
    </section>
  );
}

export function OverlapReportView(
  { report, showUnknown = true }: { report: OverlapReportOut; showUnknown?: boolean },
) {
  const empty =
    report.duplicates.length === 0 && report.gaps.length === 0 &&
    report.fixed_ok.length === 0 && report.unknown.length === 0;

  if (empty) {
    return <p className="muted">진단할 내용이 없어요. 기존보험과 여행자보험을 모두 등록하면 결과가 나옵니다.</p>;
  }

  return (
    <>
      <Group title="기존보험으로 커버되지 않아요" items={report.gaps} tone="gap" />
      <Group title="겹쳐요 — 두 개 들어도 더 받지 못합니다" items={report.duplicates} tone="dup" />
      <Group title="겹치지만 각각 다 받아요" items={report.fixed_ok} tone="ok" />

      {/* 확인불가는 건수가 많아 화면을 뒤덮는다. 접어두되 개수는 항상 보이게 해서
          "근거를 못 찾은 게 이만큼 있다"는 사실 자체는 숨기지 않는다.
          다만 보험사 순위처럼 진단이 주인공이 아닌 화면에서는 내린다 — 고를 때 볼 것이
          아니라서 자리만 차지한다. */}
      {showUnknown && report.unknown.length > 0 && (
        <details className="overlap-unknown overlap-group">
          <summary>
            <h3 className="overlap-group__title">
              확인불가
              <span className="overlap-group__count">{report.unknown.length}</span>
            </h3>
          </summary>
          {report.unknown.map((f) => (
            <Finding key={`${f.coverage_std_code}-${f.scope}-${f.external_kind}`} f={f} tone="unknown" />
          ))}
        </details>
      )}
    </>
  );
}
