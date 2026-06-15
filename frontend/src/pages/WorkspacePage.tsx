import { useEffect, useMemo, useState } from 'react';
import {
  Check,
  Circle,
  Eye,
  FileText,
  FolderOpen,
  Plus,
  RefreshCw,
  Save,
} from 'lucide-react';
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
  Input,
  Loading,
  PageHeader,
  Textarea,
} from '../components/ui';
import { workspaceApi } from '../services';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useToast } from '../hooks/useToast';
import { basename, errorMessage } from '../lib/format';
import type { WorkspaceNode } from '../types';

/** Context files every workspace is expected to carry, with a starter template. */
const CHECKLIST: ReadonlyArray<{ path: string; label: string; template: string }> = [
  {
    path: 'context/brand-voice.md',
    label: 'Brand voice',
    template:
      '# Brand voice\n\nDescribe tone, personality, and the words your brand does (and does not) use.\n',
  },
  {
    path: 'context/style-guide.md',
    label: 'Style guide',
    template:
      '# Style guide\n\nFormatting rules, headings, capitalization, and structural conventions.\n',
  },
  {
    path: 'context/keywords.md',
    label: 'Keywords',
    template: '# Keywords\n\nPrimary and secondary keywords this content should target.\n',
  },
];

/** Top-level group label for a workspace file path (the first path segment). */
function groupOf(path: string): string {
  const parts = path.split('/').filter(Boolean);
  return parts.length > 1 ? parts[0] : '/';
}

