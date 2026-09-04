import type { PremiumValueOrigin } from "../api";

export function premiumOriginLabel(origin: PremiumValueOrigin | null | undefined): string {
  if (origin === "DIRECT_QUOTE") return "직접조회값";
  if (origin === "DERIVED") return "환산값";
  if (origin === "IMPUTED") return "추정값 · 추천 점수 제외";
  return "출처 미확인 · 추천 점수 제외";
}

export function premiumBasisLabel(
  origin: PremiumValueOrigin | null | undefined,
  periodDays: number | null | undefined,
  sourcePeriodDays?: number | null,
): string {
  const days = periodDays ?? 1;
  if (origin === "DIRECT_QUOTE") return `${days}일 직접조회값`;
  if (origin === "DERIVED") {
    const source = sourcePeriodDays ? ` · 원본 ${sourcePeriodDays}일` : "";
    return `${days}일 비교용 환산값${source}`;
  }
  return premiumOriginLabel(origin);
}
