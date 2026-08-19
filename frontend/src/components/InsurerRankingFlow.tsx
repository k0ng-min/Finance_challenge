import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api, type RecommendationOut, type InsurerTierOut, type InsurerRankOut, type OverlapReportOut } from "../api";
import { useApp } from "../context/AppContext";
import { PageHero } from "./PageHero";
import { InsurerIncidentClauses } from "./InsurerIncidentClauses";
import { StandardTermsComparison } from "./StandardTermsComparison";
import { Icon3D } from "./Icon3D";
import { LoadingScreen } from "./LoadingScreen";
import { OverlapReportView } from "./OverlapReport";
import { TravelAlertBadge } from "./TravelAlertBadge";
import { NextStepCard } from "./NextStepCard";
import { PlanCoverageBoard } from "./PlanCoverageBoard";
import { Modal } from "./Modal";

type Phase = "tier" | "ranking" | "detail";

export function InsurerRankingFlow({
  result, initialTier, hasExternalPolicies, externalPoliciesReady,
}: {
  result: RecommendationOut;
  /** 여행 준비 스텝에서 이미 보장유형을 골라온 경우 — 여기서 다시 고르지 않고 바로 순위로 간다. */
  initialTier?: string | null;
  /** 이번 여행 준비에서 기존보험을 하나라도 골랐는지. 안 골랐으면 진단을 아예 조회하지
   * 않는다(빈 결과만 오므로). */
  hasExternalPolicies?: boolean;
  /** 기존보험 저장(linkExternalPolicies)의 완료를 기다리는 Promise. 저장이 fire-and-forget이라
   * 진단을 저장 직후 곧바로 조회하면 경합이 날 수 있어, 조회 전에 이 Promise를 먼저 기다린다. */
  externalPoliciesReady?: Promise<unknown>;
}) {
  const navigate = useNavigate();
  const { userId, isLoggedIn, age, sex } = useApp();
  // initialTier가 있어도 phase는 일단 "tier"로 시작한다 — fetchRanking이 끝나면 스스로
  // "ranking"으로 넘어가므로, 그전까지는 기존 "tier" 단계의 로딩 화면이 자연스럽게 보인다.
  const [phase, setPhase] = useState<Phase>("tier");
  const [tiers, setTiers] = useState<InsurerTierOut[]>([]);
  const [tier, setTier] = useState<string | null>(initialTier ?? null);
  const [ranking, setRanking] = useState<InsurerRankOut[]>([]);
  const [loading, setLoading] = useState(!!initialTier);
  const [selected, setSelected] = useState<InsurerRankOut | null>(null);
  const [registering, setRegistering] = useState(false);
  const [registered, setRegistered] = useState(false);
  const [overlap, setOverlap] = useState<OverlapReportOut | null>(null);
  const [detailTab, setDetailTab] = useState<"incidents" | "standard">("incidents");
  // 순위 목록에서 보험사 이름을 누르면(고르는 것과 별개로) 등급·담보한도를 팝업으로 미리 볼 수 있다.
  const [previewCode, setPreviewCode] = useState<string | null>(null);
  const [previewPlanByInsurer, setPreviewPlanByInsurer] = useState<Record<string, string>>({});
  // 상세 화면(선택한 보험사 확정 단계)에서 등급을 고를 때도 표는 기본으로 숨겨 두고, 눌러야 뜬다.
  const [showPlanModal, setShowPlanModal] = useState(false);
  // 이 보험사의 어느 등급(플랜)을 염두에 두고 있는지 — 등록할 때 그대로 같이 저장한다.
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const normalizedSex = sex === "F" ? "F" : sex === "M" ? "M" : null;

  useEffect(() => {
    api.getInsurerTiers().then(setTiers).catch(() => {});
  }, []);

  async function fetchRanking(tierCode: string) {
    setLoading(true);
    try {
      const rp = result.risk_profile;
      const res = await api.getInsurerRanking(tierCode, {
        destination: typeof rp.destination === "string" ? rp.destination : undefined,
        risk_level: typeof rp.risk_level === "string" ? rp.risk_level : undefined,
        trip_days: typeof rp.trip_days === "number" ? rp.trip_days : undefined,
        activities: Array.isArray(rp.activities) ? (rp.activities as string[]) : undefined,
        coverage_priority: Array.isArray(rp.coverage_priority) ? (rp.coverage_priority as string[]) : undefined,
      }, { age, sex });
      setRanking(res.ranking);
      setPhase("ranking");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (initialTier) fetchRanking(initialTier);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialTier]);

  async function pickTier(tierCode: string) {
    setTier(tierCode);
    await fetchRanking(tierCode);
  }

  function pickInsurer(item: InsurerRankOut) {
    setSelected(item);
    setRegistered(false);
    setSelectedPlan(null);
    setPhase("detail");
  }

  async function registerToMyPolicies() {
    if (!selected || !userId) return;
    if (!isLoggedIn) {
      navigate("/account");
      return;
    }
    const tripDays = typeof result.risk_profile.trip_days === "number" ? result.risk_profile.trip_days : 7;
    const startDate = typeof result.risk_profile.start_date === "string" ? result.risk_profile.start_date : undefined;
    const today = new Date();
    const start = startDate ? new Date(startDate) : today;
    const end = new Date(start);
    end.setDate(end.getDate() + tripDays);
    const iso = (d: Date) => d.toISOString().slice(0, 10);

    setRegistering(true);
    try {
      await api.registerPolicy(userId, {
        // 이 보험을 지금 준비한 여행에 묶는다 — 나중에 사고를 접수할 때 여행만 고르면
        // 보험이 자동으로 따라오게 하는 연결 고리다.
        trip_id: result.trip_id,
        insurer_name_raw: selected.insurer_name,
        product_name_raw: null,
        plan_name: selectedPlan,
        period_start: iso(start),
        period_end: iso(end),
      });
      setRegistered(true);
    } finally {
      setRegistering(false);
    }
  }

  // 이 여행에 실제로 보험을 등록한 뒤에만 진단을 조회한다 — coverage-overlap API는
  // trip.user_policy_id(방금 등록한 보험)로 검토 대상 담보를 정하는데, 등록 전에는 그게
  // 비어 있어 어차피 빈 결과만 온다. 기존보험을 하나도 안 골랐으면 호출 자체를 건너뛴다.
  // 기존보험 저장이 fire-and-forget이라 저장 완료를 기다렸다가(externalPoliciesReady) 조회한다.
  useEffect(() => {
    if (!registered || !hasExternalPolicies || !userId) return;
    let cancelled = false;
    Promise.resolve(externalPoliciesReady)
      .then(() => api.getCoverageOverlap(userId, { tripId: result.trip_id }))
      .then((r) => { if (!cancelled) setOverlap(r); })
      .catch(() => { if (!cancelled) setOverlap(null); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [registered, hasExternalPolicies, userId]);

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
          💳 여행기간·담보구성 등 실제 가입조건 보험료는 보험다모아에서 확인할 수 있어요 →
        </a>
        <p className="rank-premium-note">
          카드의 금액은 각 보험사 다이렉트 사이트에서 직접 조회한 {ranking[0]?.premium_period_days ?? 1}일 기준
          실제 가격이며, 선택한 여행일수로 환산한 견적이 아닙니다.
        </p>
        <div className="rank-list">
          {ranking.map((r, i) => (
            <motion.div
              key={r.insurer_code}
              role="button"
              tabIndex={0}
              className="rank-card"
              onClick={() => pickInsurer(r)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") pickInsurer(r); }}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="rank-card__head">
                <span className={`rank-badge${r.rank === 1 ? " rank-badge--first" : ""}`}>{r.rank}</span>
                <div className="rank-card__name">
                  <button
                    type="button"
                    className="rank-card__name-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      setPreviewCode(r.insurer_code);
                    }}
                  >
                    {r.insurer_name}
                  </button>
                  <span className="rank-card__basis">
                    {r.comparison_basis}
                    {r.plan_coverage_item_count != null && ` · 담보한도 ${r.plan_coverage_item_count}건 보기`}
                  </span>
                </div>
                {/* 이 금액은 여행일수로 환산한 견적이 아니라 비교공시 원문값이다. 숫자만 크게
                    두면 "내가 낼 돈"으로 읽히므로 기준 기간을 바로 아래에 붙여 둔다. */}
                <span className="rank-card__price">
                  {r.published_premium != null ? (
                    <>
                      <span className="rank-card__price-main">
                        <b>{r.published_premium.toLocaleString()}</b>
                        <i>원</i>
                      </span>
                      <small>{r.premium_period_days ?? 1}일 기준</small>
                    </>
                  ) : (
                    // 왜 금액이 없는지는 서버가 문구로 알려준다(가입연령 밖 등). 조용히 빼지 않는다.
                    <em>{r.premium_note ?? "가격 정보 없음"}</em>
                  )}
                </span>
                <span className="rank-card__arrow">›</span>
              </div>

              {/* 네 축 모두 "채워질수록 유리"하게 계산된 값이라, 같은 방향의 게이지로 나란히 읽힌다. */}
              <div className="rank-gauges">
                {r.dimensions.map((dimension) => (
                  <div
                    className={`rank-gauge rank-gauge--${dimension.code}`}
                    key={dimension.code}
                    title={dimension.summary}
                  >
                    <span className="rank-gauge__label">{dimension.label}</span>
                    {dimension.level > 0 ? (
                      <span
                        className="rank-gauge__bar"
                        role="img"
                        aria-label={`${dimension.label}: ${dimension.status} (5단계 중 ${dimension.level}단계)`}
                      >
                        {Array.from({ length: 5 }, (_, index) => (
                          <i key={index} className={index < dimension.level ? "is-on" : ""} />
                        ))}
                      </span>
                    ) : (
                      <span className="rank-gauge__none">아직 근거가 없어요</span>
                    )}
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        {ranking.map((r) => (
          <Modal
            key={r.insurer_code}
            open={previewCode === r.insurer_code}
            onClose={() => setPreviewCode(null)}
            title={`${r.insurer_name} 등급·담보한도`}
          >
            <PlanCoverageBoard
              insurerCode={r.insurer_code}
              age={age}
              sex={normalizedSex}
              selectedPlan={previewPlanByInsurer[r.insurer_code] ?? null}
              onSelectPlan={(plan) =>
                setPreviewPlanByInsurer((prev) => ({ ...prev, [r.insurer_code]: plan }))
              }
            />
          </Modal>
        ))}

        {/* 순위는 "어느 보험사가 나은가"까지만 답한다. 그 숫자가 실제 상황에서 어떻게
            갈리는지는 시뮬레이션이 조항 원문으로 보여주므로, 여행 준비의 마지막 자리에서
            바로 이어지게 둔다. */}
        <NextStepCard
          to="/simulate"
          icon="target"
          label="다음 단계"
          title="이 여행에서 사고가 나면?"
        />
      </div>
    );
  }

  // phase === "detail"
  const selectedTypeCodes = Array.isArray(result.risk_profile.coverage_priority)
    ? (result.risk_profile.coverage_priority as string[])
    : [];

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
      {selected && (
        <button
          type="button"
          className="card rank-plan-summary"
          onClick={() => setShowPlanModal(true)}
        >
          <span className="rank-plan-summary__label">어느 등급으로 가입하시겠어요?</span>
          <span className="rank-plan-summary__value">
            {selectedPlan ? `${selectedPlan} 선택됨 · 등급·담보한도 보기` : "등급·담보한도 보기 ›"}
          </span>
        </button>
      )}
      {selected && (
        <Modal
          open={showPlanModal}
          onClose={() => setShowPlanModal(false)}
          title={`${selected.insurer_name} 등급·담보한도`}
        >
          <PlanCoverageBoard
            insurerCode={selected.insurer_code}
            age={age}
            sex={normalizedSex}
            selectedPlan={selectedPlan}
            onSelectPlan={setSelectedPlan}
          />
        </Modal>
      )}
      <div className="detail-actions-row" style={{ display: "flex", gap: 10, marginBottom: 14 }}>
        <button type="button" className="btn-secondary" style={{ flex: 1 }} onClick={() => setPhase("ranking")}>
          ← 순위로 돌아가기
        </button>
        {!registered && (
          <button type="button" className="btn-primary" style={{ flex: 1 }} onClick={registerToMyPolicies} disabled={registering}>
            {registering ? "등록 중..." : isLoggedIn ? `${selectedPlan ? `${selectedPlan}으로 ` : ""}내 보험으로 등록하기` : "로그인하고 등록하기"}
          </button>
        )}
      </div>
      <div className="card risk-profile" style={{ marginBottom: 16 }}>
        <div>목적지: <strong>{String(result.risk_profile.destination ?? "-")}</strong> · {String(result.risk_profile.companion_type ?? "-")}</div>
        <div>
          여행 기간: <strong>{String(result.risk_profile.start_date ?? "-")} ~ {String(result.risk_profile.end_date ?? "-")}</strong>
          {" "}({String(result.risk_profile.trip_days ?? "-")}일)
        </div>
        <div>위험도: <strong>{String(result.risk_profile.risk_level ?? "-")}</strong></div>
        {/* 여행경보는 외교부 자료다. 위험도(활동·기간으로 계산한 값)와 출처가 다르므로
            같은 줄에 섞지 않고, 어디서 온 값인지 밝혀서 따로 보여준다. */}
        <TravelAlertBadge alert={result.risk_profile.travel_alert} />
        {Array.isArray(result.risk_profile.risky_activity_detected) &&
          (result.risk_profile.risky_activity_detected as string[]).length > 0 && (
            <div>감지된 위험활동: {(result.risk_profile.risky_activity_detected as string[]).join(", ")}</div>
          )}
      </div>
      {selected && (
        <>
          <div className="tabs" style={{ marginBottom: 14 }}>
            <button
              type="button"
              className={`tab${detailTab === "incidents" ? " tab--active" : ""}`}
              onClick={() => setDetailTab("incidents")}
            >
              사고유형별 조항
            </button>
            <button
              type="button"
              className={`tab${detailTab === "standard" ? " tab--active" : ""}`}
              onClick={() => setDetailTab("standard")}
            >
              표준약관과 비교
            </button>
          </div>
          {detailTab === "incidents" ? (
            <InsurerIncidentClauses insurerCode={selected.insurer_code} typeCodes={selectedTypeCodes} />
          ) : (
            <StandardTermsComparison insurerCode={selected.insurer_code} />
          )}
        </>
      )}

      {registered && (
        <div className="card" style={{ marginTop: 16 }}>
          <p style={{ marginTop: 0, fontWeight: 700 }}>✓ 내 보험에 등록했어요</p>
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            {selectedPlan ? `${selectedPlan} 등급으로, ` : ""}
            여행 기간({String(result.risk_profile.trip_days ?? "-")}일) 기준으로 자동 등록됐어요.
          </p>
          <button type="button" className="btn-secondary" style={{ width: "100%" }} onClick={() => navigate("/policies")}>
            내 보험 보관함에서 확인하기
          </button>
        </div>
      )}
      {registered && overlap && (
        <section style={{ marginTop: 16 }}>
          <h2 style={{ fontSize: "1.05rem" }}>기존보험과 겹치거나 비는 담보</h2>
          <OverlapReportView report={overlap} />
        </section>
      )}
    </div>
  );
}