export function WorkspacePage() {
  const toast = useToast();
  const treeAction = useAsyncAction();
  const fileAction = useAsyncAction();
  const saveAction = useAsyncAction();

  const [root, setRoot] = useState<string>('');
  const [nodes, setNodes] = useState<WorkspaceNode[]>([]);
  const [activePath, setActivePath] = useState<string>('');
  const [content, setContent] = useState<string>('');
  const [dirty, setDirty] = useState<boolean>(false);
  const [preview, setPreview] = useState<boolean>(false);
  const [newPath, setNewPath] = useState<string>('');

  const files = useMemo(
    () =>
      nodes
        .filter((n) => n.type === 'file')
        .slice()
        .sort((a, b) => a.path.localeCompare(b.path)),
    [nodes],
  );

  const grouped = useMemo(() => {
    const map = new Map<string, WorkspaceNode[]>();
    for (const f of files) {
      const g = groupOf(f.path);
      const list = map.get(g);
      if (list) list.push(f);
      else map.set(g, [f]);
    }
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [files]);

  const existingPaths = useMemo(() => new Set(files.map((f) => f.path)), [files]);
  const isMarkdown = activePath.toLowerCase().endsWith('.md');

  const refreshTree = async (): Promise<WorkspaceNode[]> => {
    const res = await treeAction.run(() => workspaceApi.tree());
    if (!res) return [];
    setNodes(res.nodes ?? []);
    return res.nodes ?? [];
  };

  // Initialize the workspace, then load its tree on mount.
  useEffect(() => {
    void (async () => {
      const init = await treeAction.run(() => workspaceApi.init());
      if (init) setRoot(init.workspace_root);
      await refreshTree();
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openFile = async (path: string) => {
    if (dirty && !window.confirm('Discard unsaved changes?')) return;
    const res = await fileAction.run(() => workspaceApi.read(path));
    if (!res) return;
    setActivePath(res.path);
    setContent(res.content ?? '');
    setDirty(false);
    setPreview(false);
  };

  const save = async () => {
    if (!activePath) return;
    const res = await saveAction.run(() => workspaceApi.write(activePath, content));
    if (!res) {
      toast.error(saveAction.error || 'Failed to save');
      return;
    }
    setDirty(false);
    toast.success(`Saved ${basename(activePath)}`);
  };

  const createFile = async (path: string, template: string) => {
    const clean = path.trim().replace(/^\/+/, '');
    if (!clean) {
      toast.error('Enter a file path');
      return;
    }
    if (existingPaths.has(clean)) {
      toast.info(`${clean} already exists`);
      void openFile(clean);
      return;
    }
    try {
      await workspaceApi.write(clean, template);
    } catch (err) {
      toast.error(errorMessage(err));
      return;
    }
    toast.success(`Created ${basename(clean)}`);
    const fresh = await refreshTree();
    if (fresh.some((n) => n.path === clean)) {
      await openFile(clean);
    }
  };

  const loadingTree = treeAction.loading && nodes.length === 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Workspace"
        description="Browse and edit the filesystem-backed content workspace."
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => void refreshTree()}
            loading={treeAction.loading}
            leftIcon={<RefreshCw size={14} />}
          >
            Refresh
          </Button>
        }
      />

      {root && (
        <p className="flex items-center gap-2 text-xs text-muted">
          <FolderOpen size={13} /> <span className="font-mono text-ink">{root}</span>
        </p>
      )}

      {/* Setup checklist */}
      <Card>
        <CardHeader
          title="Setup checklist"
          description="Context files agents inject into prompts (brand voice, style, keywords)."
        />
        <CardBody className="space-y-2">
          {CHECKLIST.map((item) => {
            const present = existingPaths.has(item.path);
            return (
              <div
                key={item.path}
                className="flex items-center gap-3 rounded-lg border border-line bg-elevated/40 px-3 py-2"
              >
                {present ? (
                  <Check size={16} className="shrink-0 text-good" />
                ) : (
                  <Circle size={16} className="shrink-0 text-muted" />
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-ink">{item.label}</p>
                  <p className="truncate font-mono text-xs text-muted">{item.path}</p>
                </div>
                {present ? (
                  <Button size="sm" variant="ghost" onClick={() => void openFile(item.path)}>
                    Open
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="subtle"
                    leftIcon={<Plus size={13} />}
                    onClick={() => void createFile(item.path, item.template)}
                  >
                    Create
                  </Button>
                )}
              </div>
            );
          })}
        </CardBody>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.6fr)]">
        {/* Left: file browser */}
        <Card className="self-start">
          <CardHeader
            title="Files"
            description={files.length ? `${files.length} files` : undefined}
          />
          <CardBody className="space-y-4">
            <Field label="New file" hint="Path relative to the workspace root.">
              <div className="flex gap-2">
                <Input
                  value={newPath}
                  onChange={(e) => setNewPath(e.target.value)}
                  placeholder="drafts/notes.md"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      void createFile(newPath, '');
                      setNewPath('');
                    }
                  }}
                />
                <Button
                  variant="primary"
                  leftIcon={<Plus size={14} />}
                  onClick={() => {
                    void createFile(newPath, '');
                    setNewPath('');
                  }}
                >
                  Create
                </Button>
              </div>
            </Field>

            {treeAction.error && (
              <ErrorNote message={treeAction.error} onRetry={() => void refreshTree()} />
            )}

            {loadingTree ? (
              <Loading />
            ) : files.length === 0 ? (
              <EmptyState
                icon={<FileText size={26} />}
                title="No files yet"
                description="Create a file above or add the context files from the checklist."
              />
            ) : (
              <div className="space-y-4">
                {grouped.map(([group, items]) => (
                  <div key={group}>
                    <p className="mb-1.5 font-mono text-[11px] uppercase tracking-wide text-muted">
                      {group}
                    </p>
                    <div className="space-y-0.5">
                      {items.map((f) => {
                        const active = f.path === activePath;
                        return (
                          <button
                            key={f.path}
                            onClick={() => void openFile(f.path)}
                            className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left font-mono text-xs transition-colors ${
                              active
                                ? 'bg-brand-soft text-brand'
                                : 'text-muted hover:bg-elevated hover:text-ink'
                            }`}
                            title={f.path}
                          >
                            <FileText size={13} className="shrink-0 opacity-70" />
                            <span className="truncate">{basename(f.path)}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>

        {/* Right: editor */}
        <div className="min-w-0">
          {!activePath ? (
            <Card>
              <CardBody className="py-20">
                <EmptyState
                  icon={<FileText size={28} />}
                  title="Select a file to edit"
                  description="Pick a file from the list, or create a new one to start writing."
                />
              </CardBody>
            </Card>
          ) : (
            <Card>
              <CardHeader
                title={basename(activePath)}
                description={activePath}
                actions={
                  <div className="flex items-center gap-2">
                    {dirty && <Badge tone="warn">Unsaved</Badge>}
                    {isMarkdown && (
                      <Button
                        variant="ghost"
                        size="sm"
                        leftIcon={<Eye size={14} />}
                        onClick={() => setPreview((p) => !p)}
                      >
                        {preview ? 'Edit' : 'Preview'}
                      </Button>
                    )}
                    <Button
                      variant="primary"
                      size="sm"
                      leftIcon={<Save size={14} />}
                      loading={saveAction.loading}
                      disabled={!dirty}
                      onClick={() => void save()}
                    >
                      Save
                    </Button>
                  </div>
                }
              />
              <CardBody className="space-y-3">
                {fileAction.error && (
                  <ErrorNote message={fileAction.error} onRetry={() => void openFile(activePath)} />
                )}
                {fileAction.loading ? (
                  <Loading />
                ) : preview && isMarkdown ? (
                  <ContentViewer content={content} />
                ) : (
                  <Textarea
                    value={content}
                    onChange={(e) => {
                      setContent(e.target.value);
                      setDirty(true);
                    }}
                    rows={22}
                    className="font-mono text-xs"
                    placeholder="Empty file — start writing…"
                  />
                )}
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
