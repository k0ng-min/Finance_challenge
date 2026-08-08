import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { TermsConsent, EMPTY_CONSENT, allRequiredAgreed } from "../components/TermsConsent";
import { useApp } from "../context/AppContext";
import { api, userMessage } from "../api";

/** 카카오/구글로 처음 가입했을 때 딱 한 번, 제공자 프로필 이름 대신 원하는 닉네임을 정하고
 * (소셜 로그인 화면엔 없는) 필수 약관·개인정보 동의를 받는다. */
export function SetNickname() {
  const { nickname, updateNickname, updateAge } = useApp();
  const navigate = useNavigate();
  const [value, setValue] = useState(nickname ?? "");
  const [age, setAge] = useState("");
  const [consent, setConsent] = useState(EMPTY_CONSENT);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!value.trim() || !age) return;
    if (!allRequiredAgreed(consent)) {
      setError("이용약관, 개인정보 수집·이용, 만 14세 이상 확인에 모두 동의해야 계속할 수 있어요.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await updateNickname(value.trim());
      await updateAge(Number(age));
      await api.submitConsent({
        agreeTerms: consent.agreeTerms, agreePrivacy: consent.agreePrivacy, agreeMarketing: consent.agreeMarketing,
      });
      navigate("/");
    } catch (err) {
      setError(userMessage(err, "저장하지 못했어요. 다시 시도해 주세요."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <TopBar title="닉네임 설정" />
      <PageHero
        icon="tick"
        eyebrow="WELCOME"
        title={"가입을 환영해요!\n닉네임을 정해주세요"}
        subtitle="다른 사람에게는 보이지 않아요. 나중에 계정 화면에서 언제든 바꿀 수 있어요."
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
        <p className="muted" style={{ fontSize: "0.78rem", marginTop: -10 }}>
          한 번만 입력해두면 여행 준비·사고 접수·내 보험 등록에서 매번 다시 물어보지 않아요.
        </p>
        <TermsConsent value={consent} onChange={setConsent} />
        {error && <div className="error-box">{error}</div>}
        <button
          type="submit"
          onClick={handleSubmit}
          disabled={loading || !value.trim() || !age || !allRequiredAgreed(consent)}
        >
          {loading ? "저장 중..." : "시작하기"}
        </button>
      </div>
    </div>
  );
}
