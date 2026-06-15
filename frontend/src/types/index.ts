// Type definitions for AIEO API responses & requests.

export type Provider = 'auto' | 'heuristic' | 'openai' | 'anthropic' | 'claude-cli';

/** Normalized error envelope used across the API layer. */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    retry_after?: number;
  };
}

// ---------------------------------------------------------------------------
// Audit / scoring
// ---------------------------------------------------------------------------

export interface PatternScore {
  score: number;
  max: number;
  detected?: boolean;
  evidence?: string[];
  recommendation?: string;
}

export interface AuditResult {
  score: number;
  grade: string;
  gaps: Gap[];
  pattern_scores?: Record<string, PatternScore>;
  anti_pattern_penalties?: number;
  anti_pattern_details?: { detected?: string[]; evidence?: string[] };
  word_count?: number;
  content_type?: string;
  scoring_method?: 'ai' | 'heuristic';
  provider?: string;
  model?: string;
  overall_assessment?: string;
  executive_summary?: string;
  priority_actions?: string[];
  dimensions?: {
    aieo: number;
    seo: number;
    readability: number;
    humanity: number;
    cro: number;
  };
  benchmark?: {
    percentile: number;
    engine_scores: Record<string, number>;
  };
}

export interface Gap {
  id: string;
  category?: string;
  severity: 'high' | 'medium' | 'low';
  description: string;
  recommendation?: string;
  location?: { start: number; end: number };
  example_fix?: string;
}

export interface AuditRequest {
  url?: string;
  content?: string;
  format?: string;
  provider?: string;
  model?: string;
}

// ---------------------------------------------------------------------------
// Optimize
// ---------------------------------------------------------------------------

export interface OptimizeResult {
  optimized_content: string;
  score_before: number;
  score_after: number;
  uplift: number;
  changes: Change[];
}

export interface Change {
  type: string;
  description: string;
  location?: { start: number; end: number };
  original_text?: string;
  optimized_text?: string;
  expected_uplift?: number;
}

export interface OptimizeRequest {
  content: string;
  target_engines?: string[];
  style?: 'preserve' | 'aggressive';
  content_mode?: 'enhance' | 'expand';
  model?: string;
}

// ---------------------------------------------------------------------------
// Patterns
// ---------------------------------------------------------------------------

export interface Pattern {
  id: string;
  name: string;
  category: string;
  description: string;
  citation_boost?: { min: number; max: number };
}

export interface PatternsResponse {
  patterns: Pattern[];
}

export interface ApplyPatternResult {
  optimized_content: string;
  pattern_id: string;
  pattern_name: string;
}

// ---------------------------------------------------------------------------
// Citations / dashboard
// ---------------------------------------------------------------------------

export interface Citation {
  id: string;
  url: string;
  domain: string;
  engine: string;
  prompt?: string;
  citation_text?: string;
  position?: number;
  confidence?: number;
  detected_at: string;
}

export interface CitationsResponse {
  data: Citation[];
  pagination: { next_cursor: string | null; has_more: boolean; total_count: number };
}

export interface CitedPage {
  url: string;
  citation_count: number;
  engines: string[];
}

export interface DashboardData {
  total_citations: number;
  citations_by_engine: Record<string, number>;
  top_cited_pages: CitedPage[];
  citation_trend: Array<{ date: string; count: number }>;
}

// ---------------------------------------------------------------------------
// Workspace
// ---------------------------------------------------------------------------

export interface WorkspaceNode {
  path: string;
  type: 'file' | 'dir';
  name?: string;
}

export interface WorkspaceTreeResponse {
  nodes: WorkspaceNode[];
}

export interface WorkspaceReadResponse {
  path: string;
  content: string;
}

// ---------------------------------------------------------------------------
// Lifecycle (research / write / rewrite / scrub / analyze / agents / landing)
// ---------------------------------------------------------------------------

export interface LifecycleResult {
  path?: string;
  content?: string;
  [key: string]: unknown;
}

export interface AgentRunResult {
  agent?: string;
  // The backend nests the parsed agent output under `result` (or
  // `{ raw_output }` when the model didn't return JSON).
  result?: { output?: string; content?: string; raw_output?: string; [key: string]: unknown } | string;
  [key: string]: unknown;
}

export interface LandingAuditResult {
  score?: number;
  grade?: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Data integrations
// ---------------------------------------------------------------------------

export type DataResult = Record<string, unknown> | unknown[];

// ---------------------------------------------------------------------------
// Client-side audit history (localStorage)
// ---------------------------------------------------------------------------

export interface AuditHistoryEntry {
  id: string;
  at: number;
  label: string;
  source: 'url' | 'content';
  score: number;
  grade: string;
  scoring_method?: string;
  provider?: string;
  result: AuditResult;
}
