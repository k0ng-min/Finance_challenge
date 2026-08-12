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

  const contours = [];
  let current = null;
  for (const c of rawCommands) {
    if (c.type === "M") {
      current = [];
      contours.push(current);
    }
    current?.push(c);
  }

  const groups = orderGroupsHumanLike(groupContours(contours));
  const groupPaths = groups.map((g) => commandsToPathData(g.commands));
  const d = commandsToPathData(rawCommands);

  return {
    char,
    d,
    groups: groupPaths,
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
// 이 순서 그대로 하나씩 그린다.
`;

const body = `export interface PenGlyphPath {
  char: string;
  d: string;
  groups: string[];
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
