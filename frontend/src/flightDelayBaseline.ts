import { api, type FlightDelayStatsOut } from "./api";

/** 한국공항공사 통계(국제선 출발+도착 합산) 평균 지연시간을 앱 전체에서 한 번만 받아 캐시한다.
 * 약관의 지연기준시간(ClauseTerm)을 보여줄 때마다 다시 조회할 필요가 없다. */
let cached: Promise<FlightDelayStatsOut | null> | null = null;

export function loadFlightDelayStats(): Promise<FlightDelayStatsOut | null> {
  if (!cached) {
    cached = api.getFlightDelayStats().catch(() => null);
  }
  return cached;
}

/** 국제선(해외여행이므로) 출발+도착을 가중평균한 분 단위 평균 지연시간. 자료가 없으면 null. */
export function internationalAvgDelayMinutes(stats: FlightDelayStatsOut | null): number | null {
  if (!stats) return null;
  const intl = stats.overall.filter((r) => r.kind === "국제");
  const totalFlights = intl.reduce((sum, r) => sum + r.delayed_flights, 0);
  const totalMinutes = intl.reduce((sum, r) => sum + r.delayed_flights * (r.avg_delay_minutes ?? 0), 0);
  if (totalFlights === 0) return null;
  return Math.round((totalMinutes / totalFlights) * 10) / 10;
}
