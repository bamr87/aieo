import { apiClient } from './api';

export const dataApi = {
  gaTopPages: () => apiClient.get('/aieo/data/ga/top-pages'),
  gscQueries: () => apiClient.get('/aieo/data/gsc/queries'),
  dfsSerp: (keyword: string) => apiClient.post('/aieo/data/dfs/serp', { keyword }),
};
