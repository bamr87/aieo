import { clampPct, scoreHex } from '../../lib/format';

interface ScoreRingProps {
  score: number;
  size?: number;
  label?: string;
  sublabel?: string;
}

/** Circular 0–100 score gauge. */
export function ScoreRing({ score, size = 132, label, sublabel }: ScoreRingProps) {
  const pct = clampPct(score);
  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  const color = scoreHex(pct);

  return (
    <div className="inline-flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="var(--color-line)"
            strokeWidth={stroke}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeDasharray={c}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 600ms ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold tabular-nums" style={{ color }}>
            {Math.round(pct)}
          </span>
          {label && <span className="text-[11px] uppercase tracking-wide text-muted">{label}</span>}
        </div>
      </div>
      {sublabel && <span className="text-xs text-muted">{sublabel}</span>}
    </div>
  );
}

/** Horizontal labeled meter for a single 0–100 dimension. */
export function Meter({ label, value }: { label: string; value: number }) {
  const pct = clampPct(value);
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className="font-medium tabular-nums" style={{ color: scoreHex(pct) }}>
          {Math.round(pct)}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-line">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, background: scoreHex(pct) }}
        />
      </div>
    </div>
  );
}
