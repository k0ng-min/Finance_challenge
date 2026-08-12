/** 홈 화면 히어로(나침반 자리)를 대신하는 2단계 애니메이션. 참고 영상
 * (약관형광펜 Writing.mp4)과 같은 순서 — ① 검은 펜이 "약관형광펜"을 한 글자씩
 * 순서대로 씀 → ② 다 쓰면 펜이 사라지고 노란 형광펜이 등장해 왼쪽부터 훑으며
 * 노란 배경을 칠함 → 처음(빈 화면)으로 돌아가 반복. 전부 CSS만 쓴다(이미지·영상
 * 에셋 없음). 되돌리고 싶으면 Home.tsx에서 이 컴포넌트 호출을 원래 Icon3D로
 * 바꾸면 된다. */
const CHARS = ["약", "관", "형", "광", "펜"];

export function PenWriteCompass() {
  return (
    <span className="pwc" aria-hidden="true">
      <span className="pwc__pen">
        <span className="pwc__pen-body" />
        <span className="pwc__pen-tip" />
      </span>
      <span className="pwc__highlighter">
        <span className="pwc__highlighter-body" />
        <span className="pwc__highlighter-tip" />
      </span>
      <span className="pwc__text">
        <span className="pwc__highlight-bg" />
        {CHARS.map((c, i) => (
          <span key={i} className={`pwc__char pwc__char--${i}`}>{c}</span>
        ))}
      </span>
    </span>
  );
}
