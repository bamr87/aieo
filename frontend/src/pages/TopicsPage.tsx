import { useCallback, useEffect, useState } from 'react';
import { workspaceApi } from '../services/workspaceApi';
import type { WorkspaceNode } from '../types';

export function TopicsPage() {
  const [nodes, setNodes] = useState<WorkspaceNode[]>([]);
  const [topic, setTopic] = useState('');

  const load = useCallback(async () => {
    await workspaceApi.init();
    const tree = await workspaceApi.tree();
    setNodes(tree.nodes);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const topics = nodes.filter((n) => n.type === 'file' && n.path.startsWith('topics/'));

  return (
    <div style={{ textAlign: 'left' }}>
      <h1>Topics</h1>
      <p>Capture raw content ideas and queue them for research.</p>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="New topic idea" />
        <button
          onClick={async () => {
            if (!topic.trim()) return;
            const slug = topic.toLowerCase().replace(/\s+/g, '-');
            await workspaceApi.write(`topics/${slug}.md`, `# ${topic}\n\n## Notes\n\n- \n`);
            setTopic('');
            await load();
          }}
        >
          Add topic
        </button>
      </div>
      <ul>
        {topics.map((t) => (
          <li key={t.path}>{t.path}</li>
        ))}
      </ul>
    </div>
  );
}
