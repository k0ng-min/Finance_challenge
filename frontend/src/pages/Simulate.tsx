import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api, type SimulationOut, type SimulatedScenarioOut, type SimulationResultOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { Icon3D } from "../components/Icon3D";
import { LoadingState } from "../components/LoadingState";

const VERDICT_CLASS: Record<string, string> = {
  직접: "sim-verdict--direct",
  조건부: "sim-verdict--conditional",
  면책: "sim-verdict--waived",
  확인불가: "sim-verdict--unknown",
};

// 판정 네 가지가 무슨 뜻인지 화면에 한 번은 적어둔다 — "면책"·"확인불가"는 일상어가
// 아니라서, 뜻을 모르면 색만 보고 나쁜 쪽으로 읽게 된다. 특히 확인불가는 "안 된다"가
// 아니라 "약관에서 근거를 못 찾았다"는 뜻이라 반드시 구분해서 적는다.
const VERDICT_LEGEND: { verdict: string; meaning: string }[] = [
  { verdict: "직접", meaning: "이 사고를 바로 보장하는 조항이 있어요" },
  { verdict: "조건부", meaning: "추가 요건을 채워야 걸려요" },
  { verdict: "면책", meaning: "보상하지 않는다고 적힌 조항이 있어요" },
  { verdict: "확인불가", meaning: "약관에서 근거를 못 찾았어요" },
];

/** 시나리오 하나의 판정 분포. 표를 다 읽기 전에 "대충 어떤 그림인지"를 먼저 보여준다. */
function verdictCounts(results: SimulationResultOut[]) {
  const order = ["직접", "조건부", "면책", "확인불가"];
  const counts = new Map<string, number>();
  for (const r of results) counts.set(r.verdict, (counts.get(r.verdict) ?? 0) + 1);
  return order
    .filter((v) => counts.has(v))
    .map((v) => ({ verdict: v, count: counts.get(v) as number }));
}

/**
 * 「사고 시뮬레이션」 — 가입 전에 "이 여행에서 이런 일이 나면 보험사별로 어떻게 갈리는지".
 *
 * 지금까지 보험사 비교는 전부 표의 숫자(보험료·지급한도)였다. 사용자는 숫자 차이를
 * 체감하지 못한다. 여기서는 기존 청구 판정 엔진을 그대로 태워서, 같은 사고에 대해
 * 보험사별 결론이 조항 원문과 함께 갈리는 것을 보여준다.
 *
 * 시나리오는 L1(대분류)로 뜨고, 세분화(L2)는 사용자가 직접 고른다 — 여기엔 자유서술이
 * 없어서 L2를 추론할 근거가 없기 때문이다(추측하지 않는다).
 */
export function Simulate() {
  const { tripId } = useApp();
  const navigate = useNavigate();
  const [data, setData] = useState<SimulationOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 세분화 칩을 누른 "그 카드만" 다시 도는 동안 표시할 로딩 — 카드별로 따로
  // 갖는다. 예전에는 화면 전체가 하나의 loading을 공유해서, 카드 하나의 칩을
  // 눌러도 나머지 3개 카드까지 6개사분(4×6) 전부 다시 조회되고 그동안 모든
  // 카드의 칩이 같이 잠겼다 — 이제 바뀐 카드 하나만 다시 조회하고 잠근다.
  const [busyCodes, setBusyCodes] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!tripId) return;
    setLoading(true);
    setError(null);
    api
      .getTripSimulation(tripId)
      .then(setData)
      .catch(() => setError("시뮬레이션을 불러오지 못했어요. 잠시 뒤 다시 시도해 주세요."))
      .finally(() => setLoading(false));
  }, [tripId]);

  const chooseSubType = useCallback(
    (code: string, typeId: number | null) => {
      if (!tripId) return;
      setBusyCodes((prev) => new Set(prev).add(code));
      setError(null);
      api
        .getTripSimulationScenario(tripId, code, typeId)
        .then((scenario) => {
          setData((prev) =>
            prev
              ? { ...prev, scenarios: prev.scenarios.map((s) => (s.code === code ? scenario : s)) }
              : prev,
          );
        })
        .catch(() => setError("시나리오를 다시 계산하지 못했어요. 잠시 뒤 다시 시도해 주세요."))
        .finally(() => {
          setBusyCodes((prev) => {
            const next = new Set(prev);
            next.delete(code);
            return next;
          });
        });
    },
    [tripId],
  );

  if (!tripId) {
    return (
      <div className="page">
        <TopBar title="사고 시뮬레이션" />
        <PageHero
          icon="target"
          eyebrow="SIMULATION"
          title={"이런 일이 나면\n어떻게 될까요?"}
          subtitle="여행 정보를 등록하면 그 여행에서 실제로 일어날 만한 사고를 보험사별로 미리 돌려봐요."
        />
        <div className="empty-state">
          <Icon3D src="suitcase" size={56} />
          <p className="muted">먼저 여행을 등록해 주세요.</p>
          <button type="button" className="btn btn--primary" onClick={() => navigate("/trip")}>
            여행 준비하러 가기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <TopBar title="사고 시뮬레이션" />
      <PageHero
        icon="target"
        eyebrow="SIMULATION"
        title={"이런 일이 나면\n어떻게 될까요?"}
        subtitle="같은 사고에 6개사 약관이 어떻게 갈리는지, 조항 원문과 함께 미리 봐요."
      />

      {loading && !data && <LoadingState label="약관을 대조하고 있어요..." />}
      {error && <div className="error-box">{error}</div>}

      {data && (
        <>
          <div className="sim-context">
            <Icon3D src="suitcase" size={26} />
            <span>
              <b>{data.destination}</b> · {data.start_date} ~ {data.end_date}
            </span>
          </div>

          <div className="card sim-legend">
            <span className="section-label">판정이 뜻하는 것</span>
            <ul>
              {VERDICT_LEGEND.map((l) => (
                <li key={l.verdict}>
                  <span className={`sim-verdict ${VERDICT_CLASS[l.verdict]}`}>{l.verdict}</span>
                  <span className="sim-legend__meaning">{l.meaning}</span>
                </li>
              ))}
            </ul>
          </div>

          {data.scenarios.length === 0 && (
            <div className="empty-state">
              <Icon3D src="target" size={56} />
              <p className="muted">이 여행에 맞는 시나리오가 아직 없어요.</p>
            </div>
          )}

          {data.scenarios.map((s, i) => (
            <ScenarioCard
              key={s.code}
              scenario={s}
              index={i}
              onChooseSubType={(typeId) => chooseSubType(s.code, typeId)}
              busy={busyCodes.has(s.code)}
            />
          ))}

          <p className="sim-disclaimer">{data.disclaimer}</p>
        </>
      )}
    </div>
  );
}

