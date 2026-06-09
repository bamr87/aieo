import { apiClient } from './api';
import type { WorkspaceReadResponse, WorkspaceTreeResponse } from '../types';

export const workspaceApi = {
  init: () => apiClient.post<{ workspace_root: string }>('/aieo/workspace/init'),
  tree: () => apiClient.get<WorkspaceTreeResponse>('/aieo/workspace/tree'),
  read: (path: string) =>
    apiClient.post<WorkspaceReadResponse>('/aieo/workspace/read', { path }),
  write: (path: string, content: string) =>
    apiClient.post<{ path: string }>('/aieo/workspace/write', { path, content }),
  move: (sourcePath: string, destinationPath: string) =>
    apiClient.post<{ source: string; destination: string }>('/aieo/workspace/move', {
      source_path: sourcePath,
      destination_path: destinationPath,
    }),
};
