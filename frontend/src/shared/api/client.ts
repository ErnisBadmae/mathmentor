export type Subject = 'math_profile' | 'informatics';
export type ErrorCategory = 'arithmetic' | 'sign_transfer' | 'odz_logic' | 'condition_reading' | 'probability_double_count' | 'unknown_method' | 'algorithm_logic' | 'code_syntax' | 'code_algorithm' | 'time_management' | 'none' | 'other';

export type Track = {
  subject: Subject;
  current_score: number;
  target_score: number;
  score_gap: number;
  phase: string;
};

export type Dashboard = {
  tracks: Track[];
  clean_sheet_ratio: number;
  top_errors: Array<{ category: ErrorCategory; count: number }>;
  due_reviews: number;
};

export type Mission = {
  id: string;
  subject: Subject;
  title: string;
  instructions: string;
  threshold_percent: number;
  due_date: string | null;
  timebox_minutes: number | null;
};

export type SubmitAttemptPayload = {
  mission_id: string;
  kind: 'text' | 'code' | 'photo' | 'mixed';
  mode: 'clean_sheet' | 'with_hint' | 'unknown';
  answer_text?: string;
  code_text?: string;
  time_spent_minutes?: number;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8001/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${await response.text()}`);
  }
  return response.json() as Promise<T>;
}

export function getDashboard(studentId: string): Promise<Dashboard> {
  return request<Dashboard>(`/students/${studentId}/dashboard`);
}

export function getTodayMissions(studentId: string): Promise<Mission[]> {
  return request<Mission[]>(`/students/${studentId}/missions/today`);
}

export function submitAttempt(payload: SubmitAttemptPayload) {
  return request('/attempts', { method: 'POST', body: JSON.stringify(payload) });
}
