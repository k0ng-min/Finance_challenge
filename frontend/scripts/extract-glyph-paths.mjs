// PenWriteCompass가 "보험형광펜"을 실제 폰트 모양 그대로, 자모(ㅂㅗ, ㅎㅓㅁ...)
// 순서대로 쓰는 것처럼 보이도록, 학교안심 민들레홀씨 R(KERIS, OFL) 폰트에서
// 각 글자의 실제 SVG 윤곽선을 추출한다. 단순히 폰트 파일에 저장된 컨투어
// 순서를 그대로 쓰면 실제 손으로 쓰는 순서와 무관하게 뒤죽박죽 나온다 —
// 그래서 컨투어(잉크 덩어리)들을 서로 겹치는 것끼리 자모 단위로 묶고, 그
// 묶음들을 "초성→중성→종성, 왼쪽→오른쪽, 위→아래" 순서로 다시 정렬해서
// PEN_GLYPH_PATHS[i].groups에 순서대로 저장한다 — PenWriteCompass가 이
// groups를 그대로 순서대로 그린다(한 그룹 = 펜이 한 번에 그리는 자모 단위
// 잉크 덩어리, 그 그룹 자체의 x범위 안에서만 clip-path가 훑고 지나가므로
// 복잡한 글자 전체를 가로지르는 "벽"처럼 보이지 않는다).
//
// opentype.js는 이 스크립트에서만 쓰고 번들에는 포함하지 않는다 — 결과물인
// 생성 파일만 커밋한다. 다시 만들려면: scripts/fonts/Hakgyoansim-MindeulleholssiR.woff를
// 두고 `node scripts/extract-glyph-paths.mjs` 실행.
import opentype from "opentype.js";
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const fontPath = path.join(__dirname, "fonts", "Hakgyoansim-MindeulleholssiR.woff");
const outPath = path.join(__dirname, "..", "src", "generated", "penGlyphPaths.ts");

const CHARS = ["보", "험", "형", "광", "펜"];

const font = opentype.loadSync(fontPath);
const unitsPerEm = font.unitsPerEm;
const ascender = font.ascender;
const descender = font.descender;

function commandsToPathData(commands) {
  return commands
    .map((c) => {
      switch (c.type) {
        case "M":
          return `M${round(c.x)},${round(c.y)}`;
        case "L":
          return `L${round(c.x)},${round(c.y)}`;
        case "C":
          return `C${round(c.x1)},${round(c.y1)} ${round(c.x2)},${round(c.y2)} ${round(c.x)},${round(c.y)}`;
        case "Q":
          return `Q${round(c.x1)},${round(c.y1)} ${round(c.x)},${round(c.y)}`;
        case "Z":
          return "Z";
        default:
          return "";
      }
    })
    .join(" ");
}
function round(n) {
  return Math.round(n * 100) / 100;
}

function bboxOf(commands) {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const c of commands) {
    for (const key of ["x", "x1", "x2"]) {
      if (typeof c[key] === "number") {
        minX = Math.min(minX, c[key]);
        maxX = Math.max(maxX, c[key]);
      }
    }
    for (const key of ["y", "y1", "y2"]) {
      if (typeof c[key] === "number") {
        minY = Math.min(minY, c[key]);
        maxY = Math.max(maxY, c[key]);
      }
    }
  }
  return { minX, maxX, minY, maxY };
}

function overlapFraction(aMin, aMax, bMin, bMax) {
  const overlap = Math.min(aMax, bMax) - Math.max(aMin, bMin);
  if (overlap <= 0) return 0;
  const smaller = Math.min(aMax - aMin, bMax - bMin);
  return smaller > 0 ? overlap / smaller : 0;
}

function cubicPoint(p0, p1, p2, p3, t) {
  const mt = 1 - t;
  return {
    x: mt * mt * mt * p0.x + 3 * mt * mt * t * p1.x + 3 * mt * t * t * p2.x + t * t * t * p3.x,
    y: mt * mt * mt * p0.y + 3 * mt * mt * t * p1.y + 3 * mt * t * t * p2.y + t * t * t * p3.y,
  };
}
function quadPoint(p0, p1, p2, t) {
  const mt = 1 - t;
  return {
    x: mt * mt * p0.x + 2 * mt * t * p1.x + t * t * p2.x,
    y: mt * mt * p0.y + 2 * mt * t * p1.y + t * t * p2.y,
  };
}

