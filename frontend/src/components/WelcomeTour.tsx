import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion, type MotionProps } from "framer-motion";
import { useNavigate } from "react-router-dom";

const LS_TOUR_SEEN = "travel_ai_tour_seen";

/** 한 장면이 흐르는 시간. 손끝이 두 번 눌리고 결과가 자리를 잡을 만큼은 되어야 한다. */
const SCENE_MS = 6000;

/** 이 브라우저에서 안내를 이미 닫아 두었는지. */
export function hasSeenTour(): boolean {
  try {
    return localStorage.getItem(LS_TOUR_SEEN) === "1";
  } catch {
    // 사생활 보호 모드 등에서 localStorage 접근 자체가 막히는 브라우저가 있다.
    // 그때는 "본 적 없음"으로 두고 안내를 띄운다 — 못 보는 것보다 낫다.
    return false;
  }
}

/**
 * 손끝이 화면을 눌러 가는 모습을 그대로 보여주는 첫 진입 안내.
 *
 * 처음에는 다섯 장에 걸쳐 기능을 글로 설명했다. 그런데 처음 온 사람이 앱을 열자마자
 * 읽어야 할 문단을 받으면, 읽지 않고 닫는다. 설명을 줄이는 대신 보여주기로 바꿨다 —
 * 앱의 실제 화면을 축소해 두고, 손끝이 눌러서 다음 화면으로 넘어가는 과정을 재생한다.
 * 글은 장면마다 한 줄만 남긴다.
 *
 * 마지막 장면이 이 안내의 핵심이다. 약관 원문 위로 노란 형광펜이 좌에서 우로 그어진다 —
 * 서비스 이름(BohumPen)과 이 프로젝트가 지키는 원칙("근거 없는 결과를 내지 않는다")이
 * 그 동작 하나에 같이 담긴다. 나머지 장면은 그 한 획을 향해 조용히 깔아 주는 역할만 한다.
 */
