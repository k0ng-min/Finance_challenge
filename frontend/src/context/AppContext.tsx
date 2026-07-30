import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type AuthUserOut } from "../api";

interface AppState {
  userId: number | null;
  tripId: number | null;
  incidentId: number | null;
  setTripId: (id: number) => void;
  setIncidentId: (id: number) => void;
  loading: boolean;
  // 인증 상태 — 로그인 전에는 nickname/email이 없는 익명 게스트로 동작한다
  nickname: string | null;
  email: string | null;
  // 로그인 계정에는 한 번 입력한 나이가 프로필에 저장돼, 여행준비·사고접수·내보험등록에서
  // 매번 다시 물어보지 않고 자동으로 채워진다(게스트는 세션이 매번 새로 시작돼 저장할 곳이 없다).
  age: number | null;
  isLoggedIn: boolean;
  loginWithKakao: (code: string, intent: "login" | "signup") => Promise<boolean>;
  loginWithGoogle: (code: string, intent: "login" | "signup") => Promise<boolean>;
  updateNickname: (nickname: string) => Promise<void>;
  updateAge: (age: number) => Promise<void>;
  deleteAccount: () => Promise<void>;
  logout: () => Promise<void>;
}

const AppCtx = createContext<AppState | null>(null);

const LS_USER = "travel_ai_user_id";
const LS_TRIP = "travel_ai_trip_id";
const LS_INCIDENT = "travel_ai_incident_id";
const LS_TOKEN = "travel_ai_token";
const LS_NICKNAME = "travel_ai_nickname";
const LS_EMAIL = "travel_ai_email";

export function AppProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState<number | null>(null);
  const [tripId, setTripIdState] = useState<number | null>(
    () => Number(localStorage.getItem(LS_TRIP)) || null
  );
  const [incidentId, setIncidentIdState] = useState<number | null>(
    () => Number(localStorage.getItem(LS_INCIDENT)) || null
  );
  const [loading, setLoading] = useState(true);
  const [nickname, setNickname] = useState<string | null>(() => localStorage.getItem(LS_NICKNAME));
  const [email, setEmail] = useState<string | null>(() => localStorage.getItem(LS_EMAIL));
  const [age, setAge] = useState<number | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  async function bootstrapGuest() {
    const existing = Number(localStorage.getItem(LS_USER));
    if (existing) {
      setUserId(existing);
      return;
    }
    const u = await api.createUser("guest");
    localStorage.setItem(LS_USER, String(u.user_id));
    setUserId(u.user_id);
  }

  function applyAuthResult(res: AuthUserOut) {
    localStorage.setItem(LS_TOKEN, res.token);
    localStorage.setItem(LS_USER, String(res.user_id));
    localStorage.setItem(LS_NICKNAME, res.nickname);
    localStorage.setItem(LS_EMAIL, res.email ?? "");
    setUserId(res.user_id);
    setNickname(res.nickname);
    setEmail(res.email);
    setAge(res.age);
    setIsLoggedIn(true);
  }

  useEffect(() => {
    async function restore() {
      const token = localStorage.getItem(LS_TOKEN);
      if (token) {
        try {
          const me = await api.getMe();
          localStorage.setItem(LS_USER, String(me.user_id));
          localStorage.setItem(LS_NICKNAME, me.nickname);
          if (me.email) localStorage.setItem(LS_EMAIL, me.email);
          setUserId(me.user_id);
          setNickname(me.nickname);
          setEmail(me.email);
          setAge(me.age);
          setIsLoggedIn(true);
          setLoading(false);
          return;
        } catch {
          // 토큰이 만료/무효 — 로그아웃 상태로 되돌리고 게스트로 진행
          localStorage.removeItem(LS_TOKEN);
          localStorage.removeItem(LS_NICKNAME);
          localStorage.removeItem(LS_EMAIL);
        }
      }
      await bootstrapGuest();
      setLoading(false);
    }
    restore();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setTripId = (id: number) => {
    localStorage.setItem(LS_TRIP, String(id));
    setTripIdState(id);
  };
  const setIncidentId = (id: number) => {
    localStorage.setItem(LS_INCIDENT, String(id));
    setIncidentIdState(id);
  };

  function clearTripAndIncident() {
    localStorage.removeItem(LS_TRIP);
    localStorage.removeItem(LS_INCIDENT);
    setTripIdState(null);
    setIncidentIdState(null);
  }

  async function loginWithKakao(code: string, intent: "login" | "signup") {
    clearTripAndIncident();
    const res = await api.loginWithKakao(code, userId, intent);
    applyAuthResult(res);
    return res.is_new_user;
  }

  async function loginWithGoogle(code: string, intent: "login" | "signup") {
    clearTripAndIncident();
    const res = await api.loginWithGoogle(code, userId, intent);
    applyAuthResult(res);
    return res.is_new_user;
  }

  async function updateNickname(newNickname: string) {
    const res = await api.updateNickname(newNickname);
    localStorage.setItem(LS_NICKNAME, res.nickname);
    setNickname(res.nickname);
  }

  async function updateAge(newAge: number) {
    const res = await api.updateAge(newAge);
    setAge(res.age);
  }

  async function deleteAccount() {
    await api.deleteAccount();
    // 계정 자체가 사라졌으니 세션도 같이 정리하고 새 게스트로 되돌린다(logout과 동일한 뒷정리).
    localStorage.removeItem(LS_TOKEN);
    localStorage.removeItem(LS_NICKNAME);
    localStorage.removeItem(LS_EMAIL);
    localStorage.removeItem(LS_USER);
    clearTripAndIncident();
    setNickname(null);
    setEmail(null);
    setAge(null);
    setIsLoggedIn(false);
    setUserId(null);
    setLoading(true);
    await bootstrapGuest();
    setLoading(false);
  }

  async function logout() {
    try {
      await api.logout();
    } catch {
      // 토큰이 이미 무효해도 로컬 상태는 정리한다
    }
    localStorage.removeItem(LS_TOKEN);
    localStorage.removeItem(LS_NICKNAME);
    localStorage.removeItem(LS_EMAIL);
    localStorage.removeItem(LS_USER);
    clearTripAndIncident();
    setNickname(null);
    setEmail(null);
    setAge(null);
    setIsLoggedIn(false);
    setUserId(null);
    setLoading(true);
    await bootstrapGuest();
    setLoading(false);
  }

  return (
    <AppCtx.Provider
      value={{
        userId, tripId, incidentId, setTripId, setIncidentId, loading,
        nickname, email, age, isLoggedIn, loginWithKakao, loginWithGoogle,
        updateNickname, updateAge, deleteAccount, logout,
      }}
    >
      {children}
    </AppCtx.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppCtx);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
