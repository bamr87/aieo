import { useEffect, useState } from 'react';
import { dataApi } from '../services/dataApi';
import { researchApi } from '../services/researchApi';

export function PerformancePage() {
  const [ga, setGa] = useState<Record<string, unknown> | null>(null);
  const [gsc, setGsc] = useState<Record<string, unknown> | null>(null);
  const [dfs, setDfs] = useState<Record<string, unknown> | null>(null);
  const [priorities, setPriorities] = useState<Record<string, unknown> | null>(null);
  const [keyword, setKeyword] = useState('content marketing');

  useEffect(() => {
    dataApi.gaTopPages().then((res) => setGa(res as Record<string, unknown>)).catch(() => undefined);
    dataApi.gscQueries().then((res) => setGsc(res as Record<string, unknown>)).catch(() => undefined);
    researchApi.priorities().then((res) => setPriorities(res as Record<string, unknown>)).catch(() => undefined);
  }, []);

  return (
    <div style={{ textAlign: 'left' }}>
      <h1>Performance</h1>
      <p>Analytics-driven priorities from GA4, GSC, and DataForSEO.</p>
      <div style={{ display: 'flex', gap: 8 }}>
        <input value={keyword} onChange={(e) => setKeyword(e.target.value)} />
        <button
          onClick={async () => {
            const res = await dataApi.dfsSerp(keyword);
            setDfs(res as Record<string, unknown>);
          }}
        >
          Load DataForSEO snapshot
        </button>
      </div>
      <h3>Priority queue</h3>
      <pre>{JSON.stringify(priorities, null, 2)}</pre>
      <h3>GA4 top pages</h3>
      <pre>{JSON.stringify(ga, null, 2)}</pre>
      <h3>GSC queries</h3>
      <pre>{JSON.stringify(gsc, null, 2)}</pre>
      <h3>DataForSEO</h3>
      <pre>{JSON.stringify(dfs, null, 2)}</pre>
    </div>
  );
}
