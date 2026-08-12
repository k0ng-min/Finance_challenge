import { useEffect, useRef } from "react";
import gsap from "gsap";
import { PEN_GLYPH_PATHS } from "../generated/penGlyphPaths";

/** 홈 화면 히어로(나침반 자리)를 대신하는 3단계 애니메이션. 참고한 CodePen
 * (akshsharma1218, "Animated Handwriting with DrawSVG GSAP3")과 같은 GSAP
 * 타임라인(gsap.timeline({repeat:-1}))으로 ① 펜이 "보험형광펜"을 한 글자씩,
 * 자모(잉크 덩어리) 단위로 실제 쓰는 순서대로 씀 → ② 다 쓰면 펜이 사라지고
 * 노란 형광펜이 등장해 왼쪽부터 훑으며 노란 하이라이트를 칠함 → ③ 지우개가
 * 오른쪽위→왼쪽아래 대각선을 반복하며(쓱싹쓱싹) 오른쪽으로 이동하는데, 실제로
 * 지워지는 영역은 정해진 시간이 아니라 지우개의 그 순간 실제 x좌표를 그대로
 * 따라간다 → 처음(빈 화면)으로 돌아가 반복한다.
 *
 * 글자는 학교안심 민들레홀씨 R(KERIS, OFL) 폰트에서 opentype.js로 뽑은 실제
 * 글리프 윤곽선이다(scripts/extract-glyph-paths.mjs → src/generated/
 * penGlyphPaths.ts). 컨투어(잉크 덩어리)를 자모 단위로 묶고 실제 쓰는 순서
 * (초성→중성→종성)로 정렬해 groups 배열에 담아 뒀다.
 *
 * 처음엔 각 자모 덩어리를 clip-path로 왼쪽→오른쪽 훑어 드러냈는데, 그건
 * "벽이 밀려나며 뒤에서 글자가 나타나는" 것이지 실제로 펜이 획을 그리는
 * 움직임이 아니다(참고 CodePen이 하는 방식과도 다르다). 그래서 진짜
 * stroke-dasharray/dashoffset로 윤곽선 자체를 점점 그려나가는 방식으로
 * 바꿨다 — 단, 그 윤곽선을 화면에 직접 보여주면(예전 시도) ㅁ/ㅇ처럼 안이
 * 뚫린 자모가 속이 빈 테두리로 보인다. 그래서 그 그려지는 윤곽선을 <mask>로만
 * 쓰고, 그 아래 꽉 찬 자모 모양(fill)을 그 mask를 통해서만 보여준다 — 획
 * 굵기만큼 두꺼운 stroke로 그려지는 mask가 지나간 자리만큼만 fill이
 * "잉크처럼" 드러나므로 안이 뚫린 자모도 속이 빈 테두리로 보이지 않는다.
 * mask stroke의 굵기는 그 자모 덩어리 자신의 bbox(getBBox)에서 계산해
 * 자모 크기에 비례하게 잡는다.
 *
 * 펜은 그 mask stroke(윤곽선)와 완전히 같은 path 위의 좌표를 매 프레임
 * SVGPathElement.getPointAtLength()로 읽어 이동한다 — mask의 dashoffset과
 * 펜 위치가 같은 진행률(progress)에서 동시에 나오므로 펜 끝이 항상 지금
 * 그려지는 지점에 정확히 붙어 있다. 이 진행률 계산은 GSAP 타임라인 안의
 * 더미 트윈(duration만 쓰고 onUpdate에서 직접 좌표를 찍는 프록시 트윈)으로
 * 처리해서, 재생/일시정지/속도 조절 같은 GSAP 타임라인 제어를 그대로 받는다.
 *
 * 펜·형광펜은 이 앱의 다른 아이콘과 같은 출처(Fluent Emoji 3D, MIT License,
 * Microsoft)에서 받은 실제 3D 렌더 이미지다(/public/3d/pen.webp,
 * crayon.webp). 지우개(eraser.webp)는 지우개 전용 이모지가 없어 Sketchfab의
 * "eraser" 3D 모델(by Mr.Photon/@blender.2009, CC Attribution 4.0 — 다른
 * 에셋과 달리 저작자 표시가 필요한 라이선스라 여기 남겨둔다) 렌더 이미지를
 * 썼다. 되돌리고 싶으면 Home.tsx에서 이 컴포넌트 호출을 원래 Icon3D로 바꾸면
 * 된다. */

// 자모 덩어리 하나를 그리는 데 걸리는 시간 — 글자마다 덩어리 수가 달라서
// (보=1, 험/형=3, 광/펜=4) 글자 전체 시간도 자연스럽게 복잡도에 비례한다.
const GROUP_DURATION = 0.55;
const PEN_FADE = 0.12;
const CHAR_GAP = 0.15;
// mask stroke 굵기 = 그 자모 덩어리 bbox의 짧은 쪽 변 × 이 비율. 너무 얇으면
// 안이 뚫린 자모(ㅁ/ㅇ/ㅎ)가 속이 빈 테두리로 보이고, 너무 두꺼우면 획이
// 뭉개진 덩어리로 보인다.
const MASK_WIDTH_RATIO = 0.55;
// 펜 에셋(pen.webp) 안에서 실제 펜촉이 있는 위치 — 이미지 왼쪽아래 모서리
// 근처. 이 비율만큼 이미지를 당겨서 촉이 좌표에 정확히 붙게 한다.
const PEN_W = 760;
const PEN_H = 760;
const TIP_FRAC_X = 0.1;
const TIP_FRAC_Y = 0.92;

