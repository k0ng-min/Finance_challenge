import { useEffect, useRef } from "react";
import gsap from "gsap";
import { PEN_GLYPH_PATHS } from "../generated/penGlyphPaths";

/** 홈 화면 히어로(나침반 자리)를 대신하는 3단계 애니메이션. 참고한 CodePen
 * (akshsharma1218, "Animated Handwriting with DrawSVG GSAP3")과 같은 GSAP
 * 타임라인(gsap.timeline({repeat:-1}))으로 ① 펜이 "보험형광펜"을 한 글자씩
 * 씀 → ② 다 쓰면 펜이 사라지고 노란 형광펜이 등장해 왼쪽부터 훑으며 노란
 * 하이라이트를 칠함 → ③ 지우개가 오른쪽위→왼쪽아래 대각선을 반복하며
 * (쓱싹쓱싹) 오른쪽으로 이동하는데, 실제로 지워지는 영역은 정해진 시간이
 * 아니라 지우개의 그 순간 실제 x좌표를 그대로 따라간다(펜이 글자를 쓸 때와
 * 같은 원리) → 처음(빈 화면)으로 돌아가 반복한다.
 *
 * 글자는 학교안심 민들레홀씨 R(한국교육학술정보원 KERIS, OFL 라이선스) 폰트
 * 파일에서 opentype.js로 직접 뽑아낸 실제 글리프 윤곽선(SVG path,
 * scripts/extract-glyph-paths.mjs → src/generated/penGlyphPaths.ts)이다 —
 * CSS로 흉내내거나 손으로 좌표를 그린 게 아니라 진짜 폰트 모양 그대로다.
 *
 * 펜은 그 윤곽선(guide path) 위의 실제 좌표를 매 프레임
 * SVGPathElement.getPointAtLength()로 읽어 이동하고, 동시에 "꽉 찬 글자
 * 모양"(fill path, 같은 d)을 펜이 도달한 x좌표까지만 clip-path로 드러낸다 —
 * 펜 위치와 드러나는 잉크가 같은 좌표(p.x)에서 나오므로 항상 정확히 맞물리고,
 * 폰트 윤곽선을 stroke나 mask로 직접 그리지 않으므로(그러면 ㅂ/ㅁ처럼 안이
 * 뚫린 글자가 속이 빈 테두리로 보임) 항상 "완전한 글자 모양"만 보인다. 이
 * 좌표 계산은 GSAP 타임라인 안의 더미 트윈(duration만 쓰고 onUpdate에서
 * 직접 좌표를 찍는 프록시 트윈) 하나로 처리해서, 재생/일시정지/속도 조절 같은
 * GSAP 타임라인 제어를 그대로 받는다.
 *
 * 펜·형광펜은 이 앱의 다른 아이콘과 같은 출처(Fluent Emoji 3D, MIT License,
 * Microsoft)에서 받은 실제 3D 렌더 이미지다(/public/3d/pen.webp,
 * crayon.webp). 지우개(eraser.webp)는 지우개 전용 이모지가 없어 Sketchfab의
 * "eraser" 3D 모델(by Mr.Photon/@blender.2009, CC Attribution 4.0 — 다른
 * 에셋과 달리 저작자 표시가 필요한 라이선스라 여기 남겨둔다) 렌더 이미지를
 * 썼다. 되돌리고 싶으면 Home.tsx에서 이 컴포넌트 호출을 원래 Icon3D로 바꾸면
 * 된다. */

const CHAR_DURATION = 1.4;
const PEN_FADE = 0.12;
const CHAR_GAP = 0.15;
// 펜 에셋(pen.webp) 안에서 실제 펜촉이 있는 위치 — 이미지 왼쪽아래 모서리
// 근처. 이 비율만큼 이미지를 당겨서 촉이 좌표에 정확히 붙게 한다.
const PEN_W = 760;
const PEN_H = 760;
const TIP_FRAC_X = 0.1;
const TIP_FRAC_Y = 0.92;

