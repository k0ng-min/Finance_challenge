import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion, type MotionProps, type TargetAndTransition } from "framer-motion";
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
  // 사람이 점이나 화살표를 눌렀다 = 자기 속도로 보겠다는 뜻이다. 그 뒤로는 안 넘긴다.
  const [paused, setPaused] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);

  // 움직임을 줄이도록 설정한 사람에게는 재생하지 않고 각 장면의 끝 모습만 보여준다.
  const reduceMotion =
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const playing = !paused && !reduceMotion;

  // 한 번 닫으면 다시 띄우지 않는다 — 처음 온 사람에게만 필요한 안내다.
  const close = useCallback(() => {
    try {
      localStorage.setItem(LS_TOUR_SEEN, "1");
    } catch {
      // 저장에 실패하면 다음에 또 뜬다. 안내가 한 번 더 보이는 것뿐이라 그냥 둔다.
    }
    onClose();
  }, [onClose]);

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
  // preventScroll이 없으면 브라우저가 카드를 화면 안으로 끌어오느라 감싼 층을 스크롤한다.
  // 창이 낮아 카드가 다 안 들어가는 경우 그 스크롤이 닫기 단추를 화면 위로 밀어냈다.
  useEffect(() => {
    dialogRef.current?.focus({ preventScroll: true });
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

        {/* 여행 전 → 사고 후 → 근거 확인. 이 안내가 보여주는 것이 기능 세 개가 아니라
            하나로 이어진 흐름이라는 걸 먼저 알린다. 지금 장면 다음 선이 차오르는 것이 곧
            다음 장면까지 남은 시간이라, 진행 막대를 따로 둘 필요가 없다. */}
        <nav className="tour-rail" aria-label="둘러보기 단계">
          {SCENES.map((s, i) => (
            <div className="tour-rail__item" key={s.stage}>
              {i > 0 && (
                <span className="tour-rail__line">
                  <motion.span
                    key={`line-${i}-${scene}-${playing}`}
                    className="tour-rail__line-fill"
                    initial={{ scaleX: i <= scene ? 1 : 0 }}
                    animate={{ scaleX: i <= scene || (i === scene + 1 && playing) ? 1 : 0 }}
                    transition={
                      i === scene + 1 && playing
                        ? { duration: SCENE_MS / 1000, ease: "linear" }
                        : { duration: 0.3 }
                    }
                  />
                </span>
              )}
              <button
                type="button"
                className={
                  "tour-rail__step" +
                  (i === scene ? " tour-rail__step--on" : "") +
                  (i < scene ? " tour-rail__step--done" : "")
                }
                onClick={() => goTo(i)}
                aria-current={i === scene}
              >
                {s.stage}
              </button>
            </div>
          ))}
        </nav>

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
      </motion.div>
    </motion.div>
  );
}

/* --------------------------------------------------------------------------
 * 장면들
 *
 * 시간은 전부 "장면이 시작하고 몇 초"로 적는다. 예전에는 손끝의 이동을 전체 길이에 균등
 * 분배했는데, 그러면 누르는 시점이 화면이 바뀌는 시점과 어긋난다 — 실제로 장면 1에서
 * 손끝이 3.5초에 「다음」을 눌렀고 화면은 2.5초에 이미 넘어가 있었다(없는 버튼을 누르는
 * 모습이었다). 아래 상수들이 그 순서를 한자리에서 정한다.
 *
 * playing이 false면(움직임 줄이기 설정, 또는 사람이 직접 넘긴 뒤) 재생하지 않고 각 장면의
 * 끝 모습만 그린다.
 * ----------------------------------------------------------------------- */

/** 한 번의 터치. at은 손끝이 실제로 눌리는 시각(초). */
interface Press {
  x: number;
  y: number;
  at: number;
}

/** 손끝이 자리를 옮기는 데 걸리는 시간과, 눌렀다 떼는 데 걸리는 시간. */
/** 축소 화면의 높이(app.css의 .tour-screen과 같아야 한다). 커서가 화면 밖에서
 * 나타나지 않도록 시작점을 정하는 데 쓴다. */
const SCREEN_H = 240;

const MOVE_S = 0.5;
const PRESS_S = 0.16;

