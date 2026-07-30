import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type RecommendationOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { StepFlow } from "../components/StepFlow";
import { InsurerRankingFlow } from "../components/InsurerRankingFlow";
import { DateTimeField } from "../components/DateTimeField";
import { LoadingScreen } from "../components/LoadingScreen";
import { COUNTRIES } from "../data/countries";

const COMPANION_OPTIONS = ["혼자", "가족", "친구", "연인", "동료", "반려동물 동반"];
// 현재 KB에 실제 약관이 적재된 담보는 의료비(해외상해의료비)·구조송환뿐이라, 그 두 개만
// 보험사 순위·추천 점수에 실제로 반영된다. 나머지는 선택은 가능하지만 "약관 미확보"로
// 정직하게 안내되며(보장 공백 표시) 순위 점수에는 영향을 주지 않는다.
const KB_BACKED_PRIORITIES = new Set(["의료비", "구조송환"]);
const PRIORITY_OPTIONS = ["의료비", "구조송환", "휴대품 파손·도난", "배상책임", "항공기 지연", "질병"];


export function TripPrep() {
  const { userId, setTripId } = useApp();
  const [searchParams] = useSearchParams();
  const resumeTripId = Number(searchParams.get("resultOf")) || null;
  const [step, setStep] = useState(0);
  const [destination, setDestination] = useState("");
  const [companionType, setCompanionType] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [purpose, setPurpose] = useState("");
  const [activities, setActivities] = useState("");
  const [coveragePriority, setCoveragePriority] = useState("");
  const [rentalCar, setRentalCar] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // /trip으로 다시 들어올 때마다 매번 처음(목적지 선택)부터 시작한다 — 이전 결과를 자동으로 복원하지 않는다.
  // 단, 계정의 "내 여행 기록"에서 특정 여행을 선택해 들어온 경우(?resultOf=)에는 그 결과를 바로 보여준다.
  const [result, setResult] = useState<RecommendationOut | null>(null);
  const [resuming, setResuming] = useState(!!resumeTripId);

  useEffect(() => {
    if (!resumeTripId) return;
    setTripId(resumeTripId);
    api.getTrip(resumeTripId)
      .then(setResult)
      .finally(() => setResuming(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  if (resuming) {
    return (
      <div className="page">
        <TopBar title="맞춤 보험 순위" />
        <LoadingScreen icon="suitcase" title="여행 기록을 불러오고 있어요" messages={["예전에 준비했던 여행을 찾고 있어요"]} />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page">
        <TopBar title="맞춤 보험 순위" />
        <LoadingScreen
          icon="flag"
          title="딱 맞는 보험 순위를 만들고 있어요"
          messages={[
            "목적지·기간·활동을 바탕으로 위험도를 분석하고 있어요",
            "관련된 실제 약관 조항을 찾고 있어요",
          ]}
        />
      </div>
    );
  }

  if (result) {
    return (
      <div className="page">
        <TopBar title="맞춤 보험 순위" />
        <InsurerRankingFlow result={result} />
      </div>
    );
  }

  const activityList = activities.split(",").map((a) => a.trim()).filter(Boolean);
  const priorityList = coveragePriority.split(",").map((a) => a.trim()).filter(Boolean);

  function togglePriority(option: string) {
    const next = priorityList.includes(option)
      ? priorityList.filter((p) => p !== option)
      : [...priorityList, option];
    setCoveragePriority(next.join(", "));
  }

  const steps = [
    {
      icon: "flag",
      eyebrow: "STEP 1 · 목적지",
      title: "어디로 떠나시나요?",
      subtitle: "목적지와 함께할 사람을 알려주세요.",
      content: (
        <>
          <label>
            목적지 국가
            <select value={destination} onChange={(e) => setDestination(e.target.value)} autoFocus>
              <option value="" disabled>국가를 선택하세요</option>
              {COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
          <label style={{ marginBottom: 10 }}>동반자 유형</label>
          <div className="tabs" style={{ flexWrap: "wrap" }}>
            {COMPANION_OPTIONS.map((c) => (
              <button
                key={c}
                type="button"
                className={`tab${companionType === c ? " tab--active" : ""}`}
                onClick={() => setCompanionType(c)}
              >
                {c}
              </button>
            ))}
          </div>
        </>
      ),
      canNext: destination.trim().length > 0,
    },
    {
      icon: "calendar",
      eyebrow: "STEP 2 · 기간",
      title: "언제부터 언제까지\n떠나시나요?",
      content: (
        <>
          <DateTimeField label="여행 시작일" value={startDate} onChange={setStartDate} mode="date" />
          <DateTimeField label="여행 종료일" value={endDate} onChange={setEndDate} mode="date" />
        </>
      ),
      canNext: !!startDate && !!endDate,
    },
    {
      icon: "explorer",
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
      icon: "shield",
      eyebrow: "STEP 4 · 우선순위",
      title: "가장 중요하게\n생각하는 보장은?",
      subtitle: "여러 개를 골라도 돼요.",
      content: (
        <>
          <label style={{ marginBottom: 4 }}>보장 우선순위</label>
          <p className="muted" style={{ fontSize: "0.78rem", marginTop: 0, marginBottom: 10 }}>
            "준비중" 항목은 아직 실제 약관을 확보하지 못해 순위 점수에는 반영되지 않아요.
          </p>
          <div className="tabs" style={{ marginBottom: 14, flexWrap: "wrap" }}>
            {PRIORITY_OPTIONS.map((p) => (
              <button
                key={p}
                type="button"
                className={`tab${priorityList.includes(p) ? " tab--active" : ""}`}
                onClick={() => togglePriority(p)}
              >
                {p}{!KB_BACKED_PRIORITIES.has(p) && " (준비중)"}
              </button>
            ))}
          </div>
          <label className="checkbox-label">
            <input type="checkbox" checked={rentalCar} onChange={(e) => setRentalCar(e.target.checked)} />
            렌터카를 이용할 예정입니다
          </label>
        </>
      ),
      canNext: true,
    },
    {
      icon: "tick",
      eyebrow: "STEP 5 · 확인",
      title: "이대로 분석해\n드릴까요?",
      subtitle: "6개 보험사의 실제 약관 근거와 함께 맞춤 보장을 비교해 드려요.",
      content: (
        <div className="card" style={{ textAlign: "left", marginBottom: 0, padding: 16 }}>
          <div className="muted">목적지</div>
          <div style={{ marginBottom: 6, fontWeight: 700 }}>{destination} · {companionType}</div>
          <div className="muted">기간</div>
          <div style={{ marginBottom: 6, fontWeight: 700 }}>{startDate} ~ {endDate}</div>
          <div className="muted">목적 / 활동</div>
          <div style={{ marginBottom: 6, fontWeight: 700 }}>{purpose || "-"} {activityList.length ? `· ${activityList.join(", ")}` : ""}</div>
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
        eyebrow={current.eyebrow}
        title={current.title}
        subtitle={current.subtitle}
        stepIndex={step}
        onBack={step > 0 ? () => setStep((s) => s - 1) : undefined}
        onNext={isLast ? handleSubmit : () => setStep((s) => s + 1)}
        nextLabel={isLast ? "보험사 순위 확인하기" : "다음"}
        nextDisabled={!current.canNext || !userId}
        loading={loading}
      >
        {current.content}
      </StepFlow>
    </div>
  );
}
