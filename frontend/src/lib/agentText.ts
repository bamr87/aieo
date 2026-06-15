/**
 * Extract human-readable text from an agent-run response.
 *
 * The backend `/aieo/agent/run` returns an envelope `{ agent, result }` where
 * `result` is the parsed AI output (or `{ raw_output: "<text>" }` when the model
 * didn't return JSON). The readable text therefore lives under `result`, not at
 * the top level. Returns null when there's no plain-text payload (structured
 * agents like keyword-mapper) so callers can fall back to a JSON view.
 */
export function agentResultText(output: unknown): string | null {
  if (typeof output === 'string') return output;
  const obj = output as Record<string, unknown> | null;
  if (!obj || typeof obj !== 'object') return null;

  // Unwrap the { agent, result } envelope when present.
  const inner = 'result' in obj ? obj.result : obj;

  const pick = (o: unknown): string | null => {
    if (typeof o === 'string') return o;
    const r = o as Record<string, unknown> | null;
    if (!r || typeof r !== 'object') return null;
    if (typeof r.output === 'string') return r.output;
    if (typeof r.content === 'string') return r.content;
    if (typeof r.raw_output === 'string') return r.raw_output;
    if (typeof r.text === 'string') return r.text;
    return null;
  };

  return pick(inner) ?? pick(obj);
}
