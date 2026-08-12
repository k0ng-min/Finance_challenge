// "보험형광펜" 5글자를 손으로 직접 쓰듯 보이게 하려고 손수 그린 획(스켈레톤)
// 좌표다. 폰트 파일에서 opentype.js로 뽑은 실제 글리프 윤곽선(이전 시도)은
// 글자의 "바깥 테두리"라서 그걸 따라가면 사람이 쓰는 순서/궤적이 아니라 도장
// 찍듯 테두리를 훑는 움직임이 되고, ㅂ/ㅁ처럼 안이 뚫린 글자는 속이 빈 테두리로
// 보였다. 참고한 CodePen(akshsharma1218, "Animated Handwriting with DrawSVG
// GSAP3")도 같은 이유로 폰트가 아니라 손으로 그린 스켈레톤 path + GSAP
// DrawSVGPlugin + MotionPathPlugin으로 획을 그리고 그 위를 펜이 따라가는
// 방식을 쓴다(script.js의 tl.to("#hBody",{drawSVG:true}) / tl.to("#hand",
// {motionPath:{path:"#hBody", align:"#hBody"}}) 패턴). 여기서도 같은 라이브러리·
// 같은 방식으로, 자모 한 획 한 획을 실제 쓰는 순서대로 배열에 담았다 —
// PenWriteCompass.tsx가 이 배열을 그대로 GSAP 타임라인에 순서대로 넣는다.
//
// 각 글자는 0~100(가로) × 0~100(세로) 정사각 칸 안에 자모를 배치했고, strokes는
// 그 글자를 실제로 쓸 때의 획 순서 그대로다(자모 하나가 여러 획으로 나뉘기도
// 함 — 예: ㅂ은 4획).
export interface PenCharStroke {
  char: string;
  strokes: string[];
}

export const PEN_CHAR_STROKES: PenCharStroke[] = [
  // 보 = ㅂ(top, 4획) + ㅗ(bottom, 2획)
  {
    char: "보",
    strokes: [
      "M15,5 L85,5",
      "M15,5 L15,50",
      "M85,5 L85,50",
      "M15,26 L85,26",
      "M50,60 L50,85",
      "M25,85 L75,85",
    ],
  },
  // 험 = ㅎ(top-left, 3획) + ㅓ(top-right, 2획) + ㅁ(bottom, batchim, 2획)
  {
    char: "험",
    strokes: [
      "M20,6 L33,6",
      "M8,18 L45,18",
      "M37,32 A11,11 0 1,1 15,32 A11,11 0 1,1 37,32",
      "M58,5 L58,48",
      "M58,26 L40,26",
      "M12,58 L88,58 L88,95 L12,95",
      "M12,58 L12,95",
    ],
  },
  // 형 = ㅎ(top-left, 3획) + ㅕ(top-right, 3획) + ㅇ(bottom, batchim, 1획)
  {
    char: "형",
    strokes: [
      "M20,6 L33,6",
      "M8,18 L45,18",
      "M37,32 A11,11 0 1,1 15,32 A11,11 0 1,1 37,32",
      "M58,5 L58,48",
      "M58,16 L40,16",
      "M58,36 L40,36",
      "M68,76 A18,18 0 1,1 32,76 A18,18 0 1,1 68,76",
    ],
  },
  // 광 = ㄱ(top-left, 1획) + ㅘ(=ㅗ+ㅏ, 4획) + ㅇ(bottom, batchim, 1획)
  {
    char: "광",
    strokes: [
      "M10,8 L38,8 L38,28",
      "M50,32 L50,50",
      "M25,50 L75,50",
      "M85,8 L85,50",
      "M85,28 L97,28",
      "M67,78 A17,17 0 1,1 33,78 A17,17 0 1,1 67,78",
    ],
  },
  // 펜 = ㅍ(top-left, 4획) + ㅔ(=ㅓ+ㅣ, 3획) + ㄴ(bottom, batchim, 1획)
  {
    char: "펜",
    strokes: [
      "M8,6 L45,6",
      "M8,6 L8,45",
      "M45,6 L45,45",
      "M18,32 L35,32",
      "M58,5 L58,48",
      "M58,24 L40,24",
      "M85,5 L85,48",
      "M15,58 L15,88 L55,88",
    ],
  },
];