// 커브(C/Q)를 잘게 쪼갠 점 목록으로 바꾼다 — 둘레 길이와 넓이를 다각형
// 근사로 정확히 계산하기 위해서.
function flattenSubpath(commands, samplesPerCurve = 16) {
  const pts = [];
  let cur = { x: 0, y: 0 };
  let start = { x: 0, y: 0 };
  for (const c of commands) {
    if (c.type === "M") {
      cur = { x: c.x, y: c.y };
      start = cur;
      pts.push({ ...cur });
    } else if (c.type === "L") {
      cur = { x: c.x, y: c.y };
      pts.push({ ...cur });
    } else if (c.type === "C") {
      const p1 = { x: c.x1, y: c.y1 };
      const p2 = { x: c.x2, y: c.y2 };
      const p3 = { x: c.x, y: c.y };
      for (let s = 1; s <= samplesPerCurve; s++) pts.push(cubicPoint(cur, p1, p2, p3, s / samplesPerCurve));
      cur = p3;
    } else if (c.type === "Q") {
      const p1 = { x: c.x1, y: c.y1 };
      const p2 = { x: c.x, y: c.y };
      for (let s = 1; s <= samplesPerCurve; s++) pts.push(quadPoint(cur, p1, p2, s / samplesPerCurve));
      cur = p2;
    } else if (c.type === "Z") {
      pts.push({ ...start });
      cur = start;
    }
  }
  return pts;
}

function polylineLength(pts) {
  let len = 0;
  for (let i = 1; i < pts.length; i++) len += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
  return len;
}
function shoelaceArea(pts) {
  let sum = 0;
  for (let i = 0; i < pts.length; i++) {
    const a = pts[i];
    const b = pts[(i + 1) % pts.length];
    sum += a.x * b.y - b.x * a.y;
  }
  return sum / 2;
}

// 자모 덩어리(group)의 "실제 평균 잉크 두께"를, 그 덩어리 자신의 윤곽선
// 넓이/둘레로 추정한다 — bbox 짧은 변 비율로 어림잡던 예전 방식은 ㅁ/ㅇ/ㅎ처럼
// 구멍이 있거나 "보"처럼 ㅂ+ㅗ가 하나로 합쳐진 덩어리에서 bbox가 실제 잉크
// 두께와 무관하게 글자 전체 크기를 반영해 버려서(짧은 변도 커짐) 두께를
// 심하게 잘못 추정했다(mask가 너무 얇아 획이 끊기거나, 너무 두꺼워 글자가
// 통째로 지워지는 두 방향 모두). 넓이/둘레 비율은 도형 모양에 상관없이 항상
// 성립하는 기하학적 관계다 — 폭 w, 길이 L인 띠(strip) 모양은
// 넓이 ≈ L×w, 둘레 ≈ 2L이므로 2×넓이/둘레 ≈ w. 바깥/안쪽 두 윤곽선으로 된
// 링(ㅇ/ㅁ/ㅎ, 바깥 반지름 R, 안쪽 반지름 r)은 넓이 = π(R²-r²),
// 둘레 = 2π(R+r)이므로 2×넓이/둘레 = R-r(정확히 링 두께). 폰트 윤곽선은
// 바깥/안쪽 컨투어의 감김 방향이 반대라(구멍을 뚫기 위한 표준 규칙) 부호 있는
// 넓이를 그냥 더하면 자동으로 "바깥 넓이 - 구멍 넓이"가 나온다.
function estimateGroupStrokeWidth(group, contours) {
  let netArea = 0;
  let perimeter = 0;
  for (const idx of group.indices) {
    const pts = flattenSubpath(contours[idx]);
    if (pts.length < 3) continue;
    netArea += shoelaceArea(pts);
    perimeter += polylineLength(pts);
  }
  const area = Math.abs(netArea);
  if (perimeter <= 0) return 1;
  return (2 * area) / perimeter;
}