function ScenarioCard({
  scenario, index, onChooseSubType, busy,
}: {
  scenario: SimulatedScenarioOut;
  index: number;
  onChooseSubType: (typeId: number | null) => void;
  busy: boolean;
}) {
  const isL1 = scenario.selected_type_id === scenario.l1_type_id;
  const counts = verdictCounts(scenario.results);
  const total = scenario.results.length || 1;
  return (
    <motion.div
      className="card sim-card"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 4) * 0.05 }}
    >
      <div className="sim-card__head">
        <span className="sim-card__num">{index + 1}</span>
        <strong className="sim-card__title">{scenario.title}</strong>
        <span className="sim-card__type">{scenario.incident_type_name}</span>
      </div>
      <p className="sim-card__narrative">{scenario.narrative}</p>

      {/* 표를 다 읽기 전에 "6개사가 대체로 어느 쪽인지"를 한 눈에 준다. */}
      <div className="sim-summary">
        <div className="sim-summary__bar" role="img"
             aria-label={counts.map((c) => `${c.verdict} ${c.count}개사`).join(", ")}>
          {counts.map((c) => (
            <span
              key={c.verdict}
              className={`sim-summary__seg ${VERDICT_CLASS[c.verdict]}`}
              style={{ width: `${(c.count / total) * 100}%` }}
            />
          ))}
        </div>
        <div className="sim-summary__counts">
          {counts.map((c) => (
            <span key={c.verdict}>
              <i className={`sim-summary__dot ${VERDICT_CLASS[c.verdict]}`} />
              {c.verdict} {c.count}
            </span>
          ))}
        </div>
      </div>

      {scenario.sub_types.length > 0 && (
        <div className="sim-subtypes">
          <span className="sim-subtypes__label">더 자세히 고르면 결과가 달라져요</span>
          <div className="calc-chips">
            <button
              type="button"
              disabled={busy}
              className={`premium-chip${isL1 ? " premium-chip--on" : ""}`}
              onClick={() => onChooseSubType(null)}
            >
              전체
            </button>
            {scenario.sub_types.map((t) => (
              <button
                key={t.type_id}
                type="button"
                disabled={busy}
                className={`premium-chip${scenario.selected_type_id === t.type_id ? " premium-chip--on" : ""}`}
                onClick={() => onChooseSubType(t.type_id)}
              >
                {t.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <ul className="sim-results">
        {scenario.results.map((r) => (
          <ResultRow key={r.insurer_name} result={r} />
        ))}
      </ul>
    </motion.div>
  );
}

function ResultRow({ result }: { result: SimulationResultOut }) {
  const [open, setOpen] = useState(false);
  const hasQuote = Boolean(result.clause_quote);
  return (
    <li className="sim-result">
      <button
        type="button"
        className="sim-result__head"
        onClick={() => hasQuote && setOpen((v) => !v)}
        aria-expanded={open}
        disabled={!hasQuote}
      >
        <span className="sim-result__insurer">{result.insurer_name}</span>
        <span className={`sim-verdict ${VERDICT_CLASS[result.verdict] ?? ""}`}>
          {result.verdict}
        </span>
        {hasQuote && <span className="sim-result__chevron" aria-hidden>{open ? "⌃" : "⌄"}</span>}
      </button>

      {result.coverage_name && <p className="sim-result__coverage">{result.coverage_name}</p>}
      {!hasQuote && (
        <p className="sim-result__coverage sim-result__coverage--muted">
          이 사고유형에 매핑된 조항이 없어 판단할 근거가 없어요.
        </p>
      )}

      {open && result.clause_quote && (
        <blockquote className="sim-result__quote">
          <span className="sim-result__source">{result.clause_article_no}</span>
          {result.clause_quote}
        </blockquote>
      )}
    </li>
  );
}
