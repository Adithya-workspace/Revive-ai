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