// 폰트 파일 안에서 컨투어(닫힌 도형)가 어느 점에서 시작하는지는 폰트 제작
// 프로그램이 임의로 정한 것이지, 손으로 쓸 때의 시작점과는 무관하다. 이게
// 왜 문제냐면: "보"처럼 여러 자모가 폰트 안에서 하나의 컨투어로 합쳐진
// 경우, stroke-dasharray로 그 컨투어를 시작점부터 순서대로 드러낼 때 시작점이
// 안 좋으면(예: ㅂ 획 중간 어딘가) 잠깐 동안 서로 안 이어진 두 조각이 따로
// 나타났다가 나중에 연결부가 그려지면서 합쳐지는 것처럼 보인다 — 자모 두께
// 문제와는 다른, 진짜 "끊김"이다. 닫힌 도형은 어느 점에서 시작해도 모양은
// 똑같으므로(그냥 같은 루프를 어디서 자르고 다시 잇느냐의 차이), 대신 그
// 도형의 가장 위-왼쪽 점에서 시작하도록 통째로 회전시킨다 — 한글은 위→아래,
// 왼→오른쪽으로 쓰므로 위-왼쪽에서 시작해 둘레를 따라가면 실제로 자연스럽게
// "옆으로 번져나가는" 순서가 될 가능성이 훨씬 높다.
function rotateContourToTopLeft(commands) {
  if (commands.length < 3 || commands[0].type !== "M" || commands[commands.length - 1].type !== "Z") return commands;
  const draws = commands.slice(1, -1);
  const points = [{ x: commands[0].x, y: commands[0].y }, ...draws.map((c) => ({ x: c.x, y: c.y }))];
  let bestI = 0;
  for (let i = 1; i < points.length; i++) {
    const p = points[i];
    const b = points[bestI];
    if (p.y < b.y || (p.y === b.y && p.x < b.x)) bestI = i;
  }
  if (bestI === 0) return commands;
  const newStart = points[bestI];
  const tail = draws.slice(bestI);
  const head = draws.slice(0, bestI);
  return [{ type: "M", x: newStart.x, y: newStart.y }, ...tail, ...head, { type: "Z" }];
}

// 닫힌 컨투어를 진행 방향만 거꾸로 뒤집는다(모양은 그대로). 각 세그먼트의
// 끝점을 앞점으로 바꾸고, 3차 베지어는 두 제어점의 순서도 함께 뒤집는다.
function reverseContour(commands) {
  if (commands.length < 3 || commands[0].type !== "M" || commands[commands.length - 1].type !== "Z") return commands;
  const start = { x: commands[0].x, y: commands[0].y };
  const draws = commands.slice(1, -1);
  // 각 세그먼트의 시작점을 미리 구해 둔다.
  const from = [start];
  for (const c of draws) from.push({ x: c.x, y: c.y });

  const out = [{ type: "M", x: from[from.length - 1].x, y: from[from.length - 1].y }];
  for (let i = draws.length - 1; i >= 0; i--) {
    const seg = draws[i];
    const prev = from[i];
    if (seg.type === "L") out.push({ type: "L", x: prev.x, y: prev.y });
    else if (seg.type === "Q") out.push({ type: "Q", x1: seg.x1, y1: seg.y1, x: prev.x, y: prev.y });
    else if (seg.type === "C") out.push({ type: "C", x1: seg.x2, y1: seg.y2, x2: seg.x1, y2: seg.y1, x: prev.x, y: prev.y });
    else out.push({ type: "L", x: prev.x, y: prev.y });
  }
  out.push({ type: "Z" });
  return out;
}

// "보"처럼 ㅂ과 ㅗ가 하나의 컨투어로 붙어 있는 글자는, 그 컨투어를 어느 방향으로
// 도느냐에 따라 위(ㅂ)부터 채워질 수도, 아래(ㅗ)부터 채워질 수도 있다. 한글은
// 위에서 아래로 쓰므로, 두 방향 중 "위쪽 점들이 먼저 지나가는" 방향을 고른다.
function orientGroupTopFirst(groupContours) {
  function topFirstScore(contourList) {
    const pts = contourList.flatMap((cmds) => flattenSubpath(cmds, 6));
    if (pts.length < 4) return 0;
    let minY = Infinity;
    let maxY = -Infinity;
    for (const p of pts) {
      if (p.y < minY) minY = p.y;
      if (p.y > maxY) maxY = p.y;
    }
    if (maxY - minY <= 0) return 0;
    const mid = (minY + maxY) / 2;
    // 위쪽 절반/아래쪽 절반 점들의 "평균 등장 순서"를 비교한다 — 아래쪽이
    // 늦게 나올수록(점수가 클수록) 위에서 아래로 쓰는 순서에 가깝다.
    let topSum = 0;
    let topCount = 0;
    let botSum = 0;
    let botCount = 0;
    pts.forEach((p, i) => {
      const t = i / (pts.length - 1);
      if (p.y <= mid) {
        topSum += t;
        topCount++;
      } else {
        botSum += t;
        botCount++;
      }
    });
    if (!topCount || !botCount) return 0;
    return botSum / botCount - topSum / topCount;
  }
  // 덩어리 안의 모든 컨투어를 한꺼번에 뒤집어서(상대적인 감김 방향은 그대로
  // 유지된다) 두 방향 중 위→아래 순서에 가까운 쪽을 고른다.
  const reversed = groupContours.map(reverseContour);
  return topFirstScore(reversed) > topFirstScore(groupContours) ? reversed : groupContours;
}

