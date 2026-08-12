import { useEffect, useRef } from "react";
import gsap from "gsap";
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";
import { MotionPathPlugin } from "gsap/MotionPathPlugin";
import { PEN_CHAR_STROKES } from "../data/penStrokes";

gsap.registerPlugin(DrawSVGPlugin, MotionPathPlugin);

/** 홈 화면 히어로(나침반 자리)를 대신하는 3단계 애니메이션. 참고한 CodePen
 * (akshsharma1218, "Animated Handwriting with DrawSVG GSAP3")과 같은 라이브러리
 * 구성 — GSAP의 DrawSVGPlugin(획을 stroke-dasharray/dashoffset으로 그려주는
 * 플러그인)과 MotionPathPlugin(요소를 SVG path 위로 움직여주는 플러그인) — 을
 * 그대로 써서 ① 펜이 "보험형광펜"을 한 글자씩, 손으로 쓴 획 순서 그대로
 * (src/data/penStrokes.ts) 실제로 그리듯 씀 → ② 다 쓰면 펜이 사라지고 노란
 * 형광펜이 등장해 왼쪽부터 훑으며 노란 하이라이트를 칠함 → ③ 지우개가
 * 오른쪽위→왼쪽아래 대각선을 반복하며(쓱싹쓱싹) 오른쪽으로 이동해 전체를
 * 지움 → 처음(빈 화면)으로 돌아가 반복한다. 이 전체 시퀀스가 하나의
 * gsap.timeline({repeat:-1})이다(참고 CodePen의 script.js와 같은 패턴 —
 * tl.to(path, {drawSVG:true}) + tl.to(pen, {motionPath:{path, align:path}}, "<")).
 *
 * 처음엔 폰트 파일(Gaegu)에서 opentype.js로 실제 글리프 윤곽선을 뽑아 썼는데,
 * 그 path는 "글자 안쪽을 지나는 스켈레톤"이 아니라 글자의 바깥+안쪽 테두리
 * (컨투어)라서 (1) 펜이 사람 쓰는 순서가 아니라 테두리를 훑는 궤적으로
 * 움직이고 (2) ㅂ/ㅁ처럼 안이 뚫린 글자가 속이 빈 테두리로 보이는 문제가
 * 있었다. 그래서 실제 자모 획 순서대로 손으로 좌표를 그린 스켈레톤 path로
 * 바꿨다 — 획 두께만큼 stroke를 주면 그 자체가 손글씨 굵기의 잉크가 된다.
 * 한글은 자모 단위 획순 데이터를 제공하는 공개 라이브러리가 없어서(한자의
 * Hanzi Writer 같은 것) src/data/penStrokes.ts에 5글자 분량만 직접 정의했다.
 *
 * 펜·형광펜·지우개는 이 앱의 다른 아이콘과 같은 출처(Fluent Emoji 3D, MIT
 * License, Microsoft)에서 받은 실제 3D 렌더 이미지다(/public/3d/pen.webp,
 * crayon.webp — 지우개(eraser.webp)는 지우개 전용 이모지가 없어 Sketchfab의
 * CC0(퍼블릭 도메인) "Pink Eraser" 3D 모델(by plaggy) 렌더 이미지를 썼다).
 * 되돌리고 싶으면 Home.tsx에서 이 컴포넌트 호출을 원래 Icon3D로 바꾸면 된다. */

const STROKE_DURATION = 0.3;
const PEN_FADE = 0.12;
const CHAR_GAP = 0.15;
// 펜 에셋(pen.webp) 안에서 실제 펜촉이 있는 위치 — 이미지 왼쪽아래 모서리
// 근처. MotionPathPlugin의 alignOrigin이 이 지점을 path 좌표에 맞춘다.
const PEN_TIP: [number, number] = [0.1, 0.92];

