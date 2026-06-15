import { useState } from 'react';
import { Clock, Play, Trash2, Wand2 } from 'lucide-react';
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  ContentViewer,
  ErrorNote,
  Field,
  GradeBadge,
  Input,
  JsonView,
  Meter,
  Modal,
  PageHeader,
  ScoreRing,
  Select,
  SeverityBadge,
  Tabs,
  Textarea,
} from '../components/ui';
import { DimensionRadar } from '../components/DimensionRadar';
import { ProviderSelect } from '../components/ProviderSelect';
import { auditApi, agentsApi } from '../services';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useSettings } from '../hooks/useSettings';
import { useToast } from '../hooks/useToast';
import { useAuditHistory } from '../hooks/useAuditHistory';
import { agentResultText } from '../lib/agentText';
import { formatDate, truncate } from '../lib/format';
import type { AuditResult, Gap } from '../types';

export function AuditPage() {
  const settings = useSettings();
  const toast = useToast();
  const history = useAuditHistory();
  const { loading, error, run } = useAsyncAction();

  const [mode, setMode] = useState<'content' | 'url'>('content');
  const [content, setContent] = useState('');
  const [url, setUrl] = useState('');
  const [format, setFormat] = useState('markdown');
  const [result, setResult] = useState<AuditResult | null>(null);
  const [auditedText, setAuditedText] = useState('');

  const submit = async () => {
    if (mode === 'content' && !content.trim()) return toast.error('Paste some content first');
    if (mode === 'url' && !url.trim()) return toast.error('Enter a URL first');

    const res = await run(() =>
      auditApi.audit({
        ...(mode === 'url' ? { url: url.trim() } : { content, format }),
        provider: settings.providerParam,
        model: settings.model || undefined,
      }),
    );
    if (!res) return;
    setResult(res);
    setAuditedText(mode === 'content' ? content : '');
    history.add({
      label: mode === 'url' ? url.trim() : truncate(content.replace(/\s+/g, ' ').trim(), 60),
      source: mode,
      result: res,
    });
    toast.success(`Scored ${res.score}/100 (${res.grade})`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit"
        description="Score content for citability by AI engines and surface concrete gaps."
        actions={<ProviderSelect />}
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        {/* Input */}
        <Card className="self-start">
          <CardHeader title="Content to audit" />
          <CardBody className="space-y-4">
            <Tabs
              items={[
                { id: 'content', label: 'Paste content' },
                { id: 'url', label: 'From URL' },
              ]}
              active={mode}
              onChange={(id) => setMode(id as 'content' | 'url')}
            />
            {mode === 'content' ? (
              <>
                <Field label="Markdown or HTML">
                  <Textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="# Your article…"
                    rows={12}
                  />
                </Field>
                <Field label="Format" className="max-w-40">
                  <Select value={format} onChange={(e) => setFormat(e.target.value)}>
                    <option value="markdown">Markdown</option>
                    <option value="html">HTML</option>
                  </Select>
                </Field>
              </>
            ) : (
              <Field label="Page URL" hint="The server fetches and scores the live HTML.">
                <Input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com/article"
                />
              </Field>
            )}
            <Button variant="primary" fullWidth loading={loading} onClick={submit} leftIcon={<Play size={15} />}>
              Run audit
            </Button>
            {error && <ErrorNote message={error} onRetry={submit} />}
          </CardBody>
        </Card>

        {/* Result */}
        <div className="min-w-0 space-y-6">
          {result ? (
            <AuditResultView result={result} auditedText={auditedText} />
          ) : (
            <Card>
              <CardBody className="flex flex-col items-center justify-center gap-2 py-20 text-center text-muted">
                <ScoreRing score={0} label="score" />
                <p className="text-sm">Run an audit to see the score, dimensions, and gaps.</p>
              </CardBody>
            </Card>
          )}
        </div>
      </div>

      {/* History */}
      {history.entries.length > 0 && (
        <Card>
          <CardHeader
            title="Recent audits"
            description={`${history.entries.length} saved in this browser`}
            actions={
              <Button variant="ghost" size="sm" onClick={history.clear} leftIcon={<Trash2 size={14} />}>
                Clear
              </Button>
            }
          />
          <CardBody className="space-y-1.5">
            {history.entries.slice(0, 10).map((e) => (
              <div
                key={e.id}
                className="flex items-center gap-3 rounded-lg border border-line bg-elevated/40 px-3 py-2"
              >
                <GradeBadge grade={e.grade} />
                <button
                  className="min-w-0 flex-1 text-left"
                  onClick={() => {
                    setResult(e.result);
                    setAuditedText('');
                  }}
                >
                  <p className="truncate text-sm text-ink">{e.label}</p>
                  <p className="flex items-center gap-1 text-xs text-muted">
                    <Clock size={11} /> {formatDate(e.at)} · {e.score}/100
                    {e.scoring_method && ` · ${e.scoring_method}`}
                  </p>
                </button>
                <button
                  onClick={() => history.remove(e.id)}
                  className="text-muted hover:text-bad"
                  aria-label="Remove"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </CardBody>
        </Card>
      )}
    </div>
  );
}

function AuditResultView({ result, auditedText }: { result: AuditResult; auditedText: string }) {
  const dims = result.dimensions;
  const patterns = result.pattern_scores
    ? Object.entries(result.pattern_scores).sort(
        (a, b) => a[1].score / a[1].max - b[1].score / b[1].max,
      )
    : [];

  return (
    <>
      <Card>
        <CardBody className="flex flex-col gap-6 sm:flex-row sm:items-center">
          <ScoreRing score={result.score} label="AIEO" sublabel={`Grade ${result.grade}`} />
          <div className="min-w-0 flex-1 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <GradeBadge grade={result.grade} />
              <Badge tone={result.scoring_method === 'ai' ? 'brand' : 'neutral'}>
                {result.scoring_method === 'ai' ? 'AI scored' : 'Heuristic'}
              </Badge>
              {result.provider && <Badge tone="info">{result.provider}</Badge>}
              {typeof result.word_count === 'number' && <Badge>{result.word_count} words</Badge>}
              {result.content_type && <Badge>{result.content_type}</Badge>}
            </div>
            {(result.overall_assessment || result.executive_summary) && (
              <p className="text-sm text-muted">
                {result.overall_assessment || result.executive_summary}
              </p>
            )}
            {result.benchmark?.percentile != null && (
              <p className="text-xs text-muted">
                Benchmark percentile:{' '}
                <span className="font-medium text-ink">
                  {Math.round(result.benchmark.percentile)}
                </span>
              </p>
            )}
          </div>
        </CardBody>
      </Card>

      {dims && (
        <Card>
          <CardHeader title="Dimensions" />
          <CardBody className="grid items-center gap-6 sm:grid-cols-[auto_1fr]">
            <DimensionRadar dimensions={dims} />
            <div className="space-y-2.5">
              <Meter label="AIEO" value={dims.aieo} />
              <Meter label="SEO" value={dims.seo} />
              <Meter label="Readability" value={dims.readability} />
              <Meter label="Humanity" value={dims.humanity} />
              <Meter label="CRO" value={dims.cro} />
            </div>
          </CardBody>
        </Card>
      )}

      {patterns.length > 0 && (
        <Card>
          <CardHeader title="Pattern scores" description={`${patterns.length} patterns evaluated`} />
          <CardBody className="grid gap-3 sm:grid-cols-2">
            {patterns.map(([name, p]) => (
              <div key={name} className="rounded-lg border border-line bg-elevated/40 p-3">
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <span className="text-xs font-medium capitalize text-ink">
                    {name.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs tabular-nums text-muted">
                    {p.score}/{p.max}
                  </span>
                </div>
                <Meter label="" value={p.max ? (p.score / p.max) * 100 : 0} />
                {p.recommendation && <p className="mt-1.5 text-xs text-muted">{p.recommendation}</p>}
              </div>
            ))}
          </CardBody>
        </Card>
      )}

      <GapsCard gaps={result.gaps || []} auditedText={auditedText} />
    </>
  );
}

function GapsCard({ gaps, auditedText }: { gaps: Gap[]; auditedText: string }) {
  const toast = useToast();
  const { loading, run } = useAsyncAction();
  const [fix, setFix] = useState<{ gap: Gap; output: unknown } | null>(null);

  const applyFix = async (gap: Gap) => {
    if (!auditedText.trim()) {
      toast.error('Apply-fix needs the pasted content — re-run the audit in “Paste content” mode.');
      return;
    }
    const res = await run(() => agentsApi.run('seo-optimizer', auditedText, { gap: gap.description }));
    if (res) setFix({ gap, output: res });
  };

  if (gaps.length === 0) {
    return (
      <Card>
        <CardHeader title="Gaps" />
        <CardBody>
          <p className="text-sm text-good">No significant gaps found. 🎉</p>
        </CardBody>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader title="Gaps" description={`${gaps.length} opportunities to improve`} />
        <CardBody className="space-y-2.5">
          {gaps.map((gap) => (
            <div key={gap.id} className="rounded-lg border border-line bg-elevated/40 p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="mb-1 flex items-center gap-2">
                    <SeverityBadge severity={gap.severity} />
                    {gap.category && (
                      <span className="text-xs capitalize text-muted">{gap.category}</span>
                    )}
                  </div>
                  <p className="text-sm text-ink">{gap.description}</p>
                  {gap.recommendation && (
                    <p className="mt-1 text-xs text-muted">{gap.recommendation}</p>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="subtle"
                  leftIcon={<Wand2 size={13} />}
                  loading={loading}
                  disabled={!auditedText.trim()}
                  onClick={() => applyFix(gap)}
                  title={auditedText.trim() ? 'Run the SEO optimizer agent' : 'Re-run in paste mode to enable'}
                >
                  Fix
                </Button>
              </div>
            </div>
          ))}
        </CardBody>
      </Card>

      <Modal
        open={!!fix}
        onClose={() => setFix(null)}
        title="Suggested fix (seo-optimizer)"
        className="max-w-2xl"
      >
        {fix && <AgentOutput output={fix.output} />}
      </Modal>
    </>
  );
}

/** Render an agent run result as readable content when possible, else JSON. */
export function AgentOutput({ output }: { output: unknown }) {
  const text = agentResultText(output);
  return text ? <ContentViewer content={text} /> : <JsonView data={output} />;
}
