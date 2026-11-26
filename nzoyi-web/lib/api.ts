// Client pour le backend nzoyi-api.
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Severity = "info" | "low" | "medium" | "high" | "critical";

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
  // enrichissements (liste)
  findings_count?: number;
  findings_by_severity?: Record<Severity, number>;
  steps?: number;
  steps_ran?: number;
};

export type AttackTechnique = { id: string; name: string };
export type Finding = {
  id: string;
  title: string;
  severity: Severity;
  matched_at?: string | null;
  tool?: string | null;
  attack?: AttackTechnique[];
  status: string;
  task_id?: string;
  task_name?: string;
};

export type FindingsAgg = {
  total: number;
  pending: number;
  by_severity: Record<Severity, number>;
  findings: Finding[];
};

export type Flow = {
  id: string;
  task_id?: string | null;
  request: { method?: string; url?: string; headers?: Record<string, string> };
  response: { status?: number; headers?: Record<string, string> };
  captured_at: string;
};

export type GraphData = {
  nodes: { id: string; type: string; content: any; status: string; agent?: string }[];
  edges: { source: string; target: string; relation: string }[];
};

export type ChatMsg = { role: "user" | "assistant"; text: string; ts: string };
export type Conversation = {
  id: string; title: string; task_id?: string | null;
  created_at: string; messages: ChatMsg[];
};

export type ApprovalRecord = {
  seq: number; task_id: string; task_name: string; tool: string; source: string;
  matched_rule: string; decision_source: string; arguments: Record<string, any>;
  status: "allowed" | "denied" | "pending";
  decided_by: string | null; requested_at: string; decided_at: string | null;
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
  taskFindings: (id: string) =>
    fetch(`${API_URL}/api/tasks/${id}/findings`).then(j<Finding[]>),
  allFindings: () => fetch(`${API_URL}/api/findings`).then(j<FindingsAgg>),
  traffic: (taskId?: string) =>
    fetch(`${API_URL}/api/traffic${taskId ? `?task_id=${taskId}` : ""}`).then(
      j<{ count: number; flows: Flow[]; proxy_port: number }>
    ),
  graph: (id: string) => fetch(`${API_URL}/api/tasks/${id}/graph`).then(j<GraphData>),
  sessions: (id: string) =>
    fetch(`${API_URL}/api/tasks/${id}/sessions`).then(
      j<{ events: any[]; workers: any[] }>
    ),
  streamUrl: (id: string) => `${API_URL}/api/tasks/${id}/stream`,

  // chat (main agent)
  listConversations: () =>
    fetch(`${API_URL}/api/chat/conversations`).then(j<Conversation[]>),
  createConversation: (body: { title?: string; task_id?: string | null }) =>
    fetch(`${API_URL}/api/chat/conversations`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<Conversation>),
  getConversation: (cid: string) =>
    fetch(`${API_URL}/api/chat/conversations/${cid}`).then(j<Conversation>),
  sendMessage: (cid: string, text: string) =>
    fetch(`${API_URL}/api/chat/conversations/${cid}/message`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }).then(j<ChatMsg>),
  injectHint: (taskId: string, phase: string, text = "") =>
    fetch(`${API_URL}/api/tasks/${taskId}/hint`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phase, text }),
    }).then(j),

  // approvals
  approvalRecords: () =>
    fetch(`${API_URL}/api/approval-records`).then(
      j<{ total: number; pending_count: number; records: ApprovalRecord[] }>
    ),
  decideApproval: (seq: number, status: "allowed" | "denied") =>
    fetch(`${API_URL}/api/approvals/${seq}/decide`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }).then(j<ApprovalRecord>),
};
