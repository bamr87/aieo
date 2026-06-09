import { useEffect, useState } from 'react';
import { dataApi } from '../services/dataApi';
import { workspaceApi } from '../services/workspaceApi';
import type { WorkspaceNode } from '../types';

export function PublishedPage() {
  const [published, setPublished] = useState<WorkspaceNode[]>([]);
  const [ga, setGa] = useState<Record<string, unknown> | null>(null);
  const [gsc, setGsc] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    workspaceApi.init().then(async () => {
      const tree = await workspaceApi.tree();
      setPublished(tree.nodes.filter((n) => n.type === 'file' && n.path.startsWith('published/')));
    });
    dataApi.gaTopPages().then((res) => setGa(res as Record<string, unknown>)).catch(() => undefined);
    dataApi.gscQueries().then((res) => setGsc(res as Record<string, unknown>)).catch(() => undefined);
  }, []);

  return (
    <div style={{ textAlign: 'left' }}>
      <h1>Published</h1>
      <p>Published artifacts and attached performance snapshots.</p>
      <ul>
        {published.map((file) => (
          <li key={file.path}>{file.path}</li>
        ))}
      </ul>
      <h3>GA4 snapshot</h3>
      <pre>{JSON.stringify(ga, null, 2)}</pre>
      <h3>GSC snapshot</h3>
      <pre>{JSON.stringify(gsc, null, 2)}</pre>
    </div>
  );
}
