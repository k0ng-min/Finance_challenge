import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api, type KbStatsOut } from "../api";

/**
 * 약관 KB의 규모와 근거 검증 통과율을 있는 그대로 보여준다.
 *
 * 이 프로젝트의 원칙은 "근거 없는 결과를 내지 않는다"인데, 그게 지켜지고 있다는 사실은
 * 지금까지 README에만 있었다. 화면에서 확인할 길이 없으면 원칙은 주장에 머문다.
 *
 * 숫자는 전부 서버가 DB에서 그때그때 세어 내려준 값이다 — 여기에 상수를 적어두지
 * 않는다. 보험사가 늘거나 조항이 다시 적재되면 적어둔 숫자는 조용히 낡는데(실제로
 * README의 담보 수와 서류 연결률이 그렇게 낡아 있었다), 근거를 보여주겠다는 화면이
 * 틀린 숫자를 보여주면 없느니만 못하다.
 *
 * 통과율이 100%가 아닌 항목도 그대로 내보인다. 못 채운 자리를 가리면 채운 자리의
 * 숫자까지 믿을 수 없게 된다.
 */
export function EvidenceStats() {
  const [stats, setStats] = useState<KbStatsOut | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.getKbStats()
      .then((s) => !cancelled && setStats(s))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, []);

  // 이 화면의 본래 기능(조항 찾기)을 막지 않는다 — 못 불러오면 이 구획만 조용히 빠진다.
  if (failed || !stats) return null;

  return (
    <section className="evidence">
      <p className="section-label">근거 검증 현황</p>
      <p className="evidence__lead">
        {stats.insurer_count}개 보험사 약관에서 조항 {stats.clause_count.toLocaleString()}건을 읽어
        두었고, 사고유형 {stats.incident_type_l1_count}개 대분류와{" "}
        {stats.incident_type_l2_count}개 세부유형에 {stats.incident_map_count.toLocaleString()}번
        이어 붙였어요. 아래 숫자는 지금 이 서버의 자료를 그 자리에서 센 것이에요.
      </p>

      <div className="evidence__checks">
        {stats.checks.map((c, i) => (
          <motion.div
            key={c.code}
            className="evidence-check"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.06 * i, duration: 0.3 }}
          >
            <div className="evidence-check__head">
              <strong>{c.label}</strong>
              <span className="evidence-check__rate">{c.rate}%</span>
            </div>
            <div className="evidence-check__bar">
              <motion.span
                className={`evidence-check__bar-fill${c.rate >= 100 ? " evidence-check__bar-fill--full" : ""}`}
                initial={{ width: 0 }}
                animate={{ width: `${c.rate}%` }}
                transition={{ delay: 0.06 * i + 0.1, duration: 0.7, ease: "easeOut" }}
              />
            </div>
            <p className="evidence-check__count">
              {c.passed.toLocaleString()} / {c.total.toLocaleString()}건
            </p>
            <p className="evidence-check__desc">{c.description}</p>
          </motion.div>
        ))}
      </div>

      <details className="evidence__detail">
        <summary>보험사별로 어느 판본을 읽었는지 보기</summary>
        <div className="evidence__table-wrap">
          <table className="evidence__table">
            <thead>
              <tr>
                <th>보험사</th>
                <th>조항</th>
                <th>담보</th>
                <th>수치조건</th>
                <th>읽은 약관 판본</th>
              </tr>
            </thead>
            <tbody>
              {stats.insurers.map((i) => (
                <tr key={i.insurer_code}>
                  <td>{i.insurer_name}</td>
                  <td className="evidence__num">{i.clause_count}</td>
                  <td className="evidence__num">{i.coverage_count}</td>
                  <td className="evidence__num">{i.clause_term_count}</td>
                  <td>
                    <span className="evidence__version">{i.version_label ?? "—"}</span>
                    {i.effective_date && (
                      <span className="evidence__date">{i.effective_date} 시행</span>
                    )}
                    {/* 원본 PDF의 SHA-256 앞자리. 같은 파일을 읽었는지 대조할 수 있게 남긴다 */}
                    {i.file_hash_prefix && (
                      <span className="evidence__hash">SHA-256 {i.file_hash_prefix}…</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
