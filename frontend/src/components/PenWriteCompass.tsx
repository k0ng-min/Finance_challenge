/** 홈 화면 히어로(나침반 자리)를 대신하는 2단계 애니메이션. 참고 영상
 * (약관형광펜 Writing.mp4)과 같은 순서 — ① 펜이 "보험형광펜"을 한 글자씩 순서대로
 * 씀 → ② 다 쓰면 펜이 사라지고 노란 형광펜이 등장해 왼쪽부터 훑으며 노란 하이라이트를
 * 칠함 → 처음(빈 화면)으로 돌아가 반복.
 *
 * 펜·형광펜은 이 앱의 다른 아이콘과 같은 출처(Fluent Emoji 3D, MIT License,
 * Microsoft)에서 받은 실제 3D 렌더 이미지다(/public/3d/pen.webp, crayon.webp) —
 * CSS로 그린 도형이 아니라 진짜 에셋이고, 원본 자체가 대각선으로 기울어져 위에서
 * 내려다보는 각도라 별도 원근 변형 없이 그대로 쓴다. 되돌리고 싶으면 Home.tsx에서
 * 이 컴포넌트 호출을 원래 Icon3D로 바꾸면 된다. */
const CHARS = ["보", "험", "형", "광", "펜"];

export function PenWriteCompass() {
  return (
    <span className="pwc" aria-hidden="true">
      <img className="pwc__pen" src="/3d/pen.webp" alt="" />
      <img className="pwc__highlighter" src="/3d/crayon.webp" alt="" />
      <span className="pwc__text">
        {CHARS.map((c, i) => (
          <span key={i} className={`pwc__char pwc__char--${i}`}>{c}</span>
        ))}
        <span className="pwc__highlight-bg" />
      </span>
    </span>
  );
}
