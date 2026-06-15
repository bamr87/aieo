import { useState } from 'react';
import { FileSearch, ListChecks, Microscope, Search } from 'lucide-react';
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
  JsonView,
  PageHeader,
} from '../components/ui';
import { researchApi } from '../services';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useSettings } from '../hooks/useSettings';
import { useToast } from '../hooks/useToast';
import type { LifecycleResult } from '../types';

const SLOW_HINT = 'AI research runs synchronously and may take 30–90s.';

export function ResearchPage() {
  const settings = useSettings();
  const toast = useToast();

  // 1) Research a topic
  const research = useAsyncAction();
  const [topic, setTopic] = useState('');
  const [topicResult, setTopicResult] = useState<LifecycleResult | null>(null);

  // 2) Analyze existing
  const analyze = useAsyncAction();
  const [target, setTarget] = useState('');
  const [analyzeResult, setAnalyzeResult] = useState<LifecycleResult | null>(null);

  // 3) Priorities
  const priorities = useAsyncAction();
  const [prioritiesResult, setPrioritiesResult] = useState<Record<string, unknown> | null>(null);

  const submitResearch = async () => {
    if (!topic.trim()) return toast.error('Enter a topic to research');
    const res = await research.run(() =>
      researchApi.research(topic.trim(), settings.model || undefined),
    );
    if (!res) return;
    setTopicResult(res);
    toast.success(res.path ? `Saved to ${res.path}` : 'Research complete');
  };

  const submitAnalyze = async () => {
    if (!target.trim()) return toast.error('Enter a URL or workspace path');
    const res = await analyze.run(() =>
      researchApi.analyzeExisting(target.trim(), settings.model || undefined),
    );
    if (!res) return;
    setAnalyzeResult(res);
    toast.success(res.path ? `Saved to ${res.path}` : 'Analysis complete');
  };

  const submitPriorities = async () => {
    const res = await priorities.run(() => researchApi.priorities());
    if (!res) return;
    setPrioritiesResult(res);
    toast.success('Priorities loaded');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Research"
        description="Research a topic, analyze an existing page, and surface content priorities for the workspace."
      />

      {/* 1) Research a topic */}
      <Card>
        <CardHeader
          title="Research a topic"
          description="Generate a research brief and save it to the workspace."
        />
        <CardBody className="space-y-4">
          <Field label="Topic" hint="A subject, question, or working title to research.">
            <Input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. How AI engines decide which sources to cite"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !research.loading) void submitResearch();
              }}
            />
          </Field>
          <Button
            variant="primary"
            loading={research.loading}
            onClick={submitResearch}
            leftIcon={<Search size={15} />}
          >
            {research.loading ? 'Researching…' : 'Research topic'}
          </Button>
          {research.loading && <p className="text-xs text-muted">{SLOW_HINT}</p>}
          {research.error && <ErrorNote message={research.error} onRetry={submitResearch} />}
          {topicResult && <LifecycleOutput result={topicResult} />}
        </CardBody>
      </Card>

      {/* 2) Analyze existing */}
      <Card>
        <CardHeader
          title="Analyze existing content"
          description="Evaluate a live URL or a file already in the workspace."
        />
        <CardBody className="space-y-4">
          <Field
            label="URL or workspace path"
            hint="e.g. https://example.com/post or drafts/my-article.md"
          >
            <Input
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="https://example.com/article"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !analyze.loading) void submitAnalyze();
              }}
            />
          </Field>
          <Button
            variant="primary"
            loading={analyze.loading}
            onClick={submitAnalyze}
            leftIcon={<FileSearch size={15} />}
          >
            {analyze.loading ? 'Analyzing…' : 'Analyze content'}
          </Button>
          {analyze.loading && <p className="text-xs text-muted">{SLOW_HINT}</p>}
          {analyze.error && <ErrorNote message={analyze.error} onRetry={submitAnalyze} />}
          {analyzeResult && <LifecycleOutput result={analyzeResult} />}
        </CardBody>
      </Card>

      {/* 3) Priorities */}
      <Card>
        <CardHeader
          title="Content priorities"
          description="Surface the highest-impact opportunities across the workspace."
          actions={
            <Button
              variant="secondary"
              size="sm"
              loading={priorities.loading}
              onClick={submitPriorities}
              leftIcon={<ListChecks size={14} />}
            >
              {priorities.loading ? 'Loading…' : 'Get priorities'}
            </Button>
          }
        />
        <CardBody className="space-y-4">
          {priorities.error && <ErrorNote message={priorities.error} onRetry={submitPriorities} />}
          {prioritiesResult ? (
            <JsonView data={prioritiesResult} title="Priorities" />
          ) : (
            !priorities.loading &&
            !priorities.error && (
              <EmptyState
                icon={<Microscope size={22} />}
                title="No priorities yet"
                description="Run priorities to rank workspace opportunities by impact."
              />
            )
          )}
        </CardBody>
      </Card>
    </div>
  );
}

/** Render a lifecycle result: prefer markdown content, fall back to JSON. */
function LifecycleOutput({ result }: { result: LifecycleResult }) {
  const hasContent = typeof result.content === 'string' && result.content.trim().length > 0;
  return (
    <div className="space-y-3 border-t border-line pt-4">
      {result.path && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted">Saved to</span>
          <Badge tone="brand">{result.path}</Badge>
        </div>
      )}
      {hasContent ? (
        <ContentViewer content={result.content as string} />
      ) : (
        <JsonView data={result} title="Result" />
      )}
    </div>
  );
}
