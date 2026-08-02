import { useEffect, useState } from "react";
import { api, type ChecklistOut } from "../api";
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
      setError(String(err));
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
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

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
                    <td>
                      <PickerField
                        value={it.status}
                        disabled={saving}
                        onChange={(status) => updateStatus(it.required_doc_std_id, status)}
                        modalTitle="서류 상태"
                        options={STATUS_OPTIONS.map((s) => ({ value: s, label: s }))}
                      />
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
