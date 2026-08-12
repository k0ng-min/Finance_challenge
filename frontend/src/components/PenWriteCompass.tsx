/** 홈 화면 히어로(나침반 자리)를 대신하는 3단계 애니메이션. 참고 영상
 * (약관형광펜 Writing.mp4)과 같은 순서에 지우는 단계를 더했다 — ① 펜이
 * "보험형광펜"을 한 글자씩 실제로 그려지듯 씀(펜이 지나간 만큼만 clip-path로
 * 드러남) → ② 다 쓰면 펜이 사라지고 노란 형광펜이 등장해 왼쪽부터 훑으며 노란
 * 하이라이트를 칠함 → ③ 연필 지우개 쪽으로 오른쪽위→왼쪽아래 대각선을 반복하며
 * (쓱싹쓱싹) 오른쪽으로 이동해 전체를 지움 → 처음(빈 화면)으로 돌아가 반복.
 *
 * 펜·형광펜·지우개는 이 앱의 다른 아이콘과 같은 출처(Fluent Emoji 3D, MIT
 * License, Microsoft)에서 받은 실제 3D 렌더 이미지다(/public/3d/pen.webp,
 * crayon.webp, pencil.webp — 지우개 전용 이모지가 없어 연필의 지우개 쪽 끝을
 * 아래로 오게 180도 돌려서 쓴다). CSS로 그린 도형이 아니라 진짜 에셋이고, 원본
 * 자체가 대각선으로 기울어져 위에서 내려다보는 각도라 별도 원근 변형 없이
 * 그대로 쓴다. 되돌리고 싶으면 Home.tsx에서 이 컴포넌트 호출을 원래 Icon3D로
 * 바꾸면 된다. */
const CHARS = ["보", "험", "형", "광", "펜"];

export function PenWriteCompass() {
  return (
    <span className="pwc" aria-hidden="true">
      <img className="pwc__pen" src="/3d/pen.webp" alt="" />
      <img className="pwc__highlighter" src="/3d/crayon.webp" alt="" />
      <img className="pwc__eraser" src="/3d/pencil.webp" alt="" />
      <span className="pwc__text">
        {CHARS.map((c, i) => (
          <span key={i} className={`pwc__char pwc__char--${i}`}>{c}</span>
        ))}
        <span className="pwc__highlight-bg" />
      </span>
    </span>
  );
}
