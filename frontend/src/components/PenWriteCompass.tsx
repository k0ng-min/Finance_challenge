import { useEffect, useLayoutEffect, useRef } from "react";
import { PEN_GLYPH_PATHS } from "../generated/penGlyphPaths";

/** 홈 화면 히어로(나침반 자리)를 대신하는 3단계 애니메이션. 참고 영상
 * (약관형광펜 Writing.mp4)과 같은 순서에 지우는 단계를 더했다 — ① 펜이
 * "보험형광펜"을 한 글자씩 실제 폰트 윤곽선(SVG path)을 따라 그리듯 씀 →
 * ② 다 쓰면 펜이 사라지고 노란 형광펜이 등장해 왼쪽부터 훑으며 노란
 * 하이라이트를 칠함 → ③ 연필 지우개 쪽으로 오른쪽위→왼쪽아래 대각선을 반복하며
 * (쓱싹쓱싹) 오른쪽으로 이동해 전체를 지움 → 처음(빈 화면)으로 돌아가 반복.
 *
 * 글자는 CSS로 흉내낸 게 아니라 scripts/extract-glyph-paths.mjs가 Gaegu
 * Bold(OFL) 폰트 파일에서 opentype.js로 직접 뽑아낸 실제 글리프 path다
 * (src/generated/penGlyphPaths.ts). 펜은 매 프레임 requestAnimationFrame
 * 루프에서 SVGPathElement.getPointAtLength()로 그 path 위의 실제 좌표를
 * 읽어와 정확히 따라간다 — CSS 퍼센트로 흉내낸 좌표가 아니라 진짜 획 위의
 * 좌표라서 펜촉이 항상 지금 그려지는 자리에 붙어 있다.
 *
 * 단, opentype.js가 주는 path는 "글자 안쪽으로 파고드는 스켈레톤(중심선)"이
 * 아니라 글자의 바깥+안쪽 윤곽선(외곽 컨투어)이다 — 그래서 이 path를 그대로
 * stroke나 마스크로 쓰면 ㅂ/ㅁ처럼 안이 뚫린 글자가 테두리만 있는 "빈 테두리"로
 * 보인다. 그래서 잉크가 실제로 채워지는 부분(pwc__char-fill-live)은 stroke가
 * 아니라 진짜 꽉 찬 글자 fill을 clip-path로 펜이 도달한 x좌표까지만 드러내는
 * 방식이다 — 펜이 지나간 만큼만 항상 "완전한 글자 모양"으로 칠해지므로 속이
 * 빈 부분이 생기지 않고, 그 x좌표는 펜을 움직이는 것과 같은 좌표(p.x)라서 항상
 * 펜 끝과 어긋나지 않는다. 한글은 자모 단위 획순 데이터를 제공하는 공개
 * 라이브러리가 없어서(한자의 Hanzi Writer 같은 것) 자모 하나하나(ㅂㅗㅎㅓㅁ)
 * 순서까지는 못 맞추지만, 실제 윤곽선을 따라 펜이 지나가므로 사각형 wipe나
 * 좌표 흉내보다 훨씬 필체에 가깝다.
 *
 * 펜·형광펜·지우개는 이 앱의 다른 아이콘과 같은 출처(Fluent Emoji 3D, MIT
 * License, Microsoft)에서 받은 실제 3D 렌더 이미지다(/public/3d/pen.webp,
 * crayon.webp, pencil.webp — 지우개 전용 이모지가 없어 연필의 지우개 쪽 끝을
 * 아래로 오게 180도 돌려서 쓴다). 되돌리고 싶으면 Home.tsx에서 이 컴포넌트
 * 호출을 원래 Icon3D로 바꾸면 된다. */