/**
 * 화면을 누르는 손끝. 좌표는 tour-screen 안쪽 기준(px).
 *
 * 키프레임 배열(x·y·scale·opacity·times)의 길이는 반드시 서로 같아야 한다. 예전에는
 * opacity만 9개였고 나머지는 3~6개라, 손끝이 엉뚱하게 움직였다. 아래처럼 한 번에 같이
 * 쌓으면 그런 어긋남이 생길 수 없다.
 */
function Tap({ presses, playing }: { presses: Press[]; playing: boolean }) {
  if (!playing || presses.length === 0) return null;

  const D = SCENE_MS / 1000;
  const t: number[] = [];
  const x: number[] = [];
  const y: number[] = [];
  const s: number[] = [];
  const o: number[] = [];
  const at = (time: number, px: number, py: number, scale: number, opacity: number) => {
    t.push(Math.min(1, Math.max(0, time / D)));
    x.push(px);
    y.push(py);
    s.push(scale);
    o.push(opacity);
  };

  const first = presses[0];
  // 커서는 누를 자리 바깥에서 다가온다 — 제자리에서 갑자기 나타나면 어디서 왔는지 모른다.
  // 다만 아래쪽 버튼을 누를 때 아래에서 올라오게 두면 시작점이 화면 밖이라, 잘린 채로
  // 나타났다. 대상이 화면 아래쪽이면 위에서 비스듬히 다가온다.
  const low = first.y > SCREEN_H * 0.6;
  const startX = low ? first.x - 44 : first.x;
  const startY = low ? first.y - 40 : first.y + 34;
  // 나타나는 시점을 움직이기 직전으로 당긴다. 예전에는 투명도가 0초부터 선형으로 올라가서,
  // 손끝이 할 일 없이 버튼 아래에 1.8초쯤 떠 있다가 그제야 움직였다.
  const appear = Math.max(0.3, first.at - MOVE_S - 0.15);
  at(0, startX, startY, 1, 0);
  at(Math.max(0.05, appear - 0.25), startX, startY, 1, 0);
  at(appear, startX, startY, 1, 1);

  presses.forEach((p) => {
    at(p.at - 0.12, p.x, p.y, 1, 1); // 도착
    at(p.at, p.x, p.y, 0.72, 1); // 눌림
    at(p.at + PRESS_S, p.x, p.y, 1, 1); // 뗌
  });

  const last = presses[presses.length - 1];
  at(last.at + 0.55, last.x, last.y, 1, 0);

  return (
    <motion.span
      className="tour-cursor"
      initial={{ x: x[0], y: y[0], scale: 1, opacity: 0 }}
      animate={{ x, y, scale: s, opacity: o }}
      transition={{ duration: D, times: t, ease: "easeInOut" }}
    >
      {/* 둥근 포인터. 앱이 쓰는 파랑에 흰 테두리를 둘러, 어떤 배경 위에서도 끝이 어디를
          가리키는지 보이게 한다. 끝점(3.4, 2.2)이 누르는 좌표에 오도록 CSS에서 밀어 둔다. */}
      <svg viewBox="0 0 22 22" width="25" height="25" aria-hidden="true">
        <path
          d="M3.4 2.2 15.9 11.4c.7.5.4 1.6-.5 1.7l-4.6.4-2.3 4.3c-.4.8-1.6.6-1.8-.3L3.4 2.2Z"
          fill="var(--primary)"
          stroke="#fff"
          strokeWidth="1.7"
          strokeLinejoin="round"
        />
      </svg>
    </motion.span>
  );
}

/** 눌린 자리에서 퍼지는 물결. 누르는 시각을 그대로 받아 손끝과 어긋나지 않게 한다. */
function Ripples({ presses, playing }: { presses: Press[]; playing: boolean }) {
  if (!playing) return null;
  return (
    <>
      {presses.map((p) => (
        <motion.span
          key={`${p.x}-${p.y}-${p.at}`}
          className="tour-ripple"
          style={{ left: p.x, top: p.y }}
          initial={{ scale: 0.2, opacity: 0 }}
          animate={{ scale: [0.2, 1.6], opacity: [0.5, 0] }}
          transition={{ duration: 0.65, delay: p.at, ease: "easeOut" }}
        />
      ))}
    </>
  );
}

