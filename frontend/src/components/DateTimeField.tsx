import { useEffect, useRef, useState } from "react";

const ITEM_H = 44;

function pad2(n: number) {
  return String(n).padStart(2, "0");
}

function daysInMonth(y: number, m: number) {
  return new Date(y, m, 0).getDate();
}

interface WheelColProps {
  items: string[];
  index: number;
  onIndex: (i: number) => void;
}

function WheelCol({ items, index, onIndex }: WheelColProps) {
  const ref = useRef<HTMLDivElement>(null);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const target = index * ITEM_H;
    if (Math.abs(el.scrollTop - target) > 2) {
      el.scrollTo({ top: target, behavior: "smooth" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index]);

  function handleScroll() {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      const el = ref.current;
      if (!el) return;
      const i = Math.max(0, Math.min(items.length - 1, Math.round(el.scrollTop / ITEM_H)));
      onIndex(i);
    }, 110);
  }

  function pick(i: number) {
    if (timer.current) window.clearTimeout(timer.current);
    onIndex(i);
  }

  return (
    <div className="wheel-col" ref={ref} onScroll={handleScroll}>
      {items.map((it, i) => (
        <div
          key={i}
          className={`wheel-item${i === index ? " wheel-item--center" : ""}`}
          onClick={() => pick(i)}
        >
          {it}
        </div>
      ))}
    </div>
  );
}

const WEEKDAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"];

/** YYYY-MM-DD 세 값을 하나의 정수로 눌러 크기 비교에 쓴다(2026-08-19 → 20260819). */
function dayKey(y: number, m: number, d: number) {
  return y * 10000 + m * 100 + d;
}

interface MonthCalendarProps {
  year: number;
  month: number;
  selectedDay: number;
  /** 기간 선택일 때 칠할 시작·끝. 없으면 한 날짜만 고르는 기존 동작 그대로다. */
  rangeStart?: Parsed | null;
  rangeEnd?: Parsed | null;
  /** 선택 가능한 최소/최대 날짜(포함). 없으면 제한 없음. */
  min: Parsed | null;
  max: Parsed | null;
  onSelect: (y: number, m: number, d: number) => void;
  onMoveMonth: (delta: number) => void;
}

/**
 * 바텀시트 위쪽의 한 달짜리 달력.
 *
 * 휠 스피너만 있을 때는 "8월 23일이 무슨 요일인지", "주말이 언제인지"를 알 수 없어서
 * 여행 기간처럼 요일이 중요한 날짜를 고르기 어려웠다. 시중 앱들이 쓰는 평범한 월 단위
 * 격자를 그대로 두되(요일 머리글 + 7열 격자 + 좌우 월 이동), 색과 모서리만 이 서비스의
 * 것을 쓴다. 휠은 아래에 그대로 남겨서 연·월을 멀리 건너뛸 때 계속 쓸 수 있다 — 둘은
 * 같은 draft를 보고 있어서 어느 쪽으로 골라도 서로 따라 움직인다.
 */