// 컨투어(폰트가 그린 개별 닫힌 도형)를 같은 자모끼리 묶는다. ㅁ/ㅇ/ㅎ의 안쪽
// 구멍처럼 "거의 통째로 겹치는" 경우만 같은 자모로 보고, 옆 자모끼리 살짝
// 스치듯 겹치는 정도(예: 18유닛만 겹침)는 다른 자모로 취급해야 한다 — 그래서
// 겹치는 절대량이 아니라 "더 작은 쪽 크기 대비 겹치는 비율"이 커야(threshold)
// 묶는다.
function groupContours(contours) {
  const THRESHOLD = 0.55;
  const boxes = contours.map(bboxOf);
  const parent = contours.map((_, i) => i);
  function find(i) {
    while (parent[i] !== i) {
      parent[i] = parent[parent[i]];
      i = parent[i];
    }
    return i;
  }
  function union(i, j) {
    const ri = find(i);
    const rj = find(j);
    if (ri !== rj) parent[ri] = rj;
  }
  for (let i = 0; i < contours.length; i++) {
    for (let j = i + 1; j < contours.length; j++) {
      const a = boxes[i];
      const b = boxes[j];
      const fx = overlapFraction(a.minX, a.maxX, b.minX, b.maxX);
      const fy = overlapFraction(a.minY, a.maxY, b.minY, b.maxY);
      if (fx >= THRESHOLD && fy >= THRESHOLD) {
        union(i, j);
      }
    }
  }
  const groups = new Map();
  for (let i = 0; i < contours.length; i++) {
    const root = find(i);
    if (!groups.has(root)) groups.set(root, []);
    groups.get(root).push(i);
  }
  return Array.from(groups.values()).map((idxs) => ({
    indices: idxs,
    commands: idxs.flatMap((i) => contours[i]),
    box: {
      minX: Math.min(...idxs.map((i) => boxes[i].minX)),
      maxX: Math.max(...idxs.map((i) => boxes[i].maxX)),
      minY: Math.min(...idxs.map((i) => boxes[i].minY)),
      maxY: Math.max(...idxs.map((i) => boxes[i].maxY)),
    },
  }));
}

// 자모 덩어리를 "위쪽 줄(초성/중성) 먼저, 그 안에서는 왼쪽부터, 그 다음
// 아래쪽 줄(받침)" 순서로 정렬한다 — 실제 한글 쓰는 순서(초성→중성→종성)와
// 일치한다. 세로로 몇 층인지는 글자마다 다르므로, y 중심값들을 모아서 자연
// 간격(gap)이 큰 지점을 기준으로 줄을 나눈다.
function orderGroupsHumanLike(groups) {
  const centers = groups.map((g) => (g.box.minY + g.box.maxY) / 2).sort((a, b) => a - b);
  let rowBoundary = null;
  let maxGap = -Infinity;
  for (let i = 1; i < centers.length; i++) {
    const gap = centers[i] - centers[i - 1];
    if (gap > maxGap) {
      maxGap = gap;
      rowBoundary = (centers[i] + centers[i - 1]) / 2;
    }
  }
  return [...groups].sort((a, b) => {
    const cyA = (a.box.minY + a.box.maxY) / 2;
    const cyB = (b.box.minY + b.box.maxY) / 2;
    if (rowBoundary !== null) {
      // glyph.getPath()가 이미 SVG 좌표계(y가 아래로 갈수록 커짐)로 뒤집어
      // 놓은 값이라서, y가 더 작은(더 음수인) 쪽이 화면에서 더 위 — 그 쪽을
      // 먼저 쓴다(초성/중성이 위, 받침이 아래).
      const rowA = cyA <= rowBoundary ? 0 : 1;
      const rowB = cyB <= rowBoundary ? 0 : 1;
      if (rowA !== rowB) return rowA - rowB;
    }
    const cxA = (a.box.minX + a.box.maxX) / 2;
    const cxB = (b.box.minX + b.box.maxX) / 2;
    return cxA - cxB;
  });
}

