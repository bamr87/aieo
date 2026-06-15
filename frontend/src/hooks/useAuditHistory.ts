import { useCallback, useEffect, useState } from 'react';
import type { AuditHistoryEntry, AuditResult } from '../types';

const KEY = 'aieo_audit_history';
const MAX = 50;
const EVENT = 'aieo:history';

function load(): AuditHistoryEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as AuditHistoryEntry[]) : [];
  } catch {
    return [];
  }
}

function save(entries: AuditHistoryEntry[]) {
  localStorage.setItem(KEY, JSON.stringify(entries.slice(0, MAX)));
  window.dispatchEvent(new Event(EVENT));
}

/** Client-side history of audits run, persisted in localStorage. */
export function useAuditHistory() {
  const [entries, setEntries] = useState<AuditHistoryEntry[]>(load);

  useEffect(() => {
    const sync = () => setEntries(load());
    window.addEventListener(EVENT, sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener('storage', sync);
    };
  }, []);

  const add = useCallback(
    (params: { label: string; source: 'url' | 'content'; result: AuditResult }) => {
      const entry: AuditHistoryEntry = {
        id: `${Date.now()}-${Math.round(performance.now())}`,
        at: Date.now(),
        label: params.label,
        source: params.source,
        score: params.result.score,
        grade: params.result.grade,
        scoring_method: params.result.scoring_method,
        provider: params.result.provider,
        result: params.result,
      };
      save([entry, ...load()]);
    },
    [],
  );

  const remove = useCallback((id: string) => {
    save(load().filter((e) => e.id !== id));
  }, []);

  const clear = useCallback(() => save([]), []);

  return { entries, add, remove, clear };
}
