import { useEffect, useRef } from "react";
import gsap from "gsap";
import { PEN_GLYPH_PATHS } from "../generated/penGlyphPaths";

/** 홈 화면 히어로(나침반 자리)를 대신하는 애니메이션. GSAP 타임라인
 * (gsap.timeline({repeat:-1}))으로 ① "보험형광펜"을 한 글자씩, 자모(잉크
 * 덩어리) 단위로 실제 쓰는 순서대로 그림 → ② 다 쓰면 노란 형광펜이 등장해
 * 왼쪽부터 훑으며 하이라이트를 칠함 → ③ 잠깐 멈췄다가 뿌옇게 흐려지며 사라짐
 * → 처음(빈 화면)으로 돌아가 반복한다. (떠다니는 펜 아이콘은 뺐다 — 글자
 * 자체가 순서대로 그려지는 것만으로 충분하다는 피드백.)
 *
 * 글자는 학교안심 민들레홀씨 R(KERIS, OFL) 폰트에서 opentype.js로 뽑은 실제
 * 글리프 윤곽선이다(scripts/extract-glyph-paths.mjs → src/generated/
 * penGlyphPaths.ts). 컨투어(잉크 덩어리)를 자모 단위로 묶고 실제 쓰는 순서
 * (초성→중성→종성)로 정렬해 groups 배열에 담아 뒀다.
 *
 * 각 자모 덩어리의 실제 윤곽선을 stroke-dasharray/dashoffset으로 점점
 * 그려나간다. 그 그려지는 선을 화면에 직접 보여주지 않고 <mask>로만 써서,
 * 그 아래 꽉 찬 자모 모양(fill)을 획이 지나간 만큼만 드러낸다 — 그냥
 * 윤곽선을 그대로 보여주면 ㅁ/ㅇ/ㅎ처럼 안이 뚫린 자모가 속이 빈 테두리로
 * 보이기 때문. mask 획 굵기는 자모 덩어리 자신의 bbox(getBBox)에서 계산하되,
 * ㅣ처럼 가늘고 긴 덩어리는 굵기를 훨씬 두껍게 잡는다(안 그러면 짧은 변의
 * 일부만 덮여서 가운데가 빈 것처럼 보인다).
 *
 * "보"는 이 폰트 안에서 ㅂ과 ㅗ가 서로 닿아 있어서 컨투어가 통째로 하나뿐이라
 * (extract-glyph-paths.mjs의 자모 묶기 로직으로는) ㅂ/ㅗ를 분리할 수 없다.
 * 한때 위/아래 두 구간으로 clip-path 사각형을 키워서 순서를 강제해 봤지만,
 * 그러면 실제로 획을 그리는 게 아니라 "위에서 아래로 투명한 벽이 사라지는"
 * 것처럼 보인다는 피드백을 받았다 — 정확한 ㅂ/ㅗ 순서보다 진짜 손으로 쓰는
 * 느낌(mask+stroke-dasharray로 윤곽선을 실제로 따라가며 그려지는 것)이 더
 * 중요하다고 판단해 되돌렸다. 그래서 "보"도 다른 글자와 똑같이 하나의
 * 윤곽선을 그대로 따라가며 그려진다 — ㅂ→ㅗ 완벽한 순서는 아니지만(이
 * 폰트의 실제 윤곽선이 그 둘을 하나로 이어 그리기 때문), 획이 실제로
 * "쓰이는" 느낌은 유지된다.
 *
 * 형광펜은 이 앱의 다른 아이콘과 같은 출처(Fluent Emoji 3D, MIT License,
 * Microsoft)에서 받은 실제 3D 렌더 이미지다(/public/3d/crayon.webp).
 * 되돌리고 싶으면 Home.tsx에서 이 컴포넌트 호출을 원래 Icon3D로 바꾸면 된다. */

// 자모 덩어리 하나를 그리는 데 걸리는 시간 — 글자마다 덩어리 수가 달라서
// (보=1→2밴드, 험/형=3, 광/펜=4) 글자 전체 시간도 자연스럽게 복잡도에
// 비례한다.
const GROUP_DURATION = 1.65;
const CHAR_GAP = 0.1;
// mask stroke 굵기 = bbox 짧은 쪽 변 × 비율. ㅁ/ㅇ/ㅎ처럼 널찍한(정사각形에
// 가까운) 덩어리는 bbox가 "구멍 크기"를 반영하므로 낮은 비율이 맞지만, ㅣ처럼
// 가늘고 긴 획은 bbox의 짧은 변 자체가 이미 실제 잉크 굵기라서 낮은 비율을
// 쓰면 다 못 덮어 속이 비어(테두리만 남아) 보인다 — 그래서 세로:가로 비율이
// 큰(elongated) 덩어리는 훨씬 높은 비율을 쓴다.
const MASK_WIDTH_RATIO_COMPACT = 0.55;
const MASK_WIDTH_RATIO_ELONGATED = 0.95;
const ELONGATED_ASPECT_THRESHOLD = 2.5;

