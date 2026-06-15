import { apiClient } from './api';
import type { LandingAuditResult, LifecycleResult } from '../types';

/** Landing-page lifecycle endpoints (content.py /aieo/landing/*). */
export const landingApi = {
  write: (topic: string, model?: string) =>
    apiClient.post<LifecycleResult>('/aieo/landing/write', { topic, model }),
  research: (topic: string, model?: string) =>
    apiClient.post<LifecycleResult>('/aieo/landing/research', { topic, model }),
  competitor: (url: string, model?: string) =>
    apiClient.post<LifecycleResult>('/aieo/landing/competitor', { url, model }),
  audit: (content: string) =>
    apiClient.post<LandingAuditResult>('/aieo/landing/audit', { content }),
};
