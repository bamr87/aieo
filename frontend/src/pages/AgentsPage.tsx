import { useState } from 'react';
import { Bot, Gauge, Play } from 'lucide-react';
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
  JsonView,
  Meter,
  PageHeader,
  ScoreRing,
  Select,
  SeverityBadge,
  Textarea,
} from '../components/ui';
import { ProviderSelect } from '../components/ProviderSelect';
import { AGENTS, agentsApi, auditApi } from '../services';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useSettings } from '../hooks/useSettings';
import { useToast } from '../hooks/useToast';
import { agentResultText } from '../lib/agentText';
import type { AuditResult } from '../types';

export function AgentsPage() {
  const settings = useSettings();
  const toast = useToast();

  const agentAction = useAsyncAction();
  const scoreAction = useAsyncAction();

  const [content, setContent] = useState('');
  const [agentId, setAgentId] = useState<string>(AGENTS[0].id);
  const [agentOutput, setAgentOutput] = useState<unknown>(null);
  const [score, setScore] = useState<AuditResult | null>(null);

  const activeAgent = AGENTS.find((a) => a.id === agentId);

  const runAgent = async () => {
    if (!content.trim()) {
      toast.error('Paste some content to run an agent on');
      return;
    }
    const res = await agentAction.run(() =>
      agentsApi.run(agentId, content, undefined, settings.model || undefined),
    );
    if (!res) {
      toast.error('Agent run failed');
      return;
    }
    setAgentOutput(res);
    toast.success(`${activeAgent?.label ?? agentId} finished`);
  };

  const quickScore = async () => {
    if (!content.trim()) {
      toast.error('Paste some content to score');
      return;
    }
    const res = await scoreAction.run(() =>
      auditApi.audit({
        content,
        provider: settings.providerParam,
        model: settings.model || undefined,
      }),
    );
    if (!res) {
      toast.error('Scoring failed');
      return;
    }
    setScore(res);
    toast.success(`Scored ${res.score}/100 (${res.grade})`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Agents"
        description="Run a specialized content agent against your draft, or get a quick citability score."
        actions={<ProviderSelect />}
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
        {/* Shared input + controls */}
        <Card className="self-start">
          <CardHeader title="Content" description="Shared by both the agent and the quick score." />
          <CardBody className="space-y-5">
            <Field label="Markdown or text">
              <Textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={14}
                placeholder="# Paste the content you want to work on…"
              />
            </Field>

            {/* Run agent */}
            <div className="space-y-3 rounded-lg border border-line bg-elevated/40 p-3">
              <div className="flex items-center gap-2">
                <Bot size={15} className="text-brand" />
                <span className="text-sm font-medium text-ink">Run agent</span>
              </div>
              <Field label="Agent">
                <Select value={agentId} onChange={(e) => setAgentId(e.target.value)}>
                  {AGENTS.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.label}
                    </option>
                  ))}
                </Select>
              </Field>
              <Button
                variant="primary"
                fullWidth
                loading={agentAction.loading}
                onClick={runAgent}
                leftIcon={<Play size={15} />}
              >
                {agentAction.loading ? 'Running…' : `Run ${activeAgent?.label ?? 'agent'}`}
              </Button>
              {agentAction.error && <ErrorNote message={agentAction.error} onRetry={runAgent} />}
            </div>

            {/* Quick score */}
            <div className="space-y-3 rounded-lg border border-line bg-elevated/40 p-3">
              <div className="flex items-center gap-2">
                <Gauge size={15} className="text-brand" />
                <span className="text-sm font-medium text-ink">Quick score</span>
              </div>
              <p className="text-xs text-muted">
                Audit the same content for citability without leaving this page.
              </p>
              <Button
                variant="secondary"
                fullWidth
                loading={scoreAction.loading}
                onClick={quickScore}
                leftIcon={<Gauge size={15} />}
              >
                {scoreAction.loading ? 'Scoring…' : 'Score content'}
              </Button>
              {scoreAction.error && <ErrorNote message={scoreAction.error} onRetry={quickScore} />}
            </div>
          </CardBody>
        </Card>

        {/* Results */}
        <div className="min-w-0 space-y-6">
          {score && <QuickScoreView result={score} />}

          <Card>
            <CardHeader
              title="Agent output"
              description={activeAgent ? activeAgent.label : undefined}
            />
            <CardBody>
              {agentAction.loading ? (
                <p className="py-10 text-center text-sm text-muted">Running the agent…</p>
              ) : agentOutput != null ? (
                <AgentOutput output={agentOutput} />
              ) : (
                <EmptyState
                  icon={<Bot size={24} />}
                  title="No agent run yet"
                  description="Pick an agent and run it to see its output here."
                />
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}

/** Render an agent run result as readable content when possible, else JSON. */
function AgentOutput({ output }: { output: unknown }) {
  const text = agentResultText(output);
  return text ? <ContentViewer content={text} /> : <JsonView data={output} title="Agent result" />;
}

/** Compact score summary mirroring the Audit visual language (inline, simplified). */
function QuickScoreView({ result }: { result: AuditResult }) {
  const dims = result.dimensions;
  const gaps = result.gaps ?? [];

  return (
    <Card>
      <CardHeader title="Quick score" />
      <CardBody className="space-y-5">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
          <ScoreRing score={result.score} label="AIEO" sublabel={`Grade ${result.grade}`} />
          <div className="min-w-0 flex-1 space-y-2.5">
            <div className="flex flex-wrap items-center gap-2">
              <GradeBadge grade={result.grade} />
              <Badge tone={result.scoring_method === 'ai' ? 'brand' : 'neutral'}>
                {result.scoring_method === 'ai' ? 'AI scored' : 'Heuristic'}
              </Badge>
              {result.provider && <Badge tone="info">{result.provider}</Badge>}
              {typeof result.word_count === 'number' && <Badge>{result.word_count} words</Badge>}
            </div>
            {(result.overall_assessment || result.executive_summary) && (
              <p className="text-sm text-muted">
                {result.overall_assessment || result.executive_summary}
              </p>
            )}
          </div>
        </div>

        {dims && (
          <div className="space-y-2.5">
            <Meter label="AIEO" value={dims.aieo} />
            <Meter label="SEO" value={dims.seo} />
            <Meter label="Readability" value={dims.readability} />
            <Meter label="Humanity" value={dims.humanity} />
            <Meter label="CRO" value={dims.cro} />
          </div>
        )}

        {gaps.length > 0 ? (
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted">
              Gaps ({gaps.length})
            </p>
            {gaps.map((gap) => (
              <div key={gap.id} className="rounded-lg border border-line bg-elevated/40 p-3">
                <div className="mb-1 flex items-center gap-2">
                  <SeverityBadge severity={gap.severity} />
                  {gap.category && <span className="text-xs capitalize text-muted">{gap.category}</span>}
                </div>
                <p className="text-sm text-ink">{gap.description}</p>
                {gap.recommendation && (
                  <p className="mt-1 text-xs text-muted">{gap.recommendation}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-good">No significant gaps found. 🎉</p>
        )}
      </CardBody>
    </Card>
  );
}
