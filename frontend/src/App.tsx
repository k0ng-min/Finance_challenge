import { Route, Routes, useLocation } from "react-router-dom";
import { Home } from "./pages/Home";
import { TripPrep } from "./pages/TripPrep";
import { MyPolicies } from "./pages/MyPolicies";
import { IncidentReport } from "./pages/IncidentReport";
import { DocumentCheck } from "./pages/DocumentCheck";
import { MistakeCheck } from "./pages/MistakeCheck";
import { ClauseHighlight } from "./pages/ClauseHighlight";
import { useApp } from "./context/AppContext";

function App() {
  const { loading } = useApp();
  const location = useLocation();
  const isHome = location.pathname === "/";

  return (
    <div className={`app-shell${isHome ? " app-shell--home" : ""}`}>
      <main className="app-main">
        {loading ? (
          <div className="page">불러오는 중...</div>
        ) : (
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/trip" element={<TripPrep />} />
            <Route path="/policies" element={<MyPolicies />} />
            <Route path="/incident" element={<IncidentReport />} />
            <Route path="/checklist" element={<DocumentCheck />} />
            <Route path="/mistakes" element={<MistakeCheck />} />
            <Route path="/highlights" element={<ClauseHighlight />} />
          </Routes>
        )}
      </main>
    </div>
  );
}

export default App;
