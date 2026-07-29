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
