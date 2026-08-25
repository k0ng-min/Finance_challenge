import type { RankingAxisOut } from "../api";

/**
 * 순위를 만든 다섯 축을 오각형 방사형 그래프로 그린다.
 *
 * 막대만 보면 "이 보험사가 어느 쪽으로 치우쳤는지"가 안 읽힌다. 다섯 축을 한 도형으로
 * 묶으면 모양 자체가 성향이 된다 — 보장금액 쪽으로 뾰족한지, 고르게 둥근지.
 *
 * 비교 대상 평균을 같은 그래프에 겹쳐 그린다. 혼자 있는 도형은 "큰지 작은지"를 말해주지
 * 못한다. 평균선이 있어야 이 보험사가 어느 축에서 앞서고 어느 축에서 밀리는지가 보인다.
 *
 * 꼭짓점에는 왼쪽 축 목록과 같은 번호(1~5)만 적는다. 라벨을 그대로 넣으면 글자가 도형을
 * 덮어서 정작 모양이 안 보인다.
 */
const SIZE = 168;
const CENTER = SIZE / 2;
const RADIUS = SIZE / 2 - 18;
const RINGS = [0.25, 0.5, 0.75, 1];

function vertex(index: number, ratio: number) {
  // 첫 꼭짓점을 12시 방향에 두고 시계방향으로 72°씩 돈다.
  const angle = (-90 + index * 72) * (Math.PI / 180);
  return {
    x: CENTER + Math.cos(angle) * RADIUS * ratio,
    y: CENTER + Math.sin(angle) * RADIUS * ratio,
  };
}

function polygon(values: number[]) {
  return values
    .map((value, index) => {
      const { x, y } = vertex(index, Math.max(0, Math.min(1, value)));
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function RankingRadar({
  axes,
  average,
  insurerName,
}: {
  axes: RankingAxisOut[];
  /** 같은 순서의 비교 대상 평균 점수(0~1). */
  average: number[];
  insurerName: string;
}) {
  if (axes.length !== 5 || average.length !== 5) return null;

  // 자료가 없어 계산에서 빠진 축은 0으로 찍는다 — 점수가 0이어서가 아니라 그릴 값이
  // 없어서다. 그 사실은 왼쪽 목록에 "자료 없음"으로 이미 적혀 있다.
  const mine = axes.map((axis) => (axis.available ? axis.score : 0));

  return (
    <svg
      className="rank-radar"
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      role="img"
      aria-label={`${insurerName}의 다섯 축 점수와 비교 대상 평균 비교`}
    >
      {RINGS.map((ring) => (
        <polygon
          key={ring}
          className="rank-radar__ring"
          points={polygon([ring, ring, ring, ring, ring])}
        />
      ))}
      {[0, 1, 2, 3, 4].map((index) => {
        const end = vertex(index, 1);
        return (
          <line
            key={index}
            className="rank-radar__spoke"
            x1={CENTER}
            y1={CENTER}
            x2={end.x}
            y2={end.y}
          />
        );
      })}

      <polygon className="rank-radar__avg" points={polygon(average)} />
      <polygon className="rank-radar__self" points={polygon(mine)} />

      {[0, 1, 2, 3, 4].map((index) => {
        const label = vertex(index, 1.16);
        return (
          <text
            key={index}
            className="rank-radar__num"
            x={label.x}
            y={label.y}
            textAnchor="middle"
            dominantBaseline="central"
          >
            {index + 1}
          </text>
        );
      })}
    </svg>
  );
}
