export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ModelConfig {
  id: number;
  user_id: number;
  name: string;
  provider: string;
  base_url?: string;
  model_name: string;
  params?: Record<string, unknown>;
  tags?: string[];
  is_active: boolean;
  created_at: string;
}

export interface Dataset {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  category: string;
  format: string;
  size: number;
  status: string;
  schema_meta?: {
    fields?: string[];
    sample?: Record<string, unknown>;
  };
  created_at: string;
}

export interface EvaluatorConfig {
  llm_judge?: boolean;
  judge_model_id?: number;
  judge_dimensions?: string[];
  benchmarks?: string[];
  hallucination?: boolean;
  hallucination_n_samples?: number;
  code_execution?: boolean;
  robustness?: boolean;
  robustness_perturbations?: string[];
  consistency?: boolean;
  consistency_n_runs?: number;
  safety?: boolean;
  rag_eval?: boolean;
  performance?: boolean;
  multiturn?: boolean;
  max_samples?: number;
  instruction_following?: boolean;
  cot_reasoning?: boolean;
  long_context?: boolean;
  long_context_length?: number;
  structured_output?: boolean;
  output_schema?: Record<string, unknown>;
  multilingual?: boolean;
  multilingual_languages?: string[];
  tool_calling?: boolean;
  multimodal?: boolean;
  cost_analysis?: boolean;
  // Thinking mode
  enable_thinking?: boolean;
  // Objective evaluation metrics
  objective_metrics?: boolean;
  selected_metrics?: string[];
  // Domain evaluation
  domain_eval?: boolean;
  domain?: string;
  generation_prompt_ids?: number[];
  evaluation_prompt_ids?: number[];
  eval_mode?: "evaluate" | "evaluate_optimize";
}

export interface MetricDefinition {
  id: string;
  name: string;
  category: string;
  category_label: string;
  needs_reference: boolean;
  heavy: boolean;
  description: string;
}

export interface GeneratedTrainingData {
  id: number;
  task_id: number;
  result_id: number;
  user_id: number;
  original_input?: string;
  original_output?: string;
  corrected_output?: string;
  diagnosis?: { problems?: { segment: string; issue: string; suggestion: string }[]; reasoning?: string };
  improvement_notes?: string;
  is_approved: boolean;
  is_edited: boolean;
  created_at: string;
}

