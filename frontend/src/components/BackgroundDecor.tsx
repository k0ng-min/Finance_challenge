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

// 데스크톱 기준 아이콘 몸통 폭(모바일에서는 CSS로 1/4인 24px로 그려진다 — 아래 간격
// 계산은 넉넉하게 데스크톱 크기 기준으로 잡아둬도 모바일에서는 그만큼 더 여유로워질 뿐이라
// 문제없다). 아이콘이 겹치지 않고 + 양옆으로 아이콘 4분의 1씩만 못 쓰게 막는 최소 간격.
// 각 아이콘은 낙하하는 내내 left(가로 위치)가 고정이고 세로로만 움직이므로, 이 간격만
// 스폰 시점에 지켜지면 속도가 서로 달라도(하나가 다른 하나를 스쳐 지나가듯 보여도) 가로로는
// 절대 겹치지 않는다.
const ICON_WIDTH = 96;
const MIN_GAP = ICON_WIDTH * 1.5;
// 화면에 동시에 떠 있는 개수를 2~5개로 유지한다 — 너무 휑하지도, 너무 정신없지도 않게.
const MIN_ON_SCREEN = 2;
const MAX_ON_SCREEN = 5;
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

/** 카드(또는 모바일에서는 화면 자체) 뒤 빈 공간을 채우는 장식. 매 tick마다 "지금 화면에
 * 없는 아이콘 + 기존 것들과 최소 간격을 지키는 가로 위치" 조합을 찾아 하나씩 떨어뜨리되,
 * 화면에 2~5개만 떠 있도록 유지한다(모자라면 채우고, 다 찼으면 더 스폰하지 않는다).
 *
 * 제거는 setTimeout으로 애니메이션 길이를 추정해서 지우지 않고, 그 아이콘의 실제 CSS
 * 애니메이션이 끝나는 순간(onAnimationEnd)에 지운다 — 추정치가 살짝 어긋나면 다 내려가기
 * 전에 사라지거나 다 내려간 뒤에도 한참 남아있는 것처럼 보일 수 있어서, 브라우저가 실제로
 * 애니메이션을 끝낸 시점을 그대로 신뢰하는 쪽이 더 정확하다. */
export function BackgroundDecor() {
  const [items, setItems] = useState<FallingItem[]>([]);
  const activeLefts = useRef<Map<number, number>>(new Map());
  const activeIcons = useRef<Set<string>>(new Set());

  useEffect(() => {
    const timer = setInterval(() => {
      const current = activeLefts.current.size;
      if (current >= MAX_ON_SCREEN) return;
      const belowFloor = current < MIN_ON_SCREEN;
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
    }, 700);

    return () => clearInterval(timer);
  }, []);

  function handleFallEnd(it: FallingItem) {
    activeLefts.current.delete(it.id);
    activeIcons.current.delete(it.icon);
    setItems((prev) => prev.filter((cur) => cur.id !== it.id));
  }

  return (
    <div className="bg-decor" aria-hidden="true">
      {items.map((it) => (
        <img
          key={it.id}
          className="bg-decor__icon"
          src={`/3d/${it.icon}.webp`}
          alt=""
          style={{ left: `${it.leftPx}px`, animationDuration: `${it.duration}s` }}
          onAnimationEnd={() => handleFallEnd(it)}
        />
      ))}
    </div>
  );
}
