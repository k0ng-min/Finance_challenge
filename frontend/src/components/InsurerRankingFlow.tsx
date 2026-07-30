import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api, type RecommendationOut, type InsurerTierOut, type InsurerRankOut } from "../api";
import { PageHero } from "./PageHero";
import { ResultTabs } from "./ResultTabs";
import { NextStepCard } from "./NextStepCard";
import { Icon3D } from "./Icon3D";
import { LoadingScreen } from "./LoadingScreen";

type Phase = "tier" | "ranking" | "detail";

export function InsurerRankingFlow({ result }: { result: RecommendationOut }) {
  const [phase, setPhase] = useState<Phase>("tier");
  const [tiers, setTiers] = useState<InsurerTierOut[]>([]);
  const [tier, setTier] = useState<string | null>(null);
  const [ranking, setRanking] = useState<InsurerRankOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<InsurerRankOut | null>(null);

  useEffect(() => {
    api.getInsurerTiers().then(setTiers).catch(() => {});
  }, []);

  async function pickTier(tierCode: string) {
    setTier(tierCode);
    setLoading(true);
    try {
      const rp = result.risk_profile;
      const res = await api.getInsurerRanking(tierCode, {
        destination: typeof rp.destination === "string" ? rp.destination : undefined,
        risk_level: typeof rp.risk_level === "string" ? rp.risk_level : undefined,
        trip_days: typeof rp.trip_days === "number" ? rp.trip_days : undefined,
        activities: Array.isArray(rp.activities) ? (rp.activities as string[]) : undefined,
        coverage_priority: Array.isArray(rp.coverage_priority) ? (rp.coverage_priority as string[]) : undefined,
      });
      setRanking(res.ranking);
      setPhase("ranking");
    } finally {
      setLoading(false);
    }
  }

  function pickInsurer(item: InsurerRankOut) {
    setSelected(item);
    setPhase("detail");
  }

  if (phase === "tier") {
    if (loading) {
      return (
        <div className="result-section">
          <LoadingScreen
            icon="target"
            title="딱 맞는 보험사를 찾고 있어요"
            messages={[
              "6개 보험사의 실제 약관을 대조하고 있어요",
              "선택하신 기준에 맞춰 우선순위를 매기고 있어요",
              "근거가 되는 조항을 정리하고 있어요",
            ]}
          />
        </div>
      );
    }
    return (
      <div className="result-section">
        <PageHero
          icon="target"
          eyebrow="보장 유형 선택"
          title={"어떤 기준으로\n비교해 드릴까요?"}
          subtitle="선택한 기준에 따라 6개 보험사의 실제 약관 근거를 비교해 순위를 매겨드려요."
        />
        <div className="tier-list">
          {tiers.map((t, i) => (
            <motion.button
              key={t.tier_code}
              type="button"
              className="tier-card"
              onClick={() => pickTier(t.tier_code)}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              whileTap={{ scale: 0.98 }}
              disabled={loading}
            >
              <div className="tier-card__text">
                <strong>{t.label}</strong>
                <span>{t.description}</span>
              </div>
              <span className="tier-card__arrow">›</span>
            </motion.button>
          ))}
        </div>
      </div>
    );
  }

  if (phase === "ranking") {
    return (
      <div className="result-section">
        <PageHero
          icon="chart"
          eyebrow={`${tier} 기준`}
          title={"보험사 순위,\n이렇게 나왔어요"}
          subtitle="근거가 된 약관 조항 항목을 함께 표시했어요. 눌러서 담보 추천 결과를 확인하세요."
        />
        <button type="button" className="btn-secondary" style={{ marginBottom: 10 }} onClick={() => setPhase("tier")}>
          ← 기준 다시 선택
        </button>
        <a
          className="price-link"
          href="https://www.e-insmarket.or.kr/m/tripIns/tripInsList.knia?prdtSmlClsCd=H001"
          target="_blank"
          rel="noreferrer"
        >
          💳 실제 보험료가 궁금하신가요? 보험다모아(공식 보험 비교 사이트)에서 여행 일수·목적지 기준
          실시간 견적을 바로 확인할 수 있어요 →
        </a>
        <div className="rank-list">
          {ranking.map((r, i) => (
            <motion.button
              key={r.insurer_code}
              type="button"
              className="rank-card"
              onClick={() => pickInsurer(r)}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              whileTap={{ scale: 0.98 }}
            >
              <span className={`rank-badge${r.rank <= 3 ? " rank-badge--top" : ""}`}>{r.rank}</span>
              <div className="rank-card__text">
                <div className="rank-card__toprow">
                  <strong>{r.insurer_name}</strong>
                  <span className="rank-card__score">적합도 {r.score}점</span>
                </div>
                {r.reasons[0] && <p className="rank-card__reason">{r.reasons[0]}</p>}
                {r.tags.length > 0 && (
                  <div className="rank-card__tags">
                    {r.tags.map((t) => (
                      <span className="rank-tag" key={t}>{t}</span>
                    ))}
                  </div>
                )}
              </div>
              <span className="rank-card__arrow">›</span>
            </motion.button>
          ))}
        </div>
      </div>
    );
  }

  // phase === "detail"
  const insurerFindings = result.findings.filter(
    (f) => f.insurer_code === selected?.insurer_code || f.insurer_code === null
  );
  const groups = [
    { key: "추천담보", label: "추천 담보", items: insurerFindings.filter((f) => f.finding_type === "추천담보") },
    { key: "제한조건", label: "제한조건", items: insurerFindings.filter((f) => f.finding_type === "제한조건") },
    { key: "보장공백", label: "보장 공백", items: insurerFindings.filter((f) => f.finding_type === "보장공백") },
  ];

  return (
    <div className="result-section">
      <div className="hero" style={{ marginBottom: 16 }}>
        <div className="hero__blob hero__blob--a" />
        <div className="hero__blob hero__blob--b" />
        <div className="hero__text">
          <span className="hero__eyebrow">{tier} · {selected?.rank}위</span>
          <h1 className="hero__title">{selected?.insurer_name}</h1>
          <p className="hero__subtitle">이 보험사 기준으로 추천 담보와 근거를 정리했어요.</p>
        </div>
        <Icon3D src="shield" size={72} className="hero__icon" />
      </div>
      {selected?.official_url && (
        <a className="price-link" href={selected.official_url} target="_blank" rel="noreferrer">
          🔗 {selected.insurer_name} 공식 홈페이지에서 바로 가입 상담받기 →
        </a>
      )}
      <button type="button" className="btn-secondary" style={{ marginBottom: 14 }} onClick={() => setPhase("ranking")}>
        ← 순위로 돌아가기
      </button>
      <div className="card risk-profile" style={{ marginBottom: 16 }}>
        <div>목적지: <strong>{String(result.risk_profile.destination ?? "-")}</strong> · {String(result.risk_profile.companion_type ?? "-")}</div>
        <div>
          여행 기간: <strong>{String(result.risk_profile.start_date ?? "-")} ~ {String(result.risk_profile.end_date ?? "-")}</strong>
          {" "}({String(result.risk_profile.trip_days ?? "-")}일)
        </div>
        <div>위험도: <strong>{String(result.risk_profile.risk_level ?? "-")}</strong></div>
        {Array.isArray(result.risk_profile.risky_activity_detected) &&
          (result.risk_profile.risky_activity_detected as string[]).length > 0 && (
            <div>감지된 위험활동: {(result.risk_profile.risky_activity_detected as string[]).join(", ")}</div>
          )}
      </div>
      <ResultTabs groups={groups} />
      <NextStepCard
        to={`/policies?mode=add&insurer=${encodeURIComponent(selected?.insurer_code ?? "")}`}
        icon="umbrella"
        label="다음 단계"
        title={`${selected?.insurer_name} 보험, 바로 등록하기`}
      />
    </div>
  );
}
