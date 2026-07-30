import { useEffect, useState } from "react";
import { api, type IncidentSummaryOut } from "../api";

/** 사고 접수 이력이 여러 건이면, 지금 보고 있는 화면을 어느 사고 기준으로 볼지 고를 수 있게 한다.
 * 이력이 0~1건이면 고를 필요가 없으므로 아무것도 렌더링하지 않는다. */
export function IncidentPicker({
  userId,
  value,
  onChange,
}: {
  userId: number | null;
  value: number | null;
  onChange: (id: number) => void;
}) {
  const [incidents, setIncidents] = useState<IncidentSummaryOut[]>([]);

  useEffect(() => {
    if (!userId) return;
    api.listIncidents(userId).then(setIncidents).catch(() => {});
  }, [userId]);

  if (incidents.length <= 1) return null;

  return (
    <div className="tabs" style={{ marginBottom: 14, flexWrap: "wrap" }}>
      {incidents.map((inc) => (
        <button
          key={inc.incident_id}
          type="button"
          className={`tab${inc.incident_id === value ? " tab--active" : ""}`}
          onClick={() => onChange(inc.incident_id)}
        >
          {inc.country ?? "사고"} · {inc.occurred_at ? inc.occurred_at.slice(0, 10) : `#${inc.incident_id}`}
        </button>
      ))}
    </div>
  );
}
