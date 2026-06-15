import { useState, type ReactNode } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { KeyRound, Menu, Settings, Sparkles, X } from 'lucide-react';
import { NAV_GROUPS } from './nav';
import { ProviderSelect } from './ProviderSelect';
import { useSettings } from '../hooks/useSettings';
import { cn } from '../lib/cn';

function KeyStatus() {
  const { hasKey } = useSettings();
  return (
    <Link
      to="/settings"
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors',
        hasKey
          ? 'border-good/30 bg-good/10 text-good hover:bg-good/15'
          : 'border-warn/40 bg-warn/10 text-warn hover:bg-warn/15',
      )}
      title={hasKey ? 'API key is set' : 'No API key — click to set one'}
    >
      <KeyRound size={13} />
      {hasKey ? 'Key set' : 'No key'}
    </Link>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <Link
        to="/"
        onClick={onNavigate}
        className="flex items-center gap-2 px-5 py-4 text-lg font-bold tracking-tight"
      >
        <span className="grid h-8 w-8 place-items-center rounded-lg brand-gradient text-white">
          <Sparkles size={18} />
        </span>
        <span className="brand-text">AIEO</span>
      </Link>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 pb-4">
        {NAV_GROUPS.map((group) => (
          <div key={group.title}>
            <p className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted/70">
              {group.title}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-brand-soft text-brand'
                        : 'text-muted hover:bg-elevated hover:text-ink',
                    )
                  }
                >
                  <item.icon size={16} className="shrink-0" />
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-line p-3">
        <NavLink
          to="/settings"
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors',
              isActive ? 'bg-brand-soft text-brand' : 'text-muted hover:bg-elevated hover:text-ink',
            )
          }
        >
          <Settings size={16} />
          Settings
        </NavLink>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[16rem_1fr]">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen border-r border-line bg-card lg:block">
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 border-r border-line bg-card">
            <SidebarContent onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-line bg-canvas/80 px-4 backdrop-blur lg:px-6">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setOpen(true)}
              className="grid h-9 w-9 place-items-center rounded-lg text-muted hover:bg-elevated hover:text-ink lg:hidden"
              aria-label="Open menu"
            >
              {open ? <X size={18} /> : <Menu size={18} />}
            </button>
            <span className="text-sm font-medium text-muted">
              {titleForPath(location.pathname)}
            </span>
          </div>
          <div className="flex items-center gap-2.5">
            <ProviderSelect className="hidden sm:flex" />
            <KeyStatus />
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 lg:px-8 lg:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}

function titleForPath(path: string): string {
  if (path === '/') return 'Home';
  if (path === '/settings') return 'Settings';
  for (const group of NAV_GROUPS) {
    const match = group.items.find((i) => i.to === path);
    if (match) return match.label;
  }
  return 'AIEO';
}
