import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type RecommendationOut, type InsurerTierOut, type IncidentTypeOut, type TravelAlertOut, userMessage } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { StepFlow } from "../components/StepFlow";
import { InsurerRankingFlow } from "../components/InsurerRankingFlow";
import { DateRangeField } from "../components/DateTimeField";
import { LoadingScreen } from "../components/LoadingScreen";
import { PickerField } from "../components/PickerField";
import { ExternalPolicyPicker, type PickedPolicy } from "../components/ExternalPolicyPicker";
import { TravelAlertPicker } from "../components/TravelAlertBadge";
import { COUNTRIES } from "../data/countries";

const COMPANION_OPTIONS = ["혼자", "가족", "친구", "연인", "동료", "반려동물 동반"];


export function TripPrep() {
  const { userId, setTripId, age: profileAge, updateAge, sex: profileSex, updateSex } = useApp();
  // 기존보험은 선택 항목이다 — 건너뛰어도 여행 준비는 끝까지 진행된다.
  const [picked, setPicked] = useState<PickedPolicy[]>([]);
  const [searchParams] = useSearchParams();
  const resumeTripId = Number(searchParams.get("resultOf")) || null;
  const [step, setStep] = useState(0);
  const [destination, setDestination] = useState("");
  const [companionType, setCompanionType] = useState("");
  const [age, setAge] = useState("");
  const [sex, setSex] = useState<"M" | "F" | "">("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [purpose, setPurpose] = useState("");
  const [activities, setActivities] = useState("");
  const [coveragePriority, setCoveragePriority] = useState("");
  const [rentalCar, setRentalCar] = useState(false);
  const [tiers, setTiers] = useState<InsurerTierOut[]>([]);
  const [tier, setTier] = useState<string | null>(null);
  const [incidentTypes, setIncidentTypes] = useState<IncidentTypeOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // /trip으로 다시 들어올 때마다 매번 처음(목적지 선택)부터 시작한다 — 이전 결과를 자동으로 복원하지 않는다.
  // 단, 계정의 "내 여행 기록"에서 특정 여행을 선택해 들어온 경우(?resultOf=)에는 그 결과를 바로 보여준다.
  const [result, setResult] = useState<RecommendationOut | null>(null);
  const [resuming, setResuming] = useState(!!resumeTripId);
  // 기존보험 저장(linkExternalPolicies)은 fire-and-forget이라 언제 끝나는지 알 수 없다.
  // InsurerRankingFlow가 이 여행에 실제 보험을 등록한 뒤 진단을 조회할 때, 이 Promise를
  // 먼저 기다리게 해서 "아직 저장 안 된 기존보험" 때문에 진단이 비어 보이는 경합을 막는다.
  const externalLinkReadyRef = useRef<Promise<unknown>>(Promise.resolve());
  const [hasPickedExternal, setHasPickedExternal] = useState(false);
  // 목적지 여행경보와, 그중 "여기 간다"고 체크한 지역.
  const [travelAlert, setTravelAlert] = useState<TravelAlertOut | null>(null);
  const [visitingRegionIds, setVisitingRegionIds] = useState<number[]>([]);
  // 보여줄 경보가 실제로 있을 때만 스텝을 하나 늘린다. 대부분의 나라는 경보 자료 자체가
  // 없어서(미국·대만·싱가포르 등) 빈 스텝이 생기면 안 된다.
  const hasTravelAlert = !!travelAlert && (!!travelAlert.baseline || travelAlert.regions.length > 0);

  useEffect(() => {
    if (!resumeTripId) return;
    setTripId(resumeTripId);
    api.getTrip(resumeTripId)
      .then(setResult)
      .finally(() => setResuming(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    api.getInsurerTiers().then(setTiers).catch(() => {});
  }, []);

  useEffect(() => {
    api.getIncidentTypes().then(setIncidentTypes).catch(() => {});
  }, []);

  // 목적지를 고르는 즉시 여행경보를 조회한다. 나라를 바꾸면 앞서 체크한 지역은 버린다 —
  // 다른 나라의 지역을 들고 가면 서버가 무시하지만, 화면에 남아 있는 것부터가 혼란스럽다.
  useEffect(() => {
    setVisitingRegionIds([]);
    if (!destination.trim()) {
      setTravelAlert(null);
      return;
    }
    let stale = false;
    api.getTravelAlert(destination)
      .then((res) => { if (!stale) setTravelAlert(res.alert); })
      .catch(() => { if (!stale) setTravelAlert(null); });
    return () => { stale = true; };
  }, [destination]);

  // 한 번 입력한 나이·성별은 자동으로 채워준다 — 매번 다시 입력할 필요 없게.
  // (로그인 계정은 서버 프로필에, 게스트는 로컬에 남아 있다.)
  useEffect(() => {
    if (profileAge) setAge((prev) => prev || String(profileAge));
  }, [profileAge]);
  useEffect(() => {
    if (profileSex === "M" || profileSex === "F") setSex((prev) => prev || profileSex);
  }, [profileSex]);

  async function handleSubmit() {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      // 나이·성별은 보험료 조회(순위 화면)에 바로 쓰이므로 여행 생성 전에 먼저 저장한다.
      if (age && Number(age) !== profileAge) await updateAge(Number(age)).catch(() => {});
      if (sex && sex !== profileSex) await updateSex(sex).catch(() => {});
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
        visiting_alert_region_ids: visitingRegionIds,
      });
      setResult(res);
      setTripId(res.trip_id);
      // 기존보험을 골랐으면 같이 저장한다. 여행 생성은 이미 끝났고 결과값도 쓰지 않으므로
      // await하지 않는다 — 기다리면 화면 전환이 이 저장 왕복만큼 늦어져 "흐름을 막지 않는다"는
      // 의도와 어긋난다. 실패해도 기존보험은 나중에 내 보험 화면에서 다시 등록할 수 있다.
      // Promise는 남겨둔다 — InsurerRankingFlow가 보험사를 등록한 뒤 중복·공백 진단을
      // 조회하기 전에 이 저장이 끝났는지 기다리는 데 쓴다.
      if (picked.length > 0) {
        externalLinkReadyRef.current = api
          .linkExternalPolicies(userId, { provider: "manual", items: picked })
          .catch(() => {});
        setHasPickedExternal(true);
      } else {
        setHasPickedExternal(false);
      }
    } catch (err) {
      setError(userMessage(err));
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
        <InsurerRankingFlow
          result={result}
          initialTier={tier}
          hasExternalPolicies={hasPickedExternal}
          externalPoliciesReady={externalLinkReadyRef.current}
        />
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
      eyebrow: "목적지",
      title: "어디로 떠나시나요?",
      subtitle: "목적지와 함께할 사람을 알려주세요.",
      content: (
        <>
          <label>
            목적지 국가
            <PickerField
              value={destination}
              onChange={setDestination}
              placeholder="국가를 선택하세요"
              modalTitle="목적지 국가"
              options={COUNTRIES.map((c) => ({ value: c, label: c }))}
            />
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
          <label style={{ marginTop: 14 }}>
            나이
            <input
              type="number"
              min={0}
              max={120}
              value={age}
              onChange={(e) => setAge(e.target.value)}
              placeholder="예: 30"
            />
          </label>
          {/* 여행자보험료는 나이뿐 아니라 성별로도 갈려서 둘 다 받아야 실제 금액을 보여줄 수 있다. */}
          <label style={{ marginTop: 14, marginBottom: 10 }}>성별</label>
          <div className="tabs">
            {([["M", "남자"], ["F", "여자"]] as const).map(([v, label]) => (
              <button
                key={v}
                type="button"
                className={`tab${sex === v ? " tab--active" : ""}`}
                onClick={() => setSex(v)}
              >
                {label}
              </button>
            ))}
          </div>
        </>
      ),
      canNext: destination.trim().length > 0 && !!age && !!sex,
    },
    // 여행경보는 경보가 있는 나라에서만 스텝이 하나 늘어난다. 목적지 스텝에 같이 얹으면
    // 동반자·나이·성별에 묻혀 그냥 지나치게 되는데, 이건 지나치면 안 되는 정보다.
    // 안전한 나라(대다수)는 이 스텝 자체가 없어서 흐름이 그대로다.
    ...(hasTravelAlert ? [{
      icon: "map-pin",
      eyebrow: "여행경보",
      title: `${destination}에 여행경보가 있어요`,
      subtitle: "외교부가 발령한 자료입니다. 보상 여부를 판단한 결과가 아닙니다.",
      content: (
        <TravelAlertPicker
          alert={travelAlert}
          selected={visitingRegionIds}
          onChange={setVisitingRegionIds}
        />
      ),
      canNext: true,  // 체크는 선택이다 — 해당 지역에 가지 않으면 그냥 넘어간다
    }] : []),
    {
      icon: "calendar",
      eyebrow: "기간",
      title: "언제부터 언제까지\n떠나시나요?",
      content: (
        <DateRangeField
          label="여행 기간"
          start={startDate}
          end={endDate}
          onChange={(s, e) => { setStartDate(s); setEndDate(e); }}
        />
      ),
      canNext: !!startDate && !!endDate && endDate > startDate,
    },
    {
      icon: "explorer",
      eyebrow: "활동",
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
      eyebrow: "걱정되는 사고",
      title: "어떤 사고가\n가장 걱정되시나요?",
      subtitle: "여러 개를 골라도 돼요. 고른 사고유형은 보험사 순위와, 이후 보험사별 상세 화면에서 보여드릴 약관 조항에 그대로 반영돼요.",
      content: (
        <>
          <label style={{ marginBottom: 10 }}>걱정되는 사고유형</label>
          <div className="tabs" style={{ marginBottom: 14, flexWrap: "wrap" }}>
            {incidentTypes.map((t) => (
              <button
                key={t.l1_code}
                type="button"
                className={`tab${priorityList.includes(t.l1_code) ? " tab--active" : ""}`}
                onClick={() => togglePriority(t.l1_code)}
              >
                {t.name}
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
      icon: "target",
      eyebrow: "보장유형",
      title: "어떤 기준으로\n비교해 드릴까요?",
      subtitle: "선택한 기준에 따라 6개 보험사의 실제 약관 근거를 비교해 순위를 매겨드려요.",
      content: (
        <div className="tier-list">
          {tiers.map((t) => (
            <button
              key={t.tier_code}
              type="button"
              className={`tier-card${tier === t.tier_code ? " insurer-card--active" : ""}`}
              style={tier === t.tier_code ? { borderColor: "var(--primary)" } : undefined}
              onClick={() => setTier(t.tier_code)}
            >
              <div className="tier-card__text">
                <strong>{t.label}</strong>
                <span>{t.description}</span>
              </div>
              <span className="tier-card__arrow">›</span>
            </button>
          ))}
        </div>
      ),
      canNext: !!tier,
    },
    {
      icon: "umbrella",
      eyebrow: "기존보험",
      title: "이미 들고 계신\n보험이 있나요?",
      content: <ExternalPolicyPicker value={picked} onChange={setPicked} />,
      canNext: true,  // 선택 항목이라 아무것도 안 골라도 넘어간다
    },
    {
      icon: "tick",
      eyebrow: "확인",
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
          <div className="muted">걱정되는 사고유형</div>
          <div style={{ marginBottom: 6, fontWeight: 700 }}>
            {priorityList.length
              ? priorityList.map((code) => incidentTypes.find((t) => t.l1_code === code)?.name ?? code).join(", ")
              : "-"}
          </div>
          <div className="muted">보장유형</div>
          <div style={{ fontWeight: 700 }}>{tiers.find((t) => t.tier_code === tier)?.label ?? "-"}</div>
          {error && <div className="error-box">{error}</div>}
        </div>
      ),
      canNext: true,
    },
  ];

  // 여행경보 스텝이 끼면 뒤 번호가 밀리므로 번호는 하드코딩하지 않고 여기서 매긴다.
  const current = steps[step];
  const isLast = step === steps.length - 1;

  return (
    <div className="page">
      <TopBar title="내 여행 준비" />
      <StepFlow
        icon={current.icon}
        eyebrow={`STEP ${step + 1} · ${current.eyebrow}`}
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
