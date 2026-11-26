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
  unique?: number;
  pending: number;
  by_severity: Record<Severity, number>;
  findings: (Finding & { instances?: number; assets?: string[] })[];
};

export type Secret = { name: string; created_at: string };
export type InterceptionRule = { id: number; rule_type: string; pattern: any; action: string };

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

export type AttackCoverage = {
  tactics: string[];
  by_tactic: Record<string, { id: string; name: string; count: number }[]>;
  techniques_total: number;
  techniques_exercised: number;
};

export type KillChain = {
  steps: { order: number; phase: string; target: string; action: string;
           result: string; findings: { title: string; severity: string }[] }[];
  summary: string; length: number;
};

export type Telemetry = {
  task_id: string;
  reward_series: { step: number; phase: string; tool: string; reward: number; ran: boolean }[];
  detection: { tool: string; predicted: number; observed_alerts: number }[];
  total_alerts: number; stealth_score: number; epsilon: number; steps: number;
};

export type GlobalTelemetry = {
  tasks: number; avg_stealth_score: number | null;
  total_steps: number; total_alerts: number; per_task: Telemetry[];
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
  allFindings: (dedup = false) =>
    fetch(`${API_URL}/api/findings${dedup ? "?dedup=true" : ""}`).then(j<FindingsAgg>),
  listSecrets: () => fetch(`${API_URL}/api/secrets`).then(j<Secret[]>),
  setSecret: (name: string, value: string) =>
    fetch(`${API_URL}/api/secrets`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, value }),
    }).then(j<Secret>),
  deleteSecret: (name: string) =>
    fetch(`${API_URL}/api/secrets/${encodeURIComponent(name)}`, { method: "DELETE" }).then(j),
  listRules: () => fetch(`${API_URL}/api/interception-rules`).then(j<InterceptionRule[]>),
  addRule: (rule_type: string, pattern: string, action: string) =>
    fetch(`${API_URL}/api/interception-rules`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rule_type, pattern, action }),
    }).then(j<InterceptionRule>),
  deleteRule: (id: number) =>
    fetch(`${API_URL}/api/interception-rules/${id}`, { method: "DELETE" }).then(j),
  traffic: (taskId?: string) =>
    fetch(`${API_URL}/api/traffic${taskId ? `?task_id=${taskId}` : ""}`).then(
      j<{ count: number; flows: Flow[]; proxy_port: number }>
    ),
  graph: (id: string) => fetch(`${API_URL}/api/tasks/${id}/graph`).then(j<GraphData>),
  attackCoverage: (taskId?: string) =>
    fetch(`${API_URL}/api/attack-coverage${taskId ? `?task_id=${taskId}` : ""}`).then(j<AttackCoverage>),
  killchain: (id: string) =>
    fetch(`${API_URL}/api/tasks/${id}/killchain`).then(j<KillChain>),
  taskTelemetry: (id: string) =>
    fetch(`${API_URL}/api/tasks/${id}/telemetry`).then(j<Telemetry>),
  telemetry: () => fetch(`${API_URL}/api/telemetry`).then(j<GlobalTelemetry>),
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
