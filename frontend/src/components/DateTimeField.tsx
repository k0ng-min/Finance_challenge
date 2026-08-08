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
