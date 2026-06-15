import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { BarChart3, Globe, LineChart, Search, TrendingUp } from 'lucide-react';
import {
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
  Stat,
} from '../components/ui';
import { dataApi, researchApi } from '../services';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useToast } from '../hooks/useToast';
import { truncate } from '../lib/format';
import type { DataResult } from '../types';

type RowObject = Record<string, unknown>;

/** Detect a non-empty array whose entries are all plain objects (table-able). */
function isArrayOfObjects(value: unknown): value is RowObject[] {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every(
      (item) => typeof item === 'object' && item !== null && !Array.isArray(item),
    )
  );
}

/** Pull the most likely array payload out of a DataResult-shaped wrapper. */
function extractRows(data: unknown): RowObject[] | null {
  if (isArrayOfObjects(data)) return data;
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    for (const candidate of Object.values(data as RowObject)) {
      if (isArrayOfObjects(candidate)) return candidate;
    }
  }
  return null;
}

/** True when the result is effectively empty (null, [], or {}). */
function isEmptyResult(data: unknown): boolean {
  if (data == null) return true;
  if (Array.isArray(data)) return data.length === 0;
  if (typeof data === 'object') return Object.keys(data as RowObject).length === 0;
  return false;
}

function countOf(data: unknown): number | null {
  const rows = extractRows(data);
  if (rows) return rows.length;
  if (Array.isArray(data)) return data.length;
  return null;
}

function statValue(data: unknown): ReactNode {
  if (isEmptyResult(data)) return '—';
  const n = countOf(data);
  return n != null ? n : '✓';
}

function cellText(value: unknown): string {
  if (value == null) return '—';
  if (typeof value === 'number') return value.toLocaleString();
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'object') {
    try {
      return truncate(JSON.stringify(value), 60);
    } catch {
      return String(value);
    }
  }
  return truncate(String(value), 80);
}