export function PenWriteCompass() {
  const rootRef = useRef<HTMLSpanElement>(null);
  const guideRefs = useRef<(SVGPathElement | null)[]>([]);
  const fillRefs = useRef<(SVGPathElement | null)[]>([]);
  const penRefs = useRef<(SVGImageElement | null)[]>([]);
  const highlightBgRef = useRef<HTMLSpanElement>(null);
  const highlighterRef = useRef<HTMLImageElement>(null);
  const eraserRef = useRef<HTMLImageElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const ctx = gsap.context(() => {
      // 처음 마운트될 때뿐 아니라 반복(repeat:-1)될 때마다 매번 이 상태로
      // 되돌아가야 한다 — 타임라인 밖(gsap.set)에 한 번만 넣으면 두 번째
      // 루프부터는 지난 사이클에 다 써진/드러난 상태 그대로 남아서 "쓰기 전인
      // 글자도 보이는" 버그가 생긴다. 그래서 타임라인 맨 앞의 tl.set으로 넣어
      // 매 루프 시작마다 다시 초기화되게 한다.
      const tl = gsap.timeline({ repeat: -1, defaults: { ease: "none" } });
      tl.set(fillRefs.current, { clipPath: "inset(0 100% 0 0)" });
      tl.set(penRefs.current, { autoAlpha: 0 });
      tl.set(highlightBgRef.current, { scaleX: 0, opacity: 0, transformOrigin: "left center" });
      tl.set(highlighterRef.current, { left: "-8%", opacity: 0 });
      tl.set(eraserRef.current, { left: "-8%", top: "-18%", opacity: 0 });
      tl.set(textRef.current, { clipPath: "inset(0 0 0 0%)" });

      // ① 한 글자씩 쓴다 — 프록시 트윈의 onUpdate에서 진행률(0~1)을 읽어
      // 실제 폰트 윤곽선 위 좌표(getPointAtLength)를 계산하고, 펜 위치와
      // clip-path 드러남을 같은 좌표로 동시에 갱신한다.
      PEN_GLYPH_PATHS.forEach((g, i) => {
        const pen = penRefs.current[i];
        const guide = guideRefs.current[i];
        const fill = fillRefs.current[i];
        if (!pen || !guide || !fill) return;
        const len = guide.getTotalLength();

        tl.to(pen, { autoAlpha: 1, duration: PEN_FADE });
        tl.to(
          {},
          {
            duration: CHAR_DURATION,
            onUpdate() {
              const dist = this.progress() * len;
              const p = guide.getPointAtLength(dist);
              // 획 방향을 따라 매 프레임 회전시키면(이전 버전) 펜이 이리저리
              // 돌아가며 부자연스럽게 흔들려 보인다 — 실제로 손에 쥔 펜처럼
              // 항상 같은 대각선 각도(오른쪽 위→왼쪽 아래)를 유지한다.
              pen.setAttribute("transform", `translate(${p.x} ${p.y}) rotate(45)`);
              const xPct = Math.min(100, Math.max(0, (p.x / g.width) * 100));
              fill.style.clipPath = `inset(0 ${100 - xPct}% 0 0)`;
            },
          },
        );
        tl.set(fill, { clipPath: "inset(0 0% 0 0)" });
        tl.to(pen, { autoAlpha: 0, duration: PEN_FADE });
        if (i < PEN_GLYPH_PATHS.length - 1) tl.to({}, { duration: CHAR_GAP });
      });

      tl.to({}, { duration: 0.7 });

      // ② 형광펜이 왼쪽부터 훑으며 노란 하이라이트를 칠한다.
      tl.to(highlighterRef.current, { opacity: 1, left: "-3%", duration: 0.15 });
      tl.to(highlighterRef.current, { left: "94%", duration: 1.9 }, "<");
      tl.to(highlightBgRef.current, { scaleX: 1, opacity: 1, duration: 1.9 }, "<");
      tl.to(highlighterRef.current, { left: "100%", opacity: 0, duration: 0.2 });

      tl.to({}, { duration: 1.1 });

      // ③ 지우개가 오른쪽위→왼쪽아래 대각선을 반복하며(쓱싹쓱싹) 오른쪽으로
      // 이동한다 — 위아래로 움직이는 동안에도 실제로 지워지는 영역(textRef의
      // clip-path)은 매 프레임 지우개의 "현재 x좌표"에서 직접 계산해서 항상
      // 지우개가 실제로 지나간 만큼만 지워지게 한다(그냥 정해진 시간에 맞춰
      // 지워지는 게 아니라, 펜이 글자를 쓸 때와 같은 방식으로 지우개의 실제
      // 위치를 그대로 clip-path에 반영).
      // 지우개는 .pwc(넓은 히어로 박스) 기준 %로 움직이지만 실제로 지워야
      // 할 textRef는 그 안에서 가운데 정렬된 더 좁은 박스라서, 두 %를 그냥
      // 같은 값으로 쓰면 지우개가 실제로 있는 자리와 지워지는 경계가
      // 어긋난다 — 화면 실제 좌표(getBoundingClientRect)로 직접 비율을
      // 계산해서 지우개가 시각적으로 지나간 지점과 정확히 맞춘다.
      const syncEraseClip = () => {
        const eraserRect = eraserRef.current!.getBoundingClientRect();
        const textRect = textRef.current!.getBoundingClientRect();
        const eraserX = eraserRect.left + eraserRect.width * 0.15;
        const fraction = textRect.width > 0 ? (eraserX - textRect.left) / textRect.width : 0;
        const pct = Math.min(100, Math.max(0, fraction * 100));
        textRef.current!.style.clipPath = `inset(0 0 0 ${pct}%)`;
      };
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
        { left: "98%", top: "-14%" },
      ];
      tl.to(eraserRef.current, { opacity: 1, ...scrub[0], duration: 0.15, onUpdate: syncEraseClip });
      scrub.slice(1).forEach((pos) => {
        tl.to(eraserRef.current, { ...pos, duration: 0.18, onUpdate: syncEraseClip });
      });
      tl.to(eraserRef.current, { opacity: 0, duration: 0.2 });
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
        {PEN_GLYPH_PATHS.map((g, i) => (
          <svg
            key={g.char}
            className={`pwc__char pwc__char--${i}`}
            viewBox={`${g.x} ${g.y} ${g.width} ${g.height}`}
            style={{ width: `${g.advanceEm}em` }}
            preserveAspectRatio="xMinYMax meet"
            overflow="visible"
          >
            {/* 화면에는 그리지 않고, 펜이 따라갈 좌표를 getPointAtLength로
                구하기 위한 기하 전용 path. */}
            <path
              ref={(el) => {
                guideRefs.current[i] = el;
              }}
              className="pwc__char-guide"
              d={g.d}
            />
            <path
              ref={(el) => {
                fillRefs.current[i] = el;
              }}
              className="pwc__char-fill-live"
              d={g.d}
            />
            <image
              ref={(el) => {
                penRefs.current[i] = el;
              }}
              href="/3d/pen.webp"
              className="pwc__pen-svg"
              width={PEN_W}
              height={PEN_H}
              x={-PEN_W * TIP_FRAC_X}
              y={-PEN_H * TIP_FRAC_Y}
              opacity={0}
            />
          </svg>
        ))}
        <span className="pwc__highlight-bg" ref={highlightBgRef} />
      </span>
    </span>
  );
}
