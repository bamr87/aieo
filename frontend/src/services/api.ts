/** API client for backend communication. */
import type {
  ApplyPatternResult,
  AuditRequest,
  AuditResult,
  CitationsResponse,
  DashboardData,
  OptimizeRequest,
  OptimizeResult,
  PatternsResponse,
} from '../types';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const API_KEY_STORAGE = 'aieo_api_key';

/** Default request timeout — generous because AI calls run synchronously. */
const DEFAULT_TIMEOUT_MS = 180_000;

/** A normalized API error. Thrown for every non-OK response or network failure. */
export class ApiError extends Error {
  code: string;
  status?: number;
  retryAfter?: number;

  constructor(message: string, code = 'UNKNOWN_ERROR', status?: number, retryAfter?: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

interface RequestOptions extends RequestInit {
  /** Override the default timeout (ms). */
  timeoutMs?: number;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  get baseURL(): string {
    return this.baseUrl;
  }

  getApiKey(): string | null {
    return localStorage.getItem(API_KEY_STORAGE);
  }

  setApiKey(key: string) {
    localStorage.setItem(API_KEY_STORAGE, key);
  }

  clearApiKey() {
    localStorage.removeItem(API_KEY_STORAGE);
  }

  hasApiKey(): boolean {
    return !!localStorage.getItem(API_KEY_STORAGE);
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { timeoutMs = DEFAULT_TIMEOUT_MS, ...init } = options;
    const url = `${this.baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(init.headers as Record<string, string>),
    };

    const apiKey = this.getApiKey();
    if (apiKey) headers['X-API-Key'] = apiKey;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    let response: Response;
    try {
      response = await fetch(url, { ...init, headers, signal: controller.signal });
    } catch (error) {
      clearTimeout(timer);
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ApiError(
          `Request timed out after ${Math.round(timeoutMs / 1000)}s. The server may still be working — try again or check the API.`,
          'TIMEOUT',
        );
      }
      throw new ApiError(
        'Unable to connect to the AIEO API. Is the backend running on ' +
          this.baseUrl.replace(/\/api\/v1$/, '') +
          '?',
        'NETWORK_ERROR',
      );
    }
    clearTimeout(timer);

    if (!response.ok) {
      throw await this.toError(response);
    }

    // 204 / empty body tolerance.
    const text = await response.text();
    if (!text) return undefined as T;
    try {
      return JSON.parse(text) as T;
    } catch {
      return text as unknown as T;
    }
  }

  /** Normalize the many backend error shapes into a single ApiError. */
  private async toError(response: Response): Promise<ApiError> {
    const status = response.status;
    let retryAfter: number | undefined;
    if (status === 429) {
      retryAfter = parseInt(response.headers.get('Retry-After') || '60', 10);
    }

    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // non-JSON body
    }

    // Shapes we handle:
    //   {error: {code, message}}            (optimize.py, global handler)
    //   {detail: "..."}                     (audit/workspace/content HTTPException)
    //   {detail: [{loc, msg, ...}]}         (FastAPI 422 validation)
    let message = `HTTP ${status}: ${response.statusText}`;
    let code = status === 429 ? 'RATE_LIMITED' : `HTTP_${status}`;

    const b = body as Record<string, unknown> | null;
    if (b && typeof b === 'object') {
      const errObj = b.error as { code?: string; message?: string } | undefined;
      if (errObj?.message) {
        message = errObj.message;
        code = errObj.code || code;
      } else if (typeof b.detail === 'string') {
        message = b.detail;
      } else if (Array.isArray(b.detail)) {
        message = (b.detail as Array<{ msg?: string; loc?: unknown[] }>)
          .map((d) => {
            const loc = Array.isArray(d.loc) ? d.loc.slice(1).join('.') : '';
            return loc ? `${loc}: ${d.msg}` : d.msg;
          })
          .filter(Boolean)
          .join('; ') || message;
      }
    }

    if (status === 401) {
      message =
        'Unauthorized (401). Set a valid API key in Settings — the backend requires an X-API-Key header.';
      code = 'UNAUTHORIZED';
    }

    return new ApiError(message, code, status, retryAfter);
  }

  get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data !== undefined ? JSON.stringify(data) : undefined,
    });
  }

  put<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data !== undefined ? JSON.stringify(data) : undefined,
    });
  }

  delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient(API_BASE_URL);

// ---------------------------------------------------------------------------
// Endpoint groups
// ---------------------------------------------------------------------------

export const auditApi = {
  audit: (data: AuditRequest) => apiClient.post<AuditResult>('/aieo/audit', data),
};

export const optimizeApi = {
  optimize: (data: OptimizeRequest) =>
    apiClient.post<OptimizeResult>('/aieo/optimize', data),
};

export const citationsApi = {
  getCitations: (params?: {
    url?: string;
    domain?: string;
    engine?: string;
    limit?: number;
  }) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== '') sp.append(k, String(v));
      });
    }
    const qs = sp.toString();
    return apiClient.get<CitationsResponse>(`/aieo/citations${qs ? `?${qs}` : ''}`);
  },
  getDashboard: () =>
    apiClient.get<Record<string, unknown>>('/aieo/dashboard').then(normalizeDashboard),
};

/**
 * The backend returns `{ by_engine, citation_rate, top_cited_pages:[{url,count}] }`,
 * while the UI/types use the richer `{ total_citations, citations_by_engine,
 * citation_trend, top_cited_pages:[{url,citation_count,engines}] }`. Normalize
 * so the dashboard renders regardless of which shape the server sends.
 */
function normalizeDashboard(raw: Record<string, unknown> | null): DashboardData {
  const r = raw || {};
  const byEngine = (r.citations_by_engine ?? r.by_engine ?? {}) as Record<string, number>;
  const trend = (r.citation_trend ?? r.citation_rate ?? []) as DashboardData['citation_trend'];
  const pages = (Array.isArray(r.top_cited_pages) ? r.top_cited_pages : []).map((p) => {
    const page = p as { url?: string; citation_count?: number; count?: number; engines?: string[] };
    return {
      url: page.url ?? '',
      citation_count: page.citation_count ?? page.count ?? 0,
      engines: page.engines ?? [],
    };
  });
  const total =
    typeof r.total_citations === 'number'
      ? r.total_citations
      : Object.values(byEngine).reduce((a, b) => a + (Number(b) || 0), 0);
  return {
    total_citations: total,
    citations_by_engine: byEngine,
    citation_trend: trend,
    top_cited_pages: pages,
  };
}

export const patternsApi = {
  listPatterns: () => apiClient.get<PatternsResponse>('/aieo/patterns'),
  applyPattern: (patternId: string, content: string) =>
    apiClient.post<ApplyPatternResult>(`/aieo/patterns/${patternId}/apply`, { content }),
};
