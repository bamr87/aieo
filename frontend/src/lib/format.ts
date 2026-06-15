/** Small presentation helpers shared across pages. */

/** Tailwind text-color class for a 0–100 score. */
export function scoreColor(score: number): string {
  if (score >= 80) return 'text-good';
  if (score >= 60) return 'text-info';
  if (score >= 40) return 'text-warn';
  return 'text-bad';
}

/** Hex color for a 0–100 score (for SVG strokes etc.). */
export function scoreHex(score: number): string {
  if (score >= 80) return '#34d399';
  if (score >= 60) return '#60a5fa';
  if (score >= 40) return '#fbbf24';
  return '#f87171';
}

/** Color classes (text + bg tint + border) for a letter grade. */
export function gradeClasses(grade: string): string {
  const g = (grade || '').trim().toUpperCase();
  if (g.startsWith('A')) return 'text-good bg-good/10 border-good/30';
  if (g.startsWith('B')) return 'text-info bg-info/10 border-info/30';
  if (g.startsWith('C')) return 'text-warn bg-warn/10 border-warn/30';
  if (g.startsWith('D')) return 'text-warn bg-warn/10 border-warn/30';
  return 'text-bad bg-bad/10 border-bad/30';
}

/** Color classes for a gap/issue severity. */
export function severityClasses(severity: string): string {
  switch ((severity || '').toLowerCase()) {
    case 'high':
      return 'text-bad bg-bad/10 border-bad/30';
    case 'medium':
      return 'text-warn bg-warn/10 border-warn/30';
    default:
      return 'text-info bg-info/10 border-info/30';
  }
}

export function clampPct(n: number | undefined | null): number {
  if (typeof n !== 'number' || Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(100, n));
}

export function formatDate(value: string | number | Date): string {
  try {
    const d = new Date(value);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return String(value);
  }
}

export function slugify(input: string): string {
  return input
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80) || 'untitled';
}

export function truncate(input: string, max = 120): string {
  if (input.length <= max) return input;
  return input.slice(0, max - 1).trimEnd() + '…';
}

/** Basename of a workspace/file path. */
export function basename(path: string): string {
  const parts = path.split('/').filter(Boolean);
  return parts[parts.length - 1] || path;
}

/** Extract a human-readable error message from anything thrown by the API layer. */
export function errorMessage(err: unknown): string {
  if (!err) return 'Unknown error';
  if (typeof err === 'string') return err;
  if (err instanceof Error) return err.message;
  const anyErr = err as { error?: { message?: string }; message?: string };
  return anyErr?.error?.message || anyErr?.message || 'Something went wrong';
}