const glyphs = CHARS.map((char) => {
  const glyph = font.charToGlyph(char);
  const scale = unitsPerEm / unitsPerEm; // getPath already normalizes to unitsPerEm below
  const rawCommands = glyph.getPath(0, 0, unitsPerEm).commands;

  const rawContours = [];
  let current = null;
  for (const c of rawCommands) {
    if (c.type === "M") {
      current = [];
      rawContours.push(current);
    }
    current?.push(c);
  }
  // 시작점만 먼저 위-왼쪽으로 돌린다(회전은 감김 방향을 바꾸지 않아 안전하다).
  const contours = rawContours.map(rotateContourToTopLeft);

  // 진행 방향 뒤집기는 반드시 "자모 덩어리 단위"로, 그 안의 모든 컨투어에
  // 똑같이 적용해야 한다 — ㅇ/ㅁ/ㅎ처럼 구멍이 있는 자모는 바깥 테두리와 안쪽
  // 구멍의 감김 방향이 서로 반대여야 구멍이 뚫리는데, 컨투어를 하나씩 따로
  // 뒤집으면 그 관계가 깨져서 구멍이 까맣게 메워져 버린다.
  const groups = orderGroupsHumanLike(groupContours(contours)).map((g) => {
    const oriented = orientGroupTopFirst(g.indices.map((i) => contours[i]));
    return { ...g, contours: oriented, commands: oriented.flat() };
  });
  const groupPaths = groups.map((g) => commandsToPathData(g.commands));
  const groupStrokeWidths = groups.map((g) =>
    Number(estimateGroupStrokeWidth({ indices: g.contours.map((_, i) => i) }, g.contours).toFixed(2)),
  );
  const d = commandsToPathData(rawCommands);

  return {
    char,
    d,
    groups: groupPaths,
    groupStrokeWidths,
    x: 0,
    y: Number((-ascender).toFixed(2)),
    width: Number((glyph.advanceWidth ?? 0).toFixed(2)),
    height: Number((ascender - descender).toFixed(2)),
    advanceWidth: Number((glyph.advanceWidth ?? 0).toFixed(2)),
    advanceEm: Number(((glyph.advanceWidth ?? 0) / unitsPerEm).toFixed(4)),
  };
});

const banner = `// AUTO-GENERATED by scripts/extract-glyph-paths.mjs — 직접 수정하지 말 것.
// 학교안심 민들레홀씨 R(KERIS, OFL)에서 뽑은 "보험형광펜" 각 글자의 실제
// 윤곽선. groups는 자모(잉크 덩어리) 단위로 묶고 실제 쓰는 순서(초성→중성→
// 종성, 왼쪽→오른쪽, 위→아래)로 정렬한 부분 path 배열이다 — PenWriteCompass가
// 이 순서 그대로 하나씩 그린다. groupStrokeWidths[i]는 groups[i]의 실제 평균
// 잉크 두께(넓이/둘레로 추정, estimateGroupStrokeWidth 참고) — PenWriteCompass가
// mask 획 굵기를 이 값 기준으로 잡아서 자모 모양에 상관없이 항상 실제 잉크를
// 안전하게 덮는다.
`;

const body = `export interface PenGlyphPath {
  char: string;
  d: string;
  groups: string[];
  groupStrokeWidths: number[];
  x: number;
  y: number;
  width: number;
  height: number;
  advanceWidth: number;
  advanceEm: number;
}

export const PEN_GLYPH_PATHS: PenGlyphPath[] = ${JSON.stringify(glyphs, null, 2)};
`;

writeFileSync(outPath, banner + "\n" + body, "utf-8");
console.log(`Wrote ${glyphs.length} glyph paths to ${outPath}`);
for (const g of glyphs) {
  console.log(`${g.char}: viewBox="${g.x} ${g.y} ${g.width} ${g.height}" groups=${g.groups.length}`);
}
