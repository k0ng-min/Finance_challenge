import { Fragment, useEffect, useRef } from "react";
import gsap from "gsap";
import {
  PEN_STROKE_GLYPHS,
  PEN_STROKE_VIEWBOX,
} from "../generated/penStrokeGlyphs";

/** 홈 화면 히어로(나침반 자리)를 대신하는 애니메이션. GSAP 타임라인으로
 * ① "보험형광펜"을 한 글자씩, 진짜 필순(획 순서)대로 그림 → ② 다 쓰면 노란
 * 형광펜이 위아래로 살짝 흔들리며 왼쪽부터 훑어 하이라이트를 칠함 →
 * ③ 다 칠해진 결과를 HOLD_DURATION 동안 그대로 유지 → ④ 희미하게 흐려지며
 * 사라진 뒤 처음부터 다시 재생한다.
 *
 * ── 글자를 그리는 방식 (scripts/source/boheom-handwriting.html 과 동일) ──
 * 예전에는 글리프의 "닫힌 윤곽선"을 통째로 따라 그리며 그걸 mask로 썼다.
 * 그래서 ㅁ/ㅇ처럼 구멍 있는 자모나 ㅣ처럼 가는 획에서 획이 끊겨 보이거나,
 * 윤곽선을 되짚는 구간에서 펜이 멈춘 것처럼 보이거나, "보"처럼 ㅂ+ㅗ가 한
 * 덩어리인 글자는 필순이 아예 무시되는 문제가 계속 났다 — 윤곽선에는 애초에
 * "획"이라는 정보가 없기 때문에 생기는 구조적인 한계였다.
 *
 * 지금은 획 단위 데이터를 쓴다(src/generated/penStrokeGlyphs.ts,
 * scripts/extract-stroke-glyphs.mjs). 글자마다 획이 필순대로 들어 있고, 각
 * 획은
 *   · median — 펜이 실제로 지나가는 중심선
 *   · clip   — 그 획 하나의 윤곽선
 *   · width  — 그 획을 빠짐없이 덮는 붓 굵기
 * 로 이루어진다. 중심선을 stroke-dasharray/dashoffset으로 그어 나가는 걸
 * <mask>로 쓰고 그 획의 윤곽선(clipPath)으로 잘라내면, 붓이 지나간 만큼만
 * "그 획 모양 그대로" 드러난다 — 굵기가 변하는 획 끝(삐침)까지 폰트 모양
 * 그대로 나오고, 획이 끊기거나 되짚는 구간도 없다. 마스크 아래에는 다 쓴
 * 글자의 완성된 윤곽선(outline) 하나만 깔려 있다.
 *
 * 글자는 학교안심 민들레홀씨 R(KERIS, OFL / 공공누리 1유형·출처표시)의 실제
 * 글리프이고, 필순 데이터도 그 원본 HTML에서 그대로 가져왔다.
 *
 * 형광펜(/public/3d/highlighter.webp)은 Pixabay 3D Models(Pixabay Content
 * License, 무료 사용 가능)의 형광펜 GLB(원래 초록색)를 three.js로 렌더링해서
 * 몸통을 노란색으로 리컬러한 뒤 정지 이미지로 뽑아낸 것이다. 되돌리고 싶으면
 * Home.tsx에서 이 컴포넌트 호출을 원래 Icon3D로 바꾸면 된다. */