export function PenWriteCompass() {
  const rootRef = useRef<HTMLSpanElement>(null);
  const strokeRefs = useRef<SVGPathElement[][]>(PEN_CHAR_STROKES.map(() => []));
  const penRefs = useRef<(SVGImageElement | null)[]>([]);
  const highlightBgRef = useRef<HTMLSpanElement>(null);
  const highlighterRef = useRef<HTMLImageElement>(null);
  const eraserRef = useRef<HTMLImageElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const ctx = gsap.context(() => {
      gsap.set(strokeRefs.current.flat(), { drawSVG: 0 });
      gsap.set(penRefs.current, { autoAlpha: 0 });
      gsap.set(highlightBgRef.current, { scaleX: 0, opacity: 0, transformOrigin: "left center" });
      gsap.set(highlighterRef.current, { left: "-8%", opacity: 0 });
      gsap.set(eraserRef.current, { left: "-8%", top: "-18%", opacity: 0 });
      gsap.set(textRef.current, { clipPath: "inset(0 0 0 0%)" });

      const tl = gsap.timeline({ repeat: -1, defaults: { ease: "none" } });

      // ① 한 글자씩 실제 획 순서대로 쓴다 — drawSVG로 획을 그리며 동시에
      // ("<" 포지션 파라미터) MotionPathPlugin이 펜을 그 path 위로 움직인다.
      PEN_CHAR_STROKES.forEach((_charData, i) => {
        const pen = penRefs.current[i];
        tl.to(pen, { autoAlpha: 1, duration: PEN_FADE });
        strokeRefs.current[i].forEach((strokeEl) => {
          tl.to(strokeEl, { drawSVG: true, duration: STROKE_DURATION });
          tl.to(
            pen,
            {
              motionPath: {
                path: strokeEl,
                align: strokeEl,
                alignOrigin: PEN_TIP,
                autoRotate: 45,
              },
              duration: STROKE_DURATION,
            },
            "<",
          );
        });
        tl.to(pen, { autoAlpha: 0, duration: PEN_FADE });
        if (i < PEN_CHAR_STROKES.length - 1) tl.to({}, { duration: CHAR_GAP });
      });

      tl.to({}, { duration: 0.7 });

      // ② 형광펜이 왼쪽부터 훑으며 노란 하이라이트를 칠한다.
      tl.to(highlighterRef.current, { opacity: 1, left: "-3%", duration: 0.15 });
      tl.to(highlighterRef.current, { left: "94%", duration: 1.9 }, "<");
      tl.to(highlightBgRef.current, { scaleX: 1, opacity: 1, duration: 1.9 }, "<");
      tl.to(highlighterRef.current, { left: "100%", opacity: 0, duration: 0.2 });

      tl.to({}, { duration: 1.1 });

      // ③ 지우개가 오른쪽위→왼쪽아래 대각선을 반복하며(쓱싹쓱싹) 오른쪽으로
      // 이동해 전체를 지운다 — 실제로 지워지는 건 textRef의 clip-path.
      const scrub: gsap.TweenVars[] = [
        { left: "6%", top: "-26%" },
        { left: "-2%", top: "-10%" },
        { left: "24%", top: "-26%" },
        { left: "16%", top: "-10%" },
        { left: "42%", top: "-26%" },
        { left: "34%", top: "-10%" },
        { left: "60%", top: "-26%" },
        { left: "52%", top: "-10%" },
        { left: "90%", top: "-18%" },
      ];
      tl.to(eraserRef.current, { opacity: 1, ...scrub[0], duration: 0.15 });
      tl.to(textRef.current, { clipPath: "inset(0 0 0 100%)", duration: 1.6 }, "<");
      scrub.slice(1).forEach((pos) => {
        tl.to(eraserRef.current, { ...pos, duration: 0.15 });
      });
      tl.to(eraserRef.current, { left: "98%", opacity: 0, duration: 0.2 });
      tl.set(textRef.current, { clipPath: "inset(0 0 0 0%)" });

      tl.to({}, { duration: 0.3 });
    }, rootRef);

    return () => ctx.revert();
  }, []);

  return (
    <span className="pwc" ref={rootRef} aria-hidden="true">
      <img className="pwc__highlighter" ref={highlighterRef} src="/3d/crayon.webp" alt="" />
      <img className="pwc__eraser" ref={eraserRef} src="/3d/eraser.webp" alt="" />
      <span className="pwc__text" ref={textRef}>
        {PEN_CHAR_STROKES.map((g, i) => (
          <svg
            key={g.char}
            className={`pwc__char pwc__char--${i}`}
            viewBox="0 0 100 100"
            preserveAspectRatio="xMidYMid meet"
            overflow="visible"
          >
            {g.strokes.map((d, j) => (
              <path
                key={j}
                ref={(el) => {
                  if (el) strokeRefs.current[i][j] = el;
                }}
                className="pwc__char-stroke"
                d={d}
              />
            ))}
            <image
              ref={(el) => {
                penRefs.current[i] = el;
              }}
              href="/3d/pen.webp"
              className="pwc__pen-svg"
              width={100}
              height={100}
            />
          </svg>
        ))}
        <span className="pwc__highlight-bg" ref={highlightBgRef} />
      </span>
    </span>
  );
}