export function WelcomeTour({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const [scene, setScene] = useState(0);
  const [dontShowAgain, setDontShowAgain] = useState(true);
  // 사람이 점이나 화살표를 눌렀다 = 자기 속도로 보겠다는 뜻이다. 그 뒤로는 안 넘긴다.
  const [paused, setPaused] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);

  // 움직임을 줄이도록 설정한 사람에게는 재생하지 않고 각 장면의 끝 모습만 보여준다.
  const reduceMotion =
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const playing = !paused && !reduceMotion;

  const close = useCallback(() => {
    if (dontShowAgain) {
      try {
        localStorage.setItem(LS_TOUR_SEEN, "1");
      } catch {
        // 저장에 실패하면 다음에 또 뜬다. 안내가 한 번 더 보이는 것뿐이라 그냥 둔다.
      }
    }
    onClose();
  }, [dontShowAgain, onClose]);

  // 마지막 장면에서는 멈춘다 — 저 혼자 닫히면 형광펜이 그어지는 장면을 놓친다.
  useEffect(() => {
    if (!playing || scene >= SCENES.length - 1) return;
    const timer = window.setTimeout(() => setScene((i) => i + 1), SCENE_MS);
    return () => window.clearTimeout(timer);
  }, [scene, playing]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
      if (e.key === "ArrowRight") goTo(Math.min(scene + 1, SCENES.length - 1));
      if (e.key === "ArrowLeft") goTo(Math.max(scene - 1, 0));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  // 열리면 안내 자체로 초점을 옮긴다 — 키보드·스크린리더 사용자가 뒤 화면을 더듬지 않게.
  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  function goTo(next: number) {
    setPaused(true);
    setScene(next);
  }

  const current = SCENES[scene];
  const isLast = scene === SCENES.length - 1;

  return (
    <motion.div
      className="tour-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={close}
    >
      <motion.div
        className="tour-card"
        role="dialog"
        aria-modal="true"
        aria-label="여행자보험 AI 둘러보기"
        tabIndex={-1}
        ref={dialogRef}
        initial={{ opacity: 0, y: 26, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 26, scale: 0.96 }}
        transition={{ type: "spring", stiffness: 320, damping: 28 }}
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="tour-card__close" onClick={close} aria-label="안내 닫기">
          ✕
        </button>

        {/* 앱을 축소해 놓은 화면. 손끝이 여기를 눌러 가며 다음 화면으로 넘어간다. */}
        <div className="tour-screen" aria-hidden="true">
          <AnimatePresence mode="wait">
            <motion.div
              key={scene}
              className="tour-screen__inner"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
            >
              {current.render(playing)}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* 화면이 무엇을 하고 있는지 한 줄. 여기가 길어지면 다시 읽기 싫은 안내가 된다. */}
        <div className="tour-caption">
          <AnimatePresence mode="wait">
            <motion.p
              key={scene}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.28 }}
            >
              {current.caption}
            </motion.p>
          </AnimatePresence>
        </div>

        <div className="tour-nav">
          <button
            type="button"
            className="tour-nav__arrow"
            onClick={() => goTo(Math.max(scene - 1, 0))}
            disabled={scene === 0}
            aria-label="이전"
          >
            ‹
          </button>
          {SCENES.map((s, i) => (
            <button
              key={s.caption}
              type="button"
              className={
                "tour-nav__dot" +
                (i === scene ? " tour-nav__dot--on" : "") +
                // 시간이 차오르지 않는 장면(마지막 장면, 수동으로 넘긴 뒤)에서는
                // 막대를 가득 채워 지금 어디인지 보이게 한다.
                (i === scene && (!playing || isLast) ? " tour-nav__dot--full" : "")
              }
              onClick={() => goTo(i)}
              aria-label={`${i + 1}번째 장면`}
              aria-current={i === scene}
            >
              {/* 재생 중인 점만 안에서 시간이 차오른다 — 다음 장면까지 얼마나 남았는지 */}
              {i === scene && playing && !isLast && (
                <motion.span
                  key={`fill-${scene}`}
                  className="tour-nav__dot-fill"
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ duration: SCENE_MS / 1000, ease: "linear" }}
                />
              )}
            </button>
          ))}
          <button
            type="button"
            className="tour-nav__arrow"
            onClick={() => goTo(Math.min(scene + 1, SCENES.length - 1))}
            disabled={isLast}
            aria-label="다음"
          >
            ›
          </button>
        </div>

        {isLast && (
          <motion.button
            type="button"
            className="tour-card__cta"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            onClick={() => {
              close();
              navigate("/trip");
            }}
          >
            내 여행부터 준비하기
          </motion.button>
        )}

        <label className="tour-card__again">
          <input
            type="checkbox"
            checked={dontShowAgain}
            onChange={(e) => setDontShowAgain(e.target.checked)}
          />
          다시 보지 않기
        </label>
      </motion.div>
    </motion.div>
  );
}

/* --------------------------------------------------------------------------
 * 장면들
 *
 * 각 장면은 6초 안에 "손끝이 누른다 → 화면이 바뀐다"를 한 번씩 보여준다. playing이 false면
 * (움직임 줄이기 설정) 애니메이션 없이 끝 모습만 그린다.
 * ----------------------------------------------------------------------- */

/** 화면을 누르는 손끝. 좌표는 tour-screen 안쪽 기준(px). */
function Tap({ points, playing }: { points: [number, number][]; playing: boolean }) {
  if (!playing) return null;
  // 누를 곳으로 이동 → 눌림(작아졌다 커짐) → 다음 곳으로. 마지막엔 조용히 사라진다.
  const xs = points.flatMap(([x]) => [x, x, x]);
  const ys = points.flatMap(([, y]) => [y, y, y]);
  const scales = points.flatMap(() => [1, 0.68, 1]);
  const step = 1 / (xs.length - 1);
  const times = xs.map((_, i) => Math.min(1, i * step));
  return (
    <motion.span
      className="tour-tap"
      initial={{ x: xs[0], y: ys[0], opacity: 0 }}
      animate={{ x: xs, y: ys, scale: scales, opacity: [0, 1, 1, 1, 1, 1, 1, 0.9, 0] }}
      transition={{ duration: (SCENE_MS / 1000) * 0.72, times, ease: "easeInOut" }}
    />
  );
}

