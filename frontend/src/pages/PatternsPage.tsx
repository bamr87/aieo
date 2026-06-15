import { useEffect, useMemo, useState } from 'react';
import { Layers, Sparkles, TrendingUp } from 'lucide-react';
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
  Textarea,
} from '../components/ui';
import { patternsApi } from '../services';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useToast } from '../hooks/useToast';
import type { ApplyPatternResult, Pattern } from '../types';

export function PatternsPage() {
  const toast = useToast();
  const list = useAsyncAction();
  const apply = useAsyncAction();

  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [content, setContent] = useState('');
  const [patternId, setPatternId] = useState('');
  const [result, setResult] = useState<ApplyPatternResult | null>(null);

  const load = async () => {
    const res = await list.run(() => patternsApi.listPatterns());
    if (!res) return;
    const next = res.patterns ?? [];
    setPatterns(next);
    setPatternId((prev) => prev || next[0]?.id || '');
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selected = useMemo(
    () => patterns.find((p) => p.id === patternId) ?? null,
    [patterns, patternId],
  );

  const applyPattern = async () => {
    if (!patternId) return toast.error('Pick a pattern first');
    if (!content.trim()) return toast.error('Paste some content to apply the pattern to');
    const res = await apply.run(() => patternsApi.applyPattern(patternId, content));
    if (!res) return;
    setResult(res);
    toast.success(`Applied ${res.pattern_name || res.pattern_id}`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Patterns"
        description="Browse the AIEO pattern library and preview applying a pattern to your content."
      />

      {/* Library */}
      <Card>
        <CardHeader
          title="Pattern library"
          description={patterns.length > 0 ? `${patterns.length} patterns available` : undefined}
        />
        <CardBody>
          {list.loading ? (
            <Loading />
          ) : list.error ? (
            <ErrorNote message={list.error} onRetry={load} />
          ) : patterns.length === 0 ? (
            <EmptyState
              icon={<Layers size={28} />}
              title="No patterns found"
              description="The pattern library is empty or could not be loaded."
              action={
                <Button variant="secondary" size="sm" onClick={load}>
                  Reload
                </Button>
              }
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {patterns.map((p) => (
                <PatternCard key={p.id} pattern={p} />
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Apply */}
      <Card>
        <CardHeader
          title="Apply a pattern"
          description="Run a single pattern against pasted content."
        />
        <CardBody className="space-y-4">
          <Field label="Content" hint="Markdown or plain text">
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={10}
              placeholder="# Paste the content you want to apply a pattern to…"
            />
          </Field>
          <Field label="Pattern" className="max-w-sm">
            <Select
              value={patternId}
              onChange={(e) => setPatternId(e.target.value)}
              disabled={patterns.length === 0}
            >
              {patterns.length === 0 && <option value="">No patterns loaded</option>}
              {patterns.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </Select>
          </Field>
          {selected?.description && <p className="text-xs text-muted">{selected.description}</p>}
          <Button
            variant="primary"
            loading={apply.loading}
            disabled={patterns.length === 0}
            onClick={applyPattern}
            leftIcon={<Sparkles size={15} />}
          >
            Apply pattern
          </Button>
          <p className="text-xs text-muted">
            Pattern application is a preview stub on the backend; output may equal input.
          </p>
          {apply.error && <ErrorNote message={apply.error} onRetry={applyPattern} />}

          {result && (
            <div className="space-y-3 border-t border-line pt-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="brand">{result.pattern_name || result.pattern_id}</Badge>
                <span className="text-xs text-muted">Preview output</span>
              </div>
              <ContentViewer content={result.optimized_content || ''} />
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

function PatternCard({ pattern }: { pattern: Pattern }) {
  const boost = pattern.citation_boost;
  return (
    <div className="flex h-full flex-col gap-2 rounded-lg border border-line bg-elevated/40 p-4">
      <div className="flex items-start justify-between gap-2">
        <h3 className="min-w-0 text-sm font-medium text-ink">{pattern.name}</h3>
        {pattern.category && <Badge tone="neutral">{pattern.category}</Badge>}
      </div>
      {pattern.description && (
        <p className="flex-1 text-xs leading-relaxed text-muted">{pattern.description}</p>
      )}
      {boost && (
        <Badge tone="good" className="mt-auto inline-flex w-fit items-center gap-1">
          <TrendingUp size={12} />+{boost.min}–{boost.max}% citation boost
        </Badge>
      )}
    </div>
  );
}
