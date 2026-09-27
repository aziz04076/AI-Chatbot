export type AIState = 'idle' | 'thinking' | 'speaking';

export type ThemeStyle = 'cyberpunk' | 'cosmic' | 'minimal';

export interface User {
  id: string;
  email: string;
  username: string;
  role: string;
}

export interface Citation {
  source: string;
  snippet: string;
  similarity: number;
  retrieval_method?: string;
  bm25_rank?: number;
  vector_rank?: number;
}

export interface ToolCallEvent {
  tool: string;
  input: string;
  reason?: string;
  output?: string;
}

export type SubTaskStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface SubTask {
  id: string;
  title: string;
  assigned_agent: 'planner' | 'infra_calculation' | 'research' | 'code_architect' | string;
  status: SubTaskStatus;
  dependencies?: string[];
  input_prompt?: string;
  thought?: string;
  output?: string;
}

export interface TaskPlan {
  plan_id: string;
  goal: string;
  tasks: SubTask[];
  estimated_steps: number;
}

export interface TraceSpan {
  span_id: string;
  parent_span_id?: string | null;
  name: string;
  duration_ms: number;
  status: string;
  attributes?: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  confidence_score?: number;
  model_name?: string;
  citations?: Citation[];
  follow_ups?: string[];
  tool_events?: ToolCallEvent[];
  plan?: TaskPlan;
  latency_ms?: number;
  tokens_generated?: number;
  trace_id?: string;
  traceparent?: string;
  trace_spans?: TraceSpan[];
  created_at?: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  summary?: string;
  created_at: string;
  updated_at: string;
}

export interface SystemHealth {
  gpu_available: boolean;
  gpu_name: string;
  gpu_vram_used_gb: number;
  gpu_vram_total_gb: number;
  cpu_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  status: string;
}

export interface TopicTrend {
  topic: string;
  count: number;
  percentage: number;
}

export interface AnalyticsSummary {
  total_queries: number;
  avg_latency_ms: number;
  user_satisfaction_percent: number;
  active_sessions_count: number;
  system_health: SystemHealth;
  top_topics: TopicTrend[];
  daily_query_volume: Array<{ day: string; queries: number; avg_latency: number }>;
}

export interface QueryEvalResult {
  id: string;
  query: string;
  category: string;
  retrieved_sources: string[];
  precision_at_k: number;
  recall_at_k: number;
  reciprocal_rank: number;
  grounded_score: number;
  hallucination_detected: boolean;
  latency_ms: number;
  status: 'passed' | 'flagged' | 'failed';
}

export interface EvalBenchmarkReport {
  timestamp: string;
  total_queries: number;
  retrieval_precision_at_k: number;
  retrieval_recall_at_k: number;
  mean_reciprocal_rank: number;
  hallucination_rate: number;
  faithfulness_score: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
  latency_p99_ms: number;
  composite_score: number;
  query_results: QueryEvalResult[];
}
