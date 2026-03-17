import axios from "axios";
import type {
  Token, User, ModelConfig, Dataset, EvaluationTask,
  EvaluationResult, EloScore, Report, Benchmark, PlatformStats, EvaluatorConfig,
  AgentConversation, AgentMessage, AgentToolDefinition, AgentMemoryItem, AuditLog,
  PromptTemplate, PromptExperiment, ComparisonResult, DiffResult,
  ArenaMatch, NotificationItem, APIKeyItem,
  Organization, OrgMember, ResourceShare, GeneratedTrainingData,
  BuiltinBenchmarkDataset, JudgeModelConfig, MetricDefinition, AgentModelConfig,
  EvaluationTemplate,
} from "@/types";
import { cachedFetch, invalidateCache } from "./apiCache";

export const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const BASE_WS_URL = BASE_URL.replace(/^http/, "ws");

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
  timeout: 30000, // 30s timeout
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 globally
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// Cache TTL constants
const SHORT_TTL = 15_000;  // 15s for frequently changing data
const MEDIUM_TTL = 30_000; // 30s for moderately changing data
const LONG_TTL = 300_000;  // 5min for rarely changing data

// --- Auth ---
export const authApi = {
  register: (data: { username: string; email: string; password: string; full_name?: string }) =>
    api.post<User>("/auth/register", data).then((r) => r.data),

  login: (username: string, password: string) =>
    api.post<Token>("/auth/login", { username, password }).then((r) => r.data),

  me: () => api.get<User>("/auth/me").then((r) => r.data),
};

// --- Models ---
export const modelsApi = {
  list: () => cachedFetch("models:list",
    () => api.get<ModelConfig[]>("/models/").then((r) => r.data),
    MEDIUM_TTL,
  ),
  create: (data: {
    name: string; provider: string; api_key?: string;
    base_url?: string; model_name: string; params?: Record<string, unknown>; tags?: string[];
  }) => api.post<ModelConfig>("/models/", data).then((r) => {
    invalidateCache("models:");
    return r.data;
  }),
  get: (id: number) => api.get<ModelConfig>(`/models/${id}`).then((r) => r.data),
  update: (id: number, data: Partial<{
    name: string; provider: string; api_key: string; base_url: string;
    model_name: string; params: Record<string, unknown>; tags: string[]; is_active: boolean;
  }>) => api.put<ModelConfig>(`/models/${id}`, data).then((r) => {
    invalidateCache("models:");
    return r.data;
  }),
  delete: (id: number) => api.delete(`/models/${id}`).then((r) => {
    invalidateCache("models:");
    return r;
  }),
  testConnection: (data: {
    provider: string; api_key?: string; base_url?: string; model_name: string;
  }) => api.post<{
    success: boolean; latency_ms?: number; output?: string; model?: string; error?: string;
  }>("/models/test-connection", data, { timeout: 60000 }).then((r) => r.data),
  testSaved: (id: number) => api.post<{
    success: boolean; latency_ms?: number; output?: string; model?: string; error?: string;
  }>(`/models/${id}/test`, {}, { timeout: 60000 }).then((r) => r.data),
};

// --- Datasets ---
export const datasetsApi = {
  list: () => cachedFetch("datasets:list",
    () => api.get<Dataset[]>("/datasets/").then((r) => r.data),
    MEDIUM_TTL,
  ),
  builtinBenchmarks: () => cachedFetch("datasets:builtin",
    () => api.get<BuiltinBenchmarkDataset[]>("/datasets/builtin-benchmarks").then((r) => r.data),
    LONG_TTL,
  ),
  create: (formData: FormData) =>
    api.post<Dataset>("/datasets/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 60000, // longer timeout for uploads
    }).then((r) => {
      invalidateCache("datasets:");
      return r.data;
    }),
  get: (id: number) => api.get<Dataset>(`/datasets/${id}`).then((r) => r.data),
  delete: (id: number) => api.delete(`/datasets/${id}`).then((r) => {
    invalidateCache("datasets:");
    return r;
  }),
  preview: (id: number, limit = 10) =>
    api.get<{ records: Record<string, unknown>[]; total: number }>(`/datasets/${id}/preview?limit=${limit}`).then((r) => r.data),
};

