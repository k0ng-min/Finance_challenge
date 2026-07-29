import { Navigate, Route, Routes } from "react-router-dom";
import { Nav } from "./components/Nav";
import { TripPrep } from "./pages/TripPrep";
import { MyPolicies } from "./pages/MyPolicies";
import { IncidentReport } from "./pages/IncidentReport";
import { DocumentCheck } from "./pages/DocumentCheck";
import { MistakeCheck } from "./pages/MistakeCheck";
import { ClauseHighlight } from "./pages/ClauseHighlight";
import { useApp } from "./context/AppContext";

function App() {
  const { loading } = useApp();

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-header__title">여행자보험 전 생애주기 AI</span>
        <span className="app-header__subtitle">근거 기반 · 6개 보험사 실제 약관</span>
      </header>

      <main className="app-main">
        {loading ? (
          <div className="page">불러오는 중...</div>
        ) : (
          <Routes>
            <Route path="/" element={<Navigate to="/trip" replace />} />
            <Route path="/trip" element={<TripPrep />} />
            <Route path="/policies" element={<MyPolicies />} />
            <Route path="/incident" element={<IncidentReport />} />
            <Route path="/checklist" element={<DocumentCheck />} />
            <Route path="/mistakes" element={<MistakeCheck />} />
            <Route path="/highlights" element={<ClauseHighlight />} />
          </Routes>
        )}
      </main>

      <Nav />
    </div>
  );
}

export default App;
