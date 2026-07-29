interface Icon3DProps {
  src: string;
  size?: number;
  bg?: string;
  rounded?: string;
  className?: string;
}

/**
 * 3dicons.co(CC0) 클레이 스타일 3D 렌더를 사용한다. 원본은 흰 배경 PNG/WEBP라
 * mix-blend-mode: multiply로 배경색과 합성하면 그 색의 점토 재질처럼 자연스럽게
 * 녹아든다(흰 배경이 제거되고, 음영은 배경색을 곱해 자동으로 따뜻하게 물든다).
 */
export function Icon3D({ src, size = 64, bg = "#F6DFC4", rounded = "30%", className }: Icon3DProps) {
  return (
    <div
      className={`icon3d${className ? ` ${className}` : ""}`}
      style={{ width: size, height: size, background: bg, borderRadius: rounded }}
    >
      <img src={`/3d/${src}.webp`} alt="" className="icon3d__img" />
    </div>
  );
}
