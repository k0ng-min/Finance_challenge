import { Route, Routes, useLocation } from "react-router-dom";
import { Home } from "./pages/Home";
import { TripPrep } from "./pages/TripPrep";
import { MyPolicies } from "./pages/MyPolicies";
import { IncidentReport } from "./pages/IncidentReport";
import { DocumentCheck } from "./pages/DocumentCheck";
import { MistakeCheck } from "./pages/MistakeCheck";
import { ClauseHighlight } from "./pages/ClauseHighlight";
import { Account } from "./pages/Account";
import { SetNickname } from "./pages/SetNickname";
import { OAuthCallback } from "./pages/OAuthCallback";
import { NotFound } from "./pages/NotFound";
import { LoadingState } from "./components/LoadingState";
import { BackgroundDecor } from "./components/BackgroundDecor";
import { useApp } from "./context/AppContext";

function App() {
  const { loading } = useApp();
  const location = useLocation();
  const isHome = location.pathname === "/";

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

  return (
    <>
      <BackgroundDecor />
      <div className={`app-shell${isHome ? " app-shell--home" : ""}`}>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/trip" element={<TripPrep />} />
            <Route path="/policies" element={<MyPolicies />} />
            <Route path="/incident" element={<IncidentReport />} />
            <Route path="/checklist" element={<DocumentCheck />} />
            <Route path="/mistakes" element={<MistakeCheck />} />
            <Route path="/highlights" element={<ClauseHighlight />} />
            <Route path="/account" element={<Account />} />
            <Route path="/account/nickname" element={<SetNickname />} />
            <Route path="/auth/kakao/callback" element={<OAuthCallback provider="kakao" />} />
            <Route path="/auth/google/callback" element={<OAuthCallback provider="google" />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </div>
    </>
  );
}

export default App;
