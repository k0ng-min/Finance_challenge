import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { SESSION_EXPIRED_EVENT, api, pingHealth, type AuthUserOut } from "../api";

/** 앱을 처음 열 때 서버에 닿기까지의 단계. 화면 문구가 여기에 따라 갈린다. */
export type BootPhase = "connecting" | "waking" | "failed";

// 이만큼 지나도록 서버가 응답하지 않으면 "잠든 서버를 깨우는 중"이라고 알린다.
// 깨어 있는 서버는 1초 안에 답하므로, 이 시간을 넘겼다는 건 기상 중이라는 뜻이다.
// 너무 짧게 잡으면 잠깐 느린 네트워크에도 "서버가 잠들었다"는 오해를 준다.
const WAKE_NOTICE_SECONDS = 6;
// 여기까지 못 깨우면 포기하고 다시 시도할 길을 준다. 무료 인스턴스의 기상은 보통
// 30~60초라서, 그 두 배쯤 기다려 본 뒤에도 안 되면 다른 문제로 보는 게 맞다.
const BOOT_DEADLINE_MS = 90000;

interface AppState {
  userId: number | null;
  tripId: number | null;
  incidentId: number | null;
  setTripId: (id: number) => void;
  setIncidentId: (id: number) => void;
  loading: boolean;
  /** 서버에 닿기까지의 단계. 부팅 화면이 이 값으로 문구를 고른다. */
  bootPhase: BootPhase;
  /** 부팅을 시작한 뒤 흐른 초. 기다리는 사람에게 진행 중임을 보여주는 데 쓴다. */
  bootSeconds: number;
  /** 서버 깨우기에 실패했을 때 처음부터 다시 시도한다. */
  retryBoot: () => void;
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
  const [bootPhase, setBootPhase] = useState<BootPhase>("connecting");
  const [bootSeconds, setBootSeconds] = useState(0);
  // 「다시 시도」가 이 값을 올리면 부팅 effect가 통째로 다시 돈다.
  const [bootAttempt, setBootAttempt] = useState(0);
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
    let cancelled = false;
    const startedAt = Date.now();
    setLoading(true);
    setBootPhase("connecting");
    setBootSeconds(0);

    // 1초마다 경과 시간을 올린다. 화면은 이 값으로 "몇 초째 기다리는 중"을 보여주고,
    // WAKE_NOTICE_SECONDS를 넘으면 문구를 "서버를 깨우는 중"으로 바꾼다.
    const ticker = window.setInterval(() => {
      if (cancelled) return;
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setBootSeconds(elapsed);
      if (elapsed >= WAKE_NOTICE_SECONDS) {
        setBootPhase((p) => (p === "connecting" ? "waking" : p));
      }
    }, 1000);

    /** 서버가 응답할 때까지 두드린다. 성공하면 true, 제한 시간을 넘기면 false. */
    async function wakeServer(): Promise<boolean> {
      let backoff = 1000;
      while (!cancelled && Date.now() - startedAt < BOOT_DEADLINE_MS) {
        try {
          await pingHealth(20000);
          return true;
        } catch {
          // 아직 안 깨어났거나 네트워크가 흔들린 것. 잠시 쉬었다 다시 두드린다 —
          // 붙잡혀 있던 그 시간이 곧 서버가 일어나던 시간이라 헛수고가 아니다.
          await new Promise((r) => setTimeout(r, backoff));
          backoff = Math.min(backoff * 2, 8000);
        }
      }
      return false;
    }

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
      try {
        await bootstrapGuest();
      } catch {
        // 게스트 생성까지 실패하면 지금은 서버에 닿지 않는다는 뜻이다. 여기서 그냥
        // 던져 버리면 아래 setLoading(false)가 영영 실행되지 않아, 사용자는 이유도
        // 모른 채 "준비하고 있어요..." 화면에 갇힌다(백엔드가 잠들어 있을 때 실제로
        // 그랬다). userId 없이 진행시키면 각 화면이 자기 몫의 안내를 띄운다.
      }
      setLoading(false);
    }

    (async () => {
      // 서버를 먼저 깨우고 나서 세션을 복원한다. 깨어 있을 때 /health는 수십 밀리초라
      // 사실상 공짜고, 잠들어 있을 때는 이 두드림이 곧 기상 신호가 된다.
      const awake = await wakeServer();
      if (cancelled) return;
      if (!awake) {
        // loading을 풀지 않는다 — 서버에 닿지 못하는 채로 화면을 열어 주면 어느 기능을
        // 눌러도 실패한다. 대신 이유를 밝히고 다시 시도할 길을 준다(App의 BootScreen).
        setBootPhase("failed");
        return;
      }
      await restore();
      if (!cancelled) window.clearInterval(ticker);
    })();

    return () => {
      cancelled = true;
      window.clearInterval(ticker);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bootAttempt]);

  // 서버가 세션을 끊으면(유효기간 만료, 또는 로그인 계정의 30분 무활동) api.ts가 죽은
  // 토큰을 치우고 이 신호를 보낸다. 화면 상태도 같이 게스트로 되돌려야, 상단에 닉네임이
  // 남아 "로그인돼 있는데 아무것도 안 되는" 상태가 생기지 않는다.
  //
  // 로그아웃만 시키고 끝내지 않고 게스트 세션을 새로 받는다 — 이 앱은 로그인 없이도 모든
  // 기능을 쓸 수 있는 게 기본이라, 끊긴 자리에서 그대로 이어 쓸 수 있어야 한다.
  useEffect(() => {
    function onExpired() {
      setIsLoggedIn(false);
      setNickname(null);
      setEmail(null);
      setHasPassword(false);
      setSignupCompleted(true);
      localStorage.removeItem(LS_USER);
      bootstrapGuest().catch(() => {
        // 게스트 재발급까지 실패하면 서버에 닿지 않는 상황이다. 각 화면이 자기 몫의
        // 안내를 띄우고, 다음 요청이 성공하면 자연히 회복된다.
      });
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 여행 ID도 사고와 똑같이 서버 기준으로 맞춰 준다. localStorage에 남은 trip_id를
  // 그대로 믿으면, 그 여행이 이미 없는 경우(게스트 토큰이 사라져 계정이 새로 만들어졌거나,
  // 게스트가 새 여행을 등록하며 앞 기록이 정리됐거나, 서버 데이터가 초기화된 경우)에도
  // 화면들이 그 ID로 요청을 보낸다 → 404. 「해외 서류 챙기기」에서 나라를 고르기도 전에
  // "현지 대응 정보를 불러오지 못했어요" 배너가 뜨던 게 정확히 이 경우였다.
  useEffect(() => {
    if (loading || !userId) return;
    let cancelled = false;
    api.listTrips(userId)
      .then((list) => {
        if (cancelled) return;
        if (list.length === 0) {
          localStorage.removeItem(LS_TRIP);
          setTripIdState(null);
          return;
        }
        const stored = Number(localStorage.getItem(LS_TRIP)) || null;
        const stillExists = stored != null && list.some((t) => t.trip_id === stored);
        const resolved = stillExists ? stored! : list[0].trip_id;
        localStorage.setItem(LS_TRIP, String(resolved));
        setTripIdState(resolved);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [loading, userId, isLoggedIn]);

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
        bootPhase, bootSeconds, retryBoot: () => setBootAttempt((n) => n + 1),
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
