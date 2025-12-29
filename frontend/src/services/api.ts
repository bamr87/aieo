/** API client for backend communication. */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export interface ApiError {
  error: {
    code: string;
    message: string;
    retry_after?: number;
  };
}

class ApiClient {
  private baseUrl: string;
  private apiKey: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    // Load API key from localStorage
    this.apiKey = localStorage.getItem('aieo_api_key');
  }

  setApiKey(key: string) {
    this.apiKey = key;
    localStorage.setItem('aieo_api_key', key);
  }

  clearApiKey() {
    this.apiKey = null;
    localStorage.removeItem('aieo_api_key');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        // Handle rate limiting
        if (response.status === 429) {
          const retryAfter = response.headers.get('Retry-After') || '60';
          const error: ApiError = await response.json().catch(() => ({
            error: {
              code: 'RATE_LIMITED',
              message: `Rate limit exceeded. Retry after ${retryAfter} seconds.`,
              retry_after: parseInt(retryAfter),
            },
          }));
          throw error;
        }

        // Handle other errors
        const error: ApiError = await response.json().catch(() => ({
          error: {
            code: 'UNKNOWN_ERROR',
            message: `HTTP ${response.status}: ${response.statusText}`,
          },
        }));
        throw error;
      }

      return response.json();
    } catch (error) {
      // Handle network errors
      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        throw {
          error: {
            code: 'NETWORK_ERROR',
            message: 'Unable to connect to server. Please check your connection.',
          },
        } as ApiError;
      }
      throw error;
    }
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export const apiClient = new ApiClient(API_BASE_URL);

// API endpoints
export const auditApi = {
  audit: (data: { url?: string; content?: string; format?: string }) =>
    apiClient.post('/aieo/audit', data),
};

export const optimizeApi = {
  optimize: (data: {
    content: string;
    target_engines?: string[];
    style?: string;
  }) => apiClient.post('/aieo/optimize', data),
};

export const citationsApi = {
  getCitations: (params?: {
    url?: string;
    domain?: string;
    engine?: string;
    limit?: number;
    cursor?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, String(value));
        }
      });
    }
    return apiClient.get(`/aieo/citations?${searchParams.toString()}`);
  },
  getDashboard: () => apiClient.get('/aieo/dashboard'),
};

export const patternsApi = {
  listPatterns: () => apiClient.get('/aieo/patterns'),
  applyPattern: (patternId: string, content: string) =>
    apiClient.post(`/aieo/patterns/${patternId}/apply`, { content }),
};