// --- Evaluations ---
export const evaluationsApi = {
  list: () => cachedFetch("evaluations:list",
    () => api.get<EvaluationTask[]>("/evaluations/").then((r) => r.data),
    SHORT_TTL,
  ),
  create: (data: {
    name: string; description?: string;
    model_ids: number[]; dataset_id?: number;
    evaluator_config: EvaluatorConfig;
  }) => api.post<EvaluationTask>("/evaluations/", data).then((r) => {
    invalidateCache("evaluations:");
    return r.data;
  }),
  get: (id: number) => api.get<EvaluationTask>(`/evaluations/${id}`).then((r) => r.data),
  /** Lightweight progress poll — counts actual result rows in DB */
  liveProgress: (id: number) => api.get<{
    status: string; total_samples: number; processed_samples: number;
    progress: number; per_model: Record<string, number>; error_message?: string;
  }>(`/evaluations/${id}/live-progress`).then((r) => r.data),
  cancel: (id: number) => api.delete(`/evaluations/${id}`).then((r) => {
    invalidateCache("evaluations:");
    return r;
  }),
  deleteTask: (id: number) => api.delete(`/evaluations/${id}/delete`).then((r) => {
    invalidateCache("evaluations:");
    return r;
  }),
  results: (id: number, params?: { model_id?: number; limit?: number; offset?: number }) =>
    api.get<EvaluationResult[]>(`/evaluations/${id}/results`, { params }).then((r) => r.data),
  /** Force fresh fetch, bypassing cache (for polling) */
  listFresh: () => {
    invalidateCache("evaluations:list");
    return api.get<EvaluationTask[]>("/evaluations/").then((r) => r.data);
  },
  retry: (id: number) => api.post<EvaluationTask>(`/evaluations/${id}/retry`).then((r) => {
    invalidateCache("evaluations:");
    return r.data;
  }),
  // Batch operations
  batchDelete: (ids: number[]) => api.post<{ deleted: number; ids: number[] }>("/evaluations/batch/delete", { ids }).then((r) => {
    invalidateCache("evaluations:");
    return r.data;
  }),
  batchCancel: (ids: number[]) => api.post<{ cancelled: number; ids: number[] }>("/evaluations/batch/cancel", { ids }).then((r) => {
    invalidateCache("evaluations:");
    return r.data;
  }),
  batchRetry: (ids: number[]) => api.post<{ retried: number; ids: number[] }>("/evaluations/batch/retry", { ids }).then((r) => {
    invalidateCache("evaluations:");
    return r.data;
  }),
  // Domain eval closed-loop
  diagnose: (id: number, threshold?: number) =>
    api.post(`/evaluations/${id}/diagnose`, { threshold: threshold || 0.6 }, { timeout: 120000 }).then((r) => r.data),
  generateData: (id: number) =>
    api.post(`/evaluations/${id}/generate-data`, {}, { timeout: 120000 }).then((r) => r.data),
  getGeneratedData: (id: number) =>
    api.get<GeneratedTrainingData[]>(`/evaluations/${id}/generated-data`).then((r) => r.data),
  updateGeneratedData: (id: number, dataId: number, data: { corrected_output?: string; is_approved?: boolean; is_edited?: boolean }) =>
    api.put(`/evaluations/${id}/generated-data/${dataId}`, data).then((r) => r.data),
  exportDataset: (id: number, selectedIds: number[], name: string) =>
    api.post<Dataset>(`/evaluations/${id}/export-dataset`, { selected_ids: selectedIds, name }).then((r) => r.data),
};