/**
 * 앞 화면이 물러나고 뒤 화면이 들어오는 전환.
 *
 * 두 화면이 동시에 보이지 않게 한다. 예전에는 겹치는 구간이 있어서 글자 위에 글자가
 * 얹혀 보였다 — 앞 화면이 완전히 사라진 뒤에 뒤 화면이 들어온다.
 */
function panelOut(playing: boolean, at: number): MotionProps {
  if (!playing) return { initial: { opacity: 0 }, animate: { opacity: 0 } };
  return {
    initial: { opacity: 1, x: 0 },
    animate: { opacity: 0, x: -22 },
    transition: { delay: at, duration: 0.2, ease: "easeIn" },
  };
}

function panelIn(playing: boolean, at: number): MotionProps {
  if (!playing) return { initial: { opacity: 1, x: 0 }, animate: { opacity: 1, x: 0 } };
  return {
    initial: { opacity: 0, x: 22 },
    animate: { opacity: 1, x: 0 },
    transition: { delay: at + 0.22, duration: 0.28, ease: "easeOut" },
  };
}

/** 재생할 때만 delay를 걸고, 정지 상태에서는 끝 모습을 그대로 그린다. */
function reveal(
  playing: boolean,
  delay: number,
  from: TargetAndTransition = { opacity: 0, y: 10 },
): MotionProps {
  if (!playing) return { initial: false, animate: { opacity: 1, y: 0, scaleX: 1 } };
  return {
    initial: from,
    animate: { opacity: 1, y: 0, scaleX: 1 },
    transition: { delay, duration: 0.35, ease: "easeOut" },
  };
}

interface Scene {
  /** 레일에 찍히는 단계 이름. 세 장면이 하나의 흐름임을 이 세 낱말이 이어 준다. */
  stage: string;
  caption: string;
  render: (playing: boolean) => ReactNode;
}

/* 장면 1 — 고르면 순위가 나온다.
   0.0 자리잡기 · 1.15 국가 칸 터치 · 1.4 「일본」 · 2.25 「다음」 터치 · 2.5 화면 전환 ·
   2.9~ 순위가 차오름 · 4.2~6.0 머무름 */
const S1_FIELD: Press = { x: 144, y: 89, at: 1.15 };
const S1_NEXT: Press = { x: 144, y: 137, at: 2.25 };
const S1_SWAP = 2.45;

/* 장면 2 — 한 문장이면 결과가 나온다.
   0.4~2.0 타이핑 · 2.6 「사고 분석 요청」 터치 · 2.85 화면 전환 · 3.2~ 결과 */
const S2_SEND: Press = { x: 144, y: 161, at: 2.6 };
const S2_SWAP = 2.8;

/* 장면 3 — 화면을 바꾸지 않고 그 자리에서 형광펜이 그어진다.
   1.0 「근거 보기」 터치 · 1.5 첫 획 · 2.5 둘째 획 */
const S3_SHOW: Press = { x: 144, y: 217, at: 1.0 };

