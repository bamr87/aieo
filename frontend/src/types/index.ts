// Type definitions for AIEO API responses

export interface ApiError {
  error: {
    code: string;
    message: string;
    retry_after?: number;
  };
}

export interface AuditResult {
  score: number;
  grade: string;
  gaps: Gap[];
  benchmark?: {
    percentile: number;
    engine_scores: Record<string, number>;
  };
}

export interface Gap {
  id: string;
  category: string;
  severity: 'high' | 'medium' | 'low';
  description: string;
  location?: {
    start: number;
    end: number;
  };
  example_fix?: string;
}

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
  location: {
    start: number;
    end: number;
  };
  original_text: string;
  optimized_text: string;
  expected_uplift: number;
}

export interface Pattern {
  id: string;
  name: string;
  category: string;
  description: string;
  citation_boost: {
    min: number;
    max: number;
  };
}

export interface DashboardData {
  total_citations: number;
  citations_by_engine: Record<string, number>;
  top_cited_pages: CitedPage[];
  citation_trend: Array<{
    date: string;
    count: number;
  }>;
}

export interface CitedPage {
  url: string;
  citation_count: number;
  engines: string[];
}

