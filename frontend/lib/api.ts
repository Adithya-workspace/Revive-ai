import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export const apiClient = axios.create({
  baseURL: API_URL,
});

// --- Types matching the backend's actual response shapes ---

export interface Merchant {
  id: string;
  name: string;
  email: string;
}

export interface CaseSummary {
  id: string;
  customer_name: string;
  scenario: string;
  amount_at_risk: number;
  recovery_probability: number | null;
  priority: string;
  status: string;
  recommended_action: string | null;
  diagnosis: string | null;
  policy_decision: string | null;
  created_at: string | null;
}

export interface CasesListResponse {
  total_count: number;
  returned_count: number;
  offset: number;
  limit: number;
  cases: CaseSummary[];
}

export interface AnalyticsOverview {
  total_revenue_at_risk: number;
  potentially_recoverable_revenue: number;
  recovered_revenue: number;
  recovery_rate: number;
  total_cases: number;
  recovered_cases: number;
  open_cases: number;
}

export interface ScenarioBreakdown {
  scenario: string;
  total_at_risk: number;
  recovered: number;
  recovery_rate: number;
  case_count: number;
  recovered_count: number;
}

export interface AnalyticsResponse {
  overview: AnalyticsOverview;
  by_scenario: ScenarioBreakdown[];
  policy_decisions: Record<string, number>;
  action_breakdown: Record<string, number>;
  verification_breakdown: Record<string, number>;
}

// --- API functions ---

export async function fetchMerchants(): Promise<Merchant[]> {
  const res = await apiClient.get("/merchants");
  return res.data;
}

export async function fetchAnalytics(merchantId: string): Promise<AnalyticsResponse> {
  const res = await apiClient.get(`/analytics/${merchantId}`);
  return res.data;
}

export async function fetchCases(
  merchantId: string,
  filters?: { status?: string; scenario?: string; priority?: string; limit?: number; offset?: number }
): Promise<CasesListResponse> {
  const res = await apiClient.get(`/cases/${merchantId}`, { params: filters });
  return res.data;
}

export async function fetchCaseDetail(merchantId: string, caseId: string) {
  const res = await apiClient.get(`/cases/${merchantId}/${caseId}`);
  return res.data;
}

export async function submitHumanDecision(
  merchantId: string,
  caseId: string,
  decision: "APPROVED" | "REJECTED",
  approverNote?: string
) {
  const res = await apiClient.post(`/cases/${merchantId}/${caseId}/human-decision`, {
    decision,
    approver_note: approverNote || null,
  });
  return res.data;
}

export interface ActionSummary {
  id: string;
  case_id: string;
  customer_name: string;
  action: string;
  expected_value: number;
  confidence: number;
  policy_decision: string | null;
  execution_status: string;
  execution_mode: string | null;
  created_at: string | null;
}

export interface EscalationSummary {
  case_id: string;
  customer_name: string;
  scenario: string;
  amount_at_risk: number;
  recommended_action: string;
  reason: string;
  policy_reason: string;
  confidence: number;
  created_at: string | null;
}

export async function fetchActions(
  merchantId: string,
  filters?: { action_type?: string; policy_decision?: string; limit?: number; offset?: number }
) {
  const res = await apiClient.get(`/actions/${merchantId}`, { params: filters });
  return res.data as { total_count: number; actions: ActionSummary[] };
}

export async function fetchEscalations(merchantId: string, limit = 50, offset = 0) {
  const res = await apiClient.get(`/escalations/${merchantId}`, { params: { limit, offset } });
  return res.data as { total_count: number; escalations: EscalationSummary[] };
}

export interface CustomerSummary {
  id: string;
  name: string;
  email: string;
  phone: string;
  case_count: number;
  total_at_risk: number;
  recovered: number;
}

export async function fetchCustomers(merchantId: string, limit = 100, offset = 0) {
  const res = await apiClient.get(`/customers/${merchantId}`, { params: { limit, offset } });
  return res.data as { total_count: number; customers: CustomerSummary[] };
}

export async function fetchCustomerDetail(merchantId: string, customerId: string) {
  const res = await apiClient.get(`/customers/${merchantId}/${customerId}`);
  return res.data;
}

export interface Policy {
  key: string;
  value: string;
  description: string;
  version: number;
  updated_at: string | null;
}

export async function fetchPolicies() {
  const res = await apiClient.get("/policies");
  return res.data as Policy[];
}

export interface AuditEventItem {
  id: string;
  case_id: string;
  event_type: string;
  actor: string;
  result: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
}

export async function fetchAuditEvents(
  merchantId: string,
  filters?: { event_type?: string; limit?: number; offset?: number }
) {
  const res = await apiClient.get(`/audit-events/${merchantId}`, { params: filters });
  return res.data as { total_count: number; events: AuditEventItem[] };
}

export async function createDemoCase(merchantId: string) {
  const res = await apiClient.post(`/demo/create-case/${merchantId}`);
  return res.data;
}

export async function runDetectionScan(merchantId: string) {
  const res = await apiClient.post(`/detection/run-scan/${merchantId}`);
  return res.data;
}

export async function runScoring(merchantId: string) {
  const res = await apiClient.post(`/scoring/run/${merchantId}`);
  return res.data;
}

export async function runDiagnosis(merchantId: string, maxLlmCalls = 5) {
  const res = await apiClient.post(`/diagnosis/run/${merchantId}`, null, {
    params: { max_llm_calls: maxLlmCalls },
  });
  return res.data;
}

export async function runStrategy(merchantId: string) {
  const res = await apiClient.post(`/strategy/run/${merchantId}`);
  return res.data;
}

export async function runPolicyEngine(merchantId: string) {
  const res = await apiClient.post(`/policy/run/${merchantId}`);
  return res.data;
}

export async function runActionExecutor(merchantId: string) {
  const res = await apiClient.post(`/actions/run/${merchantId}`);
  return res.data;
}

export async function runVerification(merchantId: string) {
  const res = await apiClient.post(`/verification/run/${merchantId}`);
  return res.data;
}

export async function simulateApiFailure(merchantId: string) {
  const res = await apiClient.post(`/actions/simulate-api-failure/${merchantId}`, {});
  return res.data;
}

export async function runLiveEvaluation(merchantId: string) {
  const res = await apiClient.post(`/demo/run-evaluation/${merchantId}`);
  return res.data;
}

export async function resetDemoData(merchantId: string) {
  const res = await apiClient.post(`/demo/reset/${merchantId}`);
  return res.data;
}