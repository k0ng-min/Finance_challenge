import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api";

interface AppState {
  userId: number | null;
  tripId: number | null;
  incidentId: number | null;
  setTripId: (id: number) => void;
  setIncidentId: (id: number) => void;
  loading: boolean;
}

const AppCtx = createContext<AppState | null>(null);

const LS_USER = "travel_ai_user_id";
const LS_TRIP = "travel_ai_trip_id";
const LS_INCIDENT = "travel_ai_incident_id";

export function AppProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState<number | null>(null);
  const [tripId, setTripIdState] = useState<number | null>(
    () => Number(localStorage.getItem(LS_TRIP)) || null
  );
  const [incidentId, setIncidentIdState] = useState<number | null>(
    () => Number(localStorage.getItem(LS_INCIDENT)) || null
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const existing = Number(localStorage.getItem(LS_USER));
    if (existing) {
      setUserId(existing);
      setLoading(false);
      return;
    }
    api
      .createUser("guest")
      .then((u) => {
        localStorage.setItem(LS_USER, String(u.user_id));
        setUserId(u.user_id);
      })
      .finally(() => setLoading(false));
  }, []);

  const setTripId = (id: number) => {
    localStorage.setItem(LS_TRIP, String(id));
    setTripIdState(id);
  };
  const setIncidentId = (id: number) => {
    localStorage.setItem(LS_INCIDENT, String(id));
    setIncidentIdState(id);
  };

  return (
    <AppCtx.Provider value={{ userId, tripId, incidentId, setTripId, setIncidentId, loading }}>
      {children}
    </AppCtx.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppCtx);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
