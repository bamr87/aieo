import { apiClient } from './api';
import type { LifecycleResult } from '../types';

export const researchApi = {
  research: (topic: string, model?: string) =>
    apiClient.post<LifecycleResult>('/aieo/research', { topic, model }),
  analyzeExisting: (target: string, model?: string) =>
    apiClient.post<LifecycleResult>('/aieo/analyze-existing', { target, model }),
  priorities: () => apiClient.get<Record<string, unknown>>('/aieo/priorities'),
};
