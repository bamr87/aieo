import { useState } from 'react';
import { FileText, Globe, Play, Search, Target } from 'lucide-react';
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
  GradeBadge,
  Input,
  JsonView,
  PageHeader,
  ScoreRing,
  Tabs,
  Textarea,
} from '../components/ui';
import { ProviderSelect } from '../components/ProviderSelect';
import { landingApi } from '../services';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useSettings } from '../hooks/useSettings';
import { useToast } from '../hooks/useToast';
import type { LandingAuditResult, LifecycleResult } from '../types';

type TabId = 'write' | 'research' | 'competitor' | 'audit';

const TABS = [
  { id: 'write', label: 'Write' },
  { id: 'research', label: 'Research' },
  { id: 'competitor', label: 'Competitor' },
  { id: 'audit', label: 'CRO Audit' },
];

/** Pull a renderable markdown/text body out of a lifecycle result, if any. */
function lifecycleText(result: LifecycleResult): string | null {
  if (typeof result.content === 'string' && result.content.trim()) return result.content;
  return null;
}

export function LandingPagesPage() {
  const [tab, setTab] = useState<TabId>('write');

  return (
    <div className="space-y-6">
      <PageHeader
        title="Landing pages"
        description="Draft, research, study competitors, and CRO-audit landing-page content."
        actions={<ProviderSelect />}
      />

      <Tabs items={TABS} active={tab} onChange={(id) => setTab(id as TabId)} />

      {tab === 'write' && <WriteTab />}
      {tab === 'research' && <ResearchTab />}
      {tab === 'competitor' && <CompetitorTab />}
      {tab === 'audit' && <AuditTab />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Write
// ---------------------------------------------------------------------------

function WriteTab() {
  const settings = useSettings();
  const toast = useToast();
  const { loading, error, run } = useAsyncAction();
  const [topic, setTopic] = useState('');
  const [result, setResult] = useState<LifecycleResult | null>(null);

  const submit = async () => {
    if (!topic.trim()) return toast.error('Enter a topic to write about');
    const res = await run(() => landingApi.write(topic.trim(), settings.model || undefined));
    if (!res) return;
    setResult(res);
    toast.success('Landing-page draft ready');
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
      <Card className="self-start">
        <CardHeader title="Write a landing page" description="Generate a draft from a topic." />
        <CardBody className="space-y-4">
          <Field label="Topic" hint="What the landing page is about.">
            <Input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Best CRM for small agencies"
              onKeyDown={(e) => e.key === 'Enter' && submit()}
            />
          </Field>
          <Button
            variant="primary"
            fullWidth
            loading={loading}
            onClick={submit}
            leftIcon={<FileText size={15} />}
          >
            {loading ? 'Writing…' : 'Write draft'}
          </Button>
          {loading && (
            <p className="text-center text-xs text-muted">
              AI drafting runs synchronously and can take 30–90s.
            </p>
          )}
          {error && <ErrorNote message={error} onRetry={submit} />}
        </CardBody>
      </Card>

      <div className="min-w-0">
        <LifecycleResultView
          result={result}
          emptyTitle="No draft yet"
          emptyDescription="Enter a topic and write a landing-page draft to see it here."
          resultTitle="Generated landing page"
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Research
// ---------------------------------------------------------------------------

function ResearchTab() {
  const settings = useSettings();
  const toast = useToast();
  const { loading, error, run } = useAsyncAction();
  const [topic, setTopic] = useState('');
  const [result, setResult] = useState<LifecycleResult | null>(null);

  const submit = async () => {
    if (!topic.trim()) return toast.error('Enter a topic to research');
    const res = await run(() => landingApi.research(topic.trim(), settings.model || undefined));
    if (!res) return;
    setResult(res);
    toast.success('Research ready');
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
      <Card className="self-start">
        <CardHeader
          title="Research a topic"
          description="Gather angles, intent, and proof points for a landing page."
        />
        <CardBody className="space-y-4">
          <Field label="Topic" hint="Subject to research for the landing page.">
            <Input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Project management software for remote teams"
              onKeyDown={(e) => e.key === 'Enter' && submit()}
            />
          </Field>
          <Button
            variant="primary"
            fullWidth
            loading={loading}
            onClick={submit}
            leftIcon={<Search size={15} />}
          >
            {loading ? 'Researching…' : 'Research topic'}
          </Button>
          {loading && (
            <p className="text-center text-xs text-muted">
              AI research runs synchronously and can take 30–90s.
            </p>
          )}
          {error && <ErrorNote message={error} onRetry={submit} />}
        </CardBody>
      </Card>

      <div className="min-w-0">
        <LifecycleResultView
          result={result}
          emptyTitle="No research yet"
          emptyDescription="Enter a topic and run research to see the findings here."
          resultTitle="Research findings"
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Competitor
// ---------------------------------------------------------------------------

function CompetitorTab() {
  const settings = useSettings();
  const toast = useToast();
  const { loading, error, run } = useAsyncAction();
  const [url, setUrl] = useState('');
  const [result, setResult] = useState<LifecycleResult | null>(null);

  const submit = async () => {
    if (!url.trim()) return toast.error('Enter a competitor URL');
    const res = await run(() => landingApi.competitor(url.trim(), settings.model || undefined));
    if (!res) return;
    setResult(res);
    toast.success('Competitor analysis ready');
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
      <Card className="self-start">
        <CardHeader
          title="Analyze a competitor"
          description="Break down a competitor's landing page for ideas and gaps."
        />
        <CardBody className="space-y-4">
          <Field label="Competitor URL" hint="The server fetches and analyzes the live page.">
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://competitor.com/landing"
              onKeyDown={(e) => e.key === 'Enter' && submit()}
            />
          </Field>
          <Button
            variant="primary"
            fullWidth
            loading={loading}
            onClick={submit}
            leftIcon={<Globe size={15} />}
          >
            {loading ? 'Analyzing…' : 'Analyze competitor'}
          </Button>
          {loading && (
            <p className="text-center text-xs text-muted">
              Fetching and analyzing the page can take 30–90s.
            </p>
          )}
          {error && <ErrorNote message={error} onRetry={submit} />}
        </CardBody>
      </Card>

      <div className="min-w-0">
        <LifecycleResultView
          result={result}
          emptyTitle="No analysis yet"
          emptyDescription="Enter a competitor URL and run the analysis to see it here."
          resultTitle="Competitor analysis"
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CRO Audit
// ---------------------------------------------------------------------------

function AuditTab() {
  const toast = useToast();
  const { loading, error, run } = useAsyncAction();
  const [content, setContent] = useState('');
  const [result, setResult] = useState<LandingAuditResult | null>(null);

  const submit = async () => {
    if (!content.trim()) return toast.error('Paste landing-page content to audit');
    const res = await run(() => landingApi.audit(content));
    if (!res) return;
    setResult(res);
    if (typeof res.score === 'number') {
      toast.success(`CRO score ${res.score}/100${res.grade ? ` (${res.grade})` : ''}`);
    } else {
      toast.success('CRO audit complete');
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
      <Card className="self-start">
        <CardHeader
          title="CRO audit"
          description="Score landing-page content for conversion-rate optimization."
        />
        <CardBody className="space-y-4">
          <Field label="Landing-page content" hint="Markdown, HTML, or plain copy.">
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={14}
              placeholder="# Headline&#10;&#10;Your value proposition, CTAs, social proof…"
            />
          </Field>
          <Button
            variant="primary"
            fullWidth
            loading={loading}
            onClick={submit}
            leftIcon={<Target size={15} />}
          >
            {loading ? 'Auditing…' : 'Run CRO audit'}
          </Button>
          {loading && (
            <p className="text-center text-xs text-muted">
              AI auditing runs synchronously and can take 30–90s.
            </p>
          )}
          {error && <ErrorNote message={error} onRetry={submit} />}
        </CardBody>
      </Card>

      <div className="min-w-0 space-y-6">
        {result ? (
          <AuditResultView result={result} />
        ) : (
          <Card>
            <CardBody className="flex flex-col items-center justify-center gap-2 py-20 text-center text-muted">
              <ScoreRing score={0} label="CRO" />
              <p className="text-sm">Paste content and run a CRO audit to see the score.</p>
            </CardBody>
          </Card>
        )}
      </div>
    </div>
  );
}

function AuditResultView({ result }: { result: LandingAuditResult }) {
  const hasScore = typeof result.score === 'number';
  return (
    <>
      {hasScore && (
        <Card>
          <CardBody className="flex flex-col gap-6 sm:flex-row sm:items-center">
            <ScoreRing
              score={result.score as number}
              label="CRO"
              sublabel={result.grade ? `Grade ${result.grade}` : undefined}
            />
            <div className="flex flex-wrap items-center gap-2">
              {result.grade && <GradeBadge grade={result.grade} />}
              <Badge tone="info">Conversion audit</Badge>
            </div>
          </CardBody>
        </Card>
      )}
      <Card>
        <CardHeader title="CRO audit result" />
        <CardBody>
          <JsonView data={result} />
        </CardBody>
      </Card>
    </>
  );
}

// ---------------------------------------------------------------------------
// Shared lifecycle result panel (write / research / competitor)
// ---------------------------------------------------------------------------

function LifecycleResultView({
  result,
  emptyTitle,
  emptyDescription,
  resultTitle,
}: {
  result: LifecycleResult | null;
  emptyTitle: string;
  emptyDescription: string;
  resultTitle: string;
}) {
  if (!result) {
    return (
      <Card>
        <CardBody className="py-16">
          <EmptyState icon={<Play size={22} />} title={emptyTitle} description={emptyDescription} />
        </CardBody>
      </Card>
    );
  }

  const text = lifecycleText(result);
  return (
    <Card>
      <CardHeader
        title={resultTitle}
        description={typeof result.path === 'string' ? result.path : undefined}
      />
      <CardBody>{text ? <ContentViewer content={text} /> : <JsonView data={result} />}</CardBody>
    </Card>
  );
}
