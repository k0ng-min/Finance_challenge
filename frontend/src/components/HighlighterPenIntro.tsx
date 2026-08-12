/** 약관 형광펜 페이지의 데스크톱 히어로 장식. 실제 조항 원문과는 무관한 독립 컴포넌트라 —
 * 지우고 싶으면 이 컴포넌트를 부르는 한 줄만 빼면 된다(kyeongmin 브랜치 설계 문서 참고).
 *
 * CSS 3D transform(perspective+rotate)만으로 기울어진 펜이 텍스트 위를 훑고 지나가는
 * 모습을 만든다 — 이미지 에셋이나 Three.js 없이도 입체감을 낸다. 요청대로 애니메이션은
 * 한 번 재생하고 끝나지 않고 계속 반복한다. */
export function HighlighterPenIntro() {
  return (
    <div className="pen-intro" aria-hidden="true">
      <span className="pen-intro__text">
        실제로 관련 있는 부분만{" "}
        <span className="pen-intro__target">
          노란색으로
          <span className="pen-intro__pen">
            <span className="pen-intro__pen-body" />
            <span className="pen-intro__pen-tip" />
          </span>
        </span>{" "}
        표시돼요
      </span>
    </div>
  );
}
