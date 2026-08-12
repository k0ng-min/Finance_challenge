import { useEffect, useRef } from "react";
import gsap from "gsap";
import { PEN_GLYPH_PATHS } from "../generated/penGlyphPaths";

/** 홈 화면 히어로(나침반 자리)를 대신하는 애니메이션. GSAP 타임라인로
 * ① "보험형광펜"을 한 글자씩, 자모(잉크 덩어리) 단위로 실제 쓰는 순서대로
 * 그림 → ② 다 쓰면 노란 형광펜이 위아래로 살짝 흔들리며 왼쪽부터 훑어
 * 하이라이트를 칠함 → ③ 다 칠해진 결과를 HOLD_DURATION(15초) 동안 그대로
 * 유지 → ④ 희미하게 흐려지며 사라진 뒤 처음부터 다시 재생한다. 쉬지 않고
 * 도는 루프가 아니라 "칠한 결과가 한참 유지되다가 가끔 다시 그려지는" 느낌을
 * 원한다는 요청이라, 유지 시간을 타임라인 안에 넣고 onComplete에서
 * restart를 부른다. (떠다니는 펜 아이콘은 뺐다 — 글자 자체가 순서대로
 * 그려지는 것만으로 충분하다는 피드백.)
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
 * 보이기 때문. mask 획 굵기는 그 덩어리의 실제 평균 잉크 두께(넓이/둘레로
 * 추정해 build time에 계산해 둔 groupStrokeWidths — extract-glyph-paths.mjs의
 * estimateGroupStrokeWidth 참고)를 기준으로 잡는다. 예전에는 자모 덩어리 자신의
 * bbox(getBBox) 짧은 변으로 어림잡았는데, "보"처럼 ㅂ+ㅗ가 폰트 안에서 하나로
 * 합쳐진 덩어리는 bbox가 실제 잉크 두께가 아니라 글자 전체 크기를 반영해
 * 버려서(짧은 변도 커짐) 두께를 심하게 잘못 추정했다 — 그 부분적으로 가는
 * 구간이 못 덮여서 획이 끊겨 보이는 원인이었다. 넓이/둘레 비율은 도형이
 * 단순한 획이든, ㅁ/ㅇ/ㅎ처럼 구멍이 있든, "보"처럼 여러 자모가 합쳐진
 * 덩어리든 상관없이 항상 실제 평균 두께로 수렴하는 기하학적 관계라 훨씬
 * 견고하다(실측해보면 이 폰트는 모든 자모의 두께가 약 60~68 유닛으로 고르게
 * 나온다). 이 mask 두께는 오직 "실제 잉크를 놓치지 않고 다 덮는" 용도로만
 * 넉넉하게 잡고, 화면에 보이는 글자 굵기는 fill 위에 배경색으로 한 겹 더
 * 그리는 pwc__char-erode-stroke로 가장자리를 살짝 깎아 조절한다 — 둘을 하나의
 * 값으로 겸용하면(얇게 하려고 mask를 줄이면) 커버리지가 깨져서 획이 끊겨
 * 보이는 문제가 생긴다.
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
 * 형광펜(/public/3d/highlighter.webp)은 Pixabay 3D Models(Pixabay Content
 * License, 무료 사용 가능)의 형광펜 GLB(원래 초록색)를 three.js로 렌더링해서
 * 몸통을 노란색으로 리컬러한 뒤 정지 이미지로 뽑아낸 것이다. 되돌리고 싶으면
 * Home.tsx에서 이 컴포넌트 호출을 원래 Icon3D로 바꾸면 된다. */

