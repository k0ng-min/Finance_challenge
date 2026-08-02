/** 서류체크·실수방지·약관형광펜처럼 "지금 보고 있는 게 어느 사고 건인지" 헷갈릴 수 있는
 * 화면에서, 그 사고가 어느 여행(목적지·기간)과 연결됐는지를 한 줄로 보여준다. 연결된 여행이
 * 없으면(사고만 단독 접수한 경우) 사고 접수 시 입력한 국가만이라도 보여준다. */
export function TripContextBadge({
  tripDestination,
  tripStartDate,
  tripEndDate,
  incidentCountry,
}: {
  tripDestination?: string | null;
  tripStartDate?: string | null;
  tripEndDate?: string | null;
  incidentCountry?: string | null;
}) {
  if (!tripDestination && !incidentCountry) return null;

  return (
    <div className="trip-context-badge">
      <span aria-hidden>🌍</span>
      {tripDestination ? (
        <span>
          <strong>{tripDestination}</strong> 여행 중 사고
          {tripStartDate && tripEndDate && ` · ${tripStartDate} ~ ${tripEndDate}`}
        </span>
      ) : (
        <span><strong>{incidentCountry}</strong>에서 발생한 사고</span>
      )}
    </div>
  );
}
