import { useEffect, useState } from "react";
import { api, type ClauseOut } from "../api";
import { useApp } from "../context/AppContext";
import { ClauseCard } from "../components/ClauseCard";
import { HIGHLIGHT_COLORS } from "../colors";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { Icon3D } from "../components/Icon3D";

const ORDER = ["파랑", "초록", "노랑", "빨강", "회색"];

export function ClauseHighlight() {
  const { tripId, incidentId } = useApp();
  const [clauses, setClauses] = useState<ClauseOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeColor, setActiveColor] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    const tasks: Promise<{ findings: { clauses: ClauseOut[] }[] }>[] = [];
    if (tripId) tasks.push(api.getTrip(tripId));
    if (incidentId) tasks.push(api.getIncident(incidentId));

    Promise.all(tasks)
      .then((results) => {
        const byId = new Map<number, ClauseOut>();
        results.forEach((r) => r.findings.forEach((f) => f.clauses.forEach((c) => byId.set(c.clause_id, c))));
        setClauses([...byId.values()]);
      })
      .finally(() => setLoading(false));
  }, [tripId, incidentId]);

  if (!tripId && !incidentId) {
    return (
      <div className="page">
        <TopBar title="약관 형광펜" />
        <div className="empty-state">
          <Icon3D src="star" size={72} bg="var(--cream-deep)" rounded="34%" />
          <p className="muted">
            "내 여행 준비"에서 보장 추천을 받거나 "사고가 발생했어요"에서 사고를 분석하면, 그 근거가 된
            실제 약관 조항이 여기 색상별로 모입니다.
          </p>
        </div>
      </div>
    );
  }

  const grouped = ORDER.map((color) => ({
    color,
    label: HIGHLIGHT_COLORS[color].label,
    items: clauses.filter((c) => c.highlight_color === color),
  })).filter((g) => g.items.length > 0);
  const current = grouped.find((g) => g.color === activeColor) ?? grouped[0];

  return (
    <div className="page">
      <TopBar title="약관 형광펜" />
      <PageHero
        icon="notebook"
        iconBg="var(--cream-deep)"
        eyebrow="CLAUSE HIGHLIGHT"
        title={"근거가 되는 약관,\n색깔로 한눈에"}
        subtitle="추천·경고의 근거가 된 실제 약관 원문입니다. 요약이 아니라 원문 그대로예요."
      />
      {loading && <p className="muted">불러오는 중...</p>}

      {grouped.length > 0 && (
        <>
          <div className="tabs">
            {grouped.map((g) => (
              <button
                key={g.color}
                type="button"
                className={`tab${g.color === current?.color ? " tab--active" : ""}`}
                onClick={() => setActiveColor(g.color)}
                style={g.color === current?.color ? {} : { color: HIGHLIGHT_COLORS[g.color].border }}
              >
                {g.color} · {g.items.length}
              </button>
            ))}
          </div>
          {current?.items.map((c) => (
            <ClauseCard key={c.clause_id} clause={c} />
          ))}
        </>
      )}
    </div>
  );
}
