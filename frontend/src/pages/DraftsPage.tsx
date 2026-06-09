import { useEffect, useState } from 'react';
import { agentsApi } from '../services/agentsApi';
import { workspaceApi } from '../services/workspaceApi';
import { writeApi } from '../services/writeApi';
import type { WorkspaceNode } from '../types';

const agentNames = ['meta-creator', 'internal-linker', 'keyword-mapper', 'editor', 'seo-optimizer'];

export function DraftsPage() {
  const [nodes, setNodes] = useState<WorkspaceNode[]>([]);
  const [topic, setTopic] = useState('');
  const [selectedPath, setSelectedPath] = useState('');
  const [content, setContent] = useState('');
  const [agentOutput, setAgentOutput] = useState('');

  const load = async () => {
    const tree = await workspaceApi.tree();
    setNodes(tree.nodes.filter((n) => n.type === 'file' && n.path.startsWith('drafts/')));
  };

  useEffect(() => {
    workspaceApi.init().then(load);
  }, []);

  useEffect(() => {
    if (!selectedPath) return;
    workspaceApi.read(selectedPath).then((res) => setContent(res.content));
  }, [selectedPath]);

  return (
    <div style={{ textAlign: 'left' }}>
      <h1>Drafts</h1>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic to write" />
        <button
          onClick={async () => {
            const res = await writeApi.write(topic);
            if (res.path) setSelectedPath(String(res.path));
            await load();
          }}
        >
          Create draft
        </button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr 1fr', gap: 12 }}>
        <ul>
          {nodes.map((node) => (
            <li key={node.path}>
              <button onClick={() => setSelectedPath(node.path)}>{node.path}</button>
            </li>
          ))}
        </ul>
        <div>
          <h3>{selectedPath || 'Select draft'}</h3>
          <textarea
            rows={20}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            style={{ width: '100%' }}
          />
          <button
            onClick={async () => {
              if (!selectedPath) return;
              await workspaceApi.write(selectedPath, content);
            }}
          >
            Save draft
          </button>
        </div>
        <div>
          <h3>Agent panel</h3>
          {agentNames.map((name) => (
            <button
              key={name}
              onClick={async () => {
                const out = await agentsApi.run(name, content);
                setAgentOutput(JSON.stringify(out, null, 2));
              }}
              style={{ marginRight: 6, marginBottom: 6 }}
            >
              {name}
            </button>
          ))}
          <pre>{agentOutput}</pre>
        </div>
      </div>
    </div>
  );
}
