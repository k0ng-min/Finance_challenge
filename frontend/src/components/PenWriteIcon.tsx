/** 홈 화면 "약관 형광펜" 칸의 아이콘. 실제 3D 좌표계(perspective+rotate)로 기울어진
 * 펜 모양(정지)으로 노트북 아이콘을 대신한다 — "쓰는" 동작 자체는 바로 아래 라벨
 * (PenWriteLabel)에서 실제 "약관 형광펜" 글자로 보여주므로, 여기서 또 움직이면
 * 작은 칸 안에 펜 두 개가 따로 움직여 산만해진다. animated로 필요하면 다시 켤 수 있다.
 * 지우고 싶으면 이 컴포넌트를 부르는 곳만 원래 Icon3D로 되돌리면 된다. */
export function PenWriteIcon({ size = 34, animated = false }: { size?: number; animated?: boolean }) {
  return (
    <span
      className={`pen-write-icon${animated ? "" : " pen-write-icon--static"}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <span className="pen-write-icon__pen">
        <span className="pen-write-icon__pen-body" />
        <span className="pen-write-icon__pen-tip" />
      </span>
      {animated && <span className="pen-write-icon__stroke" />}
    </span>
  );
}
