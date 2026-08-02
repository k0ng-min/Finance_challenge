import { useState } from "react";
import type { FindingOut } from "../api";
import { FindingCard } from "./FindingCard";
import { usePager, PagerNav } from "./Pager";

interface Group {
  key: string;
  label: string;
  items: FindingOut[];
}

const PAGE_SIZE = 3;

/** 결과를 카테고리 탭으로 나눠서 한 화면에 다 몰아넣지 않는다. 탭 안의 항목도 많아지면
 * 스크롤 대신 "다음"으로 페이지를 나눠서 화면 안에 다 들어오게 한다. */
export function ResultTabs({ groups, incidentId }: { groups: Group[]; incidentId?: number }) {
  const nonEmpty = groups.filter((g) => g.items.length > 0);
  const [active, setActive] = useState(nonEmpty[0]?.key);
  const activeGroup = nonEmpty.find((g) => g.key === active) ?? nonEmpty[0];
  const { page, setPage, totalPages, pageItems } = usePager(activeGroup?.items ?? [], PAGE_SIZE);

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
      {pageItems.map((f) => (
        <FindingCard key={f.finding_id} finding={f} incidentId={incidentId} />
      ))}
      <PagerNav page={page} totalPages={totalPages} onChange={setPage} label="쪽" />
    </div>
  );
}
