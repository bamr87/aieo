import { apiClient } from './api';
import type { LifecycleResult } from '../types';

export const researchApi = {
  research: (topic: string, model?: string) =>
    apiClient.post<LifecycleResult>('/aieo/research', { topic, model }),
  analyzeExisting: (target: string, model?: string) =>
    apiClient.post('/aieo/analyze-existing', { target, model }),
  priorities: () => apiClient.get('/aieo/priorities'),
};
