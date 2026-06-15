import { apiClient } from './api';

export interface WordpressPublishResult {
  id?: number | string;
  url?: string;
  link?: string;
  status?: string;
  [key: string]: unknown;
}

/** Publishing endpoints (content.py /aieo/publish/*). */
export const publishApi = {
  wordpress: (draftPath: string, title: string, metadata?: Record<string, unknown>) =>
    apiClient.post<WordpressPublishResult>('/aieo/publish/wordpress', {
      draft_path: draftPath,
      title,
      metadata: metadata ?? {},
    }),
};
