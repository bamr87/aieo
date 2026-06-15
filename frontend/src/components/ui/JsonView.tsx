import { useMemo } from 'react';
import { cn } from '../../lib/cn';
import { CopyButton } from './CopyButton';

/** Pretty, scrollable JSON viewer with a copy button. */
export function JsonView({
  data,
  className,
  maxHeight = '28rem',
  title,
}: {
  data: unknown;
  className?: string;
  maxHeight?: string;
  title?: string;
}) {
  const text = useMemo(() => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  }, [data]);

  return (
    <div className={cn('overflow-hidden rounded-lg border border-line bg-canvas', className)}>
      <div className="flex items-center justify-between border-b border-line bg-elevated/50 px-3 py-1.5">
        <span className="text-[11px] font-medium uppercase tracking-wide text-muted">
          {title || 'JSON'}
        </span>
        <CopyButton value={text} />
      </div>
      <pre
        className="overflow-auto px-4 py-3 font-mono text-xs leading-relaxed text-ink/90"
        style={{ maxHeight }}
      >
        {text}
      </pre>
    </div>
  );
}
