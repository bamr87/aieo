import type { ReactNode } from 'react';
import { cn } from '../../lib/cn';

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-line px-6 py-14 text-center',
        className,
      )}
    >
      {icon && <div className="text-3xl opacity-70">{icon}</div>}
      <div>
        <p className="text-sm font-medium text-ink">{title}</p>
        {description && <p className="mx-auto mt-1 max-w-sm text-xs text-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}

/** Inline error panel for a failed load/action. */
export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-bad/30 bg-bad/10 px-4 py-3 text-sm text-bad">
      <span className="flex items-center gap-2">
        <span aria-hidden>⚠</span>
        {message}
      </span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-md border border-bad/40 px-2 py-1 text-xs font-medium hover:bg-bad/15"
        >
          Retry
        </button>
      )}
    </div>
  );
}
