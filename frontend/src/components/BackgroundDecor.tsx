import { useEffect, useRef, useState } from "react";

interface FallingItem {
  id: number;
  icon: string;
  leftPx: number;
  duration: number;
}

// 흰색/회색이라 배경에 묻히는 것(열쇠, 트로피, 시계 등)은 빼고, 실제로 색이 뚜렷해서 잘
// 보이는 여행·보험 테마 아이콘 14개만 쓴다.
const ICONS = [
  "umbrella", "shield", "notebook", "calendar", "medal", "map-pin", "lock",
  "suitcase", "flag", "star", "chart", "wallet", "gift", "target",
];

const ICON_WIDTH = 96;
// 아이콘 몸통(96px)이 겹치지 않고 + 양옆으로 아이콘 4분의 1(24px)씩만 못 쓰게 막는
// 최소 간격. 각 아이콘은 낙하하는 내내 left(가로 위치)가 고정이고 세로로만 움직이므로,
// 이 간격만 스폰 시점에 지켜지면 속도가 서로 달라도(하나가 다른 하나를 스쳐 지나가듯 보여도)
// 가로로는 절대 겹치지 않는다.
const MIN_GAP = ICON_WIDTH * 1.5;
const MIN_ON_SCREEN = 8;
// 화면 양쪽 끝에 아이콘이 걸쳐서(반쯤 잘려서) 떨어지지 않도록, 좌우로 아이콘 3분의 1칸만큼은
// 아예 스폰 후보에서 뺀다.
const EDGE_MARGIN = ICON_WIDTH / 3;

let nextId = 1;

function findFreeLeft(activeLefts: number[], viewportWidth: number): number | null {
  const min = EDGE_MARGIN;
  const max = Math.max(min, viewportWidth - ICON_WIDTH - EDGE_MARGIN);
  const range = max - min;
  for (let attempt = 0; attempt < 40; attempt++) {
    const candidate = min + Math.random() * range;
    if (activeLefts.every((x) => Math.abs(x - candidate) >= MIN_GAP)) return candidate;
  }
  return null;
}

/** 데스크탑(≥900px)에서 카드 뒤 빈 공간을 채우는 장식. 매 tick마다 "지금 화면에 없는
 * 아이콘 + 기존 것들과 최소 간격을 지키는 가로 위치" 조합을 찾아 하나씩 떨어뜨린다.
 * 화면이 시작해서 채워지기 전 잠깐을 빼면 항상 최소 6개 이상이 떠 있도록, 개수가 모자라면
 * 확률을 따지지 않고 바로바로 채워 넣는다. 다 내려가 사라진 뒤에도 잠깐(아이콘 2개 지나갈
 * 시간 정도) 더 쉬었다가 그 자리와 아이콘 이름을 다시 쓸 수 있게 한다. */
export function BackgroundDecor() {
  const [items, setItems] = useState<FallingItem[]>([]);
  const activeLefts = useRef<Map<number, number>>(new Map());
  const activeIcons = useRef<Set<string>>(new Set());

  useEffect(() => {
    const timer = setInterval(() => {
      const belowFloor = activeLefts.current.size < MIN_ON_SCREEN;
      if (!belowFloor && Math.random() > 0.45) return;

      const freeIcons = ICONS.filter((icon) => !activeIcons.current.has(icon));
      if (freeIcons.length === 0) return;

      const left = findFreeLeft(Array.from(activeLefts.current.values()), window.innerWidth);
      if (left === null) return;

      const icon = freeIcons[Math.floor(Math.random() * freeIcons.length)];
      const duration = 16 + Math.random() * 8; // 16~24초, 서로 다르게
      const id = nextId++;

      activeLefts.current.set(id, left);
      activeIcons.current.add(icon);
      setItems((prev) => [...prev, { id, icon, leftPx: left, duration }]);

      window.setTimeout(() => {
        activeLefts.current.delete(id);
        activeIcons.current.delete(icon);
        setItems((prev) => prev.filter((it) => it.id !== id));
      }, duration * 1000 + 2800);
    }, 700);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="bg-decor" aria-hidden="true">
      {items.map((it) => (
        <img
          key={it.id}
          className="bg-decor__icon"
          src={`/3d/${it.icon}.webp`}
          alt=""
          style={{ left: `${it.leftPx}px`, animationDuration: `${it.duration}s` }}
        />
      ))}
    </div>
  );
}
