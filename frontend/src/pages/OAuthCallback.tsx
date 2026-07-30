import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { LoadingState } from "../components/LoadingState";
import { ErrorState } from "../components/ErrorState";
import { useApp } from "../context/AppContext";

/** 카카오/구글이 인가 코드를 들고 돌려보내는 콜백 페이지. 코드를 백엔드로 넘겨 로그인을 마무리한다. */
export function OAuthCallback({ provider }: { provider: "kakao" | "google" }) {
  const [searchParams] = useSearchParams();
  const { loginWithKakao, loginWithGoogle } = useApp();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return; // StrictMode 이중 마운트에도 인가 코드를 두 번 쓰지 않도록
    ran.current = true;

    const code = searchParams.get("code");
    const providerError = searchParams.get("error");
    if (providerError) {
      setError("로그인이 취소되었습니다.");
      return;
    }
    if (!code) {
      setError("인가 코드를 받지 못했습니다.");
      return;
    }

    // 리다이렉트 전(Account.tsx)에 sessionStorage에 남겨둔 의도(로그인/회원가입)를 읽는다.
    // "로그인" 버튼으로 들어왔는데 계정이 없으면 백엔드가 자동 가입 대신 거부하게 하기 위함.
    const intent = (sessionStorage.getItem("oauth_intent") as "login" | "signup" | null) ?? "login";
    sessionStorage.removeItem("oauth_intent");

    const login = provider === "kakao" ? loginWithKakao : loginWithGoogle;
    login(code, intent)
      .then((isNewUser) => navigate(isNewUser ? "/account/nickname" : "/"))
      .catch((err) => {
        const raw = String(err).replace(/^Error:\s*API \d+:\s*/, "");
        try {
          setError(JSON.parse(raw).detail ?? raw);
        } catch {
          setError(raw);
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <ErrorState
        code="error"
        title="로그인에 실패했어요"
        message={error}
        actionLabel="계정 화면으로 돌아가기"
        onAction={() => navigate("/account")}
      />
    );
  }

  return <LoadingState label={`${provider === "kakao" ? "카카오" : "구글"} 로그인 처리 중이에요...`} />;
}
