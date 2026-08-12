/** 라벨 글자를 펜이 실제로 쓰는 것처럼 왼쪽부터 드러낸다(반복). 아이콘 크기(24~50px)에
 * 글씨를 구겨넣는 대신, 이미 정상적으로 읽히는 라벨 텍스트 자체를 애니메이션 대상으로
 * 삼아서 "약관형광펜"이 실제로 읽히는 글씨로 쓰여지는 걸 보여준다. 순수 CSS
 * (background-clip: text로 드러내기 + perspective/rotate로 기울어진 펜)만 쓴다. */
export function PenWriteLabel({ text }: { text: string }) {
  return (
    <span className="pen-write-label home-quick__label">
      <span className="pen-write-label__pen" aria-hidden="true">
        <span className="pen-write-label__pen-body" />
        <span className="pen-write-label__pen-tip" />
      </span>
      <span className="pen-write-label__text">{text}</span>
    </span>
  );
}
