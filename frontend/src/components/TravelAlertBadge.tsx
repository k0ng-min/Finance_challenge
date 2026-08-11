/**
 * 목적지의 외교부 여행경보.
 *
 * 이 값은 우리가 계산한 위험도가 아니라 외교부가 발령한 자료다. 그래서 출처와 발령일을
 * 함께 밝히고, 보상 여부를 말하지 않는다 — 약관 근거가 필요한 이야기는 제한조건 카드가
 * 조항 원문과 함께 따로 한다.
 *
 * 경보는 국가가 아니라 **지역** 단위다. 일본의 3단계는 후쿠시마 원전 반경 30km고,
 * 필리핀의 4단계는 민다나오 일부다. 이것을 국가 전체 경보처럼 그리면 도쿄·세부
 * 여행자에게 출국권고가 뜨고, 그러면 사용자는 경보를 아예 무시하게 된다.
 *
 * 경보 자료에 없는 나라면 아무것도 그리지 않는다. "정보 없음"조차 띄우지 않는 이유는,
 * 대부분의 안전한 나라가 여기 해당해서 매번 빈 줄이 생기기 때문이다.
 */
import type { TravelAlertOut, TravelAlertRow } from "../api";

/** 단계가 올라갈수록 눈에 띄게. 1·2는 정보, 3·4는 경고 톤. */
const TONE: Record<number, string> = { 1: "info", 2: "info", 3: "warn", 4: "danger" };

/** 이 단계부터 "그 지역에 가시나요?"를 묻는다(백엔드 CLAUSE_FROM_LEVEL과 같은 값). */
export const ASK_FROM_LEVEL = 3;

function asAlert(alert: unknown): TravelAlertOut | null {
  if (!alert || typeof alert !== "object") return null;
  const a = alert as TravelAlertOut;
  if (!a.baseline && !(a.regions?.length > 0)) return null;
  return a;
}

function Source({ alert, row }: { alert: TravelAlertOut; row: TravelAlertRow | null }) {
  return (
    <span className="travel-alert__source">
      외교부 발령{row?.issued_on ? ` · ${row.issued_on}` : ""}
      {alert.source_url && (
        <>
          {" · "}
          <a href={alert.source_url} target="_blank" rel="noreferrer">확인</a>
        </>
      )}
    </span>
  );
}

/**
 * 배지만 그린다. 지역 경보는 "일부 지역"임을 문장에 드러내고 어디인지 함께 적는다.
 */
export function TravelAlertBadge({ alert }: { alert: unknown }) {
  const a = asAlert(alert);
  if (!a) return null;

  const base = a.baseline;
  const 눈에띄는지역 = [...(a.regions ?? [])]
    .filter((r) => r.level >= ASK_FROM_LEVEL)
    .sort((x, y) => y.level - x.level);

  return (
    <div className="travel-alert-group">
      {base && (
        <div className={`travel-alert travel-alert--${TONE[base.level] ?? "info"}`}>
          <span className="travel-alert__level">여행경보 {base.level}단계</span>
          <span className="travel-alert__label">{base.label}</span>
          <Source alert={a} row={base} />
        </div>
      )}
      {눈에띄는지역.map((r) => (
        <div key={r.alert_id ?? r.note} className={`travel-alert travel-alert--${TONE[r.level] ?? "info"}`}>
          <span className="travel-alert__level">일부 지역 {r.level}단계</span>
          <span className="travel-alert__label">{r.label}</span>
          {r.note && <span className="travel-alert__where">{r.note}</span>}
          {!base && <Source alert={a} row={r} />}
        </div>
      ))}
    </div>
  );
}

/**
 * 배지 + "이 지역에 가시나요?" 체크박스. 여행 준비 STEP 1에서 쓴다.
 *
 * 체크하지 않으면 아무 일도 일어나지 않는다 — 그게 기본값이고, 대부분의 사용자가
 * 여기 해당한다. 체크했을 때만 결과 화면에 그 보험사 약관의 전쟁·내란 면책 조항이
 * 원문과 함께 붙는다.
 */
export function TravelAlertPicker({
  alert,
  selected,
  onChange,
}: {
  alert: unknown;
  selected: number[];
  onChange: (ids: number[]) => void;
}) {
  const a = asAlert(alert);
  if (!a) return null;

  const 물어볼지역 = (a.regions ?? [])
    .filter((r) => r.level >= ASK_FROM_LEVEL && r.alert_id !== null)
    .sort((x, y) => y.level - x.level);

  function toggle(id: number) {
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  }

  return (
    <div className="travel-alert-picker">
      <TravelAlertBadge alert={alert} />
      {물어볼지역.length > 0 && (
        <div className="travel-alert-ask">
          <p className="travel-alert-ask__title">
            아래 지역이 여행 경로에 포함되나요?
          </p>
          {물어볼지역.map((r) => (
            <label key={r.alert_id} className="travel-alert-ask__item">
              <input
                type="checkbox"
                checked={selected.includes(r.alert_id!)}
                onChange={() => toggle(r.alert_id!)}
              />
              <span>
                <strong>{r.level}단계 {r.label}</strong>
                {r.note && <> · {r.note}</>}
              </span>
            </label>
          ))}
          <p className="travel-alert-ask__hint">
            체크하시면 각 보험사 약관의 전쟁·내란 면책 조항을 원문과 함께 보여드립니다.
            해당 지역에 가지 않으신다면 그냥 넘어가셔도 됩니다.
          </p>
        </div>
      )}
    </div>
  );
}