function MonthCalendar({
  year, month, selectedDay, rangeStart = null, rangeEnd = null, min, max, onSelect, onMoveMonth,
}: MonthCalendarProps) {
  const startKey = rangeStart ? dayKey(rangeStart.y, rangeStart.m, rangeStart.d) : null;
  const endKey = rangeEnd ? dayKey(rangeEnd.y, rangeEnd.m, rangeEnd.d) : null;
  const isRange = startKey !== null;

  const firstWeekday = new Date(year, month - 1, 1).getDay();
  const dayCount = daysInMonth(year, month);
  // 앞쪽 빈 칸 + 날짜 — 뒤쪽 빈 칸은 격자가 알아서 비우므로 채우지 않는다.
  const cells: (number | null)[] = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: dayCount }, (_, i) => i + 1),
  ];

  function disabled(day: number) {
    const key = dayKey(year, month, day);
    if (min && key < dayKey(min.y, min.m, min.d)) return true;
    if (max && key > dayKey(max.y, max.m, max.d)) return true;
    return false;
  }

  // 이전/다음 달로 넘어갈 수 있는지 — 넘어가 봐야 고를 날이 하나도 없으면 막는다.
  const prevBlocked = !!min && dayKey(year, month, 1) <= dayKey(min.y, min.m, min.d);
  const nextBlocked = !!max && dayKey(year, month, dayCount) >= dayKey(max.y, max.m, max.d);

  return (
    <div className="calendar">
      <div className="calendar__head">
        <button
          type="button"
          className="calendar__nav"
          onClick={() => onMoveMonth(-1)}
          disabled={prevBlocked}
          aria-label="이전 달"
        >
          ‹
        </button>
        <span className="calendar__title">{year}년 {month}월</span>
        <button
          type="button"
          className="calendar__nav"
          onClick={() => onMoveMonth(1)}
          disabled={nextBlocked}
          aria-label="다음 달"
        >
          ›
        </button>
      </div>
      <div className="calendar__weekdays">
        {WEEKDAY_LABELS.map((w, i) => (
          <span key={w} className={`calendar__weekday${i === 0 ? " calendar__weekday--sun" : ""}${i === 6 ? " calendar__weekday--sat" : ""}`}>
            {w}
          </span>
        ))}
      </div>
      <div className="calendar__grid">
        {cells.map((day, i) =>
          day === null ? (
            <span key={`pad-${i}`} className="calendar__cell calendar__cell--empty" />
          ) : (
            (() => {
              const key = dayKey(year, month, day);
              const isStart = startKey !== null && key === startKey;
              const isEnd = endKey !== null && key === endKey;
              const inside = startKey !== null && endKey !== null && key > startKey && key < endKey;
              const on = isRange ? isStart || isEnd : day === selectedDay;
              // 시작~끝 사이는 한 줄로 이어 보이게 칸 배경을 띠로 깐다. 시작·끝 칸은
              // 동그라미를 유지하되 안쪽 방향으로만 띠를 이어 붙인다.
              const bandClass = endKey === null || key < startKey! || key > endKey
                ? ""
                : isStart && isEnd
                  ? ""
                  : isStart
                    ? " calendar__cell--band-from"
                    : isEnd
                      ? " calendar__cell--band-to"
                      : " calendar__cell--band";
              return (
                <button
                  key={day}
                  type="button"
                  className={`calendar__cell${on ? " calendar__cell--on" : ""}${inside ? " calendar__cell--inside" : ""}${bandClass}${i % 7 === 0 ? " calendar__cell--sun" : ""}${i % 7 === 6 ? " calendar__cell--sat" : ""}`}
                  disabled={disabled(day)}
                  onClick={() => onSelect(year, month, day)}
                >
                  <span>{day}</span>
                </button>
              );
            })()
          ),
        )}
      </div>
    </div>
  );
}

interface Parsed { y: number; m: number; d: number; h: number; min: number }

type FieldMode = "date" | "datetime" | "month";

function parseValue(value: string, mode: FieldMode): Parsed {
  const now = new Date();
  if (!value) {
    return { y: now.getFullYear(), m: now.getMonth() + 1, d: now.getDate(), h: now.getHours(), min: now.getMinutes() };
  }
  const [datePart, timePart] = value.split("T");
  // month 모드의 값은 "YYYY-MM"이라 일(d)이 없다 — 1일로 채워 같은 Parsed 구조를 쓴다.
  const [y, m, d] = datePart.split("-").map(Number);
  let h = now.getHours();
  let min = now.getMinutes();
  if (mode === "datetime" && timePart) {
    const [hh, mm] = timePart.split(":").map(Number);
    h = hh;
    min = mm;
  }
  return { y, m, d: Number.isFinite(d) ? d : 1, h, min };
}

