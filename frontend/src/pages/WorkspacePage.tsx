import { useCallback, useEffect, useMemo, useState } from 'react';
import { workspaceApi } from '../services/workspaceApi';
import type { WorkspaceNode } from '../types';
import './WorkspacePage.css';

const setupPaths = [
  'context/brand-voice.md',
  'context/target-keywords.md',
  'context/internal-links-map.md',
  'context/competitor-analysis.md',
];

export function WorkspacePage() {
  const [nodes, setNodes] = useState<WorkspaceNode[]>([]);
  const [selectedPath, setSelectedPath] = useState<string>('');
  const [content, setContent] = useState('');
  const [saved, setSaved] = useState('');

  const load = useCallback(async () => {
    await workspaceApi.init();
    const tree = await workspaceApi.tree();
    setNodes(tree.nodes);
    if (!selectedPath) {
      const first = tree.nodes.find((n) => n.type === 'file' && n.path.startsWith('context/'));
      if (first) {
        setSelectedPath(first.path);
      }
    }
  }, [selectedPath]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedPath) {
      return;
    }
    workspaceApi.read(selectedPath).then((res) => setContent(res.content)).catch(() => setContent(''));
  }, [selectedPath]);

  const completedSetup = useMemo(
    () => setupPaths.filter((path) => nodes.some((node) => node.path === path)).length,
    [nodes]
  );

  return (
    <div className="workspace-page">
      <h1>Workspace</h1>
      <p>Edit context files and lifecycle artifacts in `.aieo-workspace`.</p>
      <div className="setup-wizard">
        <strong>Setup wizard:</strong> {completedSetup}/{setupPaths.length} required context files found
      </div>
      <div className="workspace-grid">
        <aside>
          <h3>Files</h3>
          <ul className="workspace-tree">
            {nodes
              .filter((node) => node.type === 'file')
              .map((node) => (
                <li key={node.path}>
                  <button
                    className={selectedPath === node.path ? 'selected' : ''}
                    onClick={() => setSelectedPath(node.path)}
                  >
                    {node.path}
                  </button>
                </li>
              ))}
          </ul>
        </aside>
        <section>
          <h3>{selectedPath || 'Select a file'}</h3>
          <textarea
            value={content}
            onChange={(event) => setContent(event.target.value)}
            rows={18}
            placeholder="Workspace file contents"
          />
          <div className="workspace-actions">
            <button
              onClick={async () => {
                if (!selectedPath) return;
                await workspaceApi.write(selectedPath, content);
                setSaved(`Saved ${selectedPath}`);
                await load();
              }}
            >
              Save
            </button>
            <span>{saved}</span>
          </div>
          <h4>Preview</h4>
          <pre>{content.slice(0, 1000)}</pre>
        </section>
      </div>
    </div>
  );
}