/** 눌린 자리에서 퍼지는 물결. 손끝과 같은 시점에 맞춰 delay로 띄운다. */
function Ripple({ x, y, delay, playing }: { x: number; y: number; delay: number; playing: boolean }) {
  if (!playing) return null;
  return (
    <motion.span
      className="tour-ripple"
      style={{ left: x, top: y }}
      initial={{ scale: 0.2, opacity: 0 }}
      animate={{ scale: [0.2, 1.6], opacity: [0.55, 0] }}
      transition={{ duration: 0.7, delay, ease: "easeOut" }}
    />
  );
}

/** 앞 화면이 물러나고 뒤 화면이 들어오는 전환. t는 전체 장면에서 바뀌는 시점(0~1). */
function panelMotion(playing: boolean, t: number, direction: "out" | "in"): MotionProps {
  if (!playing) {
    return direction === "out"
      ? { initial: { opacity: 0 }, animate: { opacity: 0 } }
      : { initial: { opacity: 1 }, animate: { opacity: 1, x: 0 } };
  }
  const dur = SCENE_MS / 1000;
  return direction === "out"
    ? {
        initial: { opacity: 1, x: 0 },
        animate: { opacity: [1, 1, 0], x: [0, 0, -26] },
        transition: { duration: dur, times: [0, t, t + 0.09], ease: "easeInOut" },
      }
    : {
        initial: { opacity: 0, x: 26 },
        animate: { opacity: [0, 0, 1], x: [26, 26, 0] },
        transition: { duration: dur, times: [0, t + 0.02, t + 0.13], ease: "easeOut" },
      };
}

interface Scene {
  caption: string;
  render: (playing: boolean) => ReactNode;
}