export interface EvaluationTask {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  model_ids: number[];
  dataset_id?: number;
  evaluator_config: EvaluatorConfig;
  results_summary?: ResultsSummary;
  progress: number;
  total_samples: number;
  processed_samples: number;
  error_message?: string;
  retry_count?: number;
  max_retries?: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface ResultsSummary {
  by_model: Record<string, ModelSummary>;
}

export interface ModelSummary {
  model_name: string;
  scores: Record<string, number>;
  avg_latency_ms: number;
  sample_count: number;
}

export interface EvaluationResult {
  id: number;
  task_id: number;
  sample_index: number;
  model_id: number;
  input_text?: string;
  output_text?: string;
  reference_text?: string;
  scores: Record<string, number>;
  metadata: Record<string, unknown>;
  latency_ms?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  created_at: string;
}

export interface EloScore {
  rank: number;
  model_id: number;
  model_name: string;
  elo_score: number;
  wins: number;
  losses: number;
  draws: number;
  total_matches: number;
  win_rate: number;
}

export interface Report {
  id: number;
  task_id: number;
  user_id: number;
  format: string;
  file_path?: string;
  file_size?: number;
  generated_at: string;
}

export interface Benchmark {
  id: string;
  name: string;
  description: string;
  metric: string;
  categories: string[];
  sample_size: number;
  data_available?: boolean;
  data_source?: string;
  actual_sample_count?: number;
}

export interface BuiltinBenchmarkDataset {
  id: string;
  benchmark_id: string;
  name: string;
  description: string;
  category: string;
  format: string;
  size: number;
  metric: string;
  categories: string[];
  data_available: boolean;
  data_source: string;
  status: string;
  is_builtin: boolean;
}

export interface JudgeModelConfig {
  id: number;
  user_id: number;
  name: string;
  provider: string;
  base_url?: string;
  model_name: string;
  params?: Record<string, unknown>;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
}

export interface AgentModelConfig {
  id: number;
  user_id: number;
  name: string;
  provider: string;
  base_url?: string;
  model_name: string;
  max_tokens: number;
  temperature: number;
  params?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}

export interface PlatformStats {
  total_users: number;
  total_models: number;
  total_datasets: number;
  total_evaluations: number;
  completed_evaluations: number;
}

export interface ProgressEvent {
  status: string;
  progress: number;
  processed?: number;
  total?: number;
  current_model?: string;
  current_model_id?: number;
  sample_index?: number;
  summary?: ResultsSummary;
  error?: string;
  message?: string;
  processing_sample?: number;
  per_model_progress?: Record<string, { processed: number; total: number; model_name?: string; is_processing?: boolean }>;
  live_sample?: {
    input: string;
    output: string;
    scores: Record<string, number>;
  };
}

// ────────────── Audit ──────────────

export interface AuditLog {
  id: number;
  user_id?: number;
  action: string;
  resource_type?: string;
  resource_id?: number;
  details?: Record<string, unknown>;
  ip_address?: string;
  created_at: string;
}

// ────────────── Agent (AI Assistant) ──────────────

export interface AgentConversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface AgentMessage {
  id: number;
  conversation_id: number;
  role: "user" | "assistant" | "tool";
  content?: string;
  tool_calls?: AgentToolCall[];
  tool_call_id?: string;
  tool_name?: string;
  created_at: string;
}

export interface AgentToolCall {
  id: string;
  type: "function";
  function: {
    name: string;
    arguments: string;
  };
}

export interface AgentToolDefinition {
  name: string;
  description: string;
  category: string;
  parameters: Record<string, unknown>;
  requires_confirmation: boolean;
}

export interface AgentToolResult {
  tool_call_id: string;
  name: string;
  result: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: {
    id: string;
    name: string;
    arguments: Record<string, unknown>;
    status: "running" | "done" | "error";
    result?: Record<string, unknown>;
  }[];
  timestamp: Date;
}

// ────────────── Prompt Engineering ──────────────

export interface PromptTemplate {
  id: number;
  user_id: number;
  name: string;
  content: string;
  variables?: string[];
  version: number;
  parent_id?: number;
  tags?: string[];
  is_active: boolean;
  prompt_type: "generation" | "evaluation";
  domain?: string;
  created_at: string;
  updated_at: string;
}

export interface PromptExperiment {
  id: number;
  user_id: number;
  name: string;
  template_ids: number[];
  model_ids: number[];
  test_inputs: Record<string, unknown>[];
  results?: Record<string, unknown>;
  status: string;
  created_at: string;
}

// ────────────── Comparison ──────────────

export interface ComparisonResult {
  tasks: { id: number; name: string; model_ids: number[]; status: string; created_at: string }[];
  by_model: Record<string, { scores: Record<string, number>; avg_latency_ms: number; sample_count: number }>;
  score_keys: string[];
}

export interface DiffResult {
  samples: {
    index: number;
    input: string;
    output_a: string;
    output_b: string;
    scores_a: Record<string, number>;
    scores_b: Record<string, number>;
  }[];
  summary: { a_better_count: number; b_better_count: number; tie_count: number; task_a: number; task_b: number };
}

// ────────────── Arena ──────────────

export interface ArenaMatch {
  id: number;
  user_id: number;
  prompt: string;
  model_a_id: number;
  model_b_id: number;
  output_a?: string;
  output_b?: string;
  winner?: string;
  latency_a_ms?: number;
  latency_b_ms?: number;
  created_at: string;
}

// ────────────── Notifications ──────────────

export interface NotificationItem {
  id: number;
  user_id: number;
  type: string;
  title: string;
  message?: string;
  data?: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}

// ────────────── Agent Memory ──────────────

export interface AgentMemoryItem {
  id: number;
  memory_type: string;
  key: string;
  value: string;
  confidence: number;
  access_count: number;
  created_at: string;
}

// ────────────── API Keys ──────────────

export interface APIKeyItem {
  id: number;
  name: string;
  key_prefix: string;
  permissions: string[];
  is_active: boolean;
  last_used_at?: string;
  expires_at?: string;
  created_at: string;
}

// ────────────── Teams ──────────────

export interface Organization {
  id: number;
  name: string;
  description?: string;
  owner_id: number;
  member_count: number;
  created_at: string;
}

export interface OrgMember {
  id: number;
  user_id: number;
  username: string;
  role: string;
  joined_at: string;
}

export interface ResourceShare {
  id: number;
  org_id: number;
  resource_type: string;
  resource_id: number;
  shared_by: number;
  created_at: string;
}

// ────────────── Evaluation Templates ──────────────

export interface EvaluationTemplate {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  model_ids: number[];
  dataset_id?: number;
  evaluator_config: EvaluatorConfig;
  created_at: string;
  updated_at: string;
}