export function PenWriteCompass() {
  const rootRef = useRef<HTMLSpanElement>(null);
  const maskStrokeRefs = useRef<(SVGPathElement | null)[][]>(PEN_GLYPH_PATHS.map(() => []));
  const penRefs = useRef<(SVGImageElement | null)[]>([]);
  const highlightBgRef = useRef<HTMLSpanElement>(null);
  const highlighterRef = useRef<HTMLImageElement>(null);
  const eraserRef = useRef<HTMLImageElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    // 마스크 획 굵기는 자모 덩어리 크기에 비례해야 하므로, 실제 렌더된 후
    // getBBox로 한 번씩 재서 stroke-width/dasharray/dashoffset 기본값을
    // 잡아둔다(반응형 폰트 크기 변화와 무관하게 그 svg 내부 좌표 단위 기준).
    maskStrokeRefs.current.forEach((group) => {
      group.forEach((el) => {
        if (!el) return;
        const box = el.getBBox();
        const width = Math.max(1, Math.min(box.width, box.height) * MASK_WIDTH_RATIO);
        const len = el.getTotalLength();
        el.style.strokeWidth = String(width);
        el.style.strokeDasharray = String(len);
        el.style.strokeDashoffset = String(len);
      });
    });

    const ctx = gsap.context(() => {
      // 처음 마운트될 때뿐 아니라 반복(repeat:-1)될 때마다 매번 이 상태로
      // 되돌아가야 한다 — 타임라인 밖(gsap.set)에 한 번만 넣으면 두 번째
      // 루프부터는 지난 사이클에 다 써진 상태 그대로 남아서 "쓰기 전인
      // 글자도 보이는" 버그가 생긴다. 그래서 타임라인 맨 앞의 tl.set으로 넣어
      // 매 루프 시작마다 다시 초기화되게 한다.
      const tl = gsap.timeline({ repeat: -1, defaults: { ease: "none" } });
      tl.set(penRefs.current, { autoAlpha: 0 });
      tl.set(highlightBgRef.current, { scaleX: 0, opacity: 0, transformOrigin: "left center" });
      tl.set(highlighterRef.current, { left: "-8%", opacity: 0 });
      tl.set(eraserRef.current, { left: "-8%", top: "-18%", opacity: 0 });
      tl.set(textRef.current, { clipPath: "inset(0 0 0 0%)" });

      // ① 한 글자씩, 자모 덩어리(groups) 단위로 순서대로 쓴다 — 각 덩어리의
      // 실제 윤곽선을 stroke-dasharray/dashoffset으로 점점 그려나가고(mask),
      // 펜은 같은 path의 같은 진행률 지점을 따라간다.
      PEN_GLYPH_PATHS.forEach((_g, i) => {
        const pen = penRefs.current[i];
        if (!pen) return;

        tl.to(pen, { autoAlpha: 1, duration: PEN_FADE });
        maskStrokeRefs.current[i].forEach((strokeEl) => {
          if (!strokeEl) return;
          const len = strokeEl.getTotalLength();

          tl.set(strokeEl, { strokeDashoffset: len });
          tl.to(
            {},
            {
              duration: GROUP_DURATION,
              onUpdate() {
                const dist = this.progress() * len;
                const p = strokeEl.getPointAtLength(dist);
                // 획 방향을 따라 매 프레임 회전시키면 펜이 이리저리 돌아가며
                // 부자연스럽게 흔들려 보인다 — 실제로 손에 쥔 펜처럼 항상
                // 같은 대각선 각도(오른쪽 위→왼쪽 아래)를 유지한다.
                pen.setAttribute("transform", `translate(${p.x} ${p.y}) rotate(45)`);
                strokeEl.style.strokeDashoffset = String(len - dist);
              },
            },
          );
        });
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
      // 지우개가 실제로 지나간 만큼만 지워지게 한다.
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
            {g.groups.map((groupD, j) => (
              <g key={j}>
                <mask id={`pwc-mask-${i}-${j}`} maskUnits="userSpaceOnUse" x={g.x} y={g.y} width={g.width} height={g.height}>
                  <path
                    ref={(el) => {
                      maskStrokeRefs.current[i][j] = el;
                    }}
                    className="pwc__char-mask-stroke"
                    d={groupD}
                  />
                </mask>
                <path className="pwc__char-fill-live" d={groupD} mask={`url(#pwc-mask-${i}-${j})`} />
              </g>
            ))}
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
