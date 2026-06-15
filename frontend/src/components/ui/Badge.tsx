import type { ReactNode } from 'react';
import { cn } from '../../lib/cn';
import { gradeClasses, severityClasses } from '../../lib/format';

export function Badge({
  children,
  className,
  tone = 'neutral',
}: {
  children: ReactNode;
  className?: string;
  tone?: 'neutral' | 'brand' | 'good' | 'warn' | 'bad' | 'info';
}) {
  const tones: Record<string, string> = {
    neutral: 'border-line bg-elevated text-muted',
    brand: 'border-brand/30 bg-brand-soft text-brand',
    good: 'border-good/30 bg-good/10 text-good',
    warn: 'border-warn/30 bg-warn/10 text-warn',
    bad: 'border-bad/30 bg-bad/10 text-bad',
    info: 'border-info/30 bg-info/10 text-info',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function GradeBadge({ grade, className }: { grade: string; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex h-7 min-w-7 items-center justify-center rounded-md border px-2 text-sm font-bold',
        gradeClasses(grade),
        className,
      )}
    >
      {grade || '—'}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide',
        severityClasses(severity),
      )}
    >
      {severity}
    </span>
  );
}
