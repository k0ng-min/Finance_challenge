import { useEffect, useState } from "react";
import { api, type ChecklistOut } from "../api";
import { useApp } from "../context/AppContext";
import { TopBar } from "../components/TopBar";
import { PageHero } from "../components/PageHero";
import { Icon3D } from "../components/Icon3D";
import { NextStepCard } from "../components/NextStepCard";

const STATUS_OPTIONS = ["미확인", "보유", "미보유", "발급불가"];

export function DocumentCheck() {
  const { incidentId } = useApp();
  const [checklist, setChecklist] = useState<ChecklistOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTarget, setActiveTarget] = useState<string | null>(null);

  async function load() {
    if (!incidentId) return;
    setLoading(true);
    try {
      const res = await api.getChecklist(incidentId);
      setChecklist(res);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [incidentId]);

  async function updateStatus(docId: number, status: string) {
    if (!incidentId) return;
    setLoading(true);
    try {
      const res = await api.submitEvidence(incidentId, [{ required_doc_std_id: docId, status }]);
      setChecklist(res);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  if (!incidentId) {
    return (
      <div className="page">
        <TopBar title="서류 체크" />
        <div className="empty-state">
          <Icon3D src="file-text" size={72} bg="var(--mint-soft)" rounded="34%" />
          <p className="muted">먼저 "사고가 발생했어요" 메뉴에서 사고를 등록해주세요.</p>
        </div>
      </div>
    );
  }

  const grouped = new Map<string, ChecklistOut["items"]>();
  checklist?.items.forEach((it) => {
    const key = it.coverage_target_ref;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(it);
  });
  const targets = [...grouped.keys()];
  const current = activeTarget ?? targets[0];
  const items = current ? grouped.get(current) ?? [] : [];

  return (
    <div className="page">
      <TopBar title="서류 체크" />
      <PageHero
        icon="file-text"
        iconBg="var(--mint-soft)"
        eyebrow="DOCUMENT CHECK"
        title={"필요한 서류,\n빠짐없이 챙기세요"}
        subtitle="현지에서만 발급 가능한 서류는 귀국 전에 꼭 챙기세요."
      />
      {error && <div className="error-box">{error}</div>}
      {loading && !checklist && <p className="muted">불러오는 중...</p>}

      {checklist?.validation_results.map((v) => (
        <div className={`card alert alert--${v.passed ? "ok" : "warn"}`} key={v.rule_code}>
          <strong>{v.rule_name}</strong>
          <p>{v.detail}</p>
        </div>
      ))}

      {targets.length > 0 && (
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
                {items.map((it) => (
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
                      <select value={it.status} onChange={(e) => updateStatus(it.required_doc_std_id, e.target.value)}>
                        {STATUS_OPTIONS.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <NextStepCard
        to="/mistakes"
        icon="shield"
        iconBg="var(--orange-soft)"
        label="다음 단계"
        title="실수 방지 점검하러 가기"
      />
    </div>
  );
}
