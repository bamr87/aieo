import { Select } from './ui/Field';
import { PROVIDERS, useSettings } from '../hooks/useSettings';
import { cn } from '../lib/cn';

/**
 * Bound dropdown for choosing the scoring/AI provider (incl. Claude Code OAuth).
 * Persists via useSettings; pages pass `settings.providerParam` to the API.
 */
export function ProviderSelect({ className, label = true }: { className?: string; label?: boolean }) {
  const { provider, setProvider } = useSettings();
  return (
    <label className={cn('flex items-center gap-2 text-xs text-muted', className)}>
      {label && <span className="whitespace-nowrap">Provider</span>}
      <Select
        value={provider}
        onChange={(e) => setProvider(e.target.value as typeof provider)}
        className="h-8 w-auto py-0 text-xs"
        title="Which engine scores/optimizes content"
      >
        {PROVIDERS.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
      </Select>
    </label>
  );
}
