import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Icon3D } from "./Icon3D";
import { INSURER_COUNT } from "../data/insurers";

const LS_TOUR_SEEN = "travel_ai_tour_seen";

/** 한 장이 저절로 넘어가기까지의 시간. 짧은 문장 두 줄을 읽고 그림을 볼 만큼은 되고,
 * 다 읽은 사람이 답답해하지 않을 만큼은 짧게 잡았다. */
const SLIDE_MS = 4500;

interface Slide {
  icon: string;
  title: string;
  body: string;
  /** 마지막 장에만 있다. 누르면 그 화면으로 보내고 안내를 닫는다. */
  cta?: { label: string; to: string };
}

const SLIDES: Slide[] = [
  {
    icon: "shield",
    title: "실제 약관이 근거예요",
    body: `${INSURER_COUNT}개 손해보험사의 진짜 약관을 조항 단위로 읽어 두었어요. 어떤 안내든 그 원문을 함께 보여드리고, 근거를 못 찾으면 지어내지 않고 "확인불가"라고 말합니다.`,
  },
  {
    icon: "suitcase",
    title: "여행 전에는 고르는 걸 도와요",
    body: "어디로 얼마나 가는지만 알려주시면, 필요한 보장을 짚고 보험사별 실제 보험료까지 나란히 비교해 드려요.",
  },
  {
    icon: "collision",
    title: "사고가 나면 한 문장이면 돼요",
    body: '"길에서 넘어져 발목을 다쳤어요"처럼 편하게 쓰시면, 무슨 사고인지 분류하고 받을 수 있는 담보와 필요한 서류를 찾아드려요.',
  },
  {
    icon: "highlighter",
    title: "근거를 형광펜으로 짚어줘요",
    body: "왜 그렇게 안내했는지 궁금하면 약관 원문에서 관련 구간에 형광펜이 칠해진 걸 그대로 확인하실 수 있어요.",
  },
  {
    icon: "key",
    title: "가입 없이 전부 써보실 수 있어요",
    body: "로그인은 기록을 남기고 싶을 때만 하시면 돼요. 지금 바로 둘러보세요.",
    cta: { label: "내 여행부터 준비하기", to: "/trip" },
  },
];

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
 * 앱을 처음 연 사람에게 이 서비스가 무엇인지 한 바퀴 보여주는 안내.
 *
 * 홈 화면은 카드 이름만 늘어놓기 때문에, 처음 온 사람은 이 앱의 핵심(모든 안내에 실제
 * 약관 원문이 근거로 붙는다는 것)을 만나기까지 여러 번을 눌러 들어가야 한다. 그래서
 * 열자마자 다섯 장으로 요약해 저절로 넘겨 보여주고, 마지막 장에서 첫 화면으로 보낸다.
 *
 * 저절로 넘어가되 사람이 손대는 순간 멈춘다 — 읽는 속도는 저마다 다른데 화면이 계속
 * 제 맘대로 넘어가면 안내가 아니라 방해가 된다.
 */
export function WelcomeTour({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const [index, setIndex] = useState(0);
  const [dontShowAgain, setDontShowAgain] = useState(true);
  // 사람이 화살표나 점을 눌렀다 = 자기 속도로 읽겠다는 뜻이다. 그 뒤로는 안 넘긴다.
  const [paused, setPaused] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);

  // 움직임을 줄이도록 설정한 사람에게는 저절로 넘기지 않는다(멀미·주의력 문제).
  const reduceMotion =
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const autoAdvancing = !paused && !reduceMotion;

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

  // 저절로 넘기기. 마지막 장에서는 멈춘다 — 저 혼자 닫히면 마지막 문장을 놓친다.
  useEffect(() => {
    if (!autoAdvancing || index >= SLIDES.length - 1) return;
    const timer = window.setTimeout(() => setIndex((i) => i + 1), SLIDE_MS);
    return () => window.clearTimeout(timer);
  }, [index, autoAdvancing]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
      if (e.key === "ArrowRight") goTo(Math.min(index + 1, SLIDES.length - 1));
      if (e.key === "ArrowLeft") goTo(Math.max(index - 1, 0));
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
    setIndex(next);
  }

  const slide = SLIDES[index];
  const isLast = index === SLIDES.length - 1;

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
        initial={{ opacity: 0, y: 28, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 28, scale: 0.96 }}
        transition={{ type: "spring", stiffness: 320, damping: 28 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 몇 장 중 몇 번째인지, 그리고 다음 장까지 얼마나 남았는지를 같은 막대로 보여준다 */}
        <div className="tour-card__bars" aria-hidden="true">
          {SLIDES.map((_, i) => (
            <span key={i} className="tour-card__bar">
              {i < index && <span className="tour-card__bar-fill tour-card__bar-fill--done" />}
              {i === index && (
                <motion.span
                  key={`${index}-${autoAdvancing}`}
                  className="tour-card__bar-fill"
                  initial={{ width: autoAdvancing && !isLast ? "0%" : "100%" }}
                  animate={{ width: "100%" }}
                  transition={
                    autoAdvancing && !isLast
                      ? { duration: SLIDE_MS / 1000, ease: "linear" }
                      : { duration: 0.2 }
                  }
                />
              )}
            </span>
          ))}
        </div>

        <button type="button" className="tour-card__close" onClick={close} aria-label="안내 닫기">
          ✕
        </button>

        <div className="tour-card__stage">
          <AnimatePresence mode="wait">
            <motion.div
              key={index}
              className="tour-slide"
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -40 }}
              transition={{ duration: 0.32, ease: "easeOut" }}
            >
              <motion.div
                initial={{ scale: 0.7, rotate: -6, opacity: 0 }}
                animate={{ scale: 1, rotate: 0, opacity: 1 }}
                transition={{ type: "spring", stiffness: 240, damping: 18 }}
              >
                <Icon3D src={slide.icon} size={78} />
              </motion.div>
              <strong className="tour-slide__title">{slide.title}</strong>
              <p className="tour-slide__body">{slide.body}</p>
            </motion.div>
          </AnimatePresence>
        </div>

        <div className="tour-card__dots">
          <button
            type="button"
            className="tour-card__arrow"
            onClick={() => goTo(Math.max(index - 1, 0))}
            disabled={index === 0}
            aria-label="이전"
          >
            ‹
          </button>
          {SLIDES.map((_, i) => (
            <button
              key={i}
              type="button"
              className={`tour-card__dot${i === index ? " tour-card__dot--on" : ""}`}
              onClick={() => goTo(i)}
              aria-label={`${i + 1}번째 안내`}
              aria-current={i === index}
            />
          ))}
          <button
            type="button"
            className="tour-card__arrow"
            onClick={() => goTo(Math.min(index + 1, SLIDES.length - 1))}
            disabled={isLast}
            aria-label="다음"
          >
            ›
          </button>
        </div>

        {slide.cta && (
          <button
            type="button"
            className="tour-card__cta"
            onClick={() => {
              close();
              navigate(slide.cta!.to);
            }}
          >
            {slide.cta.label}
          </button>
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