export function PerformancePage() {
  const toast = useToast();

  const gaAction = useAsyncAction();
  const gscAction = useAsyncAction();
  const prioritiesAction = useAsyncAction();
  const serpAction = useAsyncAction();

  const [gaData, setGaData] = useState<DataResult | null>(null);
  const [gscData, setGscData] = useState<DataResult | null>(null);
  const [priorities, setPriorities] = useState<Record<string, unknown> | null>(null);
  const [serp, setSerp] = useState<DataResult | null>(null);

  const [keyword, setKeyword] = useState('');

  const loadGa = async () => {
    const res = await gaAction.run(() => dataApi.gaTopPages());
    if (res !== undefined) setGaData(res);
  };
  const loadGsc = async () => {
    const res = await gscAction.run(() => dataApi.gscQueries());
    if (res !== undefined) setGscData(res);
  };
  const loadPriorities = async () => {
    const res = await prioritiesAction.run(() => researchApi.priorities());
    if (res !== undefined) setPriorities(res);
  };

  useEffect(() => {
    void loadGa();
    void loadGsc();
    void loadPriorities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runSerp = async () => {
    const kw = keyword.trim();
    if (!kw) return toast.error('Enter a keyword to look up SERP data');
    const res = await serpAction.run(() => dataApi.dfsSerp(kw));
    if (res === undefined) return;
    setSerp(res);
    const rows = extractRows(res);
    toast.success(rows ? `${rows.length} SERP results for “${kw}”` : `SERP data for “${kw}”`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Performance"
        description="Live analytics from GA4, Google Search Console, and DataForSEO, plus content priorities."
      />

      <Card>
        <CardBody className="flex items-start gap-3 text-sm text-muted">
          <Globe size={18} className="mt-0.5 shrink-0 text-info" />
          <p>
            GA4, Search Console, and DataForSEO require credentials in the backend{' '}
            <code className="rounded bg-elevated px-1 py-0.5 text-xs text-ink">.env</code>. When a
            connector is unconfigured the matching card below has nothing to display — that is
            expected, not a failure.
          </p>
        </CardBody>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="GA4 top pages" value={statValue(gaData)} sub="Most-visited pages" />
        <Stat label="GSC queries" value={statValue(gscData)} sub="Search queries" />
        <Stat label="Priorities" value={statValue(priorities)} sub="Recommended next moves" />
      </div>

      <DataCard
        title="GA4 top pages"
        description="Most-visited pages from Google Analytics 4"
        icon={<BarChart3 size={26} />}
        loading={gaAction.loading}
        error={gaAction.error}
        data={gaData}
        emptyTitle="No GA4 data"
        emptyHint="Set GA4 credentials in the backend .env, then reload."
        onRetry={loadGa}
      />

      <DataCard
        title="Search Console queries"
        description="Top search queries driving impressions and clicks"
        icon={<Search size={26} />}
        loading={gscAction.loading}
        error={gscAction.error}
        data={gscData}
        emptyTitle="No Search Console data"
        emptyHint="Connect Google Search Console in the backend .env, then reload."
        onRetry={loadGsc}
      />

      <DataCard
        title="Content priorities"
        description="Recommended next actions from your workspace and analytics"
        icon={<TrendingUp size={26} />}
        loading={prioritiesAction.loading}
        error={prioritiesAction.error}
        data={priorities}
        emptyTitle="No priorities yet"
        emptyHint="Priorities derive from connected analytics and your workspace audits."
        onRetry={loadPriorities}
      />

      <Card>
        <CardHeader
          title="DataForSEO — SERP lookup"
          description="Inspect live search-engine results for a keyword"
        />
        <CardBody className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <Field label="Keyword" className="flex-1" hint="e.g. “ai engine optimization”">
              <Input
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void runSerp();
                }}
                placeholder="Enter a keyword…"
              />
            </Field>
            <Button
              variant="primary"
              loading={serpAction.loading}
              onClick={runSerp}
              leftIcon={<Search size={15} />}
            >
              Search
            </Button>
          </div>

          {serpAction.error && <ErrorNote message={serpAction.error} onRetry={runSerp} />}

          {serpAction.loading ? (
            <Loading />
          ) : serp ? (
            <DataResultBody
              data={serp}
              title="SERP results"
              emptyTitle="No SERP results"
              emptyHint="DataForSEO returned nothing — check the keyword and your DataForSEO credentials."
            />
          ) : (
            !serpAction.error && (
              <EmptyState
                icon={<LineChart size={26} />}
                title="Run a SERP lookup"
                description="Enter a keyword above to fetch live search results via DataForSEO."
              />
            )
          )}
        </CardBody>
      </Card>
    </div>
  );
}

function DataCard({
  title,
  description,
  icon,
  loading,
  error,
  data,
  emptyTitle,
  emptyHint,
  onRetry,
}: {
  title: string;
  description: string;
  icon: ReactNode;
  loading: boolean;
  error: string | null;
  data: unknown;
  emptyTitle: string;
  emptyHint: string;
  onRetry: () => void;
}) {
  return (
    <Card>
      <CardHeader title={title} description={description} />
      <CardBody>
        {loading ? (
          <Loading />
        ) : error ? (
          <ErrorNote message={error} onRetry={onRetry} />
        ) : (
          <DataResultBody
            data={data}
            title={title}
            emptyTitle={emptyTitle}
            emptyHint={emptyHint}
            emptyIcon={icon}
          />
        )}
      </CardBody>
    </Card>
  );
}

/** Render a DataResult as a table (array-of-objects) or JSON, with an EmptyState fallback. */
function DataResultBody({
  data,
  title,
  emptyTitle,
  emptyHint,
  emptyIcon,
}: {
  data: unknown;
  title: string;
  emptyTitle: string;
  emptyHint: string;
  emptyIcon?: ReactNode;
}) {
  if (isEmptyResult(data)) {
    return <EmptyState icon={emptyIcon} title={emptyTitle} description={emptyHint} />;
  }

  const rows = extractRows(data);
  if (rows) return <DataTable rows={rows} />;

  return <JsonView data={data} title={title} />;
}

/** Clean table from an array of objects: union of keys as headers, first ~10 rows. */
function DataTable({ rows }: { rows: RowObject[] }) {
  const visible = rows.slice(0, 10);
  const headers = Array.from(
    visible.reduce<Set<string>>((set, row) => {
      Object.keys(row).forEach((k) => set.add(k));
      return set;
    }, new Set<string>()),
  );

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto rounded-lg border border-line">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-line bg-elevated/50 text-left">
              {headers.map((h) => (
                <th
                  key={h}
                  className="whitespace-nowrap px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted"
                >
                  {h.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((row, i) => (
              <tr key={i} className="border-b border-line/60 last:border-0 hover:bg-elevated/30">
                {headers.map((h) => (
                  <td key={h} className="whitespace-nowrap px-3 py-2 text-ink/90">
                    {cellText(row[h])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > visible.length && (
        <p className="text-xs text-muted">
          Showing {visible.length} of {rows.length} rows.
        </p>
      )}
    </div>
  );
}
