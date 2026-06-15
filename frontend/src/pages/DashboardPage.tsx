import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BarChart3, Quote, RefreshCw, Settings } from 'lucide-react';
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  Loading,
  PageHeader,
  Stat,
} from '../components/ui';
import { citationsApi } from '../services';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { scoreHex, truncate } from '../lib/format';
import type { CitedPage, DashboardData } from '../types';

export function DashboardPage() {
  const { loading, error, run } = useAsyncAction();
  const [data, setData] = useState<DashboardData | null>(null);

  const load = async () => {
    const res = await run(() => citationsApi.getDashboard());
    if (res) setData(res);
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const engines = data ? Object.entries(data.citations_by_engine) : [];
  const trend = data?.citation_trend ?? [];
  const pages = data?.top_cited_pages ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Citation share-of-voice across AI engines."
        actions={
          <Button
            variant="secondary"
            size="sm"
            loading={loading}
            onClick={() => void load()}
            leftIcon={<RefreshCw size={14} />}
          >
            Refresh
          </Button>
        }
      />

      {loading && !data ? (
        <Loading />
      ) : error || !data ? (
        // The dashboard endpoint uses strict DB-backed auth (registered key + Postgres).
        // In dev it will 401 or return nothing — treat that as an expected empty state,
        // not a scary error.
        <EmptyState
          icon={<Quote size={28} />}
          title="No citation data yet"
          description="The citations dashboard needs a database-registered API key and tracked citations. See Settings."
          action={
            <Link to="/settings">
              <Button variant="primary" size="sm" leftIcon={<Settings size={14} />}>
                Open Settings
              </Button>
            </Link>
          }
        />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Stat label="Total citations" value={data.total_citations.toLocaleString()} />
            <Stat
              label="Engines"
              value={engines.length}
              sub={engines.length ? engines.map(([e]) => e).join(', ') : undefined}
            />
            <Stat label="Cited pages" value={pages.length} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <ByEngineCard engines={engines} />
            <TrendCard trend={trend} />
          </div>

          <TopPagesCard pages={pages} />
        </>
      )}
    </div>
  );
}

function ByEngineCard({ engines }: { engines: Array<[string, number]> }) {
  const sorted = [...engines].sort((a, b) => b[1] - a[1]);
  const max = sorted.reduce((m, [, n]) => Math.max(m, n), 0);

  return (
    <Card>
      <CardHeader title="By engine" description="Citations attributed to each AI engine" />
      <CardBody>
        {sorted.length === 0 ? (
          <EmptyState
            icon={<BarChart3 size={24} />}
            title="No engine breakdown"
            description="No citations have been attributed to an engine yet."
          />
        ) : (
          <div className="space-y-3">
            {sorted.map(([engine, count]) => {
              const pct = max ? (count / max) * 100 : 0;
              return (
                <div key={engine}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="font-medium capitalize text-ink">{engine}</span>
                    <span className="tabular-nums text-muted">{count.toLocaleString()}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-line">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${Math.max(pct, 2)}%`, background: 'var(--color-brand)' }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function TrendCard({ trend }: { trend: Array<{ date: string; count: number }> }) {
  return (
    <Card>
      <CardHeader title="Citation trend" description="Citations detected over time" />
      <CardBody>
        {trend.length === 0 ? (
          <EmptyState
            icon={<BarChart3 size={24} />}
            title="No trend data"
            description="Citation history will appear here once detections accumulate."
          />
        ) : (
          <TrendChart trend={trend} />
        )}
      </CardBody>
    </Card>
  );
}

/** Hand-built inline SVG bar chart — no chart library. */
function TrendChart({ trend }: { trend: Array<{ date: string; count: number }> }) {
  const max = trend.reduce((m, p) => Math.max(m, p.count), 0) || 1;
  const width = 100;
  const height = 48;
  const gap = trend.length > 1 ? 1.5 : 0;
  const barW = Math.max((width - gap * (trend.length - 1)) / trend.length, 0.5);
  // Only label a sparse subset of dates to avoid crowding.
  const labelEvery = Math.max(1, Math.ceil(trend.length / 6));
  const fmtDate = (d: string) => {
    const dt = new Date(d);
    return Number.isNaN(dt.getTime()) ? d : `${dt.getMonth() + 1}/${dt.getDate()}`;
  };
  const peak = trend.reduce((p, c) => (c.count > p.count ? c : p), trend[0]);

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between text-xs text-muted">
        <span>
          Peak <span className="font-medium text-ink">{peak.count.toLocaleString()}</span> on{' '}
          {fmtDate(peak.date)}
        </span>
        <span className="tabular-nums">{trend.length} days</span>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="h-32 w-full"
        role="img"
        aria-label="Citation trend bar chart"
      >
        {trend.map((p, i) => {
          const h = (p.count / max) * (height - 1);
          const x = i * (barW + gap);
          return (
            <rect
              key={`${p.date}-${i}`}
              x={x}
              y={height - h}
              width={barW}
              height={h}
              rx={0.5}
              fill={scoreHex((p.count / max) * 100)}
            >
              <title>
                {fmtDate(p.date)}: {p.count.toLocaleString()}
              </title>
            </rect>
          );
        })}
      </svg>
      <div className="flex justify-between text-[10px] tabular-nums text-muted">
        {trend.map((p, i) =>
          i % labelEvery === 0 || i === trend.length - 1 ? (
            <span key={`${p.date}-label-${i}`}>{fmtDate(p.date)}</span>
          ) : null,
        )}
      </div>
    </div>
  );
}

function TopPagesCard({ pages }: { pages: CitedPage[] }) {
  const sorted = [...pages].sort((a, b) => b.citation_count - a.citation_count);

  return (
    <Card>
      <CardHeader title="Top cited pages" description={`${pages.length} pages tracked`} />
      <CardBody className="space-y-2">
        {sorted.length === 0 ? (
          <EmptyState
            icon={<Quote size={24} />}
            title="No cited pages"
            description="Pages cited by AI engines will be ranked here."
          />
        ) : (
          sorted.map((page) => (
            <div
              key={page.url}
              className="flex items-center gap-3 rounded-lg border border-line bg-elevated/40 px-3 py-2"
            >
              <div className="min-w-0 flex-1">
                <a
                  href={page.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block truncate text-sm text-ink hover:text-brand"
                  title={page.url}
                >
                  {truncate(page.url.replace(/^https?:\/\//, ''), 70)}
                </a>
                {page.engines.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {page.engines.map((engine) => (
                      <Badge key={engine} tone="info" className="capitalize">
                        {engine}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              <span className="shrink-0 text-sm font-semibold tabular-nums text-ink">
                {page.citation_count.toLocaleString()}
              </span>
            </div>
          ))
        )}
      </CardBody>
    </Card>
  );
}
