import { useEffect, useState } from 'react';
import { workspaceApi } from '../services/workspaceApi';
import { writeApi } from '../services/writeApi';
import type { WorkspaceNode } from '../types';

export function RewritesPage() {
  const [drafts, setDrafts] = useState<WorkspaceNode[]>([]);
  const [rewrites, setRewrites] = useState<WorkspaceNode[]>([]);
  const [sourcePath, setSourcePath] = useState('');
  const [source, setSource] = useState('');
  const [rewrite, setRewrite] = useState('');

  const load = async () => {
    const tree = await workspaceApi.tree();
    setDrafts(tree.nodes.filter((n) => n.type === 'file' && n.path.startsWith('drafts/')));
    setRewrites(tree.nodes.filter((n) => n.type === 'file' && n.path.startsWith('rewrites/')));
  };

  useEffect(() => {
    workspaceApi.init().then(load);
  }, []);

  return (
    <div style={{ textAlign: 'left' }}>
      <h1>Rewrites</h1>
      <div style={{ display: 'flex', gap: 8 }}>
        <select value={sourcePath} onChange={(e) => setSourcePath(e.target.value)}>
          <option value="">Select draft</option>
          {drafts.map((d) => (
            <option key={d.path} value={d.path}>
              {d.path}
            </option>
          ))}
        </select>
        <button
          onClick={async () => {
            if (!sourcePath) return;
            const sourceRes = await workspaceApi.read(sourcePath);
            setSource(sourceRes.content);
            const out = await writeApi.rewrite(sourcePath);
            if (out.path) {
              const rewriteRes = await workspaceApi.read(String(out.path));
              setRewrite(rewriteRes.content);
            }
            await load();
          }}
        >
          Rewrite selected
        </button>
      </div>
      <div style={{ marginTop: 8 }}>
        <strong>Existing rewrites:</strong> {rewrites.length}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
        <div>
          <h3>Original</h3>
          <pre>{source}</pre>
        </div>
        <div>
          <h3>Rewrite</h3>
          <pre>{rewrite}</pre>
        </div>
      </div>
    </div>
  );
}
