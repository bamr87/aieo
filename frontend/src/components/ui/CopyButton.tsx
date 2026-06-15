import { useState } from 'react';
import { cn } from '../../lib/cn';

export function CopyButton({
  value,
  label = 'Copy',
  className,
}: {
  value: string;
  label?: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <button
      type="button"
      onClick={copy}
      className={cn(
        'inline-flex h-7 items-center gap-1 rounded-md border border-line bg-elevated px-2 text-xs text-muted transition-colors hover:text-ink',
        className,
      )}
    >
      {copied ? '✓ Copied' : label}
    </button>
  );
}
