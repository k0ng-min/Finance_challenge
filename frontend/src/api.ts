const API_BASE = "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export interface ClauseOut {
  clause_id: number;
  article_no: string;
  text: string;
  page_ref: string | null;
  default_color: string;
  highlight_color: string;
}

export interface FindingOut {
  finding_id: number;
  finding_type: string;
  status: string;
  target_ref: string | null;
  insurer_code: string | null;
  insurer_name: string | null;
  description: string;
  confidence: string | null;
  clauses: ClauseOut[];
}

export interface RecommendationOut {
  analysis_run_id: number;
  trip_id: number;
  risk_profile: Record<string, unknown>;
  findings: FindingOut[];
}

export interface UserOut {
  user_id: number;
  nickname: string;
}

export interface UserCoverageOut {
  user_coverage_id: number;
  raw_name: string;
  subscribed_amount: string | null;
  matched_std_code: string | null;
  matched_std_name: string | null;
  match_confidence: number;
}

export interface UserPolicyOut {
  user_policy_id: number;
  insurer_name_raw: string;
  product_name_raw: string | null;
  policy_type: string;
  period_start: string;
  period_end: string;
  matched_insurer_name: string | null;
  matched_product_name: string | null;
  coverages: UserCoverageOut[];
}

export interface PendingQuestionOut {
  question_id: number;
  question_text: string;
  target_field: string;
  impact_weight: number;
}

export interface ValidationResultOut {
  rule_code: string;
  rule_name: string;
  severity: string;
  passed: boolean;
  detail: string;
}

export interface IncidentAnalysisOut {
  incident_id: number;
  analysis_run_id: number;
  structured: Record<string, { value: unknown; confidence: number; source_span: string | null }>;
  findings: FindingOut[];
  pending_questions: PendingQuestionOut[];
  validation_results: ValidationResultOut[];
}

export interface ChecklistItemOut {
  required_doc_std_id: number;
  doc_code: string;
  doc_name: string;
  acquire_location: string;
  is_mandatory: boolean;
  coverage_target_ref: string;
  insurer_name: string;
  status: string;
  memo: string | null;
  clause: ClauseOut | null;
}

export interface ChecklistOut {
  incident_id: number;
  items: ChecklistItemOut[];
  validation_results: ValidationResultOut[];
}

export const api = {
  createUser: (nickname: string) =>
    request<UserOut>("/users", { method: "POST", body: JSON.stringify({ nickname }) }),

  createTrip: (payload: object) =>
    request<RecommendationOut>("/trips", { method: "POST", body: JSON.stringify(payload) }),

  getTrip: (tripId: number) => request<RecommendationOut>(`/trips/${tripId}`),

  listPolicies: (userId: number) => request<UserPolicyOut[]>(`/users/${userId}/policies`),

  registerPolicy: (userId: number, payload: object) =>
    request<UserPolicyOut>(`/users/${userId}/policies`, { method: "POST", body: JSON.stringify(payload) }),

  createIncident: (payload: object) =>
    request<IncidentAnalysisOut>("/incidents", { method: "POST", body: JSON.stringify(payload) }),

  getIncident: (incidentId: number) => request<IncidentAnalysisOut>(`/incidents/${incidentId}`),

  answerQuestion: (incidentId: number, questionId: number, answerText: string) =>
    request<IncidentAnalysisOut>(`/incidents/${incidentId}/answers`, {
      method: "POST",
      body: JSON.stringify({ question_id: questionId, answer_text: answerText }),
    }),

  getChecklist: (incidentId: number) => request<ChecklistOut>(`/incidents/${incidentId}/checklist`),

  submitEvidence: (incidentId: number, items: { required_doc_std_id: number; status: string; memo?: string }[]) =>
    request<ChecklistOut>(`/incidents/${incidentId}/evidence`, {
      method: "POST",
      body: JSON.stringify(items),
    }),
};
