interface Icon3DProps {
  src: string;
  size?: number;
  className?: string;
}

/**
 * 3dicons.co(CC0) 클레이 3D 렌더. 흰 배경은 제거된 실제 알파 PNG/WEBP이며,
 * 파란 색조는 CSS filter(sepia+hue-rotate)로 입혀 라이트/다크 테마마다 다르게 보인다.
 * 별도의 배경 박스 없이 아이콘 실루엣만 표면 위에 바로 놓인다.
 */
export function Icon3D({ src, size = 64, className }: Icon3DProps) {
  return (
    <img
      src={`/3d/${src}.webp`}
      alt=""
      className={`icon3d${className ? ` ${className}` : ""}`}
      style={{ width: size, height: size }}
    />
  );
}
