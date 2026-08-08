import { useCallback, useEffect, useRef, useState } from "react";

/**
 * 프레임(.app-shell) 안쪽에 얹는 스크롤 막대.
 *
 * 네이티브 막대는 스크롤 영역의 높이를 전부 쓴다. 이 앱의 프레임은 모서리가 32px로 둥글어서
 * 막대 위아래 끝이 그 곡선과 겹쳐 잘려 보였다(= 튀어나온 것처럼 보이는 원인). 막대 길이를
 * 줄이는 CSS는 없으므로, 네이티브 막대는 감추고 프레임 높이의 2/3만 차지하는 막대를 가운데에
 * 직접 그린다. 곡선 구간을 아예 지나가지 않으니 겹칠 일이 없다.
 *
 * 스크롤 자체는 손대지 않는다 — 휠·터치·키보드는 브라우저 기본 동작 그대로고, 이 컴포넌트는
 * 위치를 비추고 드래그를 받는 표시기일 뿐이다.
 */

/** 막대가 차지하는 세로 비율. 위아래로 1/16씩 비워 둥근 모서리를 피한다. */
const TRACK_RATIO = 7 / 8;
const MIN_THUMB = 36;

export function FrameScrollbar({ targetRef }: { targetRef: React.RefObject<HTMLElement | null> }) {
  const [metrics, setMetrics] = useState({ visible: false, top: 0, height: 0 });
  const dragRef = useRef<{ startY: number; startScroll: number; range: number; travel: number } | null>(null);
  const frameRef = useRef<number | null>(null);

  const measure = useCallback(() => {
    const el = targetRef.current;
    if (!el) return;
    const { scrollHeight, clientHeight, scrollTop } = el;
    const overflow = scrollHeight - clientHeight;
    if (overflow <= 1 || clientHeight === 0) {
      setMetrics((m) => (m.visible ? { ...m, visible: false } : m));
      return;
    }
    const trackHeight = clientHeight * TRACK_RATIO;
    const thumbHeight = Math.max(MIN_THUMB, trackHeight * (clientHeight / scrollHeight));
    const travel = trackHeight - thumbHeight;
    const top = travel > 0 ? (scrollTop / overflow) * travel : 0;
    setMetrics({ visible: true, top, height: thumbHeight });
  }, [targetRef]);

  /** 스크롤은 매 프레임 들어오므로 rAF로 한 번만 계산한다. */
  const schedule = useCallback(() => {
    if (frameRef.current !== null) return;
    frameRef.current = requestAnimationFrame(() => {
      frameRef.current = null;
      measure();
    });
  }, [measure]);

  useEffect(() => {
    const el = targetRef.current;
    if (!el) return;

    measure();
    el.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);

    // 화면(라우트)이 바뀌면 내용 높이가 달라진다. 스크롤 컨테이너의 ResizeObserver는 내용이
    // 늘어난 것까지는 알려주지 않으므로 자식 변화를 함께 지켜본다.
    const resizeObserver = new ResizeObserver(schedule);
    resizeObserver.observe(el);
    const mutationObserver = new MutationObserver(schedule);
    mutationObserver.observe(el, { childList: true, subtree: true });

    return () => {
      el.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      resizeObserver.disconnect();
      mutationObserver.disconnect();
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
  }, [targetRef, measure, schedule]);

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    const el = targetRef.current;
    if (!el) return;
    const trackHeight = el.clientHeight * TRACK_RATIO;
    dragRef.current = {
      startY: e.clientY,
      startScroll: el.scrollTop,
      range: el.scrollHeight - el.clientHeight,
      travel: trackHeight - metrics.height,
    };
    e.currentTarget.setPointerCapture(e.pointerId);
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    const el = targetRef.current;
    if (!drag || !el || drag.travel <= 0) return;
    const moved = e.clientY - drag.startY;
    el.scrollTop = drag.startScroll + (moved / drag.travel) * drag.range;
  }

  function endDrag(e: React.PointerEvent<HTMLDivElement>) {
    dragRef.current = null;
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
  }

  if (!metrics.visible) return null;

  return (
    <div className="frame-scrollbar" aria-hidden>
      <div
        className="frame-scrollbar__thumb"
        style={{ transform: `translateY(${metrics.top}px)`, height: metrics.height }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
      />
    </div>
  );
}
