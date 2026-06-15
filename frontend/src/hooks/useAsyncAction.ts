import { useCallback, useRef, useState } from 'react';
import { errorMessage } from '../lib/format';

interface RunOptions {
  /** Suppress setting the shared error state (e.g. handled inline). */
  silent?: boolean;
}

/**
 * Tracks loading/error for an async action. `run(thunk)` resolves to the value
 * on success or `undefined` on failure (error is captured, not thrown), so call
 * sites can `const res = await run(...); if (!res) return;` without try/catch.
 */
export function useAsyncAction() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  const run = useCallback(
    async <T>(thunk: () => Promise<T>, options: RunOptions = {}): Promise<T | undefined> => {
      setLoading(true);
      if (!options.silent) setError(null);
      try {
        const result = await thunk();
        return result;
      } catch (err) {
        if (!options.silent) setError(errorMessage(err));
        else throw err;
        return undefined;
      } finally {
        if (mounted.current) setLoading(false);
      }
    },
    [],
  );

  const reset = useCallback(() => setError(null), []);

  return { loading, error, run, reset, setError };
}
