import { apiClient } from './api';
import type { DataResult } from '../types';

export const dataApi = {
  gaTopPages: () => apiClient.get<DataResult>('/aieo/data/ga/top-pages'),
  gscQueries: () => apiClient.get<DataResult>('/aieo/data/gsc/queries'),
  dfsSerp: (keyword: string) =>
    apiClient.post<DataResult>('/aieo/data/dfs/serp', { keyword }),
};
