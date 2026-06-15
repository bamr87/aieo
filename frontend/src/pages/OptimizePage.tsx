import { useState } from 'react';
import { ArrowRight, Sparkles } from 'lucide-react';
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  ContentViewer,
  ErrorNote,
  Field,
  PageHeader,
  ScoreRing,
  Select,
  Textarea,
} from '../components/ui';
import { optimizeApi } from '../services';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useSettings } from '../hooks/useSettings';
import { useToast } from '../hooks/useToast';
import type { OptimizeResult } from '../types';

export function OptimizePage() {
  const settings = useSettings();
  const toast = useToast();
  const { loading, error, run } = useAsyncAction();

  const [content, setContent] = useState('');
  const [style, setStyle] = useState<'preserve' | 'aggressive'>('preserve');
  const [mode, setMode] = useState<'enhance' | 'expand'>('enhance');
  const [result, setResult] = useState<OptimizeResult | null>(null);

  const submit = async () => {
    if (!content.trim()) return toast.error('Paste some content to optimize');
    const res = await run(() =>
      optimizeApi.optimize({
        content,
        style,
        content_mode: mode,
        model: settings.model || undefined,
      }),
    );
    if (!res) return;
    setResult(res);
    toast.success(`Score ${res.score_before} → ${res.score_after} (${res.uplift >= 0 ? '+' : ''}${res.uplift})`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Optimize"
        description="Rewrite content with AIEO patterns to raise its citability score."
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
        <Card className="self-start">
          <CardHeader title="Original content" />
          <CardBody className="space-y-4">
            <Field label="Markdown or text">
              <Textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={14}
                placeholder="# Paste the content you want to optimize…"
              />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Style" hint="How freely it may rewrite">
                <Select value={style} onChange={(e) => setStyle(e.target.value as typeof style)}>
                  <option value="preserve">Preserve voice</option>
                  <option value="aggressive">Aggressive</option>
                </Select>
              </Field>
              <Field label="Mode" hint="Enhance edits; expand adds depth">
                <Select value={mode} onChange={(e) => setMode(e.target.value as typeof mode)}>
                  <option value="enhance">Enhance</option>
                  <option value="expand">Expand</option>
                </Select>
              </Field>
            </div>
            <Button
              variant="primary"
              fullWidth
              loading={loading}
              onClick={submit}
              leftIcon={<Sparkles size={15} />}
            >
              {loading ? 'Optimizing…' : 'Optimize'}
            </Button>
            {loading && (
              <p className="text-center text-xs text-muted">
                AI rewrites run synchronously and can take 30–90s.
              </p>
            )}
            {error && <ErrorNote message={error} onRetry={submit} />}
          </CardBody>
        </Card>

        <div className="min-w-0 space-y-6">
          {result ? (
            <OptimizeResultView result={result} />
          ) : (
            <Card>
              <CardBody className="py-20 text-center text-sm text-muted">
                Optimized content and the before/after score will appear here.
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function OptimizeResultView({ result }: { result: OptimizeResult }) {
  const uplift = result.uplift ?? result.score_after - result.score_before;
  return (
    <>
      <Card>
        <CardBody className="flex flex-wrap items-center justify-center gap-6">
          <ScoreRing score={result.score_before} label="before" size={108} />
          <ArrowRight className="text-muted" />
          <ScoreRing score={result.score_after} label="after" size={108} />
          <Badge tone={uplift > 0 ? 'good' : uplift < 0 ? 'bad' : 'neutral'} className="text-sm">
            {uplift >= 0 ? '+' : ''}
            {uplift} points
          </Badge>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Optimized content" />
        <CardBody>
          <ContentViewer content={result.optimized_content || ''} />
        </CardBody>
      </Card>

      {result.changes && result.changes.length > 0 && (
        <Card>
          <CardHeader title="Changes" description={`${result.changes.length} applied`} />
          <CardBody className="space-y-2">
            {result.changes.map((c, i) => (
              <div key={i} className="flex items-start gap-2 rounded-lg border border-line bg-elevated/40 p-3">
                <Badge tone="brand">{c.type}</Badge>
                <p className="text-sm text-ink">{c.description}</p>
              </div>
            ))}
          </CardBody>
        </Card>
      )}
    </>
  );
}
