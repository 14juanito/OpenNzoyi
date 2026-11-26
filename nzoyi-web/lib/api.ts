// Client minimal pour le backend nzoyi-api.
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Task = {
  id: string;
  name: string;
  target: string;
  scope: { cidrs: string[]; domains: string[] };
  profile: "quiet" | "balanced" | "aggressive";
  status: "pending" | "running" | "paused" | "done" | "failed" | "killed";
  budget_tokens?: number | null;
  budget_turns?: number | null;
  created_at: string;
};

export type Finding = {
  id: string;
  title: string;
  severity: "info" | "low" | "medium" | "high" | "critical";
  matched_at?: string | null;
  tool?: string | null;
  status: string;
};

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export const api = {
  listTasks: () => fetch(`${API_URL}/api/tasks`).then(j<Task[]>),
  getTask: (id: string) => fetch(`${API_URL}/api/tasks/${id}`).then(j<Task>),
  createTask: (body: Partial<Task>) =>
    fetch(`${API_URL}/api/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<Task>),
  deleteTask: (id: string) =>
    fetch(`${API_URL}/api/tasks/${id}`, { method: "DELETE" }).then(j),
  findings: (id: string) =>
    fetch(`${API_URL}/api/tasks/${id}/findings`).then(j<Finding[]>),
  streamUrl: (id: string) => `${API_URL}/api/tasks/${id}/stream`,
};
