import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHero } from "../components/PageHero";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { TermsConsent, EMPTY_CONSENT, allRequiredAgreed } from "../components/TermsConsent";
import { useApp } from "../context/AppContext";
import { api, userMessage } from "../api";

/** 카카오/구글로 처음 가입했을 때 딱 한 번, 제공자 프로필 이름 대신 원하는 닉네임을 정하고
 * (소셜 로그인 화면엔 없는) 필수 약관·개인정보 동의를 받는다.
 *
 * 이 화면은 "가입의 마지막 단계"이지 건너뛸 수 있는 안내가 아니다. 예전에는 TopBar의
 * 뒤로가기로 그냥 빠져나갈 수 있었고, 그러면 계정 행만 남고 닉네임·나이·동의가 빈
 * 상태로 굳어 다시 채울 방법이 없었다. 그래서
 *   · TopBar(뒤로가기)를 두지 않고,
 *   · 나가려면 "가입 취소"를 눌러 계정 자체를 지우게 하고(cancelPendingSignup),
 *   · 주소창으로 다른 화면에 가더라도 App이 여기로 되돌린다(signupCompleted).
 */
export function SetNickname() {
  const { nickname, updateNickname, updateAge, setPassword, applyAuthUser, cancelPendingSignup } = useApp();
  const navigate = useNavigate();
  const [value, setValue] = useState(nickname ?? "");
  const [age, setAge] = useState("");
  // 가입 마지막 단계에서 비밀번호를 반드시 만든다 — 그래야 카카오·구글 로그인이
  // 막힐 때도 이메일+비밀번호로 들어올 길이 남는다. 따로 설정하는 자리는 두지 않는다.
  const [password, setPasswordValue] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [consent, setConsent] = useState(EMPTY_CONSENT);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  async function handleCancel() {
    setCancelling(true);
    try {
      await cancelPendingSignup();
      navigate("/", { replace: true });
    } finally {
      setCancelling(false);
      setConfirmCancel(false);
    }
  }

  async function handleSubmit() {
    if (!value.trim() || !age) return;
    if (password.length < 8) {
      setError("비밀번호는 8자 이상으로 정해주세요.");
      return;
    }
    if (password !== passwordConfirm) {
      setError("비밀번호가 서로 다릅니다.");
      return;
    }
    if (!allRequiredAgreed(consent)) {
      setError("이용약관, 개인정보 수집·이용, 만 14세 이상 확인에 모두 동의해야 계속할 수 있어요.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await updateNickname(value.trim());
      await updateAge(Number(age));
      await setPassword(password, null);
      // 동의 응답에는 갱신된 계정 상태(가입 완료 표시)가 들어 있다 — 그대로 반영해야
      // App의 "가입 미완료 리다이렉트"가 풀려서 홈으로 넘어갈 수 있다.
      const me = await api.submitConsent({
        agreeTerms: consent.agreeTerms, agreePrivacy: consent.agreePrivacy, agreeMarketing: consent.agreeMarketing,
      });
      applyAuthUser(me);
      navigate("/", { replace: true });
    } catch (err) {
      setError(userMessage(err, "저장하지 못했어요. 다시 시도해 주세요."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <PageHero
        icon="tick"
        eyebrow="WELCOME"
        title={"가입을 환영해요!\n바로 시작해볼까요?"}
        subtitle="닉네임과 비밀번호만 정하면 끝나요. 이메일과 비밀번호로도 로그인할 수 있게 돼요."
      />
      <div className="form">
        <label>
          닉네임
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="예: 여행자"
            maxLength={20}
            autoFocus
          />
        </label>
        <label>
          나이
          <input
            type="number"
            min={0}
            max={120}
            value={age}
            onChange={(e) => setAge(e.target.value)}
            placeholder="예: 30"
          />
        </label>
        <label>
          비밀번호 (8자 이상)
          <input
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPasswordValue(e.target.value)}
          />
        </label>
        <label>
          비밀번호 확인
          <input
            type="password"
            autoComplete="new-password"
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
          />
        </label>
        <p className="muted" style={{ fontSize: "0.78rem", marginTop: -10 }}>
          한 번만 입력해두면 여행 준비·사고 접수·내 보험 등록에서 매번 다시 물어보지 않아요.
        </p>
        <TermsConsent value={consent} onChange={setConsent} />
        {error && <div className="error-box">{error}</div>}
        <button
          type="submit"
          onClick={handleSubmit}
          disabled={
            loading || !value.trim() || !age || password.length < 8
            || password !== passwordConfirm || !allRequiredAgreed(consent)
          }
        >
          {loading ? "저장 중..." : "시작하기"}
        </button>
        <button
          type="button"
          className="account-withdraw-link"
          onClick={() => setConfirmCancel(true)}
        >
          가입 취소하고 돌아가기
        </button>
      </div>

      <ConfirmDialog
        open={confirmCancel}
        title="가입 취소"
        message="지금 나가면 방금 만들어진 계정은 삭제돼요. 다음에 다시 가입할 수 있어요."
        confirmLabel={cancelling ? "취소하는 중..." : "가입 취소하기"}
        onConfirm={handleCancel}
        onCancel={() => setConfirmCancel(false)}
      />
    </div>
  );
}
