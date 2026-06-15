import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '../../lib/cn';
import { CopyButton } from './CopyButton';

const PROSE = cn(
  'text-sm leading-relaxed text-ink/90',
  '[&_h1]:mb-3 [&_h1]:mt-5 [&_h1]:text-xl [&_h1]:font-semibold [&_h1]:text-ink',
  '[&_h2]:mb-2 [&_h2]:mt-5 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-ink',
  '[&_h3]:mb-2 [&_h3]:mt-4 [&_h3]:text-base [&_h3]:font-semibold [&_h3]:text-ink',
  '[&_p]:my-3',
  '[&_ul]:my-3 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-3 [&_ol]:list-decimal [&_ol]:pl-5',
  '[&_li]:my-1 [&_li]:marker:text-muted',
  '[&_a]:text-brand [&_a]:underline [&_a]:underline-offset-2',
  '[&_strong]:font-semibold [&_strong]:text-ink',
  '[&_code]:rounded [&_code]:bg-elevated [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-xs',
  '[&_pre]:my-3 [&_pre]:overflow-auto [&_pre]:rounded-lg [&_pre]:border [&_pre]:border-line [&_pre]:bg-canvas [&_pre]:p-3',
  '[&_pre_code]:bg-transparent [&_pre_code]:p-0',
  '[&_blockquote]:my-3 [&_blockquote]:border-l-2 [&_blockquote]:border-brand/50 [&_blockquote]:pl-3 [&_blockquote]:text-muted',
  '[&_table]:my-3 [&_table]:w-full [&_table]:border-collapse [&_table]:text-xs',
  '[&_th]:border [&_th]:border-line [&_th]:bg-elevated [&_th]:px-2 [&_th]:py-1 [&_th]:text-left',
  '[&_td]:border [&_td]:border-line [&_td]:px-2 [&_td]:py-1',
  '[&_hr]:my-4 [&_hr]:border-line',
);

export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn(PROSE, className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}

/**
 * Viewer for generated content: toggles between rendered markdown and raw
 * source, with a copy button. Used by Optimize/Drafts/Rewrites/Research etc.
 */
export function ContentViewer({
  content,
  className,
  maxHeight = '32rem',
  defaultView = 'rendered',
}: {
  content: string;
  className?: string;
  maxHeight?: string;
  defaultView?: 'rendered' | 'source';
}) {
  const [view, setView] = useState<'rendered' | 'source'>(defaultView);

  return (
    <div className={cn('overflow-hidden rounded-lg border border-line bg-card', className)}>
      <div className="flex items-center justify-between border-b border-line bg-elevated/50 px-3 py-1.5">
        <div className="flex gap-1">
          {(['rendered', 'source'] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={cn(
                'rounded px-2 py-0.5 text-[11px] font-medium capitalize transition-colors',
                view === v ? 'bg-brand-soft text-brand' : 'text-muted hover:text-ink',
              )}
            >
              {v}
            </button>
          ))}
        </div>
        <CopyButton value={content} />
      </div>
      <div className="overflow-auto p-4" style={{ maxHeight }}>
        {view === 'rendered' ? (
          <Markdown>{content}</Markdown>
        ) : (
          <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-ink/80">
            {content}
          </pre>
        )}
      </div>
    </div>
  );
}
