import { useEffect, useMemo, useState } from 'react';
import { FileText, RefreshCw, RotateCw } from 'lucide-react';
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  ContentViewer,
  EmptyState,
  ErrorNote,
  Field,
  Loading,
  PageHeader,
  Select,
} from '../components/ui';
import { workspaceApi, writeApi } from '../services';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useSettings } from '../hooks/useSettings';
import { useToast } from '../hooks/useToast';
import { basename } from '../lib/format';
import type { LifecycleResult, WorkspaceNode } from '../types';

function filesUnder(nodes: WorkspaceNode[], prefix: string): WorkspaceNode[] {
  return nodes
    .filter((n) => n.type === 'file' && n.path.startsWith(prefix))
    .sort((a, b) => a.path.localeCompare(b.path));
}

export function RewritesPage() {
  const settings = useSettings();
  const toast = useToast();

  const tree = useAsyncAction();
  const loadAction = useAsyncAction();
  const rewriteAction = useAsyncAction();

  const [nodes, setNodes] = useState<WorkspaceNode[]>([]);
  const [selected, setSelected] = useState<string>('');
  const [original, setOriginal] = useState<string>('');
  const [rewrite, setRewrite] = useState<LifecycleResult | null>(null);

  const draftFiles = useMemo(() => filesUnder(nodes, 'drafts/'), [nodes]);
  const rewriteFiles = useMemo(() => filesUnder(nodes, 'rewrites/'), [nodes]);

  const loadTree = async () => {
    await tree.run(() => workspaceApi.init());
    const res = await tree.run(() => workspaceApi.tree());
    if (res) setNodes(res.nodes);
  };

  useEffect(() => {
    void loadTree();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectDraft = async (path: string) => {
    setSelected(path);
    setOriginal('');
    setRewrite(null);
    if (!path) return;
    const res = await loadAction.run(() => workspaceApi.read(path));
    if (res) setOriginal(res.content);
  };

  const runRewrite = async () => {
    if (!selected) return toast.error('Select a draft to rewrite first');
    const res = await rewriteAction.run(() =>
      writeApi.rewrite(selected, settings.model || undefined),
    );
    if (!res) return;
    setRewrite(res);
    toast.success(res.path ? `Saved to ${basename(res.path)}` : 'Rewrite complete');
    // Refresh the tree so the new rewrites/ file shows up.
    void loadTree();
  };

  const rewriteText = typeof rewrite?.content === 'string' ? rewrite.content : '';

  return (
    <div className="space-y-6">
      <PageHeader
        title="Rewrites"
        description="Rewrite an existing draft with AIEO patterns and compare it side-by-side."
      />

      <Card>
        <CardHeader
          title="Pick a draft"
          description={`${draftFiles.length} draft${draftFiles.length === 1 ? '' : 's'} in the workspace`}
          actions={
            <Button
              variant="ghost"
              size="sm"
              loading={tree.loading}
              onClick={() => void loadTree()}
              leftIcon={<RefreshCw size={14} />}
            >
              Refresh
            </Button>
          }
        />
        <CardBody className="space-y-4">
          {tree.error && <ErrorNote message={tree.error} onRetry={() => void loadTree()} />}

          {tree.loading && nodes.length === 0 ? (
            <Loading />
          ) : draftFiles.length === 0 ? (
            <EmptyState
              icon={<FileText size={22} />}
              title="No drafts yet"
              description="Create drafts in the Write workflow, then come back to rewrite them here."
            />
          ) : (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <Field label="Draft file" className="flex-1">
                <Select value={selected} onChange={(e) => void selectDraft(e.target.value)}>
                  <option value="">Select a draft…</option>
                  {draftFiles.map((f) => (
                    <option key={f.path} value={f.path}>
                      {basename(f.path)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Button
                variant="primary"
                loading={rewriteAction.loading}
                disabled={!selected || loadAction.loading}
                onClick={runRewrite}
                leftIcon={<RotateCw size={15} />}
              >
                {rewriteAction.loading ? 'Rewriting…' : 'Rewrite'}
              </Button>
            </div>
          )}

          {rewriteAction.loading && (
            <p className="text-xs text-muted">
              AI rewrites run synchronously and can take 30–90s.
            </p>
          )}
          {rewriteAction.error && (
            <ErrorNote message={rewriteAction.error} onRetry={runRewrite} />
          )}
        </CardBody>
      </Card>

      {selected && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="min-w-0">
            <CardHeader title="Original" description={basename(selected)} />
            <CardBody>
              {loadAction.error ? (
                <ErrorNote message={loadAction.error} onRetry={() => void selectDraft(selected)} />
              ) : loadAction.loading ? (
                <Loading />
              ) : original ? (
                <ContentViewer content={original} />
              ) : (
                <p className="py-10 text-center text-sm text-muted">This draft is empty.</p>
              )}
            </CardBody>
          </Card>

          <Card className="min-w-0">
            <CardHeader
              title="Rewrite"
              actions={
                rewrite?.path ? <Badge tone="brand">{basename(rewrite.path)}</Badge> : undefined
              }
            />
            <CardBody>
              {rewriteAction.loading ? (
                <Loading />
              ) : rewriteText ? (
                <ContentViewer content={rewriteText} />
              ) : (
                <p className="py-10 text-center text-sm text-muted">
                  Click <span className="font-medium text-ink">Rewrite</span> to generate an
                  improved version.
                </p>
              )}
            </CardBody>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader
          title="Saved rewrites"
          description={`${rewriteFiles.length} file${rewriteFiles.length === 1 ? '' : 's'} under rewrites/`}
        />
        <CardBody>
          {rewriteFiles.length === 0 ? (
            <p className="text-sm text-muted">No rewrites saved yet.</p>
          ) : (
            <ul className="space-y-1.5">
              {rewriteFiles.map((f) => (
                <li
                  key={f.path}
                  className="flex items-center gap-2 rounded-lg border border-line bg-elevated/40 px-3 py-2"
                >
                  <FileText size={14} className="shrink-0 text-muted" />
                  <span className="truncate text-sm text-ink">{basename(f.path)}</span>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