function formatDisplay(value: string, mode: FieldMode) {
  if (!value) return null;
  const { y, m, d, h, min } = parseValue(value, mode);
  if (mode === "month") return `${y}년 ${m}월`;
  const wd = "일월화수목금토"[new Date(y, m - 1, d).getDay()];
  const datePart = `${y}년 ${m}월 ${d}일 (${wd})`;
  return mode === "date" ? datePart : `${datePart} ${pad2(h)}:${pad2(min)}`;
}

interface DateTimeFieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  /** month는 연·월만 고르고 "YYYY-MM"을 돌려준다(실손 가입시기처럼 일자가 의미 없는 값). */
  mode?: FieldMode;
  placeholder?: string;
  /** 이 날짜(포함) 이전은 고를 수 없다. YYYY-MM-DD. */
  minDate?: string;
  /** 이 날짜(포함) 이후는 고를 수 없다. YYYY-MM-DD. */
  maxDate?: string;
  /** 고른 값을 지울 수 있게 한다(선택 입력 필드용). */
  clearable?: boolean;
  /** 트리거 버튼에 쓸 아이콘. 기본은 달력. */
  icon?: string;
}

/**
 * iOS 설정/캘린더 앱의 휠 스피너를 참고한 바텀시트형 날짜·시간 선택기.
 * 모바일에서 가장 널리 쓰이는 날짜 입력 패턴이라 네이티브 date input보다 손에 익는다.
 */