// --- Reports ---
export const reportsApi = {
  list: () => cachedFetch("reports:list",
    () => api.get<Report[]>("/reports/").then((r) => r.data),
    MEDIUM_TTL,
  ),
  generate: (task_id: number, format: string) =>
    api.post<Report>("/reports/generate", { task_id, format }).then((r) => {
      invalidateCache("reports:");
      return r.data;
    }),
  downloadUrl: (id: number) => `${BASE_URL}/api/v1/reports/${id}/download`,
  download: (id: number) =>
    api.get<Blob>(`/reports/${id}/download`, { responseType: "blob" }).then((r) => r.data),
};

// --- Leaderboard ---
export const leaderboardApi = {
  elo: () => cachedFetch("leaderboard:elo",
    () => api.get<EloScore[]>("/leaderboard/elo").then((r) => r.data),
    MEDIUM_TTL,
  ),
  benchmarks: (benchmark?: string) =>
    cachedFetch(`leaderboard:benchmarks:${benchmark || "all"}`,
      () => api.get("/leaderboard/benchmarks", { params: benchmark ? { benchmark } : {} }).then((r) => r.data),
      MEDIUM_TTL,
    ),
};

// --- Benchmarks ---
export const benchmarksApi = {
  list: () => cachedFetch("benchmarks:list",
    () => api.get<Benchmark[]>("/benchmarks/").then((r) => r.data),
    LONG_TTL, // benchmarks rarely change
  ),
  get: (id: string) => api.get<Benchmark>(`/benchmarks/${id}`).then((r) => r.data),
  preview: (id: string, limit = 10) =>
    api.get<{ records: Record<string, unknown>[]; total: number; data_available: boolean }>(
      `/benchmarks/${id}/preview?limit=${limit}`
    ).then((r) => r.data),
  dataInfo: (id: string) =>
    api.get<{ benchmark_id: string; data_available: boolean; sample_count: number; source: string; downloaded_at: string | null }>(
      `/benchmarks/${id}/data-info`
    ).then((r) => r.data),
};

// --- Judge Models ---
export const judgeModelsApi = {
  list: () => cachedFetch("judge-models:list",
    () => api.get<JudgeModelConfig[]>("/judge-models/").then((r) => r.data),
    MEDIUM_TTL,
  ),
  create: (data: {
    name: string; provider: string; api_key?: string;
    base_url?: string; model_name: string; is_default?: boolean;
  }) => api.post<JudgeModelConfig>("/judge-models/", data).then((r) => {
    invalidateCache("judge-models:");
    return r.data;
  }),
  update: (id: number, data: Partial<{
    name: string; provider: string; api_key: string;
    base_url: string; model_name: string; is_default: boolean; is_active: boolean;
  }>) => api.put<JudgeModelConfig>(`/judge-models/${id}`, data).then((r) => {
    invalidateCache("judge-models:");
    return r.data;
  }),
  delete: (id: number) => api.delete(`/judge-models/${id}`).then((r) => {
    invalidateCache("judge-models:");
    return r;
  }),
  test: (id: number) => api.post(`/judge-models/${id}/test`).then((r) => r.data),
};

// --- Agent Model ---
export const agentModelApi = {
  get: () => api.get<AgentModelConfig | null>("/agent-model/").then((r) => r.data),
  upsert: (data: {
    name: string; provider: string; api_key?: string;
    base_url?: string; model_name: string; max_tokens?: number; temperature?: number;
  }) => api.put<AgentModelConfig>("/agent-model/", data).then((r) => r.data),
  remove: () => api.delete("/agent-model/").then((r) => r),
  test: () => api.post("/agent-model/test").then((r) => r.data),
};

// --- Metrics ---
export const metricsApi = {
  registry: () => cachedFetch("metrics:registry",
    () => api.get<MetricDefinition[]>("/metrics/registry").then((r) => r.data),
    LONG_TTL,
  ),
};

