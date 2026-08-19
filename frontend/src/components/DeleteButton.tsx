/**
 * 목록에서 한 줄을 지우는 버튼.
 *
 * 예전에는 🗑 이모지 하나였다. 이모지는 브라우저·OS마다 모양과 색이 제각각이라(안드로이드는
 * 회색 플라스틱 통, iOS는 파란 통) 화면 톤과 어긋나고, 크기를 맞춰도 선 굵기가 주변 아이콘과
 * 따로 논다.
 *
 * 그래서 웹에서 삭제 아이콘으로 가장 널리 쓰이는 형태(뚜껑 + 손잡이 + 몸통 + 세로선 두 개,
 * Feather/Material/Bootstrap이 모두 같은 골격을 쓴다)를 선 아이콘으로 직접 그린다. 선 굵기와
 * 끝 처리를 화면의 다른 선 아이콘과 같은 값으로 맞춰서, 어느 기기에서 열어도 같은 모양으로
 * 보이고 색은 CSS(currentColor)가 정한다.
 */
export function DeleteButton({
  onClick,
  label = "삭제",
  className = "history-card__delete",
}: {
  onClick: () => void;
  label?: string;
  className?: string;
}) {
  return (
    <button type="button" className={className} title={label} aria-label={label} onClick={onClick}>
      <TrashIcon />
    </button>
  );
}

export function TrashIcon({ size = 17 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      focusable="false"
    >
      {/* 뚜껑 */}
      <path d="M3 6h18" />
      {/* 손잡이 */}
      <path d="M9 6V4.5A1.5 1.5 0 0 1 10.5 3h3A1.5 1.5 0 0 1 15 4.5V6" />
      {/* 몸통 */}
      <path d="M18.5 6l-.8 13.1a1.9 1.9 0 0 1-1.9 1.9H8.2a1.9 1.9 0 0 1-1.9-1.9L5.5 6" />
      {/* 안쪽 세로선 */}
      <path d="M10 10.5v6M14 10.5v6" />
    </svg>
  );
}
