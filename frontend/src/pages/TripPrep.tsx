import { useEffect, useState } from "react";
import { api, type RecommendationOut } from "../api";
import { useApp } from "../context/AppContext";
import { FindingCard } from "../components/FindingCard";

const LS_RESULT = "travel_ai_trip_result";

export function TripPrep() {
  const { userId, setTripId } = useApp();
  const [destination, setDestination] = useState("스위스");
  const [startDate, setStartDate] = useState("2026-08-10");
  const [endDate, setEndDate] = useState("2026-08-20");
  const [purpose, setPurpose] = useState("휴양 및 관광");
  const [activities, setActivities] = useState("");
  const [companionType, setCompanionType] = useState("가족");
  const [rentalCar, setRentalCar] = useState(false);
  const [coveragePriority, setCoveragePriority] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RecommendationOut | null>(() => {
    const cached = localStorage.getItem(LS_RESULT);
    return cached ? JSON.parse(cached) : null;
  });

  useEffect(() => {
    if (result) localStorage.setItem(LS_RESULT, JSON.stringify(result));
  }, [result]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.createTrip({
        user_id: userId,
        destination,
        start_date: startDate,
        end_date: endDate,
        purpose,
        activities: activities.split(",").map((a) => a.trim()).filter(Boolean),
        companion_type: companionType,
        rental_car: rentalCar,
        coverage_priority: coveragePriority.split(",").map((a) => a.trim()).filter(Boolean),
      });
      setResult(res);
      setTripId(res.trip_id);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  const grouped = result
    ? {
        추천담보: result.findings.filter((f) => f.finding_type === "추천담보"),
        제한조건: result.findings.filter((f) => f.finding_type === "제한조건"),
        보장공백: result.findings.filter((f) => f.finding_type === "보장공백"),
      }
    : null;

  return (
    <div className="page">
      <h1>내 여행 준비</h1>
      <p className="page-desc">
        여행 정보를 입력하면 위험 프로필을 만들고, 6개 보험사의 실제 약관을 근거로 필요한 보장과
        가입 전 검토할 상품을 비교해 드립니다.
      </p>

      <form className="card form" onSubmit={handleSubmit}>
        <div className="form-row">
          <label>
            목적지 국가
            <input value={destination} onChange={(e) => setDestination(e.target.value)} required />
          </label>
          <label>
            동반자 유형
            <input value={companionType} onChange={(e) => setCompanionType(e.target.value)} />
          </label>
        </div>
        <div className="form-row">
          <label>
            여행 시작일
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
          </label>
          <label>
            여행 종료일
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
          </label>
        </div>
        <label>
          여행 목적
          <input value={purpose} onChange={(e) => setPurpose(e.target.value)} />
        </label>
        <label>
          예정 활동 (쉼표로 구분, 예: 등반, 스노클링)
          <input value={activities} onChange={(e) => setActivities(e.target.value)} placeholder="등반, 스쿠버다이빙" />
        </label>
        <label>
          보장 우선순위 (쉼표로 구분)
          <input value={coveragePriority} onChange={(e) => setCoveragePriority(e.target.value)} placeholder="의료비, 구조송환" />
        </label>
        <label className="checkbox-label">
          <input type="checkbox" checked={rentalCar} onChange={(e) => setRentalCar(e.target.checked)} />
          렌터카를 이용할 예정입니다
        </label>
        <button type="submit" disabled={loading || !userId}>
          {loading ? "분석 중..." : "위험 프로필 생성 및 보장 추천 받기"}
        </button>
        {error && <div className="error-box">{error}</div>}
      </form>

      {result && (
        <div className="result-section">
          <h2>여행 위험 프로필</h2>
          <div className="card risk-profile">
            <div>위험도: <strong>{String(result.risk_profile.risk_level ?? "-")}</strong></div>
            <div>여행 일수: {String(result.risk_profile.trip_days ?? "-")}일</div>
            {Array.isArray(result.risk_profile.risky_activity_detected) &&
              (result.risk_profile.risky_activity_detected as string[]).length > 0 && (
                <div>감지된 위험활동: {(result.risk_profile.risky_activity_detected as string[]).join(", ")}</div>
              )}
          </div>

          {grouped && grouped.추천담보.length > 0 && (
            <>
              <h2>우선 검토 대상 보장 (보험사별 비교)</h2>
              {grouped.추천담보.map((f) => (
                <FindingCard key={f.finding_id} finding={f} />
              ))}
            </>
          )}

          {grouped && grouped.제한조건.length > 0 && (
            <>
              <h2>가입 전 확인해야 할 제한조건</h2>
              {grouped.제한조건.map((f) => (
                <FindingCard key={f.finding_id} finding={f} />
              ))}
            </>
          )}

          {grouped && grouped.보장공백.length > 0 && (
            <>
              <h2>현재 시스템에서 판단할 수 없는 보장</h2>
              {grouped.보장공백.map((f) => (
                <FindingCard key={f.finding_id} finding={f} />
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