// --- Admin ---
export const adminApi = {
  users: () => cachedFetch("admin:users",
    () => api.get<User[]>("/admin/users").then((r) => r.data),
    SHORT_TTL,
  ),
  stats: () => cachedFetch("admin:stats",
    () => api.get<PlatformStats>("/admin/stats").then((r) => r.data),
    SHORT_TTL,
  ),
  toggleUser: (id: number) => api.put(`/admin/users/${id}/toggle-active`).then((r) => {
    invalidateCache("admin:");
    return r.data;
  }),
};

// --- Audit ---
export const auditApi = {
  logs: (params?: { action?: string; user_id?: number; limit?: number; offset?: number }) =>
    api.get<AuditLog[]>("/audit/logs", { params }).then((r) => r.data),
  count: () => api.get<{ total: number }>("/audit/logs/count").then((r) => r.data),
};

// --- Agent (AI Assistant) ---
export const agentApi = {
  chatStreamUrl: `${BASE_URL}/api/v1/agent/chat`,
  tools: () => cachedFetch("agent:tools",
    () => api.get<AgentToolDefinition[]>("/agent/tools").then((r) => r.data),
    LONG_TTL,
  ),
  conversations: () =>
    api.get<AgentConversation[]>("/agent/conversations").then((r) => r.data),
  conversation: (id: number) =>
    api.get<AgentConversation & { messages: AgentMessage[] }>(
      `/agent/conversations/${id}`
    ).then((r) => r.data),
  deleteConversation: (id: number) => api.delete(`/agent/conversations/${id}`),
  memories: () => api.get<AgentMemoryItem[]>("/agent/memories").then((r) => r.data),
  deleteMemory: (id: number) => api.delete(`/agent/memories/${id}`),
  clearMemories: () => api.delete("/agent/memories"),
};

// --- Prompts ---
export const promptsApi = {
  list: (promptType?: string, domain?: string) => cachedFetch(
    `prompts:list:${promptType || ""}:${domain || ""}`,
    () => api.get<PromptTemplate[]>("/prompts/", {
      params: { ...(promptType ? { prompt_type: promptType } : {}), ...(domain ? { domain } : {}) },
    }).then((r) => r.data),
    MEDIUM_TTL,
  ),
  create: (data: { name: string; content: string; variables?: string[]; tags?: string[]; prompt_type?: string; domain?: string }) =>
    api.post<PromptTemplate>("/prompts/", data).then((r) => { invalidateCache("prompts:"); return r.data; }),
  get: (id: number) => api.get<PromptTemplate>(`/prompts/${id}`).then((r) => r.data),
  update: (id: number, data: Partial<{ name: string; content: string; variables: string[]; tags: string[]; is_active: boolean; prompt_type: string; domain: string }>) =>
    api.put<PromptTemplate>(`/prompts/${id}`, data).then((r) => { invalidateCache("prompts:"); return r.data; }),
  delete: (id: number) => api.delete(`/prompts/${id}`).then((r) => { invalidateCache("prompts:"); return r; }),
  experiments: () => api.get<PromptExperiment[]>("/prompts/experiments").then((r) => r.data),
  createExperiment: (data: { name: string; template_ids: number[]; model_ids: number[]; test_inputs: Record<string, unknown>[] }) =>
    api.post<PromptExperiment>("/prompts/experiments", data).then((r) => r.data),
  runExperiment: (id: number) => api.post<PromptExperiment>(`/prompts/experiments/${id}/run`, {}, { timeout: 120000 }).then((r) => r.data),
  getExperiment: (id: number) => api.get<PromptExperiment>(`/prompts/experiments/${id}`).then((r) => r.data),
};

// --- Comparison ---
export const comparisonApi = {
  compare: (task_ids: number[]) =>
    api.post<ComparisonResult>("/comparison/tasks", { task_ids }).then((r) => r.data),
  diff: (task_a: number, task_b: number, model_id?: number, limit?: number) =>
    api.post<DiffResult>("/comparison/diff", { task_a, task_b, model_id, limit }).then((r) => r.data),
};

