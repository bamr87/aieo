import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles } from 'lucide-react';
import { Button } from '../components/ui';
import { NAV_GROUPS } from '../components/nav';
import { useSettings } from '../hooks/useSettings';

export function HomePage() {
  const { hasKey } = useSettings();

  return (
    <div className="space-y-10">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-2xl border border-line bg-card px-6 py-12 sm:px-10 sm:py-16">
        <div className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full brand-gradient opacity-20 blur-3xl" />
        <div className="relative max-w-2xl">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-brand/30 bg-brand-soft px-3 py-1 text-xs font-medium text-brand">
            <Sparkles size={13} /> AI Engine Optimization
          </span>
          <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
            Make your content <span className="brand-text">citable by AI engines</span>
          </h1>
          <p className="mt-3 text-base text-muted">
            Score, audit, and optimize content for citability by ChatGPT, Claude, Gemini, and
            Perplexity — then run the full lifecycle from research to publish.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/audit">
              <Button variant="primary" size="lg">
                Run an audit <ArrowRight size={16} />
              </Button>
            </Link>
            <Link to="/optimize">
              <Button variant="secondary" size="lg">
                Optimize content
              </Button>
            </Link>
          </div>
          {!hasKey && (
            <p className="mt-4 text-xs text-warn">
              Heads up: set an API key in{' '}
              <Link to="/settings" className="underline">
                Settings
              </Link>{' '}
              before calling the backend.
            </p>
          )}
        </div>
      </section>

      {/* Capability groups */}
      {NAV_GROUPS.map((group) => (
        <section key={group.title}>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
            {group.title}
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {group.items.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="group flex items-start gap-3 rounded-xl border border-line bg-card p-4 transition-colors hover:border-line-strong hover:bg-elevated"
              >
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-brand-soft text-brand">
                  <item.icon size={18} />
                </span>
                <div className="min-w-0">
                  <p className="flex items-center gap-1 text-sm font-medium text-ink">
                    {item.label}
                    <ArrowRight
                      size={13}
                      className="opacity-0 transition-opacity group-hover:opacity-100"
                    />
                  </p>
                  <p className="mt-0.5 text-xs text-muted">{item.description}</p>
                </div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