const SCENES: Scene[] = [
  {
    caption: "여행 정보만 넣으면 7개사를 비교해요",
    render: (playing) => (
      <>
        <motion.div className="tour-panel" {...panelMotion(playing, 0.42, "out")}>
          <p className="tour-mini__eyebrow">STEP 1 · 목적지</p>
          <p className="tour-mini__ask">어디로 떠나시나요?</p>
          <div className="tour-mini__field">
            {playing ? (
              <motion.span
                initial={{ opacity: 1 }}
                animate={{ opacity: [1, 1, 0] }}
                transition={{ duration: 1, times: [0, 0.6, 1], delay: 1.2 }}
              >
                국가를 선택하세요
              </motion.span>
            ) : null}
            {playing && (
              <motion.span
                className="tour-mini__value"
                initial={{ opacity: 0 }}
                animate={{ opacity: [0, 0, 1] }}
                transition={{ duration: 1, times: [0, 0.6, 1], delay: 1.2 }}
              >
                일본
              </motion.span>
            )}
            {!playing && <span className="tour-mini__value">일본</span>}
            <span className="tour-mini__chev">⌄</span>
          </div>
          <div className="tour-mini__btn">다음</div>
          <Tap points={[[124, 89], [124, 137]]} playing={playing} />
          <Ripple x={124} y={89} delay={1.3} playing={playing} />
          <Ripple x={124} y={137} delay={2.4} playing={playing} />
        </motion.div>

        <motion.div className="tour-panel" {...panelMotion(playing, 0.42, "in")}>
          <p className="tour-mini__eyebrow">균형형 기준 · 표준 등급</p>
          {RANKING.map((r, i) => (
            <motion.div
              key={r.name}
              className="tour-rank"
              initial={playing ? { opacity: 0, y: 10 } : false}
              animate={playing ? { opacity: [0, 0, 1], y: [10, 10, 0] } : {}}
              transition={{ duration: SCENE_MS / 1000, times: [0, 0.5 + i * 0.04, 0.6 + i * 0.04] }}
            >
              <span className="tour-rank__no">{i + 1}</span>
              <span className="tour-rank__name">{r.name}</span>
              <span className="tour-rank__won">{r.won}</span>
              <span className="tour-rank__bar">
                <motion.span
                  style={{ width: `${r.score}%` }}
                  initial={playing ? { scaleX: 0 } : false}
                  animate={playing ? { scaleX: [0, 0, 1] } : {}}
                  transition={{ duration: SCENE_MS / 1000, times: [0, 0.58 + i * 0.04, 0.78 + i * 0.04] }}
                />
              </span>
            </motion.div>
          ))}
        </motion.div>
      </>
    ),
  },
  {
    caption: "사고는 한 문장이면 충분해요",
    render: (playing) => (
      <>
        <motion.div className="tour-panel" {...panelMotion(playing, 0.46, "out")}>
          <p className="tour-mini__eyebrow">STEP 2 · 사고 내용</p>
          <p className="tour-mini__ask">무슨 일이 있었나요?</p>
          <div className="tour-mini__note">
            {playing ? (
              <motion.span
                className="tour-type"
                initial={{ width: 0 }}
                animate={{ width: ["0px", "0px", "168px"] }}
                transition={{ duration: SCENE_MS / 1000, times: [0, 0.06, 0.36], ease: "linear" }}
              >
                길에서 넘어져 발목을 다쳤어요
              </motion.span>
            ) : (
              <span className="tour-type tour-type--done">길에서 넘어져 발목을 다쳤어요</span>
            )}
            {playing && <span className="tour-caret" />}
          </div>
          <div className="tour-mini__btn">사고 분석 요청</div>
          <Tap points={[[124, 161]]} playing={playing} />
          <Ripple x={124} y={161} delay={2.6} playing={playing} />
        </motion.div>

        <motion.div className="tour-panel" {...panelMotion(playing, 0.46, "in")}>
          <p className="tour-mini__eyebrow">상해 · 해외상해치료</p>
          <div className="tour-result">
            <span className="tour-result__tag">받을 수 있어요</span>
            <p className="tour-result__title">해외여행중 상해치료비</p>
            <p className="tour-result__sub">제4조 · 실제 부담한 의료비</p>
          </div>
          <p className="tour-mini__eyebrow">필요한 서류</p>
          <div className="tour-chips">
            {DOCS.map((d, i) => (
              <motion.span
                key={d}
                className="tour-chip"
                initial={playing ? { opacity: 0, scale: 0.9 } : false}
                animate={playing ? { opacity: [0, 0, 1], scale: [0.9, 0.9, 1] } : {}}
                transition={{ duration: SCENE_MS / 1000, times: [0, 0.6 + i * 0.05, 0.7 + i * 0.05] }}
              >
                {d}
              </motion.span>
            ))}
          </div>
        </motion.div>
      </>
    ),
  },
  {
    // 이 장면이 안내의 핵심이라 화면을 갈아끼우지 않는다. 보고 있던 그 약관 원문 위에
    // 형광펜이 그대로 그어져야, "근거를 원문에서 짚는다"는 말이 눈으로 확인된다.
    caption: "왜 그런지 약관 원문에서 짚어줘요",
    render: (playing) => (
      <div className="tour-panel">
        <p className="tour-mini__eyebrow">카카오페이손해보험 · 제4조</p>
        <div className="tour-clause">
          <p>
            회사는 피보험자가 보험기간 중에 발생한
            <span className="tour-clause__target">
              {playing && (
                <motion.span
                  className="tour-clause__ink"
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ duration: 0.85, delay: 2.7, ease: "easeInOut" }}
                />
              )}
              {!playing && <span className="tour-clause__ink tour-clause__ink--done" />}
              <span className="tour-clause__word">급격하고 우연한 외래의 사고</span>
            </span>
            로 상해를 입은 경우
            <span className="tour-clause__target">
              {playing && (
                <motion.span
                  className="tour-clause__ink"
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ duration: 0.7, delay: 3.5, ease: "easeInOut" }}
                />
              )}
              {!playing && <span className="tour-clause__ink tour-clause__ink--done" />}
              <span className="tour-clause__word">보험금을 지급합니다</span>
            </span>
            .
          </p>
        </div>
        <div className="tour-mini__btn tour-mini__btn--ghost">근거 보기</div>
        <Tap points={[[124, 200]]} playing={playing} />
        <Ripple x={124} y={200} delay={2.4} playing={playing} />
        <motion.p
          className="tour-stamp"
          initial={playing ? { opacity: 0, y: 6 } : false}
          animate={playing ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 4.4, duration: 0.4 }}
        >
          원문 대조 완료
        </motion.p>
      </div>
    ),
  },
];

const RANKING = [
  { name: "카카오페이손보", won: "3,863원", score: 92 },
  { name: "신한EZ손보", won: "4,610원", score: 84 },
  { name: "메리츠화재", won: "4,945원", score: 79 },
];

const DOCS = ["진료비 영수증", "진단서", "신분증"];