export function PenWriteCompass() {
  const rootRef = useRef<HTMLSpanElement>(null);
  const maskStrokeRefs = useRef<(SVGPathElement | null)[][]>(PEN_GLYPH_PATHS.map(() => []));
  const highlightBgRef = useRef<HTMLSpanElement>(null);
  const highlighterRef = useRef<HTMLImageElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    // 마스크 획 굵기는 자모 덩어리 크기에 비례해야 하므로, 실제 렌더된 후
    // getBBox로 한 번씩 재서 stroke-width/dasharray/dashoffset 기본값을
    // 잡아둔다(반응형 폰트 크기 변화와 무관하게 그 svg 내부 좌표 단위 기준).
    // 여기서 dashoffset을 len(= 완전히 숨김)으로 못 박아 두는 게 중요하다 —
    // 이후 타임라인의 tl.set이 매 루프 다시 같은 값으로 리셋하긴 하지만,
    // 이 초기값이 틀리면 GSAP 타임라인이 아직 준비되기 전(mount 직후 첫
    // 페인트)에 자모 일부가 잘못된 길이로 살짝 보이는 깜빡임이 생길 수 있다.
    maskStrokeRefs.current.forEach((group) => {
      group.forEach((el) => {
        if (!el) return;
        const box = el.getBBox();
        const shortSide = Math.min(box.width, box.height);
        const longSide = Math.max(box.width, box.height);
        const aspect = shortSide > 0 ? longSide / shortSide : 1;
        const ratio = aspect >= ELONGATED_ASPECT_THRESHOLD ? MASK_WIDTH_RATIO_ELONGATED : MASK_WIDTH_RATIO_COMPACT;
        const width = Math.max(1, shortSide * ratio);
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
      // 매 루프 시작마다 다시 초기화되게 한다 — 모든 자모 덩어리를 한 번에.
      const tl = gsap.timeline({ repeat: -1, defaults: { ease: "none" } });
      const allStrokes = maskStrokeRefs.current.flat().filter((el): el is SVGPathElement => !!el);
      tl.call(() => {
        allStrokes.forEach((el) => {
          el.style.strokeDashoffset = el.style.strokeDasharray;
        });
      });
      tl.set(highlightBgRef.current, { scaleX: 0, opacity: 0, transformOrigin: "left center" });
      tl.set(highlighterRef.current, { left: "-8%", opacity: 0 });
      tl.set(textRef.current, { opacity: 1, filter: "blur(0px)" });

      // ① 한 글자씩, 자모 덩어리(groups) 단위로 순서대로 그린다 — 한 번에
      // 딱 하나의 덩어리만 진행 중이고 나머지는 모두 완전히 숨겨진(dashoffset
      // = 전체 길이) 상태다.
      PEN_GLYPH_PATHS.forEach((_g, i) => {
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
                strokeEl.style.strokeDashoffset = String(len - dist);
              },
            },
          );
        });
        if (i < PEN_GLYPH_PATHS.length - 1) tl.to({}, { duration: CHAR_GAP });
      });

      tl.to({}, { duration: 0.7 });

      // ② 형광펜이 왼쪽부터 훑으며 노란 하이라이트를 칠한다.
      tl.to(highlighterRef.current, { opacity: 1, left: "-3%", duration: 0.15 });
      tl.to(highlighterRef.current, { left: "94%", duration: 1.9 }, "<");
      tl.to(highlightBgRef.current, { scaleX: 1, opacity: 1, duration: 1.9 }, "<");
      tl.to(highlighterRef.current, { left: "100%", opacity: 0, duration: 0.2 });

      tl.to({}, { duration: 1.2 });

      // ③ 다 쓰인 글자+하이라이트가 통째로 뿌옇게 흐려지며(blur) 옅어지다
      // 사라진다.
      tl.to(textRef.current, { opacity: 0, filter: "blur(14px)", duration: 1.4 });

      tl.to({}, { duration: 0.4 });
    }, rootRef);

    return () => ctx.revert();
  }, []);

  return (
    <span className="pwc" ref={rootRef} aria-hidden="true">
      <img className="pwc__highlighter" ref={highlighterRef} src="/3d/crayon.webp" alt="" />
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
          </svg>
        ))}
        <span className="pwc__highlight-bg" ref={highlightBgRef} />
      </span>
    </span>
  );
}
