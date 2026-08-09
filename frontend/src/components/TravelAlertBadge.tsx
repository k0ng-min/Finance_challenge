/**
 * 목적지의 외교부 여행경보 단계.
 *
 * 이 값은 우리가 계산한 위험도가 아니라 외교부가 발령한 자료다. 그래서 출처와 발령일을
 * 함께 밝히고, 보상 여부를 말하지 않는다 — 약관 근거가 필요한 이야기는 아래 제한조건
 * 카드가 조항 원문과 함께 따로 한다.
 *
 * 경보 자료에 없는 나라면 아무것도 그리지 않는다. "정보 없음"조차 띄우지 않는 이유는,
 * 대부분의 안전한 나라가 여기 해당해서 매번 빈 줄이 생기기 때문이다.
 */

export interface TravelAlertOut {
  level: number;
  label: string;
  region_type: string | null;
  note: string | null;
  issued_on: string | null;
  source: string | null;
  source_url: string | null;
}

/** 단계가 올라갈수록 눈에 띄게. 1·2는 정보, 3·4는 경고 톤. */
const TONE: Record<number, string> = { 1: "info", 2: "info", 3: "warn", 4: "danger" };

export function TravelAlertBadge({ alert }: { alert: unknown }) {
  if (!alert || typeof alert !== "object") return null;
  const a = alert as TravelAlertOut;
  if (!a.level) return null;

  const tone = TONE[a.level] ?? "info";
  return (
    <div className={`travel-alert travel-alert--${tone}`}>
      <span className="travel-alert__level">여행경보 {a.level}단계</span>
      <span className="travel-alert__label">{a.label}</span>
      {a.region_type && <span className="travel-alert__region">{a.region_type}</span>}
      <span className="travel-alert__source">
        외교부 발령{a.issued_on ? ` · ${a.issued_on}` : ""}
        {a.source_url && (
          <>
            {" · "}
            <a href={a.source_url} target="_blank" rel="noreferrer">확인</a>
          </>
        )}
      </span>
    </div>
  );
}