// "보험형광펜"을 다 쓰는 데 걸리는 전체 시간(초). 각 자모 덩어리에 같은 시간을
// 주면 ㅎ의 작은 고리처럼 짧은 획도 큰 원만큼 오래 걸려서 "거의 안 자라는 작은
// 점" 상태로 한참 머문다 — 그래서 이 전체 시간을 각 덩어리의 실제 획 길이에
// 비례해서 나눠 갖는다(짧은 획은 금방, 긴 획은 그만큼 오래). 속도를 고정하는
// 대신 전체 시간을 고정하는 방식이라, 글자를 바꿔도 항상 이 시간 안에 끝난다.
const WRITE_DURATION = 15;
// 글자와 글자 사이의 아주 짧은 쉼(초). 실제로 손으로 쓸 때도 글자 사이에는
// 살짝 뜸이 있지만, 길면 "쓰다가 멈칫하는" 것처럼 보여서 최소한만 준다.
const CHAR_GAP = 0.02;
// 다 칠해진 뒤 그 결과를 그대로 유지하는 시간(초) — "칠한 시점부터 15초 동안
// 유지"라서, 글 쓰는 시간이 아니라 칠하기가 끝난 시점부터 센다.
const HOLD_DURATION = 10;
// 유지 시간이 끝나고 희미하게 흐려지며 사라지는 시간.
const FADE_OUT_DURATION = 1.2;
// mask stroke 굵기 = build time에 계산해 둔 실제 평균 잉크 두께
// (penGlyphPaths.ts의 groupStrokeWidths) × 안전 배율.
//
// ㅣ처럼 가늘고 긴 획은 윤곽선이 "한쪽 옆면을 타고 내려갔다가 반대쪽 옆면을
// 타고 올라오는" 두 옆면으로 이루어진 좁은 루프다 — 붓이 실제 잉크 두께의
// 절반보다만 넓으면(예전처럼 1.35배), 내려가는 옆면을 훑을 때는 아직 반대쪽
// 옆면까지 다 못 덮어서, 다시 올라오는 옆면을 훑을 때가 돼서야 마저 덮인다.
// 그러면 화면에는 "한 번에 죽 그어지는" 게 아니라 "내려갔다 다시 올라오며
// 두 번 칠하는" 것처럼 보인다 — 두께 문제가 아니라 배율이 부족해서 생기는
// 별개의 문제다. 내려가는 옆면 한 번만으로 반대쪽까지 다 덮으려면 붓
// 폭(지름)이 실제 두께의 최소 2배는 돼야 하므로(붓이 옆면 위에 중심을 두고
// 반지름만큼 반대쪽으로 뻗어야 함) 넉넉히 2.4배로 잡는다.
//
// 중요: 이 상수는 "실제 잉크를 놓치지 않고 다 덮는 안전값"으로만 써야 한다 —
// 화면에 보이는 글자 굵기를 조절하려고 이 값을 낮추면 안 된다(한 번 그렇게
// 했다가 끊긴 획이 재발했다). mask 획은 눈에 안 보이는 "펼치는 붓"일 뿐이라,
// 실제 잉크(fill)를 다 덮을 만큼만 넉넉하면 그 이상 두꺼워도 화면에 보이는
// 결과(= fill과 겹치는 부분만 보임)에는 아무 차이가 없다 — 그래서 굵기는
// 아래 EROSION_WIDTH_RATIO로 완전히 별도로 조절한다.
const MASK_WIDTH_SAFETY = 3.2;
// 화면에 보이는 글자를 살짝 얇게 보이도록, 다 채워진 자모(fill) 위에 배경색
// 테두리선을 한 겹 더 그려서 가장자리를 살짝 깎아낸다 — mask 두께와는 무관한
// 순수 화장용 레이어라 아무리 굵기를 조절해도 커버리지(끊김) 문제가 생기지
// 않는다. 각 "덩어리(group)" 자신의 bbox를 기준으로 잡으면 "보"처럼 ㅂ+ㅗ가
// 하나로 합쳐진 덩어리는 bbox가 실제 잉크 굵기가 아니라 글자 전체 크기를
// 반영해서(짧은 변도 큼) 깎아내는 테두리가 실제 잉크보다 훨씬 두꺼워져
// 글자가 통째로 지워져 버린다 — 그래서 덩어리별 bbox가 아니라 그 글자
// 전체의 em 높이(모든 글자에서 동일)를 기준으로 잡는다.
const EROSION_WIDTH_RATIO = 0;
// 이미 그려진 자리를 되짚는 구간에서 최대 몇 배까지 빨라질 수 있는지를 정한다
// (1 / MIN_NOVELTY 배). 너무 작으면 그 구간을 순간이동하듯 지나가서 "끊겼다가
// 갑자기 빨라지는" 느낌이 나고, 1에 가까우면 예전처럼 멈춘 것처럼 보인다.
const MIN_NOVELTY = 0.55;

