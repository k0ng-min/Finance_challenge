import type { OverlapFindingOut, OverlapReportOut } from "../api";

/** 진단 결과 표시. 근거 조항 원문을 그대로 붙이고, 근거가 없으면 "확인불가"라고 밝힌다. */

function Finding({ f }: { f: OverlapFindingOut }) {
  return (
    <div className="card" style={{ marginBottom: 10 }}>
      <strong>{f.coverage_std_name}</strong>
      {f.scope !== "전체" && <span className="muted"> · {f.scope}</span>}
      {f.note && <p style={{ margin: "6px 0 0", fontSize: "0.9rem" }}>{f.note}</p>}
      {f.clause_quote ? (
        <blockquote style={{ margin: "10px 0 0", padding: "8px 12px", borderLeft: "3px solid var(--accent, #888)", fontSize: "0.82rem" }}>
          {f.clause_quote}
          <div className="muted" style={{ marginTop: 4 }}>— {f.clause_article_no}</div>
        </blockquote>
      ) : (
        <p className="muted" style={{ margin: "8px 0 0", fontSize: "0.82rem" }}>
          약관 근거를 찾지 못해 확인불가입니다.
        </p>
      )}
    </div>
  );
}

export function OverlapReportView({ report }: { report: OverlapReportOut }) {
  const empty =
    report.duplicates.length === 0 && report.gaps.length === 0 &&
    report.fixed_ok.length === 0 && report.unknown.length === 0;

  if (empty) {
    return <p className="muted">진단할 내용이 없어요. 기존보험과 여행자보험을 모두 등록하면 결과가 나옵니다.</p>;
  }

  return (
    <>
      {report.gaps.length > 0 && (
        <section>
          <h3>기존보험으로 커버되지 않아요</h3>
          {report.gaps.map((f) => <Finding key={`${f.coverage_std_code}-${f.scope}-${f.external_kind}`} f={f} />)}
        </section>
      )}
      {report.duplicates.length > 0 && (
        <section>
          <h3>겹쳐요 — 두 개 들어도 더 받지 못합니다</h3>
          {report.duplicates.map((f) => <Finding key={`${f.coverage_std_code}-${f.scope}-${f.external_kind}`} f={f} />)}
        </section>
      )}
      {report.fixed_ok.length > 0 && (
        <section>
          <h3>겹치지만 각각 다 받아요</h3>
          {report.fixed_ok.map((f) => <Finding key={`${f.coverage_std_code}-${f.scope}-${f.external_kind}`} f={f} />)}
        </section>
      )}
      {report.unknown.length > 0 && (
        <section>
          <h3>확인불가</h3>
          {report.unknown.map((f) => <Finding key={`${f.coverage_std_code}-${f.scope}-${f.external_kind}`} f={f} />)}
        </section>
      )}
    </>
  );
}
