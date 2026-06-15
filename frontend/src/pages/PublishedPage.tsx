import { useEffect, useState } from 'react';
import {
  BarChart3,
  ExternalLink,
  FileText,
  RefreshCw,
  Search,
  Send,
} from 'lucide-react';
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  ErrorNote,
  Field,
  Input,
  JsonView,
  Loading,
  PageHeader,
  Select,
} from '../components/ui';
import { dataApi, publishApi, workspaceApi } from '../services';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useToast } from '../hooks/useToast';
import { basename } from '../lib/format';
import type { WorkspaceNode } from '../types';
import type { WordpressPublishResult } from '../services';

export function PublishedPage() {
  const toast = useToast();

  const tree = useAsyncAction();
  const publish = useAsyncAction();
  const ga = useAsyncAction();
  const gsc = useAsyncAction();

  const [published, setPublished] = useState<WorkspaceNode[]>([]);
  const [drafts, setDrafts] = useState<WorkspaceNode[]>([]);
  const [draftPath, setDraftPath] = useState('');
  const [title, setTitle] = useState('');
  const [result, setResult] = useState<WordpressPublishResult | null>(null);

  const [gaData, setGaData] = useState<unknown>(null);
  const [gscData, setGscData] = useState<unknown>(null);

  const loadTree = async () => {
    const res = await tree.run(async () => {
      await workspaceApi.init();
      return workspaceApi.tree();
    });
    if (!res) return;
    const files = res.nodes.filter((n) => n.type === 'file');
    setPublished(files.filter((n) => n.path.startsWith('published/')));
    setDrafts(files.filter((n) => n.path.startsWith('drafts/')));
  };

  const loadGa = async () => {
    const res = await ga.run(() => dataApi.gaTopPages(), { silent: true }).catch(() => undefined);
    if (res) setGaData(res);
  };

  const loadGsc = async () => {
    const res = await gsc.run(() => dataApi.gscQueries(), { silent: true }).catch(() => undefined);
    if (res) setGscData(res);
  };

  useEffect(() => {
    void loadTree();
    void loadGa();
    void loadGsc();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submitPublish = async () => {
    if (!draftPath) return toast.error('Pick a draft to publish');
    if (!title.trim()) return toast.error('Enter a post title');
    const res = await publish.run(() => publishApi.wordpress(draftPath, title.trim()));
    if (!res) {
      toast.error('Publish failed — check WordPress credentials on the server');
      return;
    }
    setResult(res);
    toast.success('Published to WordPress');
    void loadTree();
  };

  const postUrl = result?.url || result?.link;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Published"
        description="Published artifacts, WordPress publishing, and performance snapshots."
        actions={
          <Button
            variant="ghost"
            size="sm"
            onClick={loadTree}
            loading={tree.loading}
            leftIcon={<RefreshCw size={14} />}
          >
            Refresh
          </Button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        {/* Published files */}
        <Card className="self-start">
          <CardHeader
            title="Published artifacts"
            description={published.length ? `${published.length} file${published.length === 1 ? '' : 's'}` : undefined}
          />
          <CardBody>
            {tree.loading ? (
              <Loading />
            ) : tree.error ? (
              <ErrorNote message={tree.error} onRetry={loadTree} />
            ) : published.length === 0 ? (
              <EmptyState
                icon={<FileText size={22} />}
                title="Nothing published yet"
                description="Publish a draft to WordPress and it will be tracked under published/."
              />
            ) : (
              <ul className="space-y-1.5">
                {published.map((file) => (
                  <li
                    key={file.path}
                    className="flex items-center gap-2 rounded-lg border border-line bg-elevated/40 px-3 py-2"
                  >
                    <FileText size={15} className="shrink-0 text-muted" />
                    <span className="min-w-0 flex-1 truncate text-sm text-ink" title={file.path}>
                      {file.name || basename(file.path)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        {/* Publish to WordPress */}
        <div className="min-w-0 space-y-6">
          <Card>
            <CardHeader
              title="Publish to WordPress"
              description="Server-side WordPress credentials are required."
            />
            <CardBody className="space-y-4">
              <Field label="Draft" hint="Files under drafts/ in the workspace">
                <Select value={draftPath} onChange={(e) => setDraftPath(e.target.value)}>
                  <option value="">Select a draft…</option>
                  {drafts.map((d) => (
                    <option key={d.path} value={d.path}>
                      {d.name || basename(d.path)}
                    </option>
                  ))}
                </Select>
              </Field>
              {drafts.length === 0 && !tree.loading && (
                <p className="text-xs text-muted">No drafts found — create one on the Drafts page first.</p>
              )}
              <Field label="Post title">
                <Input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="How AI engines cite content"
                />
              </Field>
              <Button
                variant="primary"
                fullWidth
                loading={publish.loading}
                onClick={submitPublish}
                leftIcon={<Send size={15} />}
              >
                Publish
              </Button>
              {publish.error && (
                <ErrorNote
                  message={`${publish.error} — WordPress credentials may be unconfigured on the server.`}
                  onRetry={submitPublish}
                />
              )}
            </CardBody>
          </Card>

          {result && (
            <Card>
              <CardHeader title="Publish result" />
              <CardBody className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  {result.status && <Badge tone="good">{result.status}</Badge>}
                  {result.id != null && <Badge tone="neutral">ID {String(result.id)}</Badge>}
                </div>
                {postUrl ? (
                  <a
                    href={postUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-sm text-brand hover:underline"
                  >
                    <ExternalLink size={14} /> {postUrl}
                  </a>
                ) : (
                  <p className="text-sm text-muted">No post URL returned.</p>
                )}
              </CardBody>
            </Card>
          )}
        </div>
      </div>

      {/* Integration snapshots */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="GA4 — top pages"
            description="Requires Google Analytics integration credentials."
            actions={
              <Button
                variant="ghost"
                size="sm"
                onClick={loadGa}
                loading={ga.loading}
                leftIcon={<RefreshCw size={13} />}
              >
                Reload
              </Button>
            }
          />
          <CardBody>
            {ga.loading ? (
              <Loading />
            ) : gaData ? (
              <JsonView data={gaData} />
            ) : (
              <EmptyState
                icon={<BarChart3 size={22} />}
                title="No GA4 data"
                description="Connect a GA4 property to see top-page performance here."
              />
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Search Console — queries"
            description="Requires Google Search Console integration credentials."
            actions={
              <Button
                variant="ghost"
                size="sm"
                onClick={loadGsc}
                loading={gsc.loading}
                leftIcon={<RefreshCw size={13} />}
              >
                Reload
              </Button>
            }
          />
          <CardBody>
            {gsc.loading ? (
              <Loading />
            ) : gscData ? (
              <JsonView data={gscData} />
            ) : (
              <EmptyState
                icon={<Search size={22} />}
                title="No Search Console data"
                description="Connect Search Console to see top queries here."
              />
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