// "보험형광펜"을 다 쓰는 데 걸리는 전체 시간(초). 획마다의 상대적인 리듬
// (긴 획은 오래, 짧은 획은 금방, 글자와 글자 사이는 조금 쉬고)은 원본 그대로
// 두고, 그 리듬 전체를 이 시간에 딱 맞게 늘려 쓴다.
//
// 홈 히어로는 사용자가 머무는 화면이라 천천히 쓰는 편이 보기 좋지만, 로딩 화면은
// 몇 초 만에 끝나는 기다림이라 같은 속도로 두면 형광펜이 나오기도 전에 화면이
// 넘어간다. 그래서 화면마다 다르게 줄 수 있도록 props로 뺐다(기본값은 홈 기준).
const WRITE_DURATION = 15;
// 원본의 획 하나당 시간(ms) = STROKE_BASE_MS + 길이 × STROKE_LENGTH_MS.
// 짧은 획도 최소한의 시간은 갖게 하는 상수항이다.
const STROKE_BASE_MS = 90;
const STROKE_LENGTH_MS = 0.55;
// 같은 글자 안에서 획과 획 사이의 쉼(ms).
const STROKE_GAP_MS = 40;
// 글자가 바뀔 때의 쉼(ms) — 손으로 쓸 때 글자 사이에서 잠깐 뜸 들이는 느낌.
const CHAR_GAP_MS = 230;
// 다 칠해진 뒤 그 결과를 그대로 유지하는 시간(초).
const HOLD_DURATION = 10;
// 유지 시간이 끝나고 희미하게 흐려지며 사라지는 시간.
const FADE_OUT_DURATION = 1.2;
// 형광펜 띠는 실제 글자(잉크)가 차지하는 범위를 기준으로 잡되, 위아래로 이만큼
// (글자 높이 대비 비율) 더 넉넉히 덮는다 — 실제로 형광펜을 그으면 글자보다
// 조금씩 넘치게 칠해지기 때문.
const HIGHLIGHT_PAD_TOP = 0.1;
const HIGHLIGHT_PAD_BOTTOM = 0.08;
const HIGHLIGHT_PAD_X = 0.02;
// 형광펜이 글자 왼쪽에서 얼마나 앞서 들어와 오른쪽으로 얼마나 지나쳐 나가는지 —
// 글자 폭 대비 비율이다. 바깥 상자(.pwc) 폭에 대한 고정 비율로 두면, 글씨가 작은
// 화면(로딩)에서는 글자보다 훨씬 앞에서 시작해 훨씬 뒤까지 지나가 버린다.
const SWEEP_LEAD_IN = 0.1;
const SWEEP_LEAD_OUT = 0.06;

const [VB_X, VB_Y, VB_W, VB_H] = PEN_STROKE_VIEWBOX.split(/\s+/).map(Number);

