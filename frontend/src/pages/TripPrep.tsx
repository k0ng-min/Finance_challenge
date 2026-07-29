import { useEffect, useState } from "react";
import { api, type RecommendationOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { StepFlow } from "../components/StepFlow";
import { ResultTabs } from "../components/ResultTabs";
import { NextStepCard } from "../components/NextStepCard";

const LS_RESULT = "travel_ai_trip_result";
const STEP_COUNT = 5;

export function TripPrep() {
  const { userId, setTripId } = useApp();
  const [step, setStep] = useState(0);
  const [destination, setDestination] = useState("스위스");
  const [companionType, setCompanionType] = useState("가족");
  const [startDate, setStartDate] = useState("2026-08-10");
  const [endDate, setEndDate] = useState("2026-08-20");
  const [purpose, setPurpose] = useState("휴양 및 관광");
  const [activities, setActivities] = useState("");
  const [coveragePriority, setCoveragePriority] = useState("");
  const [rentalCar, setRentalCar] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RecommendationOut | null>(() => {
    const cached = localStorage.getItem(LS_RESULT);
    return cached ? JSON.parse(cached) : null;
  });

  useEffect(() => {
    if (result) localStorage.setItem(LS_RESULT, JSON.stringify(result));
  }, [result]);

  async function handleSubmit() {
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

  if (result) {
    const groups = [
      { key: "추천담보", label: "추천 담보", items: result.findings.filter((f) => f.finding_type === "추천담보") },
      { key: "제한조건", label: "제한조건", items: result.findings.filter((f) => f.finding_type === "제한조건") },
      { key: "보장공백", label: "보장 공백", items: result.findings.filter((f) => f.finding_type === "보장공백") },
    ];
    return (
      <div className="page">
        <TopBar title="여행 위험 프로필" />
        <div className="result-section">
          <div className="card risk-profile">
            <div>위험도: <strong>{String(result.risk_profile.risk_level ?? "-")}</strong></div>
            <div>여행 일수: {String(result.risk_profile.trip_days ?? "-")}일</div>
            {Array.isArray(result.risk_profile.risky_activity_detected) &&
              (result.risk_profile.risky_activity_detected as string[]).length > 0 && (
                <div>감지된 위험활동: {(result.risk_profile.risky_activity_detected as string[]).join(", ")}</div>
              )}
          </div>
          <h2>보장 추천 결과</h2>
          <ResultTabs groups={groups} />
          <NextStepCard
            to="/policies"
            icon="umbrella"
            iconBg="var(--orange-soft)"
            label="다음 단계"
            title="마음에 드는 보험, 보관함에 등록하기"
          />
        </div>
      </div>
    );
  }

  const activityList = activities.split(",").map((a) => a.trim()).filter(Boolean);
  const priorityList = coveragePriority.split(",").map((a) => a.trim()).filter(Boolean);

  const steps = [
    {
      icon: "flag", iconBg: "var(--cream-deep)",
      eyebrow: "STEP 1 · 목적지",
      title: "어디로 떠나시나요?",
      subtitle: "목적지와 함께할 사람을 알려주세요.",
      content: (
        <>
          <label>
            목적지 국가
            <input value={destination} onChange={(e) => setDestination(e.target.value)} placeholder="예: 스위스" autoFocus />
          </label>
          <label>
            동반자 유형
            <input value={companionType} onChange={(e) => setCompanionType(e.target.value)} placeholder="예: 가족, 친구, 혼자" />
          </label>
        </>
      ),
      canNext: destination.trim().length > 0,
    },
    {
      icon: "calendar", iconBg: "var(--yellow-soft)",
      eyebrow: "STEP 2 · 기간",
      title: "언제부터 언제까지\n떠나시나요?",
      content: (
        <>
          <label>
            여행 시작일
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </label>
          <label>
            여행 종료일
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </label>
        </>
      ),
      canNext: !!startDate && !!endDate,
    },
    {
      icon: "explorer", iconBg: "var(--mint-soft)",
      eyebrow: "STEP 3 · 활동",
      title: "무엇을 하며\n보내실 예정인가요?",
      subtitle: "위험도가 있는 활동은 자동으로 감지해서 필요한 보장을 알려드려요.",
      content: (
        <>
          <label>
            여행 목적
            <input value={purpose} onChange={(e) => setPurpose(e.target.value)} placeholder="예: 휴양 및 관광" />
          </label>
          <label>
            예정 활동 (쉼표로 구분)
            <input value={activities} onChange={(e) => setActivities(e.target.value)} placeholder="등반, 스쿠버다이빙" />
          </label>
          {activityList.length > 0 && (
            <div className="tabs" style={{ marginTop: 4 }}>
              {activityList.map((a) => <span key={a} className="tab tab--active">{a}</span>)}
            </div>
          )}
        </>
      ),
      canNext: true,
    },
    {
      icon: "shield", iconBg: "var(--orange-soft)",
      eyebrow: "STEP 4 · 우선순위",
      title: "가장 중요하게\n생각하는 보장은?",
      content: (
        <>
          <label>
            보장 우선순위 (쉼표로 구분)
            <input value={coveragePriority} onChange={(e) => setCoveragePriority(e.target.value)} placeholder="의료비, 구조송환" />
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={rentalCar} onChange={(e) => setRentalCar(e.target.checked)} />
            렌터카를 이용할 예정입니다
          </label>
          {priorityList.length > 0 && (
            <div className="tabs" style={{ marginTop: 4 }}>
              {priorityList.map((a) => <span key={a} className="tab tab--active">{a}</span>)}
            </div>
          )}
        </>
      ),
      canNext: true,
    },
    {
      icon: "tick", iconBg: "var(--mint-soft)",
      eyebrow: "STEP 5 · 확인",
      title: "이대로 분석해\n드릴까요?",
      subtitle: "6개 보험사의 실제 약관 근거와 함께 맞춤 보장을 비교해 드려요.",
      content: (
        <div className="card" style={{ textAlign: "left" }}>
          <div className="muted">목적지</div>
          <div style={{ marginBottom: 10, fontWeight: 700 }}>{destination} · {companionType}</div>
          <div className="muted">기간</div>
          <div style={{ marginBottom: 10, fontWeight: 700 }}>{startDate} ~ {endDate}</div>
          <div className="muted">목적 / 활동</div>
          <div style={{ marginBottom: 10, fontWeight: 700 }}>{purpose || "-"} {activityList.length ? `· ${activityList.join(", ")}` : ""}</div>
          <div className="muted">보장 우선순위</div>
          <div style={{ fontWeight: 700 }}>{priorityList.length ? priorityList.join(", ") : "-"}</div>
          {error && <div className="error-box">{error}</div>}
        </div>
      ),
      canNext: true,
    },
  ];

  const current = steps[step];
  const isLast = step === steps.length - 1;

  return (
    <div className="page">
      <TopBar title="내 여행 준비" />
      <StepFlow
        icon={current.icon}
        iconBg={current.iconBg}
        eyebrow={current.eyebrow}
        title={current.title}
        subtitle={current.subtitle}
        stepIndex={step}
        stepCount={STEP_COUNT}
        onBack={step > 0 ? () => setStep((s) => s - 1) : undefined}
        onNext={isLast ? handleSubmit : () => setStep((s) => s + 1)}
        nextLabel={isLast ? "위험 프로필 생성하기" : "다음"}
        nextDisabled={!current.canNext || !userId}
        loading={loading}
      >
        {current.content}
      </StepFlow>
    </div>
  );
}
