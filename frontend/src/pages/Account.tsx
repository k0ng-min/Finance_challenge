import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { Icon3D } from "../components/Icon3D";
import { Modal } from "../components/Modal";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { PickerField } from "../components/PickerField";
import { DateTimeField } from "../components/DateTimeField";
import { COUNTRIES } from "../data/countries";
import { useApp } from "../context/AppContext";
import { shortInsurerName } from "../data/insurers";
import {
  api,
  type ProviderStatusOut,
  type TripSummaryOut,
  type IncidentSummaryOut,
  type UserPolicyOut,
} from "../api";

function kakaoAuthorizeUrl(clientId: string, redirectUri: string) {
  const params = new URLSearchParams({ client_id: clientId, redirect_uri: redirectUri, response_type: "code" });
  return `https://kauth.kakao.com/oauth/authorize?${params.toString()}`;
}

function googleAuthorizeUrl(clientId: string, redirectUri: string) {
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: "code",
    scope: "openid email profile",
  });
  return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
}

export function Account() {
  const { isLoggedIn, userId, nickname, email, logout, deleteAccount } = useApp();
  const navigate = useNavigate();
  const [providers, setProviders] = useState<ProviderStatusOut | null>(null);
  const [trips, setTrips] = useState<TripSummaryOut[]>([]);
  const [incidents, setIncidents] = useState<IncidentSummaryOut[]>([]);
  const [policies, setPolicies] = useState<UserPolicyOut[]>([]);
  const [tripModal, setTripModal] = useState<TripSummaryOut | null>(null);
  // 사고 접수 중에 급히 만든 여행처럼, 나중에 목적지·기간을 고칠 수 있게 한다.
  const [editingTrip, setEditingTrip] = useState(false);
  const [editDestination, setEditDestination] = useState("");
  const [editStart, setEditStart] = useState("");
  const [editEnd, setEditEnd] = useState("");
  const [savingTrip, setSavingTrip] = useState(false);
  const [incidentModal, setIncidentModal] = useState<IncidentSummaryOut | null>(null);
  const [confirmDeleteTrip, setConfirmDeleteTrip] = useState<number | null>(null);
  const [confirmDeleteIncident, setConfirmDeleteIncident] = useState<number | null>(null);
  const [confirmWithdraw, setConfirmWithdraw] = useState(false);
  const [withdrawing, setWithdrawing] = useState(false);

  async function handleWithdraw() {
    setWithdrawing(true);
    try {
      await deleteAccount();
      navigate("/");
    } finally {
      setWithdrawing(false);
      setConfirmWithdraw(false);
    }
  }

  // 로그인이 기본(주), 회원가입은 그 밑에 작은 링크로 — 카카오·구글만 지원한다(이메일
  // 비밀번호 계정은 서버에 비밀번호를 아예 저장하지 않는 편이 유출 위험이 적어서 만들지
  // 않기로 했다). "로그인" 의도로 눌렀는데 가입 이력이 없는 계정이면, 조용히 회원가입
  // 되는 대신 백엔드가 거부하도록 intent를 리다이렉트 전에 sessionStorage에 남겨둔다.
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");

  function startOAuth(url: string) {
    sessionStorage.setItem("oauth_intent", authMode);
    window.location.href = url;
  }

  useEffect(() => {
    api.getAuthProviders().then(setProviders).catch(() => {});
  }, []);

  function refreshHistory() {
    if (!userId) return;
    api.listTrips(userId).then(setTrips).catch(() => {});
    api.listIncidents(userId).then(setIncidents).catch(() => {});
    api.listPolicies(userId).then(setPolicies).catch(() => {});
  }

  useEffect(() => {
    if (isLoggedIn && userId) refreshHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn, userId]);

  async function handleDeleteTrip(tripId: number) {
    await api.deleteTrip(tripId);
    setTripModal(null);
    setConfirmDeleteTrip(null);
    refreshHistory();
  }

  async function handleDeleteIncident(incidentId: number) {
    await api.deleteIncident(incidentId);
    setIncidentModal(null);
    setConfirmDeleteIncident(null);
    refreshHistory();
  }

  const linkedPolicy = incidentModal
    ? policies.find((p) => p.user_policy_id === incidentModal.user_policy_id)
    : undefined;

  if (isLoggedIn) {
    return (
      <div className="page">
        <TopBar title="내 계정" />
        <PageHero
          icon="shield"
          eyebrow="ACCOUNT"
          title={`${nickname}님,\n환영합니다`}
          subtitle="여행·보험 정보가 이 계정에 안전하게 저장돼요."
        />
        <div className="card">
          <div className="muted">계정</div>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>{email ?? "소셜 계정으로 로그인됨"}</div>
        </div>

        <p className="section-label" style={{ margin: "20px 2px 10px" }}>내 여행 기록</p>
        {trips.length === 0 && <p className="muted" style={{ fontSize: "0.85rem" }}>아직 만든 여행 프로필이 없어요.</p>}
        <div className="rank-list">
          {trips.map((t) => (
            <div className="history-card" key={t.trip_id}>
              <button type="button" className="history-card__main" onClick={() => setTripModal(t)}>
                <Icon3D src="suitcase" size={36} />
                <div className="history-card__text">
                  <strong>{t.destination}</strong>
                  <div className="history-card__tags">
                    <span className="history-tag">{t.start_date} ~ {t.end_date}</span>
                    {t.risk_level && <span className="history-tag">위험도 {t.risk_level}</span>}
                  </div>
                </div>
              </button>
              <button
                type="button"
                className="history-card__delete"
                title="삭제"
                onClick={() => setConfirmDeleteTrip(t.trip_id)}
              >
                🗑
              </button>
            </div>
          ))}
        </div>

        <p className="section-label" style={{ margin: "20px 2px 10px" }}>내 사고 접수 이력</p>
        {incidents.length === 0 && <p className="muted" style={{ fontSize: "0.85rem" }}>아직 접수한 사고가 없어요.</p>}
        <div className="rank-list">
          {incidents.map((i) => (
            <div className="history-card" key={i.incident_id}>
              <button type="button" className="history-card__main" onClick={() => setIncidentModal(i)}>
                <Icon3D src="chat-bubble" size={36} />
                <div className="history-card__text">
                  <strong>{i.diagnosis ?? i.cause ?? "사고 접수 내역"}</strong>
                  <div className="history-card__tags">
                    {i.country && <span className="history-tag">{i.country}</span>}
                    {i.occurred_at && <span className="history-tag">{i.occurred_at.slice(0, 10)}</span>}
                    {i.linked_insurer_name && (
                      <span className="history-tag">{shortInsurerName(i.linked_insurer_code, i.linked_insurer_name)}</span>
                    )}
                  </div>
                </div>
              </button>
              <button
                type="button"
                className="history-card__delete"
                title="삭제"
                onClick={() => setConfirmDeleteIncident(i.incident_id)}
              >
                🗑
              </button>
            </div>
          ))}
        </div>

        <Modal open={!!tripModal} onClose={() => { setTripModal(null); setEditingTrip(false); }} title="여행 기록">
          {tripModal && (
            <>
              <p style={{ marginTop: 0 }}>
                <strong>{tripModal.destination}</strong>으로의 여행 · {tripModal.start_date} ~ {tripModal.end_date}
              </p>
              <p className="muted" style={{ fontSize: "0.82rem", marginBottom: 12 }}>등록된 보험</p>
              {policies.length === 0 && <p className="muted" style={{ fontSize: "0.85rem" }}>등록된 보험이 없어요.</p>}
              {policies.map((p) => (
                <div className="modal-policy" key={p.user_policy_id}>
                  <strong>{shortInsurerName(p.matched_insurer_code, p.matched_insurer_name ?? p.insurer_name_raw)} 여행자보험</strong>
                  {p.coverages.map((c) => (
                    <div className="modal-policy__row" key={c.user_coverage_id}>
                      <span>{c.matched_std_name ?? c.raw_name}</span>
                      <span>{c.subscribed_amount ?? "-"}</span>
                    </div>
                  ))}
                </div>
              ))}
              {editingTrip ? (
                <>
                  <label>
                    목적지 국가
                    <PickerField
                      value={editDestination}
                      onChange={setEditDestination}
                      placeholder="국가를 선택하세요"
                      modalTitle="목적지 국가"
                      options={COUNTRIES.map((c) => ({ value: c, label: c }))}
                    />
                  </label>
                  <DateTimeField label="여행 시작일" value={editStart} onChange={setEditStart} />
                  <DateTimeField label="여행 종료일" value={editEnd} onChange={setEditEnd} />
                  <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ flex: 1 }}
                      onClick={() => setEditingTrip(false)}
                    >
                      취소
                    </button>
                    <button
                      type="button"
                      className="btn-primary"
                      style={{ flex: 1 }}
                      disabled={savingTrip}
                      onClick={async () => {
                        setSavingTrip(true);
                        try {
                          await api.updateTrip(tripModal.trip_id, {
                            destination: editDestination || null,
                            start_date: editStart || null,
                            end_date: editEnd || null,
                          });
                          const list = await api.listTrips(userId!);
                          setTrips(list);
                          setTripModal(list.find((t) => t.trip_id === tripModal.trip_id) ?? null);
                          setEditingTrip(false);
                        } finally {
                          setSavingTrip(false);
                        }
                      }}
                    >
                      {savingTrip ? "저장 중..." : "저장"}
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    className="btn-primary"
                    style={{ width: "100%", marginTop: 6 }}
                    onClick={() => {
                      setEditDestination(tripModal.destination ?? "");
                      setEditStart(tripModal.start_date ?? "");
                      setEditEnd(tripModal.end_date ?? "");
                      setEditingTrip(true);
                    }}
                  >
                    여행 정보 수정
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    style={{ width: "100%", marginTop: 8 }}
                    onClick={() => setConfirmDeleteTrip(tripModal.trip_id)}
                  >
                    이 여행 기록 삭제
                  </button>
                </>
              )}
            </>
          )}
        </Modal>

        <Modal open={!!incidentModal} onClose={() => setIncidentModal(null)} title="사고 접수 이력">
          {incidentModal && (
            <>
              <p style={{ marginTop: 0 }}>
                <strong>{incidentModal.diagnosis ?? incidentModal.cause ?? "사고 접수 내역"}</strong>
              </p>
              {incidentModal.country && <p className="modal-policy__row"><span>발생 국가</span><span>{incidentModal.country}</span></p>}
              {incidentModal.occurred_at && (
                <p className="modal-policy__row"><span>사고 일시</span><span>{incidentModal.occurred_at.slice(0, 10)}</span></p>
              )}
              <p className="muted" style={{ fontSize: "0.82rem", margin: "12px 0 8px" }}>연계된 보험</p>
              {linkedPolicy ? (
                <div className="modal-policy">
                  <strong>{shortInsurerName(linkedPolicy.matched_insurer_code, linkedPolicy.matched_insurer_name ?? linkedPolicy.insurer_name_raw)} 여행자보험</strong>
                  {linkedPolicy.coverages.map((c) => (
                    <div className="modal-policy__row" key={c.user_coverage_id}>
                      <span>{c.matched_std_name ?? c.raw_name}</span>
                      <span>{c.subscribed_amount ?? "-"}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted" style={{ fontSize: "0.85rem" }}>연계된 보험이 없어요.</p>
              )}
              <button
                type="button"
                className="btn-secondary"
                style={{ width: "100%", marginTop: 6 }}
                onClick={() => navigate(`/incident?resultOf=${incidentModal.incident_id}`)}
              >
                청구 검토 결과 자세히 보기
              </button>
              <button
                type="button"
                className="btn-secondary"
                style={{ width: "100%", marginTop: 8 }}
                onClick={() => setConfirmDeleteIncident(incidentModal.incident_id)}
              >
                이 사고 이력 삭제
              </button>
            </>
          )}
        </Modal>

        <ConfirmDialog
          open={confirmDeleteTrip !== null}
          title="여행 기록 삭제"
          message="이 여행 기록을 삭제할까요? 되돌릴 수 없어요."
          onConfirm={() => confirmDeleteTrip !== null && handleDeleteTrip(confirmDeleteTrip)}
          onCancel={() => setConfirmDeleteTrip(null)}
        />
        <ConfirmDialog
          open={confirmDeleteIncident !== null}
          title="사고 접수 이력 삭제"
          message="이 사고 접수 이력을 삭제할까요? 되돌릴 수 없어요."
          onConfirm={() => confirmDeleteIncident !== null && handleDeleteIncident(confirmDeleteIncident)}
          onCancel={() => setConfirmDeleteIncident(null)}
        />
        <ConfirmDialog
          open={confirmWithdraw}
          title="회원 탈퇴"
          message="정말 탈퇴하시겠어요? 이 계정과 저장된 모든 여행·사고·보험 기록이 되돌릴 수 없이 삭제돼요."
          confirmLabel={withdrawing ? "탈퇴 처리 중..." : "탈퇴하기"}
          onConfirm={handleWithdraw}
          onCancel={() => setConfirmWithdraw(false)}
        />

        <button
          type="button"
          className="btn-secondary"
          style={{ width: "100%", marginTop: 20 }}
          onClick={async () => {
            await logout();
            navigate("/");
          }}
        >
          로그아웃
        </button>
        <button
          type="button"
          className="account-withdraw-link"
          onClick={() => setConfirmWithdraw(true)}
        >
          회원 탈퇴
        </button>
      </div>
    );
  }

  const kakaoReady = providers?.kakao_enabled;
  const googleReady = providers?.google_enabled;

  return (
    <div className="page account-auth">
      <TopBar title="로그인" />
      <PageHero
        icon="lock"
        eyebrow="ACCOUNT"
        title={"로그인하면\n자동으로 저장돼요"}
        subtitle="지금까지 입력한 여행·보험 정보는 그대로 이어져요. 카카오·구글 계정 하나면 다른 기기에서도 이어서 쓸 수 있어요."
      />

      <div className="card">
        <p className="muted" style={{ fontSize: "0.85rem", marginTop: 0, marginBottom: 14 }}>
          {authMode === "login"
            ? "카카오 또는 구글 계정으로 로그인하세요."
            : "처음이신가요? 카카오 또는 구글 계정으로 바로 시작할 수 있어요. 비밀번호를 따로 만들 필요가 없어요."}
        </p>
        <div className="social-login-row">
          <button
            type="button"
            className="social-btn social-btn--kakao"
            disabled={!kakaoReady}
            title={kakaoReady ? undefined : "카카오 개발자 앱 키 연동 후 이용할 수 있어요"}
            onClick={() => {
              if (providers) startOAuth(kakaoAuthorizeUrl(providers.kakao_client_id, providers.kakao_redirect_uri));
            }}
          >
            <Icon3D src="chat-bubble" size={24} />
            {authMode === "login" ? "카카오로 로그인" : "카카오로 가입하기"}
          </button>
          <button
            type="button"
            className="social-btn"
            disabled={!googleReady}
            title={googleReady ? undefined : "구글 OAuth 연동 후 이용할 수 있어요"}
            onClick={() => {
              if (providers) startOAuth(googleAuthorizeUrl(providers.google_client_id, providers.google_redirect_uri));
            }}
          >
            <Icon3D src="star" size={24} />
            {authMode === "login" ? "구글로 로그인" : "구글로 가입하기"}
          </button>
        </div>
        {!(kakaoReady && googleReady) && (
          <p className="muted" style={{ fontSize: "0.78rem", textAlign: "center", marginTop: 14, lineHeight: 1.6 }}>
            {kakaoReady || googleReady
              ? "나머지 로그인 연동을 준비 중이에요."
              : "카카오·구글 로그인 연동을 준비 중이에요."}
          </p>
        )}

        <button
          type="button"
          className="account-auth__switch"
          onClick={() => setAuthMode(authMode === "login" ? "signup" : "login")}
        >
          {authMode === "login" ? "계정이 없으신가요? 회원가입" : "이미 계정이 있으신가요? 로그인"}
        </button>
      </div>

      <div className="account-auth__footer">
        {authMode === "signup" && (
          <p className="muted" style={{ fontSize: "0.76rem", textAlign: "center", lineHeight: 1.6 }}>
            가입 시 닉네임 설정과 함께 이용약관·개인정보 수집 동의를 한 번 받아요.
          </p>
        )}
        <p className="muted" style={{ fontSize: "0.78rem", textAlign: "center", marginTop: 8, lineHeight: 1.6 }}>
          로그인 없이도 게스트로 모든 기능을 그대로 이용할 수 있어요.
        </p>
      </div>
    </div>
  );
}