// 각 글자가 그려지는 시간 구간(%) — 부모의 pwc-text-erase(app.css)와
// 겹치지 않게(88% 이전) 맞춰 둠.
const CYCLE_MS = 36000;
const WINDOWS_PCT: [number, number][] = [
  [4, 11],
  [11.2, 18],
  [18.2, 25],
  [25.2, 32],
  [32.2, 39],
];
const WINDOWS_MS = WINDOWS_PCT.map(
  ([s, e]) => [(s / 100) * CYCLE_MS, (e / 100) * CYCLE_MS] as [number, number],
);

// 펜 에셋(pen.webp) 안에서 실제 펜촉이 있는 위치 — 이미지 왼쪽아래 모서리
// 근처를 향해 있다. 이 비율만큼 이미지를 당겨서 촉이 좌표에 정확히 붙게 한다.
const PEN_W = 820;
const PEN_H = 820;
const TIP_FRAC_X = 0.1;
const TIP_FRAC_Y = 0.92;

export function PenWriteCompass() {
  const guideRefs = useRef<(SVGPathElement | null)[]>([]);
  const fillRefs = useRef<(SVGPathElement | null)[]>([]);
  const penRefs = useRef<(SVGImageElement | null)[]>([]);
  const lensRef = useRef<number[]>([]);

  useLayoutEffect(() => {
    guideRefs.current.forEach((el, i) => {
      if (!el) return;
      lensRef.current[i] = el.getTotalLength();
    });
  }, []);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let rafId: number;
    let mounted = true;
    const start = performance.now();

    function tick(now: number) {
      if (!mounted) return;
      const elapsed = (now - start) % CYCLE_MS;
      for (let i = 0; i < WINDOWS_MS.length; i++) {
        const img = penRefs.current[i];
        const guide = guideRefs.current[i];
        const fill = fillRefs.current[i];
        const g = PEN_GLYPH_PATHS[i];
        if (!img || !guide || !fill) continue;
        const [ws, we] = WINDOWS_MS[i];

        if (elapsed < ws) {
          img.style.opacity = "0";
          fill.style.clipPath = "inset(0 100% 0 0)";
          continue;
        }
        if (elapsed > we) {
          img.style.opacity = "0";
          fill.style.clipPath = "inset(0 0% 0 0)";
          continue;
        }

        const len = lensRef.current[i] ?? guide.getTotalLength();
        const t = Math.min(1, Math.max(0, (elapsed - ws) / (we - ws)));
        const dist = t * len;
        const p = guide.getPointAtLength(dist);
        const p2 = guide.getPointAtLength(Math.min(len, dist + 1));
        const angle = Math.atan2(p2.y - p.y, p2.x - p.x) * (180 / Math.PI);

        img.style.opacity = "1";
        img.setAttribute("transform", `translate(${p.x} ${p.y}) rotate(${angle + 45})`);
        const xPct = Math.min(100, Math.max(0, ((p.x - g.x) / g.width) * 100));
        fill.style.clipPath = `inset(0 ${100 - xPct}% 0 0)`;
      }
      rafId = requestAnimationFrame(tick);
    }
    rafId = requestAnimationFrame(tick);
    return () => {
      mounted = false;
      cancelAnimationFrame(rafId);
    };
  }, []);

  return (
    <span className="pwc" aria-hidden="true">
      <img className="pwc__highlighter" src="/3d/crayon.webp" alt="" />
      <img className="pwc__eraser" src="/3d/pencil.webp" alt="" />
      <span className="pwc__text">
        {PEN_GLYPH_PATHS.map((g, i) => (
          <svg
            key={g.char}
            className={`pwc__char pwc__char--${i}`}
            viewBox={`${g.x} ${g.y} ${g.width} ${g.height}`}
            style={{ width: `${g.advanceEm}em` }}
            preserveAspectRatio="xMinYMax meet"
            overflow="visible"
          >
            {/* 화면에는 안 그려지고, 펜이 따라갈 좌표를 getPointAtLength로
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
        <span className="pwc__highlight-bg" />
      </span>
    </span>
  );
}