/** 경로를 어디까지 그렸을 때 화면이 얼마나 드러나는지를 미리 재 둔 표.
 *
 * 마스크는 자모의 "닫힌 윤곽선"을 따라가는데, 붓이 실제 잉크 두께보다 훨씬
 * 넓어서(MASK_WIDTH_SAFETY) 한쪽 모서리를 지나는 순간 이미 그 획이 다 드러난다
 * — 반대편 모서리를 되짚어 올라오는 구간은 화면에 아무 변화를 주지 않는다.
 * 시간을 경로 길이에 그냥 비례해서 나눠주면 그 "아무 변화 없는" 구간에서 펜이
 * 멈춘 것처럼 보여서 글씨가 툭툭 끊겨 보인다.
 *
 * 그래서 경로를 잘게 샘플링해서, 각 지점이 "이미 지나간 곳 근처"인지
 * (= 새로 드러나는 게 없는지) 판정해 가중치를 매긴 뒤 누적한다. 애니메이션은
 * 이 누적 노출량을 일정한 속도로 올리기 때문에, 되짚는 구간은 빠르게 지나가고
 * 실제로 새 획이 나오는 구간은 차분하게 그려진다.
 */
function buildRevealProfile(el: SVGPathElement, len: number, brushRadius: number) {
  const step = Math.max(2, brushRadius / 2);
  const count = Math.min(400, Math.max(24, Math.ceil(len / step)));
  const dist = new Float64Array(count + 1);
  const reveal = new Float64Array(count + 1);
  const xs = new Float64Array(count + 1);
  const ys = new Float64Array(count + 1);

  for (let k = 0; k <= count; k++) {
    const d = (len * k) / count;
    dist[k] = d;
    const p = el.getPointAtLength(d);
    xs[k] = p.x;
    ys[k] = p.y;
  }

  // 바로 직전 몇 샘플은 원래 붙어 있는 게 정상이라(앞으로 나아가는 중) 제외하고,
  // 그보다 예전에 지나간 지점들과만 거리를 잰다.
  const skip = Math.max(2, Math.ceil(brushRadius / (len / count)));
  const radiusSq = brushRadius * brushRadius;
  let acc = 0;
  for (let k = 1; k <= count; k++) {
    let nearestSq = Infinity;
    for (let m = 0; m <= k - skip; m++) {
      const dx = xs[k] - xs[m];
      const dy = ys[k] - ys[m];
      const dsq = dx * dx + dy * dy;
      if (dsq < nearestSq) nearestSq = dsq;
    }
    // 이미 붓이 덮은 자리면 0에 가깝고, 완전히 새 자리면 1.
    const novelty = nearestSq === Infinity ? 1 : Math.min(1, Math.sqrt(nearestSq / radiusSq));
    // 되짚는 구간을 너무 많이 빨리 넘기면 "멈췄다가 갑자기 확 빨라지는" 것처럼
    // 보인다 — 최소치를 넉넉히 둬서 속도 차이가 최대 1/MIN_NOVELTY배를 넘지
    // 않게 제한한다(멈춤도, 급가속도 아닌 중간).
    acc += Math.max(MIN_NOVELTY, novelty);
    reveal[k] = acc;
  }
  if (acc > 0) for (let k = 0; k <= count; k++) reveal[k] /= acc;
  return { len, dist, reveal };
}

/** 누적 노출량 t(0~1)에 해당하는 경로 거리를 찾는다(표를 선형보간). */
function distanceForReveal(profile: { len: number; dist: Float64Array; reveal: Float64Array }, t: number) {
  const { dist, reveal } = profile;
  if (t <= 0) return 0;
  if (t >= 1) return profile.len;
  let lo = 0;
  let hi = reveal.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (reveal[mid] < t) lo = mid + 1;
    else hi = mid;
  }
  const k = Math.max(1, lo);
  const r0 = reveal[k - 1];
  const r1 = reveal[k];
  const f = r1 > r0 ? (t - r0) / (r1 - r0) : 0;
  return dist[k - 1] + (dist[k] - dist[k - 1]) * f;
}

