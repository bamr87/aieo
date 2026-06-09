import { apiClient } from './api';
import type { LifecycleResult } from '../types';

export const writeApi = {
  write: (topic: string, briefPath?: string, model?: string) =>
    apiClient.post<LifecycleResult>('/aieo/write', { topic, brief_path: briefPath, model }),
  rewrite: (sourcePath: string, model?: string) =>
    apiClient.post<LifecycleResult>('/aieo/rewrite', { source_path: sourcePath, model }),
  scrub: (content: string, model?: string) =>
    apiClient.post<LifecycleResult>('/aieo/scrub', { content, model }),
};