export function DateTimeField({
  label, value, onChange, mode = "date", placeholder = "선택해주세요", minDate, maxDate,
  clearable = false, icon = "📅",
}: DateTimeFieldProps) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Parsed>(() => parseValue(value, mode));

  const minParsed = minDate ? parseValue(minDate, "date") : null;
  const maxParsed = maxDate ? parseValue(maxDate, "date") : null;

  function clampToRange(p: Parsed): Parsed {
    const key = (a: Parsed) => a.y * 10000 + a.m * 100 + a.d;
    let next = p;
    if (minParsed && key(next) < key(minParsed)) next = { ...minParsed, h: next.h, min: next.min };
    if (maxParsed && key(next) > key(maxParsed)) next = { ...maxParsed, h: next.h, min: next.min };
    return next;
  }

  function openSheet() {
    setDraft(clampToRange(parseValue(value, mode)));
    setOpen(true);
  }

  const yearFrom = minParsed ? minParsed.y : new Date().getFullYear() - 1;
  const yearTo = maxParsed ? maxParsed.y : new Date().getFullYear() + 4;
  const years = Array.from({ length: Math.max(1, yearTo - yearFrom + 1) }, (_, i) => yearFrom + i);

  const monthFrom = minParsed && draft.y === minParsed.y ? minParsed.m : 1;
  const monthTo = maxParsed && draft.y === maxParsed.y ? maxParsed.m : 12;
  const months = Array.from({ length: Math.max(1, monthTo - monthFrom + 1) }, (_, i) => monthFrom + i);

  const maxDay = daysInMonth(draft.y, draft.m);
  const dayFrom = minParsed && draft.y === minParsed.y && draft.m === minParsed.m ? minParsed.d : 1;
  const dayTo = maxParsed && draft.y === maxParsed.y && draft.m === maxParsed.m ? Math.min(maxParsed.d, maxDay) : maxDay;
  const days = Array.from({ length: Math.max(1, dayTo - dayFrom + 1) }, (_, i) => dayFrom + i);
  const dClamped = Math.min(Math.max(draft.d, dayFrom), dayTo);
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const minutes = Array.from({ length: 60 }, (_, i) => i);

  function confirm() {
    if (mode === "month") {
      onChange(`${draft.y}-${pad2(draft.m)}`);
      setOpen(false);
      return;
    }
    const datePart = `${draft.y}-${pad2(draft.m)}-${pad2(dClamped)}`;
    onChange(mode === "date" ? datePart : `${datePart}T${pad2(draft.h)}:${pad2(draft.min)}`);
    setOpen(false);
  }

  const display = formatDisplay(value, mode);

  return (
    <div className="field-block">
      <span className="field-block__label">{label}</span>
      <button type="button" className="field-trigger" onClick={openSheet}>
        <span className={display ? "" : "field-trigger__placeholder"}>{display ?? placeholder}</span>
        {clearable && display ? (
          <span
            role="button"
            tabIndex={0}
            className="field-trigger__clear"
            aria-label={`${label} 지우기`}
            onClick={(e) => { e.stopPropagation(); onChange(""); }}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") { e.preventDefault(); e.stopPropagation(); onChange(""); }
            }}
          >
            ×
          </span>
        ) : (
          <span className="field-trigger__icon">{icon}</span>
        )}
      </button>

      {open && (
        <div className="sheet-overlay" onClick={() => setOpen(false)}>
          <div className="sheet" onClick={(e) => e.stopPropagation()}>
            <div className="sheet__handle" />
            <div className="sheet__title">{label}</div>
            <div className="sheet__value">
              {mode === "month"
                ? `${draft.y}년 ${draft.m}월`
                : `${draft.y}년 ${draft.m}월 ${dClamped}일${mode === "datetime" ? ` ${pad2(draft.h)}:${pad2(draft.min)}` : ""}`}
            </div>
            {/* 달력이 주인공이고, 아래 휠은 연·월을 멀리 건너뛸 때 쓰는 보조 수단이다.
                연·월만 고르는 month 모드에는 날짜 격자가 의미가 없어서 달력을 두지 않는다. */}
            {mode !== "month" && (
              <MonthCalendar
                year={draft.y}
                month={draft.m}
                selectedDay={dClamped}
                min={minParsed}
                max={maxParsed}
                onSelect={(y, m, d) => setDraft((p) => ({ ...p, y, m, d }))}
                onMoveMonth={(delta) => {
                  setDraft((p) => {
                    const moved = new Date(p.y, p.m - 1 + delta, 1);
                    const y = moved.getFullYear();
                    const m = moved.getMonth() + 1;
                    // 31일에서 2월로 넘어가는 것처럼 그 달에 없는 날짜가 되면 말일로 당긴다.
                    const d = Math.min(p.d, daysInMonth(y, m));
                    return clampToRange({ ...p, y, m, d });
                  });
                }}
              />
            )}
            <div className="wheel-row">
              <div className="wheel-highlight" />
              <WheelCol
                items={years.map(String)}
                index={Math.max(0, years.indexOf(draft.y))}
                onIndex={(i) => setDraft((p) => clampToRange({ ...p, y: years[i] }))}
              />
              <WheelCol
                items={months.map((mm) => `${mm}월`)}
                index={Math.max(0, months.indexOf(draft.m))}
                onIndex={(i) => setDraft((p) => clampToRange({ ...p, m: months[i] }))}
              />
              {mode !== "month" && (
                <WheelCol
                  items={days.map((dd) => `${dd}일`)}
                  index={Math.max(0, days.indexOf(dClamped))}
                  onIndex={(i) => setDraft((p) => clampToRange({ ...p, d: days[i] }))}
                />
              )}
              {mode === "datetime" && (
                <>
                  <WheelCol
                    items={hours.map(pad2)}
                    index={draft.h}
                    onIndex={(i) => setDraft((p) => ({ ...p, h: hours[i] }))}
                  />
                  <WheelCol
                    items={minutes.map(pad2)}
                    index={draft.min}
                    onIndex={(i) => setDraft((p) => ({ ...p, min: minutes[i] }))}
                  />
                </>
              )}
            </div>
            <button type="button" className="btn-primary sheet__confirm" style={{ width: "100%" }} onClick={confirm}>
              확인
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* 여행 기간 — 출발일과 도착일을 달력 하나에서 이어서 고른다.           */
/* ------------------------------------------------------------------ */

function toParsed(value: string): Parsed | null {
  if (!value) return null;
  return parseValue(value, "date");
}

function fmtDate(p: Parsed) {
  return `${p.y}-${pad2(p.m)}-${pad2(p.d)}`;
}

function keyOf(p: Parsed) {
  return dayKey(p.y, p.m, p.d);
}

function dayCountBetween(a: Parsed, b: Parsed) {
  const ms = new Date(b.y, b.m - 1, b.d).getTime() - new Date(a.y, a.m - 1, a.d).getTime();
  return Math.round(ms / 86400000) + 1;
}

interface DateRangeFieldProps {
  label?: string;
  /** YYYY-MM-DD. 둘 다 비어 있으면 아직 안 고른 상태다. */
  start: string;
  end: string;
  onChange: (start: string, end: string) => void;
  /** 이 날짜(포함) 이전은 고를 수 없다. */
  minDate?: string;
  placeholder?: string;
}

/**
 * 출발일 → 도착일을 달력 하나에서 이어서 고르는 기간 선택기.
 *
 * 예전에는 시작일·종료일 달력이 각각 따로 열렸다. 두 번 열고 두 번 확인해야 했고,
 * 무엇보다 "며칠짜리 여행인지"가 화면 어디에도 보이지 않았다. 시중 예약 앱들이 그렇듯
 * 달력 하나에서 두 번 눌러 기간을 칠하는 방식으로 바꾼다.
 *
 * 단계는 둘이다.
 *   1. 출발일 — 달력에서 날짜를 누르거나, 아래 휠로 맞춘 뒤 버튼을 누르면 다음 단계로 간다.
 *   2. 도착일 — 달력에 출발일이 칠해진 채로 도착일을 고른다. 확인을 누르면 닫힌다.
 *
 * 이미 고른 출발일을 다시 누르면 그 선택이 취소되고 1단계로 돌아간다 — 잘못 골랐을 때
 * 창을 닫았다 다시 열지 않아도 되게.
 */
export function DateRangeField({
  label = "여행 기간", start, end, onChange, minDate, placeholder = "여행 기간을 선택하세요",
}: DateRangeFieldProps) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<"start" | "end">("start");
  const [rangeStart, setRangeStart] = useState<Parsed | null>(null);
  const [rangeEnd, setRangeEnd] = useState<Parsed | null>(null);
  const [draft, setDraft] = useState<Parsed>(() => parseValue(start, "date"));

  const minParsed = minDate ? parseValue(minDate, "date") : null;

  function openSheet() {
    const s0 = toParsed(start);
    const e0 = toParsed(end);
    setRangeStart(s0);
    setRangeEnd(e0);
    setStep(s0 ? "end" : "start");
    setDraft(s0 ?? parseValue("", "date"));
    setOpen(true);
  }

  const years = Array.from({ length: 7 }, (_, i) => draft.y - 3 + i);
  const months = Array.from({ length: 12 }, (_, i) => i + 1);
  const days = Array.from({ length: daysInMonth(draft.y, draft.m) }, (_, i) => i + 1);
  const dClamped = Math.min(draft.d, days.length);

  function pick(y: number, m: number, d: number) {
    const picked: Parsed = { y, m, d, h: draft.h, min: draft.min };
    setDraft(picked);
    if (step === "start" || !rangeStart) {
      setRangeStart(picked);
      setRangeEnd(null);
      setStep("end");
      return;
    }
    const k = keyOf(picked);
    const sk = keyOf(rangeStart);
    if (k === sk) {
      // 고른 출발일을 다시 눌렀다 = 취소하고 처음부터 다시 고른다.
      setRangeStart(null);
      setRangeEnd(null);
      setStep("start");
      return;
    }
    if (k < sk) {
      // 출발일보다 앞을 눌렀으면 그게 새 출발일이다.
      setRangeStart(picked);
      setRangeEnd(null);
      return;
    }
    setRangeEnd(picked);
  }

  // 휠로 맞춰 둔 날짜도 "아직 확정 안 한 도착일"로 미리 칠해 보여준다.
  const pendingEnd =
    rangeEnd ?? (rangeStart && keyOf({ ...draft, d: dClamped }) > keyOf(rangeStart)
      ? { ...draft, d: dClamped }
      : null);
  const canConfirm = step === "start" ? true : !!(rangeStart && pendingEnd);

  function confirm() {
    if (step === "start") {
      const picked: Parsed = { ...draft, d: dClamped };
      setRangeStart(picked);
      setRangeEnd(null);
      setStep("end");
      return;
    }
    if (!rangeStart || !pendingEnd) return;
    onChange(fmtDate(rangeStart), fmtDate(pendingEnd));
    setOpen(false);
  }

  const s0 = toParsed(start);
  const e0 = toParsed(end);
  const display = s0 && e0
    ? `${s0.y}년 ${s0.m}월 ${s0.d}일 → ${e0.m}월 ${e0.d}일 · ${dayCountBetween(s0, e0)}일`
    : null;

  return (
    <div className="field-block">
      <span className="field-block__label">{label}</span>
      <button type="button" className="field-trigger" onClick={openSheet}>
        <span className={display ? "" : "field-trigger__placeholder"}>{display ?? placeholder}</span>
        <span className="field-trigger__icon">📅</span>
      </button>

      {open && (
        <div className="sheet-overlay sheet-overlay--center" onClick={() => setOpen(false)}>
          <div className="sheet sheet--range" onClick={(e) => e.stopPropagation()}>
            <button type="button" className="sheet__close" aria-label="닫기" onClick={() => setOpen(false)}>
              ✕
            </button>
            {/* 넓은 화면에서는 달력을 왼쪽에 크게 두고, 단계칸·휠·확인을 오른쪽에 모은다 —
                세로로만 쌓으면 달력만으로 화면이 차서 확인 버튼이 밖으로 밀려난다. */}
            <div className="range-layout">
            <div className="range-layout__cal">
            <MonthCalendar
              year={draft.y}
              month={draft.m}
              selectedDay={dClamped}
              rangeStart={rangeStart}
              rangeEnd={pendingEnd}
              min={step === "end" && rangeStart ? rangeStart : minParsed}
              max={null}
              onSelect={pick}
              onMoveMonth={(delta) => {
                setDraft((p) => {
                  const moved = new Date(p.y, p.m - 1 + delta, 1);
                  const y = moved.getFullYear();
                  const m = moved.getMonth() + 1;
                  return { ...p, y, m, d: Math.min(p.d, daysInMonth(y, m)) };
                });
              }}
            />
            </div>

            <div className="range-layout__pick">
            <div className="wheel-row wheel-row--compact">
              <div className="wheel-highlight" />
              <WheelCol
                items={years.map(String)}
                index={Math.max(0, years.indexOf(draft.y))}
                onIndex={(i) => setDraft((p) => ({ ...p, y: years[i] }))}
              />
              <WheelCol
                items={months.map((mm) => `${mm}월`)}
                index={Math.max(0, months.indexOf(draft.m))}
                onIndex={(i) => setDraft((p) => ({ ...p, m: months[i] }))}
              />
              <WheelCol
                items={days.map((dd) => `${dd}일`)}
                index={Math.max(0, days.indexOf(dClamped))}
                onIndex={(i) => setDraft((p) => ({ ...p, d: days[i] }))}
              />
            </div>

            <button
              type="button"
              className="btn-primary sheet__confirm"
              style={{ width: "100%" }}
              disabled={!canConfirm}
              onClick={confirm}
            >
              {step === "start" ? "이 날 출발할게요" : "확인"}
            </button>
            </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