export function PenWriteCompass() {
  const rootRef = useRef<HTMLSpanElement>(null);
  const maskStrokeRefs = useRef<(SVGPathElement | null)[][]>(PEN_GLYPH_PATHS.map(() => []));
  const erodeStrokeRefs = useRef<(SVGPathElement | null)[][]>(PEN_GLYPH_PATHS.map(() => []));
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
    // 각 마스크 획을 "화면에 새로 드러나는 양" 기준으로 진행시키기 위한 표.
    // reveal[k]는 경로를 dist[k]까지 그렸을 때의 누적 노출량(0~1)이다.
    const revealProfiles = new Map<SVGPathElement, { len: number; dist: Float64Array; reveal: Float64Array }>();

    maskStrokeRefs.current.forEach((group, i) => {
      group.forEach((el, j) => {
        if (!el) return;
        const width = Math.max(1, PEN_GLYPH_PATHS[i].groupStrokeWidths[j] * MASK_WIDTH_SAFETY);
        const len = el.getTotalLength();
        el.style.strokeWidth = String(width);
        el.style.strokeDasharray = String(len);
        el.style.strokeDashoffset = String(len);
        revealProfiles.set(el, buildRevealProfile(el, len, width / 2));

        const erodeEl = erodeStrokeRefs.current[i]?.[j];
        if (erodeEl) erodeEl.style.strokeWidth = String(Math.max(0, PEN_GLYPH_PATHS[i].height * EROSION_WIDTH_RATIO));
      });
    });

    const ctx = gsap.context(() => {
      // 유지 시간(HOLD_DURATION)을 타임라인 안에 넣고, 타임라인이 끝나면
      // onComplete에서 restart를 부른다 — setInterval로 15초마다 부르면
      // "글 쓰는 시간"까지 그 15초에 포함돼서 실제 유지 시간이 15초보다 짧아진다
      // (칠한 시점부터 15초를 온전히 유지하려면 타임라인 안에 넣어야 한다).
      // restart()는 처음부터 다시 재생하는 거라 아래 tl.set들이 여전히 필요하다
      // (매번 다시 초기화 안 하면 지난번에 다 써진 상태 그대로 남아서
      // "쓰기 전인 글자도 보이는" 버그가 생긴다).
      const tl = gsap.timeline({ defaults: { ease: "none" } });
      const allStrokes = maskStrokeRefs.current.flat().filter((el): el is SVGPathElement => !!el);
      tl.call(() => {
        allStrokes.forEach((el) => {
          el.style.strokeDashoffset = el.style.strokeDasharray;
          // 아직 자기 차례가 안 온 자모는 아예 숨겨 둔다 — round 캡이 dash
          // 길이가 0일 때도 작은 점으로 렌더링되는 걸 막기 위한 것(app.css의
          // .pwc__char-mask-stroke 주석 참고).
          el.style.visibility = "hidden";
        });
      });
      tl.set(highlightBgRef.current, { scaleX: 0, opacity: 0, transformOrigin: "left center" });
      tl.set(highlighterRef.current, { left: "-8%", opacity: 0 });
      tl.set(textRef.current, { opacity: 1, filter: "blur(0px)" });

      // ① 한 글자씩, 자모 덩어리(groups) 단위로 순서대로 그린다 — 한 번에
      // 딱 하나의 덩어리만 진행 중이고 나머지는 모두 완전히 숨겨진(dashoffset
      // = 전체 길이) 상태다.
      //
      // 시간은 경로 길이가 아니라 "그 덩어리가 화면에 실제로 드러내는 양"에
      // 비례해서 나눈다(buildRevealProfile 참고). 윤곽선을 되짚느라 아무것도
      // 안 드러나는 구간까지 길이에 넣어 시간을 주면, 그 구간에서 펜이 멈춘
      // 것처럼 보여 글씨가 툭툭 끊긴다.
      const strokeWeights = new Map<SVGPathElement, number>();
      allStrokes.forEach((el) => {
        const profile = revealProfiles.get(el);
        if (!profile) return;
        // 되짚는 구간을 뺀 "실질적으로 그리는 길이" — 노출량 곡선의 기울기가
        // 곧 새로 드러나는 속도라, 전체 길이 × 평균 기울기로 환산한다.
        let effective = 0;
        for (let k = 1; k < profile.reveal.length; k++) {
          const dr = profile.reveal[k] - profile.reveal[k - 1];
          const dd = profile.dist[k] - profile.dist[k - 1];
          effective += dr * dd;
        }
        strokeWeights.set(el, Math.max(1, effective * profile.reveal.length));
      });
      const totalWeight = Array.from(strokeWeights.values()).reduce((a, b) => a + b, 0);
      const gapTotal = CHAR_GAP * (PEN_GLYPH_PATHS.length - 1);
      const drawingTotal = Math.max(0.1, WRITE_DURATION - gapTotal);

      PEN_GLYPH_PATHS.forEach((_g, i) => {
        maskStrokeRefs.current[i].forEach((strokeEl) => {
          if (!strokeEl) return;
          const profile = revealProfiles.get(strokeEl);
          const len = profile?.len ?? strokeEl.getTotalLength();
          const weight = strokeWeights.get(strokeEl) ?? 1;
          const duration = totalWeight > 0 ? (drawingTotal * weight) / totalWeight : drawingTotal;

          tl.set(strokeEl, { strokeDashoffset: len, visibility: "visible" });
          tl.to(
            {},
            {
              duration,
              onUpdate() {
                // 진행률을 "누적 노출량"으로 보고, 거기에 해당하는 경로 거리를
                // 찾아 그린다 — 되짚는 구간은 알아서 빨리 지나가고, 새 획이
                // 나오는 구간은 일정한 속도로 그려진다.
                const t = this.progress();
                const dist = profile ? distanceForReveal(profile, t) : t * len;
                strokeEl.style.strokeDashoffset = String(len - dist);
              },
            },
          );
        });
        if (i < PEN_GLYPH_PATHS.length - 1) tl.to({}, { duration: CHAR_GAP });
      });

      tl.to({}, { duration: 0.7 });

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
      // 시작해서 같은 시간 동안" 진행되어야 속도가 맞아 보인다. 예전에는 띠
      // 트윈의 "<"가 (지그재그 트윈이 아니라) 그 뒤에 놓인 set 기준으로 붙는
      // 바람에 띠가 펜보다 한참 늦게 시작했다 — 시작 지점을 라벨로 못 박는다.
      const sweepStart = "pwcSweep";
      tl.addLabel(sweepStart);
      tl.to(highlighterRef.current, { opacity: 1, duration: 0.15 }, sweepStart);
      tl.to(highlighterRef.current, { left: "94%", duration: SWEEP_DURATION }, sweepStart);
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
        { left: "100%", opacity: 0, duration: 0.2 },
        `${sweepStart}+=${SWEEP_DURATION}`,
      );

      // ③ 다 칠해진 상태로 HOLD_DURATION(15초) 동안 그대로 유지된다 — 다
       // 칠해진 시점부터 15초라서, 그 사이에는 아무 변화 없이 결과만 보인다.
      tl.to({}, { duration: HOLD_DURATION });

      // ④ 유지 시간이 끝나면 갑자기 사라지지 않고 희미하게 흐려지며 사라진다.
      // 이 페이드가 끝난 직후 타임라인이 끝나고, onComplete가 곧바로
      // 처음부터 다시 재생시킨다(= 자연스럽게 이어지는 사이클).
      tl.to(textRef.current, { opacity: 0, filter: "blur(10px)", duration: FADE_OUT_DURATION, ease: "power1.in" });

      tl.eventCallback("onComplete", () => tl.restart());
    }, rootRef);

    return () => ctx.revert();
  }, []);

  return (
    <span className="pwc" ref={rootRef} aria-hidden="true">
      <img className="pwc__highlighter" ref={highlighterRef} src="/3d/highlighter.webp" alt="" />
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
                <path
                  ref={(el) => {
                    erodeStrokeRefs.current[i][j] = el;
                  }}
                  className="pwc__char-erode-stroke"
                  d={groupD}
                  mask={`url(#pwc-mask-${i}-${j})`}
                />
              </g>
            ))}
          </svg>
        ))}
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
