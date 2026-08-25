import { useEffect, useState } from "react";
import { api, ApiError, type ChecklistOut, userMessage } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { Icon3D } from "../components/Icon3D";
import { NextStepCard } from "../components/NextStepCard";
import { ErrorState } from "../components/ErrorState";
import { IncidentPicker } from "../components/IncidentPicker";
import { LoadingScreen } from "../components/LoadingScreen";
import { PickerField } from "../components/PickerField";
import { TripContextBadge } from "../components/TripContextBadge";
import { usePager, PagerNav } from "../components/Pager";
import { DocPhotoCheck } from "../components/DocPhotoCheck";

const STATUS_OPTIONS = ["미확인", "보유", "미보유", "발급불가"];

export function DocumentCheck({ embedded = false }: { embedded?: boolean } = {}) {
  const { userId, incidentId } = useApp();
  const [activeIncidentId, setActiveIncidentId] = useState<number | null>(incidentId);
  const [checklist, setChecklist] = useState<ChecklistOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTarget, setActiveTarget] = useState<string | null>(null);

  useEffect(() => {
    setActiveIncidentId(incidentId);
  }, [incidentId]);

  async function load() {
    if (!activeIncidentId) return;
    setLoading(true);
    try {
      const res = await api.getChecklist(activeIncidentId);
      setChecklist(res);
      setActiveTarget(null);
    } catch (err) {
      // 브라우저에 남아 있던 사고 id가 서버에서 사라진 경우(게스트 기록 정리 등)는
      // 오류가 아니라 "아직 접수한 사고가 없는 상태"다. 안내 화면으로 되돌린다.
      if (err instanceof ApiError && err.status === 404) {
        setActiveIncidentId(null);
        setChecklist(null);
        setError(null);
      } else {
        setError(userMessage(err));
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeIncidentId]);

  async function updateStatus(docId: number, status: string) {
    if (!activeIncidentId) return;
    setSaving(true);
    try {
      const res = await api.submitEvidence(activeIncidentId, [{ required_doc_std_id: docId, status }]);
      setChecklist(res);
    } catch (err) {
      setError(userMessage(err));
    } finally {
      setSaving(false);
    }
  }

  // activeIncidentId가 없으면 아래에서 안내 화면으로 일찍 반환하는데, 그 반환 이전에
  // 훅을 전부 호출해 둬야 한다 — usePager를 반환 뒤(조건부)에 두면 사고를 고르는 순간
  // 훅 개수가 늘어나 React가 "Rendered more hooks than during the previous render"로
  // 터진다(2026-08-19 oxlint가 잡은 버그, PolicyCard가 쓰는 정답 패턴을 따랐다).
  const grouped = new Map<string, ChecklistOut["items"]>();
  (checklist?.items ?? []).forEach((it) => {
    const key = it.coverage_target_ref;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(it);
  });
  const targets = [...grouped.keys()];
  const current = activeTarget ?? targets[0];
  const items = current ? grouped.get(current) ?? [] : [];
  const { page, setPage, totalPages, pageItems } = usePager(items, 4);

  if (!activeIncidentId) {
    return (
      <div className={embedded ? "" : "page"}>
        {!embedded && <TopBar title="서류 체크" />}
        <div className="empty-state">
          <Icon3D src="file-text" size={72} />
          <p className="muted">먼저 "사고가 발생했어요" 메뉴에서 사고를 등록해주세요.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={embedded ? "" : "page"}>
      {!embedded && <TopBar title="서류 체크" />}
      {!embedded && <PageHero
        icon="file-text"
        eyebrow="DOCUMENT CHECK"
        title={"필요한 서류,\n빠짐없이 챙기세요"}
        subtitle="현지에서만 발급 가능한 서류는 귀국 전에 꼭 챙기세요."
      />}
      <IncidentPicker userId={userId} value={activeIncidentId} onChange={setActiveIncidentId} />
      {checklist && (
        <TripContextBadge
          tripDestination={checklist.trip_destination}
          tripStartDate={checklist.trip_start_date}
          tripEndDate={checklist.trip_end_date}
          incidentCountry={checklist.incident_country}
        />
      )}
      {error && !checklist && (
        <ErrorState code="502" title="서류 목록을 불러오지 못했어요" message={error} actionLabel="다시 시도" onAction={load} />
      )}
      {error && checklist && <div className="error-box">{error}</div>}
      {loading && (
        <LoadingScreen icon="file-text" title="필요 서류를 정리하고 있어요" messages={["등록된 보험 약관과 대조하고 있어요"]} />
      )}

      {!loading && checklist?.validation_results.map((v) => (
        <div className={`card alert alert--${v.passed ? "ok" : "warn"}`} key={v.rule_code}>
          <strong>{v.rule_name}</strong>
          <p>{v.detail}</p>
        </div>
      ))}

      {!loading && targets.length > 0 && (
        <>
          <div className="tabs">
            {targets.map((t) => (
              <button
                key={t}
                type="button"
                className={`tab${t === current ? " tab--active" : ""}`}
                onClick={() => setActiveTarget(t)}
              >
                {t.split(" - ")[0]}
              </button>
            ))}
          </div>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>{current}</h3>
            {/* 아이콘만 두면 뭘 하는 버튼인지 알 수 없다. 표 위에 한 줄로만 알린다 —
                행마다 설명을 붙이면 다시 시끄러워진다. */}
            <p className="doc-photo-hint">
              <span className="doc-photo-hint__icon" aria-hidden>
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor"
                     strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                  <circle cx="12" cy="13" r="4" />
                </svg>
              </span>
              외국어로 된 서류는 카메라 버튼을 눌러보세요. 번역해서 필요한 내용이 담겼는지 확인해 드려요.
            </p>
            <table className="coverage-table">
              <thead>
                <tr>
                  <th>서류</th>
                  <th>발급 위치</th>
                  <th>필수여부</th>
                  <th>상태</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.map((it) => (
                  <tr key={`${it.required_doc_std_id}-${current}`}>
                    <td>{it.doc_name}</td>
                    <td>
                      {it.acquire_location === "현지only" ? (
                        <span className="badge badge--warn">현지에서만 발급</span>
                      ) : (
                        it.acquire_location
                      )}
                    </td>
                    <td>{it.is_mandatory ? "필수" : "상황에 따라"}</td>
                    {/* 상태 선택이 주인공이고, 사진은 그 옆에 붙는 보조 수단이다. */}
                    <td>
                      <div className="doc-status-cell">
                        <PickerField
                          value={it.status}
                          disabled={saving}
                          onChange={(status) => updateStatus(it.required_doc_std_id, status)}
                          modalTitle="서류 상태"
                          options={STATUS_OPTIONS.map((s) => ({ value: s, label: s }))}
                        />
                        <DocPhotoCheck
                          incidentId={activeIncidentId}
                          docStdId={it.required_doc_std_id}
                          onChecklist={setChecklist}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <PagerNav page={page} totalPages={totalPages} onChange={setPage} label="쪽" />
          </div>
        </>
      )}

      <NextStepCard
        to="/mistakes"
        icon="shield"
        label="다음 단계"
        title="실수 방지 점검하러 가기"
      />
    </div>
  );
}
