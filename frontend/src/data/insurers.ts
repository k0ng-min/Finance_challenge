export interface InsurerOption {
  code: string;
  name: string;
  logo: string; // /insurers/*.jpg — 공식 앱스토어 앱 아이콘 (브랜드 식별용)
}

export const INSURERS: InsurerOption[] = [
  { code: "SAMSUNG", name: "삼성화재", logo: "/insurers/samsung.jpg" },
  { code: "HYUNDAI", name: "현대해상", logo: "/insurers/hyundai.jpg" },
  { code: "MERITZ", name: "메리츠화재", logo: "/insurers/meritz.jpg" },
  { code: "KB", name: "KB손해보험", logo: "/insurers/kb.jpg" },
  { code: "DB", name: "DB손해보험", logo: "/insurers/db.jpg" },
  { code: "KAKAOPAY", name: "카카오페이손해보험", logo: "/insurers/kakaopay.jpg" },
];

/** 보험사 정식명(예: "삼성화재해상보험")은 목록/드롭다운에서 너무 길어 보이므로,
 * 6개 보험사 공통 짧은 이름으로 통일해서 보여줄 때 쓴다. */
export function shortInsurerName(code?: string | null, fallback?: string | null): string {
  const found = INSURERS.find((i) => i.code === code);
  return found?.name ?? fallback ?? "보험사 미상";
}
