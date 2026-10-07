import { useEffect, useRef } from 'react';

/**
 * Run `callback` once, when the component mounts.
 *
 * Pages use this to start their initial data load. The load sets state after an
 * awaited request, which is the pattern React's docs allow for fetching on
 * mount. `react-hooks/set-state-in-effect` cannot tell that apart from a
 * synchronous setState cascade when an effect calls a local loader directly, so
 * the one mount effect lives here. That also removes the
 * `react-hooks/exhaustive-deps` suppression every page used to carry.
 */
export function useOnMount(callback: () => void) {
  const first = useRef(callback);
  useEffect(() => {
    first.current();
  }, []);
}
