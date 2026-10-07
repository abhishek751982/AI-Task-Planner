const API_BASE = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export type Health = {
  ok: boolean;
  onboarded: boolean;
  google_calendar: boolean;
  google_oauth_configured: boolean;
  llm_configured: boolean;
  todoist_configured: boolean;
};

export type Progress = {
  main_goal: string;
  total_tasks: number;
  completed: number;
  pending: number;
  progress_pct: number;
  leetcode: { total: number; by_difficulty: Record<string, number> };
};

export type ProfileResponse = {
  profile: Record<string, unknown>;
  memories: { kind: string; content: string }[];
};

export type BriefResponse = {
  date: string;
  brief?: string;
  plan?: string;
  free_slots?: string[];
  report?: string;
};

export const api = {
  health: () => request<Health>("/health"),
  onboardStatus: () => request<{ onboarded: boolean }>("/onboard/status"),
  onboard: (body: Record<string, unknown>) =>
    request("/onboard", { method: "POST", body: JSON.stringify(body) }),
  profile: () => request<ProfileResponse>("/profile"),
  patchProfile: (body: Record<string, unknown>) =>
    request("/profile", { method: "PATCH", body: JSON.stringify(body) }),
  progress: () => request<Progress>("/progress"),
  tasks: (status?: string) =>
    request<{ tasks: Record<string, unknown>[] }>(`/tasks${status ? `?status=${status}` : ""}`),
  dailyPlan: () => request<BriefResponse>("/plan/daily", { method: "POST" }),
  morningBrief: () => request<BriefResponse>("/brief/morning"),
  weeklyReview: () => request<BriefResponse>("/review/weekly"),
  calendarStatus: () => request<{ connected: boolean }>("/calendar/status"),
  calendarSlots: () => request<{ slots: { start: string; end: string }[] }>("/calendar/slots"),
  googleAuthUrl: () => request<{ url: string }>("/auth/google"),
  leetcodeStats: () => request<Progress["leetcode"]>("/leetcode/stats"),
  logLeetcode: (body: { problem_slug: string; title: string; difficulty?: string }) =>
    request<{ stats: Progress["leetcode"] }>("/leetcode/log", { method: "POST", body: JSON.stringify(body) }),
  syncTodoist: () => request("/sync/todoist", { method: "POST" }),
};