const SCENES: Scene[] = [
  {
    stage: "여행 전",
    caption: "여행 정보만 넣으면 7개사를 비교해요",
    render: (playing) => (
      <>
        <motion.div className="tour-panel" {...panelOut(playing, S1_SWAP)}>
          <p className="tour-mini__eyebrow">STEP 1 · 목적지</p>
          <p className="tour-mini__ask">어디로 떠나시나요?</p>
          <div className="tour-mini__field">
            <motion.span
              initial={playing ? { opacity: 1 } : false}
              animate={{ opacity: playing ? 0 : 0 }}
              transition={{ delay: S1_FIELD.at + 0.15, duration: 0.2 }}
            >
              국가를 선택하세요
            </motion.span>
            <motion.span
              className="tour-mini__value"
              initial={playing ? { opacity: 0 } : false}
              animate={{ opacity: 1 }}
              transition={{ delay: S1_FIELD.at + 0.25, duration: 0.2 }}
            >
              일본
            </motion.span>
            <span className="tour-mini__chev">⌄</span>
          </div>
          <div className="tour-mini__btn">다음</div>
          <Tap presses={[S1_FIELD, S1_NEXT]} playing={playing} />
          <Ripples presses={[S1_FIELD, S1_NEXT]} playing={playing} />
        </motion.div>

        <motion.div className="tour-panel" {...panelIn(playing, S1_SWAP)}>
          <p className="tour-mini__eyebrow">균형형 기준 · 표준 등급</p>
          {RANKING.map((r, i) => (
            <motion.div key={r.name} className="tour-rank" {...reveal(playing, S1_SWAP + 0.5 + i * 0.1)}>
              <span className="tour-rank__no">{i + 1}</span>
              <span className="tour-rank__name">{r.name}</span>
              <span className="tour-rank__won">{r.won}</span>
              <span className="tour-rank__bar">
                <motion.span
                  style={{ width: `${r.score}%` }}
                  {...reveal(playing, S1_SWAP + 0.7 + i * 0.1, { scaleX: 0 })}
                />
              </span>
            </motion.div>
          ))}
        </motion.div>
      </>
    ),
  },
  {
    stage: "사고 후",
    caption: "사고는 한 문장이면 충분해요",
    render: (playing) => (
      <>
        <motion.div className="tour-panel" {...panelOut(playing, S2_SWAP)}>
          <p className="tour-mini__eyebrow">STEP 2 · 사고 내용</p>
          <p className="tour-mini__ask">무슨 일이 있었나요?</p>
          <div className="tour-mini__note">
            {/* 글자 폭을 px로 적어 두면 글이 바뀔 때 잘린다. 오른쪽에서 왼쪽으로 덮개를
                걷어내는 방식이라 어떤 길이든 정확히 끝까지 드러난다. */}
            <motion.span
              className="tour-type"
              initial={playing ? { clipPath: "inset(0 100% 0 0)" } : false}
              animate={{ clipPath: "inset(0 0% 0 0)" }}
              transition={{ delay: 0.4, duration: 1.6, ease: "linear" }}
            >
              길에서 넘어져 발목을 다쳤어요
              {playing && <span className="tour-caret" />}
            </motion.span>
          </div>
          <div className="tour-mini__btn">사고 분석 요청</div>
          <Tap presses={[S2_SEND]} playing={playing} />
          <Ripples presses={[S2_SEND]} playing={playing} />
        </motion.div>

        <motion.div className="tour-panel" {...panelIn(playing, S2_SWAP)}>
          <p className="tour-mini__eyebrow">상해 · 해외상해치료</p>
          <motion.div className="tour-result" {...reveal(playing, S2_SWAP + 0.5)}>
            <span className="tour-result__tag">받을 수 있어요</span>
            <p className="tour-result__title">해외여행중 상해치료비</p>
            <p className="tour-result__sub">제4조 · 실제 부담한 의료비</p>
          </motion.div>
          <p className="tour-mini__eyebrow">필요한 서류</p>
          <div className="tour-chips">
            {DOCS.map((d, i) => (
              <motion.span
                key={d}
                className="tour-chip"
                {...reveal(playing, S2_SWAP + 0.8 + i * 0.12, { opacity: 0, y: 6 })}
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
    stage: "근거 확인",
    caption: "왜 그런지 약관 원문에서 짚어줘요",
    render: (playing) => (
      <div className="tour-panel">
        <p className="tour-mini__eyebrow">카카오페이손해보험 · 제4조</p>
        <div className="tour-clause">
          <p>
            회사는 피보험자가 보험기간 중에 발생한
            <span className="tour-clause__target">
              <motion.span
                className="tour-clause__ink"
                initial={playing ? { scaleX: 0 } : false}
                animate={{ scaleX: 1 }}
                transition={{ delay: 1.5, duration: 0.8, ease: "easeInOut" }}
              />
              <span className="tour-clause__word">급격하고 우연한 외래의 사고</span>
            </span>
            로 상해를 입은 경우
            <span className="tour-clause__target">
              <motion.span
                className="tour-clause__ink"
                initial={playing ? { scaleX: 0 } : false}
                animate={{ scaleX: 1 }}
                transition={{ delay: 2.5, duration: 0.65, ease: "easeInOut" }}
              />
              <span className="tour-clause__word">보험금을 지급합니다</span>
            </span>
            . 다만, 약관에서 보장하지 않는다고 정한 사유로 생긴 손해는 보상하지 않습니다.
          </p>
        </div>
        <div className="tour-mini__btn tour-mini__btn--ghost">근거 보기</div>
        <Tap presses={[S3_SHOW]} playing={playing} />
        <Ripples presses={[S3_SHOW]} playing={playing} />
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
