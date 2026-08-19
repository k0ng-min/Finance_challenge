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
  /** "M" | "F" — 보험료가 나이와 함께 성별로도 갈려서 같이 들고 다닌다. */
  sex: string | null;
  isLoggedIn: boolean;
  /** 닉네임·나이·필수동의까지 마친 계정인지. 소셜 콜백에서 계정 행이 먼저 만들어지는
   * 구조라 "계정은 있는데 프로필이 빈" 중간 상태가 생기는데, 이 값이 false인 동안에는
   * App이 어느 화면에 있든 가입 마무리 화면으로 되돌린다. */
  signupCompleted: boolean;
  /** 이메일+비밀번호로도 로그인할 수 있게 비밀번호를 정해 뒀는지. */
  hasPassword: boolean;
  loginWithKakao: (code: string, intent: "login" | "signup") => Promise<boolean>;
  loginWithGoogle: (code: string, intent: "login" | "signup") => Promise<boolean>;
  loginWithEmail: (email: string, password: string) => Promise<void>;
  setPassword: (newPassword: string, currentPassword?: string | null) => Promise<void>;
  /** 가입 마무리를 끝냈다고 표시한다(약관 동의 응답을 그대로 반영). */
  applyAuthUser: (res: AuthUserOut) => void;
  /** 가입 마무리 전에 되돌아 나갈 때 — 아직 완료되지 않은 계정을 지우고 게스트로 되돌린다. */
  cancelPendingSignup: () => Promise<void>;
  updateNickname: (nickname: string) => Promise<void>;
  updateAge: (age: number) => Promise<void>;
  updateSex: (sex: string) => Promise<void>;
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
// 게스트도 서버에서 토큰을 받아 자기 데이터를 꺼내므로, "토큰이 있다 = 로그인했다"가
// 아니다 — 실제로 로그인한 계정과 자동 생성된 게스트를 구분하는 표시.
const LS_GUEST = "travel_ai_is_guest";
// 나이·성별은 게스트도 다시 묻지 않도록 로컬에도 남긴다(로그인 계정은 서버 프로필이 우선).
const LS_AGE = "travel_ai_age";
const LS_SEX = "travel_ai_sex";

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
  const [age, setAge] = useState<number | null>(() => Number(localStorage.getItem(LS_AGE)) || null);
  const [sex, setSex] = useState<string | null>(() => localStorage.getItem(LS_SEX));
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [signupCompleted, setSignupCompleted] = useState(true);
  const [hasPassword, setHasPassword] = useState(false);

  async function bootstrapGuest() {
    const existing = Number(localStorage.getItem(LS_USER));
    // 예전에 만든 게스트는 토큰이 없다. 서버가 이제 소유권 증명을 요구하므로(익명 접근
    // 차단) 토큰이 없으면 자기 데이터를 못 꺼낸다 — 계정을 새로 만들어 토큰을 받는다.
    if (existing && localStorage.getItem(LS_TOKEN)) {
      setUserId(existing);
      return;
    }
    const u = await api.createUser("guest");
    localStorage.setItem(LS_USER, String(u.user_id));
    localStorage.setItem(LS_TOKEN, u.token);
    localStorage.setItem(LS_GUEST, "1");
    setUserId(u.user_id);
  }

  function applyAuthResult(res: AuthUserOut) {
    localStorage.removeItem(LS_GUEST);
    localStorage.setItem(LS_TOKEN, res.token);
    localStorage.setItem(LS_USER, String(res.user_id));
    localStorage.setItem(LS_NICKNAME, res.nickname);
    localStorage.setItem(LS_EMAIL, res.email ?? "");
    setUserId(res.user_id);
    setNickname(res.nickname);
    setEmail(res.email);
    setAge(res.age);
    setSex(res.sex ?? null);
    setSignupCompleted(res.signup_completed);
    setHasPassword(res.has_password);
    setIsLoggedIn(true);
  }

  useEffect(() => {
    async function restore() {
      const token = localStorage.getItem(LS_TOKEN);
      if (token) {
        try {
          const me = await api.getMe();
          // 게스트는 토큰이 있어도 "로그인한 사용자"가 아니다 — 로그인한 적이
          // 없는데 상단에 게스트 닉네임이 로그인 계정처럼 뜨던 원인이 여기였다.
          // 표시가 없는 예전 세션은 이메일 유무로 판별한다(게스트는 이메일이 없다).
          const guestFlag = localStorage.getItem(LS_GUEST);
          const isGuest = guestFlag === "1" || (guestFlag === null && !me.email);
          localStorage.setItem(LS_USER, String(me.user_id));
          setUserId(me.user_id);
          setAge(me.age);
          setSex(me.sex ?? null);
          if (isGuest) {
            // 게스트는 그대로 쓰되(데이터 접근은 토큰으로 계속 된다) 로그인
            // 상태로는 취급하지 않는다.
            localStorage.setItem(LS_GUEST, "1");
            localStorage.removeItem(LS_NICKNAME);
            localStorage.removeItem(LS_EMAIL);
            setNickname(null);
            setEmail(null);
            setSignupCompleted(true);
            setHasPassword(false);
            setIsLoggedIn(false);
          } else {
            localStorage.setItem(LS_NICKNAME, me.nickname);
            if (me.email) localStorage.setItem(LS_EMAIL, me.email);
            setNickname(me.nickname);
            setEmail(me.email);
            setSignupCompleted(me.signup_completed);
            setHasPassword(me.has_password);
            setIsLoggedIn(true);
          }
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

  // 지금까지는 "지금 보고 있는 사고"를 localStorage에만 들고 있어서, 로그인하거나 브라우저를
  // 껐다 켜거나 다른 기기에서 열면 그 값이 비고 → 약관 형광펜·서류 체크·실수 방지 화면이
  // 사고가 여러 건 접수돼 있는데도 "접수된 사고가 없어요"로 보였다. 서버 이력을 기준으로
  // 다시 맞춘다: 저장된 ID가 실제로 남아 있으면 그대로 쓰고, 없거나 비었으면 가장 최근 사고를 고른다.
  useEffect(() => {
    if (loading || !userId) return;
    let cancelled = false;
    api.listIncidents(userId)
      .then((list) => {
        if (cancelled) return;
        if (list.length === 0) {
          localStorage.removeItem(LS_INCIDENT);
          setIncidentIdState(null);
          return;
        }
        const stored = Number(localStorage.getItem(LS_INCIDENT)) || null;
        const stillExists = stored != null && list.some((i) => i.incident_id === stored);
        const resolved = stillExists ? stored! : list[0].incident_id;
        localStorage.setItem(LS_INCIDENT, String(resolved));
        setIncidentIdState(resolved);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [loading, userId, isLoggedIn]);

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

  async function loginWithEmail(email: string, password: string) {
    clearTripAndIncident();
    const res = await api.loginWithEmail(email, password);
    applyAuthResult(res);
  }

  async function setPassword(newPassword: string, currentPassword?: string | null) {
    const res = await api.setPassword(newPassword, currentPassword);
    setHasPassword(res.has_password);
  }

  /** 약관 동의 응답처럼 계정 상태 전체가 담긴 응답을 그대로 반영한다(토큰은 그대로 유지). */
  function applyAuthUser(res: AuthUserOut) {
    localStorage.setItem(LS_NICKNAME, res.nickname);
    if (res.email) localStorage.setItem(LS_EMAIL, res.email);
    setNickname(res.nickname);
    setEmail(res.email);
    setAge(res.age);
    setSex(res.sex ?? null);
    setSignupCompleted(res.signup_completed);
    setHasPassword(res.has_password);
  }

  async function cancelPendingSignup() {
    try {
      await api.cancelPendingSignup();
    } catch {
      // 이미 지워졌거나 세션이 끊긴 경우 — 아래 뒷정리는 그대로 진행한다.
    }
    await logout();
  }

  async function updateNickname(newNickname: string) {
    const res = await api.updateNickname(newNickname);
    localStorage.setItem(LS_NICKNAME, res.nickname);
    setNickname(res.nickname);
  }

  async function updateAge(newAge: number) {
    localStorage.setItem(LS_AGE, String(newAge));
    setAge(newAge);
    if (!localStorage.getItem(LS_TOKEN)) return; // 게스트는 로컬에만 남긴다
    const res = await api.updateAge(newAge);
    setAge(res.age);
  }

  async function updateSex(newSex: string) {
    localStorage.setItem(LS_SEX, newSex);
    setSex(newSex);
    if (!localStorage.getItem(LS_TOKEN)) return; // 게스트는 로컬에만 남긴다
    const res = await api.updateSex(newSex);
    setSex(res.sex ?? newSex);
  }

  async function deleteAccount() {
    await api.deleteAccount();
    // 계정 자체가 사라졌으니 세션도 같이 정리하고 새 게스트로 되돌린다(logout과 동일한 뒷정리).
    localStorage.removeItem(LS_TOKEN);
    localStorage.removeItem(LS_NICKNAME);
    localStorage.removeItem(LS_EMAIL);
    localStorage.removeItem(LS_USER);
    localStorage.removeItem(LS_GUEST);
    clearTripAndIncident();
    setNickname(null);
    setEmail(null);
    setAge(null);
    setSignupCompleted(true);
    setHasPassword(false);
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
    localStorage.removeItem(LS_GUEST);
    clearTripAndIncident();
    setNickname(null);
    setEmail(null);
    setAge(null);
    setSignupCompleted(true);
    setHasPassword(false);
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
        nickname, email, age, sex, isLoggedIn, signupCompleted, hasPassword,
        loginWithKakao, loginWithGoogle, loginWithEmail, setPassword,
        applyAuthUser, cancelPendingSignup,
        updateNickname, updateAge, updateSex, deleteAccount, logout,
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