// --- Arena ---
export const arenaApi = {
  createMatch: (data: { prompt: string; model_a_id: number; model_b_id: number }) =>
    api.post<ArenaMatch>("/arena/matches", data, { timeout: 120000 }).then((r) => r.data),
  vote: (matchId: number, winner: string) =>
    api.post<ArenaMatch>(`/arena/matches/${matchId}/vote`, { winner }).then((r) => r.data),
  list: () => api.get<ArenaMatch[]>("/arena/matches").then((r) => r.data),
};

// --- Notifications ---
export const notificationsApi = {
  list: (params?: { is_read?: boolean; limit?: number }) =>
    api.get<NotificationItem[]>("/notifications/", { params }).then((r) => r.data),
  unreadCount: () =>
    api.get<{ count: number }>("/notifications/unread-count").then((r) => r.data),
  markRead: (id: number) =>
    api.put(`/notifications/${id}/read`).then((r) => r.data),
  markAllRead: () =>
    api.put("/notifications/read-all").then((r) => r.data),
  delete: (id: number) =>
    api.delete(`/notifications/${id}`).then((r) => r.data),
};

// --- API Keys ---
export const apiKeysApi = {
  list: () => api.get<APIKeyItem[]>("/api-keys/").then((r) => r.data),
  create: (data: { name: string; permissions?: string[]; expires_in_days?: number }) =>
    api.post("/api-keys/", data).then((r) => r.data),
  revoke: (id: number) => api.delete(`/api-keys/${id}`).then((r) => r.data),
  toggle: (id: number) => api.put(`/api-keys/${id}/toggle`).then((r) => r.data),
};

// --- Teams ---
export const teamsApi = {
  list: () => api.get<Organization[]>("/teams/").then((r) => r.data),
  create: (data: { name: string; description?: string }) =>
    api.post<Organization>("/teams/", data).then((r) => r.data),
  get: (id: number) => api.get<Organization & { members: OrgMember[] }>(`/teams/${id}`).then((r) => r.data),
  addMember: (orgId: number, username: string, role?: string) =>
    api.post(`/teams/${orgId}/members`, { username, role }).then((r) => r.data),
  removeMember: (orgId: number, userId: number) =>
    api.delete(`/teams/${orgId}/members/${userId}`),
  share: (orgId: number, data: { resource_type: string; resource_id: number }) =>
    api.post(`/teams/${orgId}/share`, data).then((r) => r.data),
  sharedResources: (orgId: number) =>
    api.get<ResourceShare[]>(`/teams/${orgId}/shared`).then((r) => r.data),
  unshare: (orgId: number, shareId: number) =>
    api.delete(`/teams/${orgId}/share/${shareId}`),
};

// --- Evaluation Templates ---
export const evalTemplatesApi = {
  list: () => cachedFetch("eval-templates:list",
    () => api.get<EvaluationTemplate[]>("/eval-templates/").then((r) => r.data),
    MEDIUM_TTL,
  ),
  create: (data: {
    name: string; description?: string; model_ids: number[];
    dataset_id?: number; evaluator_config: Record<string, unknown>;
  }) => api.post<EvaluationTemplate>("/eval-templates/", data).then((r) => {
    invalidateCache("eval-templates:");
    return r.data;
  }),
  update: (id: number, data: Partial<{
    name: string; description: string; model_ids: number[];
    dataset_id: number; evaluator_config: Record<string, unknown>;
  }>) => api.put<EvaluationTemplate>(`/eval-templates/${id}`, data).then((r) => {
    invalidateCache("eval-templates:");
    return r.data;
  }),
  delete: (id: number) => api.delete(`/eval-templates/${id}`).then((r) => {
    invalidateCache("eval-templates:");
    return r;
  }),
};

export default api;
