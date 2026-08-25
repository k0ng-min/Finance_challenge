import { lazy, Suspense, useRef } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { LoadingState } from "./components/LoadingState";
import { AppFooter } from "./components/AppFooter";
import { BackgroundDecor } from "./components/BackgroundDecor";
import { FrameScrollbar } from "./components/FrameScrollbar";
import { useApp } from "./context/AppContext";

// 화면마다 code-split한다 — 특히 홈 화면의 손글씨 애니메이션이 gsap을
// 끌고 오는데, 예전에는 그게 다른 모든 화면(사고 시뮬레이션, 약관
// 형광펜 등)의 코드와 한 덩어리(706KB)로 묶여서 앱을 처음 열 때 전부
// 같이 내려받아야 했다. 화면별로 나누면 방금 연 화면의 코드만 받는다.
const Home = lazy(() => import("./pages/Home").then((m) => ({ default: m.Home })));
const TripPrep = lazy(() => import("./pages/TripPrep").then((m) => ({ default: m.TripPrep })));
const MyPolicies = lazy(() => import("./pages/MyPolicies").then((m) => ({ default: m.MyPolicies })));
const IncidentReport = lazy(() =>
  import("./pages/IncidentReport").then((m) => ({ default: m.IncidentReport })),
);
const ClaimCheck = lazy(() => import("./pages/ClaimCheck").then((m) => ({ default: m.ClaimCheck })));
const PremiumCalc = lazy(() => import("./pages/PremiumCalc").then((m) => ({ default: m.PremiumCalc })));
const ClauseHighlight = lazy(() =>
  import("./pages/ClauseHighlight").then((m) => ({ default: m.ClauseHighlight })),
);
const Onsite = lazy(() => import("./pages/Onsite").then((m) => ({ default: m.Onsite })));
const Simulate = lazy(() => import("./pages/Simulate").then((m) => ({ default: m.Simulate })));
const Account = lazy(() => import("./pages/Account").then((m) => ({ default: m.Account })));
const SetNickname = lazy(() => import("./pages/SetNickname").then((m) => ({ default: m.SetNickname })));
const OAuthCallback = lazy(() =>
  import("./pages/OAuthCallback").then((m) => ({ default: m.OAuthCallback })),
);
const NotFound = lazy(() => import("./pages/NotFound").then((m) => ({ default: m.NotFound })));

function App() {
  const { loading, isLoggedIn, signupCompleted } = useApp();
  const location = useLocation();
  const isHome = location.pathname === "/";
  const mainRef = useRef<HTMLElement>(null);
  // 소셜 콜백은 계정 행을 먼저 만든 뒤 닉네임 설정 화면으로 보낸다. 예전에는 거기서
  // 뒤로 나가면 계정만 남고 프로필은 빈 채로 굳어버렸다(다시 로그인해도 채울 화면이
  // 없었다). 가입 마무리가 끝나지 않은 동안에는 어느 주소로 들어와도 그 화면으로 되돌린다.
  const needsSignupFinish = isLoggedIn && !signupCompleted;

  if (loading) {
    return (
      <div className="app-shell">
        <main className="app-main">
          <div className="page">
            <LoadingState label="여행자보험 AI를 준비하고 있어요..." />
          </div>
        </main>
      </div>
    );
  }

  if (needsSignupFinish && location.pathname !== "/account/nickname") {
    return <Navigate to="/account/nickname" replace />;
  }

  return (
    <>
      <BackgroundDecor />
      <div className={`app-shell${isHome ? " app-shell--home" : ""}`}>
        <main className="app-main" ref={mainRef}>
          <Suspense
            fallback={
              <div className="page">
                <LoadingState label="불러오는 중..." />
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/trip" element={<TripPrep />} />
              <Route path="/policies" element={<MyPolicies />} />
              <Route path="/incident" element={<IncidentReport />} />
              <Route path="/checklist" element={<ClaimCheck />} />
              {/* 예전 경로로 들어와도 합쳐진 화면으로 보내되, 원래 보려던 탭을 편다 */}
              <Route path="/mistakes" element={<Navigate to="/checklist?tab=mistakes" replace />} />
              <Route path="/premium" element={<PremiumCalc />} />
              <Route path="/highlights" element={<ClauseHighlight />} />
              <Route path="/onsite" element={<Onsite />} />
              <Route path="/simulate" element={<Simulate />} />
              <Route path="/account" element={<Account />} />
              <Route path="/account/nickname" element={<SetNickname />} />
              <Route path="/auth/kakao/callback" element={<OAuthCallback provider="kakao" />} />
              <Route path="/auth/google/callback" element={<OAuthCallback provider="google" />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
          {/* 홈은 프레임 높이에 맞춘 자체 배치 안에 같은 문구를 이미 갖고 있다(.home__footer) —
              여기서 또 붙이면 두 번 나온다. */}
          {!isHome && <AppFooter />}
        </main>
        <FrameScrollbar targetRef={mainRef} />
      </div>
    </>
  );
}

export default App;
