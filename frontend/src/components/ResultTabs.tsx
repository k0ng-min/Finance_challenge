import { useState } from "react";
import type { FindingOut } from "../api";
import { FindingCard } from "./FindingCard";

interface Group {
  key: string;
  label: string;
  items: FindingOut[];
}

/** 결과를 카테고리 탭으로 나눠서 한 화면에 다 몰아넣지 않는다. */
export function ResultTabs({ groups, incidentId }: { groups: Group[]; incidentId?: number }) {
  const nonEmpty = groups.filter((g) => g.items.length > 0);
  const [active, setActive] = useState(nonEmpty[0]?.key);
  const activeGroup = nonEmpty.find((g) => g.key === active) ?? nonEmpty[0];

  if (!activeGroup) return null;

  return (
    <div>
      <div className="tabs">
        {nonEmpty.map((g) => (
          <button
            key={g.key}
            type="button"
            className={`tab${g.key === activeGroup.key ? " tab--active" : ""}`}
            onClick={() => setActive(g.key)}
          >
            {g.label} {g.items.length}
          </button>
        ))}
      </div>
      {activeGroup.items.map((f) => (
        <FindingCard key={f.finding_id} finding={f} incidentId={incidentId} />
      ))}
    </div>
  );
}