export function PenWriteCompass({
  writeDuration = WRITE_DURATION,
  holdDuration = HOLD_DURATION,
  className,
}: {
  /** "보험형광펜"을 다 쓰는 데 걸리는 시간(초). */
  writeDuration?: number;
  /** 형광펜을 다 칠한 뒤 그 결과를 그대로 두는 시간(초). 이 시간이 지나면 흐려지며 사라지고 처음부터 다시 쓴다. */
  holdDuration?: number;
  /** 크기를 화면에 맞게 줄일 때 쓴다(예: 로딩 화면). */
  className?: string;
} = {}) {
  const rootRef = useRef<HTMLSpanElement>(null);
  const wordRef = useRef<SVGGElement>(null);
  // 획 중심선(마스크) — 원본과 같은 필순 순서로 평평하게 담는다.
  const strokeRefs = useRef<(SVGPathElement | null)[]>([]);
  const highlightBgRef = useRef<HTMLSpanElement>(null);
  const highlighterRef = useRef<HTMLImageElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  // 형광펜이 훑을 구간(바깥 상자 .pwc 폭에 대한 %). 실제 글자 위치를 재서 채운다.
  const sweepRef = useRef({ start: "-8%", end: "94%", exit: "100%" });

  // 형광펜 띠를 실제 글자가 차지하는 자리에 맞춘다. 글자를 하나의 svg
  // 좌표계에 그리기 때문에, 띠 위치도 그 좌표계에서 재서 %로 환산해야
  // 글꼴 크기가 바뀌어도(반응형) 항상 글자에 딱 맞는다.
  useEffect(() => {
    const bg = highlightBgRef.current;
    const word = wordRef.current;
    if (!bg || !word) return;
    const box = word.getBBox();
    if (!box.width || !box.height) return;
    const left = (box.x - VB_X) / VB_W - HIGHLIGHT_PAD_X;
    const right = (box.x + box.width - VB_X) / VB_W + HIGHLIGHT_PAD_X;
    const top = (box.y - VB_Y) / VB_H - HIGHLIGHT_PAD_TOP * (box.height / VB_H);
    const bottom =
      (box.y + box.height - VB_Y) / VB_H + HIGHLIGHT_PAD_BOTTOM * (box.height / VB_H);
    bg.style.left = `${left * 100}%`;
    bg.style.right = `${(1 - right) * 100}%`;
    bg.style.top = `${top * 100}%`;
    bg.style.bottom = `${(1 - bottom) * 100}%`;

    // 형광펜은 글자 상자(.pwc__text)가 아니라 바깥 상자(.pwc) 안에서 움직인다.
    // 두 상자는 폭이 다르다 — 글씨가 작은 화면에서는 글자 상자가 훨씬 좁다.
    // 그래서 글자가 실제로 차지하는 구간을 바깥 상자 기준으로 환산해 두고,
    // 펜이 딱 그 구간만 훑게 한다. 안 그러면 로딩 화면에서 글자보다 한참 앞에서
    // 시작해 한참 뒤까지 지나간다.
    const root = rootRef.current;
    const text = textRef.current;
    if (!root || !text) return;
    const rootRect = root.getBoundingClientRect();
    const textRect = text.getBoundingClientRect();
    if (!rootRect.width || !textRect.width) return;
    const textOffset = (textRect.left - rootRect.left) / rootRect.width;
    const textScale = textRect.width / rootRect.width;
    const inkLeft = textOffset + left * textScale;
    const inkRight = textOffset + right * textScale;
    const inkWidth = inkRight - inkLeft;
    sweepRef.current = {
      start: `${(inkLeft - SWEEP_LEAD_IN * inkWidth) * 100}%`,
      end: `${(inkRight - SWEEP_LEAD_OUT * inkWidth) * 100}%`,
      exit: `${(inkRight + SWEEP_LEAD_OUT * inkWidth) * 100}%`,
    };
  }, []);

  useEffect(() => {
    const strokes = strokeRefs.current.filter((el): el is SVGPathElement => !!el);

    // 획마다 자기 길이만큼의 dash를 만들어 두고 완전히 밀어 둔다(= 아직 안
    // 그려진 상태). 빈 간격을 길이보다 살짝(+12) 크게 잡는 건, 다 그린 뒤
    // dash가 정확히 맞물려 다음 패턴이 시작점에 겹쳐 보이는 걸 막기 위함이다.
    const lengths = strokes.map((el) => el.getTotalLength());
    strokes.forEach((el, i) => {
      const len = lengths[i];
      el.style.strokeDasharray = `${len} ${len + 12}`;
      el.style.strokeDashoffset = String(len);
      el.style.visibility = "visible";
    });

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      // 애니메이션 없이 완성된 글자만 보여준다.
      strokes.forEach((el) => {
        el.style.strokeDashoffset = "0";
      });
      const bg = highlightBgRef.current;
      if (bg) bg.style.opacity = "1";
      return;
    }

    // 획이 몇 번째 글자에 속하는지 — 글자가 바뀌는 자리에서만 좀 더 쉰다.
    const charOfStroke: number[] = [];
    PEN_STROKE_GLYPHS.forEach((g, gi) => g.strokes.forEach(() => charOfStroke.push(gi)));

    // 원본의 리듬(획 길이에 비례한 시간 + 쉼)을 그대로 계산한 뒤, 전체 합이
    // WRITE_DURATION이 되도록 한 번에 같은 비율로 늘린다 — 글자를 바꿔도 항상
    // 이 시간 안에 끝나면서, 획끼리의 상대적인 속도감은 원본과 똑같이 남는다.
    const rawDurations = lengths.map((len) => STROKE_BASE_MS + len * STROKE_LENGTH_MS);
    const rawGaps: number[] = strokes.map((_el, i) =>
      i + 1 < strokes.length
        ? charOfStroke[i + 1] !== charOfStroke[i]
          ? CHAR_GAP_MS
          : STROKE_GAP_MS
        : 0,
    );
    const rawTotal = rawDurations.reduce((a, b) => a + b, 0) + rawGaps.reduce((a, b) => a + b, 0);
    const scale = rawTotal > 0 ? (writeDuration * 1000) / rawTotal : 0;

    const ctx = gsap.context(() => {
      // 유지 시간(HOLD_DURATION)을 타임라인 안에 넣고, 타임라인이 끝나면
      // onComplete에서 restart를 부른다 — setInterval로 돌리면 "글 쓰는 시간"까지
      // 그 간격에 포함돼서 실제 유지 시간이 짧아진다.
      const tl = gsap.timeline({ defaults: { ease: "none" } });

      // 매 루프 처음 상태로 되돌린다(안 되돌리면 지난번에 다 써진 글자가 그대로
      // 남아서 "쓰기 전인데 이미 보이는" 상태가 된다).
      strokes.forEach((el, i) => {
        tl.set(el, { strokeDashoffset: lengths[i] }, 0);
      });
      tl.set(highlightBgRef.current, { scaleX: 0, opacity: 0, transformOrigin: "left center" }, 0);
      tl.set(highlighterRef.current, { left: sweepRef.current.start, opacity: 0 }, 0);
      tl.set(textRef.current, { opacity: 1, filter: "blur(0px)" }, 0);

      // ① 한 획씩 필순대로 그린다 — 한 번에 딱 하나의 획만 진행 중이다.
      let at = 0;
      strokes.forEach((el, i) => {
        const duration = (rawDurations[i] * scale) / 1000;
        tl.to(el, { strokeDashoffset: 0, duration, ease: "power1.out" }, at);
        at += duration + (rawGaps[i] * scale) / 1000;
      });

      tl.to({}, { duration: 0.7 }, at);

      // ② 형광펜이 왼쪽부터 훑으며 노란 하이라이트를 칠한다. 실제로 형광펜으로
      // 넓은 부분을 칠할 때처럼, 글자 가운데 높이를 기준으로 위아래로 크게
      // 왔다갔다(지그재그) 하면서 오른쪽으로 나아간다 — 오른쪽 이동(left)과
      // 위아래 왕복(y)을 같은 구간에 겹쳐 돌려서 만든다.
      const SWEEP_DURATION = 3;
      // 위아래 "왕복" 횟수. 한 번 왕복 = 내려갔다 올라오기(2번 이동)이므로
      // 실제 이동 횟수는 2배다.
      const ZIGZAG_ROUND_TRIPS = 16;
      const ZIGZAG_LEG_COUNT = ZIGZAG_ROUND_TRIPS * 2;
      // 글자 위아래 틀 밖으로 펜이 튀어나가지 않을 만큼만 흔든다 — 펜 이미지
      // 자체가 글자 높이와 비슷해서, 진폭을 키우면 바로 틀을 벗어난다(실측으로
      // 13일 때 위아래로 8~9px씩 삐져나왔다).
      const ZIGZAG_AMPLITUDE = 5;

      // 형광펜의 가로 이동과 노란 띠가 차오르는 것이 "정확히 같은 시각에
      // 시작해서 같은 시간 동안" 진행되어야 속도가 맞아 보인다.
      const sweepStart = "pwcSweep";
      tl.addLabel(sweepStart);
      tl.to(highlighterRef.current, { opacity: 1, duration: 0.15 }, sweepStart);
      tl.to(highlighterRef.current, { left: sweepRef.current.end, duration: SWEEP_DURATION }, sweepStart);
      tl.to(highlightBgRef.current, { scaleX: 1, opacity: 1, duration: SWEEP_DURATION }, sweepStart);
      // 위쪽 끝에서 출발해 아래로 내려갔다 올라오길 반복한다.
      tl.set(highlighterRef.current, { y: -ZIGZAG_AMPLITUDE }, sweepStart);
      tl.to(
        highlighterRef.current,
        {
          y: ZIGZAG_AMPLITUDE,
          duration: SWEEP_DURATION / ZIGZAG_LEG_COUNT,
          repeat: ZIGZAG_LEG_COUNT - 1,
          yoyo: true,
          ease: "sine.inOut",
        },
        sweepStart,
      );
      // 훑기가 끝나는 시각에 맞춰 펜을 가운데 높이로 돌려놓고 화면 밖으로 뺀다.
      tl.set(highlighterRef.current, { y: 0 }, `${sweepStart}+=${SWEEP_DURATION}`);
      tl.to(
        highlighterRef.current,
        { left: sweepRef.current.exit, opacity: 0, duration: 0.2 },
        `${sweepStart}+=${SWEEP_DURATION}`,
      );

      // ③ 다 칠해진 상태로 holdDuration 동안 그대로 유지된다.
      tl.to({}, { duration: holdDuration });

      // ④ 유지 시간이 끝나면 갑자기 사라지지 않고 희미하게 흐려지며 사라진다.
      // 이 페이드가 끝난 직후 타임라인이 끝나고, onComplete가 곧바로
      // 처음부터 다시 재생시킨다(= 자연스럽게 이어지는 사이클).
      tl.to(textRef.current, {
        opacity: 0,
        filter: "blur(10px)",
        duration: FADE_OUT_DURATION,
        ease: "power1.in",
      });

      tl.eventCallback("onComplete", () => tl.restart());
    }, rootRef);

    return () => ctx.revert();
  }, [writeDuration, holdDuration]);

  // 필순대로 평평하게 매기는 획 번호 — ref 배열의 자리와 맞춘다.
  let strokeIndex = 0;

  return (
    <span className={`pwc${className ? ` ${className}` : ""}`} ref={rootRef} aria-hidden="true">
      <img className="pwc__highlighter" ref={highlighterRef} src="/3d/highlighter.webp" alt="" />
      <span className="pwc__text" ref={textRef}>
        <svg className="pwc__word" viewBox={PEN_STROKE_VIEWBOX} preserveAspectRatio="xMidYMid meet">
          <defs>
            {PEN_STROKE_GLYPHS.map((glyph, gi) => (
              <Fragment key={glyph.char}>
                {glyph.strokes.map((stroke, si) => (
                  <clipPath key={si} id={`pwc-clip-${gi}-${si}`} clipPathUnits="userSpaceOnUse">
                    <path d={stroke.clip} />
                  </clipPath>
                ))}
                {/* 그 글자의 획들을 다 담은 마스크 — 지금까지 그어진 붓 자국만
                    흰색이라, 아래 완성된 글자 모양이 그만큼만 드러난다. */}
                <mask
                  id={`pwc-mask-${gi}`}
                  maskUnits="userSpaceOnUse"
                  x="-200"
                  y="-200"
                  width="1400"
                  height="1400"
                >
                  {glyph.strokes.map((stroke, si) => {
                    const flatIndex = strokeIndex++;
                    return (
                      <g key={si} clipPath={`url(#pwc-clip-${gi}-${si})`}>
                        <path
                          ref={(el) => {
                            strokeRefs.current[flatIndex] = el;
                          }}
                          className="pwc__word-stroke"
                          d={stroke.median}
                          strokeWidth={stroke.width}
                        />
                      </g>
                    );
                  })}
                </mask>
              </Fragment>
            ))}
          </defs>
          <g ref={wordRef}>
            {PEN_STROKE_GLYPHS.map((glyph, gi) => (
              <g key={glyph.char} transform={`translate(${glyph.offsetX},0)`}>
                <g mask={`url(#pwc-mask-${gi})`}>
                  <g transform={glyph.glyphTransform}>
                    <path className="pwc__char-fill-live" d={glyph.outline} />
                  </g>
                </g>
              </g>
            ))}
          </g>
        </svg>
        <span className="pwc__highlight-bg" ref={highlightBgRef} />
      </span>
      {/* 실제 형광펜은 가장자리가 매끈한 직선이 아니라 종이 결을 타고 살짝
          울퉁불퉁하다 — feTurbulence로 만든 잡음을 feDisplacementMap으로
          pwc__highlight-bg의 테두리에 입혀서 그 느낌을 낸다(app.css에서
          filter: url(#pwc-marker-rough)로 적용). 화면에 안 보이는 필터
          정의만 필요해서 0x0 크기로 둔다. */}
      <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
        <defs>
          <filter id="pwc-marker-rough" x="-20%" y="-150%" width="140%" height="400%">
            <feTurbulence type="fractalNoise" baseFrequency="0.9 0.12" numOctaves="2" seed="7" result="pwcNoise" />
            <feDisplacementMap in="SourceGraphic" in2="pwcNoise" scale="7" xChannelSelector="R" yChannelSelector="G" />
          </filter>
        </defs>
      </svg>
    </span>
  );
}
