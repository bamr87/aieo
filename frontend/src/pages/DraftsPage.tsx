import { useEffect, useMemo, useState } from 'react';
import { FileText, Plus, RefreshCw, Save, Sparkles, Wand2 } from 'lucide-react';
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  ContentViewer,
  EmptyState,
  ErrorNote,
  Field,
  Input,
  JsonView,
  Loading,
  PageHeader,
  Select,
  Textarea,
} from '../components/ui';
import { AGENTS, agentsApi, workspaceApi, writeApi } from '../services';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useSettings } from '../hooks/useSettings';
import { useToast } from '../hooks/useToast';
import { agentResultText as agentText } from '../lib/agentText';
import { basename } from '../lib/format';
import type { WorkspaceNode } from '../types';

const DRAFTS_PREFIX = 'drafts/';

export function DraftsPage() {
  const settings = useSettings();
  const toast = useToast();

  const listAction = useAsyncAction();
  const openAction = useAsyncAction();
  const createAction = useAsyncAction();
  const saveAction = useAsyncAction();
  const agentAction = useAsyncAction();

  const [nodes, setNodes] = useState<WorkspaceNode[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [editorContent, setEditorContent] = useState('');
  const [topic, setTopic] = useState('');
  const [agentId, setAgentId] = useState<string>(AGENTS[0].id);
  const [agentOutput, setAgentOutput] = useState<unknown>(null);

  const draftFiles = useMemo(
    () =>
      nodes
        .filter((n) => n.type === 'file' && n.path.startsWith(DRAFTS_PREFIX))
        .sort((a, b) => a.path.localeCompare(b.path)),
    [nodes],
  );

  const loadTree = async () => {
    const res = await listAction.run(async () => {
      await workspaceApi.init();
      return workspaceApi.tree();
    });
    if (res) setNodes(res.nodes ?? []);
  };

  useEffect(() => {
    void loadTree();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openDraft = async (path: string) => {
    const res = await openAction.run(() => workspaceApi.read(path));
    if (!res) {
      toast.error('Could not open draft');
      return;
    }
    setSelectedPath(path);
    setEditorContent(res.content ?? '');
    setAgentOutput(null);
  };

  const createDraft = async () => {
    if (!topic.trim()) return toast.error('Enter a topic first');
    const res = await createAction.run(() =>
      writeApi.write(topic.trim(), undefined, settings.model || undefined),
    );
    if (!res) return;
    toast.success('Draft written');
    setTopic('');
    await loadTree();
    if (typeof res.path === 'string') {
      await openDraft(res.path);
    } else if (typeof res.content === 'string') {
      setSelectedPath(null);
      setEditorContent(res.content);
      setAgentOutput(null);
    }
  };

  const saveDraft = async () => {
    if (!selectedPath) return toast.error('Open a draft to save');
    const res = await saveAction.run(() => workspaceApi.write(selectedPath, editorContent));
    if (res) toast.success('Saved');
  };

  const runAgent = async () => {
    if (!editorContent.trim()) {
      return toast.error('The editor is empty — nothing to send the agent');
    }
    const res = await agentAction.run(() =>
      agentsApi.run(agentId, editorContent, undefined, settings.model || undefined),
    );
    if (res === undefined) return;
    setAgentOutput(res);
    const label = AGENTS.find((a) => a.id === agentId)?.label ?? agentId;
    toast.success(`${label} finished`);
  };

  const agentOutputText = agentOutput == null ? null : agentText(agentOutput);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Drafts"
        description="Author drafts in the workspace and refine them with content agents."
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={loadTree}
            loading={listAction.loading}
            leftIcon={<RefreshCw size={14} />}
          >
            Refresh
          </Button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,300px)_minmax(0,1fr)]">
        {/* Drafts list */}
        <Card className="self-start">
          <CardHeader title="Drafts" description={`${draftFiles.length} in workspace`} />
          <CardBody className="space-y-2">
            {listAction.error ? (
              <ErrorNote message={listAction.error} onRetry={loadTree} />
            ) : listAction.loading && draftFiles.length === 0 ? (
              <Loading label="Loading drafts…" />
            ) : draftFiles.length === 0 ? (
              <EmptyState
                icon={<FileText size={22} />}
                title="No drafts yet"
                description="Create one from a topic on the right."
              />
            ) : (
              <ul className="space-y-1.5">
                {draftFiles.map((node) => {
                  const active = node.path === selectedPath;
                  return (
                    <li key={node.path}>
                      <button
                        onClick={() => void openDraft(node.path)}
                        className={`flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                          active
                            ? 'border-line-strong bg-brand-soft text-ink'
                            : 'border-line bg-elevated/40 text-muted hover:text-ink'
                        }`}
                      >
                        <FileText size={14} className="shrink-0 text-muted" />
                        <span className="truncate">{node.name ?? basename(node.path)}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardBody>
        </Card>

        {/* Editor column */}
        <div className="min-w-0 space-y-6">
          {/* Create draft */}
          <Card>
            <CardHeader title="Create draft" description="Generates a first draft from a topic." />
            <CardBody className="space-y-4">
              <Field label="Topic" hint="A working title or angle for the article.">
                <Input
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="How AI engines pick which sources to cite"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') void createDraft();
                  }}
                />
              </Field>
              <Button
                variant="primary"
                loading={createAction.loading}
                onClick={createDraft}
                leftIcon={<Plus size={15} />}
              >
                {createAction.loading ? 'Writing draft…' : 'Write draft'}
              </Button>
              {createAction.loading && (
                <p className="text-xs text-muted">
                  AI writes run synchronously and can take 30–90s.
                </p>
              )}
              {createAction.error && (
                <ErrorNote message={createAction.error} onRetry={createDraft} />
              )}
            </CardBody>
          </Card>

          {/* Editor */}
          <Card>
            <CardHeader
              title="Editor"
              description={selectedPath ?? 'No draft selected'}
              actions={
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={saveDraft}
                  loading={saveAction.loading}
                  disabled={!selectedPath}
                  leftIcon={<Save size={14} />}
                >
                  Save
                </Button>
              }
            />
            <CardBody className="space-y-3">
              {openAction.loading ? (
                <Loading label="Opening draft…" />
              ) : !selectedPath && !editorContent ? (
                <EmptyState
                  icon={<FileText size={22} />}
                  title="Open or create a draft"
                  description="Select a draft on the left, or write a new one from a topic above."
                />
              ) : (
                <>
                  <Field label="Draft content">
                    <Textarea
                      value={editorContent}
                      onChange={(e) => setEditorContent(e.target.value)}
                      rows={18}
                      placeholder="# Draft…"
                    />
                  </Field>
                  {!selectedPath && editorContent && (
                    <p className="text-xs text-muted">
                      This draft was returned inline and isn’t saved to a file yet.
                    </p>
                  )}
                </>
              )}
              {openAction.error && <ErrorNote message={openAction.error} />}
              {saveAction.error && <ErrorNote message={saveAction.error} onRetry={saveDraft} />}
            </CardBody>
          </Card>

          {/* Agent assist */}
          <Card>
            <CardHeader
              title="Agent assist"
              description="Run a content agent over the current editor text."
            />
            <CardBody className="space-y-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                <Field label="Agent" className="flex-1">
                  <Select value={agentId} onChange={(e) => setAgentId(e.target.value)}>
                    {AGENTS.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Button
                  variant="subtle"
                  loading={agentAction.loading}
                  disabled={!editorContent.trim()}
                  onClick={runAgent}
                  leftIcon={<Wand2 size={15} />}
                >
                  Run agent
                </Button>
              </div>
              {agentAction.loading && (
                <p className="text-xs text-muted">Agent runs synchronously and may take a while.</p>
              )}
              {agentAction.error && <ErrorNote message={agentAction.error} onRetry={runAgent} />}

              {agentOutput == null ? (
                <EmptyState
                  icon={<Sparkles size={22} />}
                  title="No agent output yet"
                  description="Pick an agent and run it to see suggestions here."
                />
              ) : agentOutputText !== null ? (
                <ContentViewer content={agentOutputText} />
              ) : (
                <JsonView data={agentOutput} title="Agent result" />
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}
