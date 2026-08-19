/** 모든 화면 맨 아래에 붙는 저작권 표시.
 *
 * 홈에는 원래부터 같은 문구가 있었는데(.home__footer) 다른 화면에는 없어서, 스크롤을
 * 끝까지 내리면 화면마다 마감이 달라 보였다. 홈은 프레임 높이에 딱 맞춰 배치가 짜여
 * 있어(flex 밴드) 자기 것을 그대로 두고, 나머지 화면은 App이 라우트 뒤에 이걸 한 번 붙인다. */
export function AppFooter() {
  return <p className="app-footer">© 2026 BohumPen</p>;
}
