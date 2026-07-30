// ne.md 7.3 형광펜 기준: 파랑=보장정의 / 초록=현재확인된조건 / 노랑=기간·금액·상해정도 / 빨강=면책·제한 / 회색=관련성낮음
export const HIGHLIGHT_COLORS: Record<string, { bg: string; border: string; label: string }> = {
  파랑: { bg: "rgba(59,130,246,0.16)", border: "#3b82f6", label: "보장 정의" },
  초록: { bg: "rgba(34,197,94,0.16)", border: "#22c55e", label: "현재 확인된 조건" },
  노랑: { bg: "rgba(234,179,8,0.20)", border: "#ca8a04", label: "기간·금액·상해정도" },
  빨강: { bg: "rgba(239,68,68,0.16)", border: "#ef4444", label: "면책·제한·주의" },
  회색: { bg: "rgba(148,163,184,0.18)", border: "#94a3b8", label: "관련성 낮음" },
};

export function highlightStyle(color: string) {
  const c = HIGHLIGHT_COLORS[color] ?? HIGHLIGHT_COLORS["회색"];
  return { backgroundColor: c.bg, borderLeft: `4px solid ${c.border}` };
}

export const STATUS_TONE: Record<string, string> = {
  "우선 검토 대상": "#3b82f6",
  청구검토후보: "#3b82f6",
  "추가 확인 필요": "#ca8a04",
  서류확보필요: "#ca8a04",
  확인불가: "#94a3b8",
  "계약확인필요": "#ef4444",
};
