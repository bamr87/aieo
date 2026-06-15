import { clampPct } from '../lib/format';

type Dimensions = {
  aieo: number;
  seo: number;
  readability: number;
  humanity: number;
  cro: number;
};

interface DimensionRadarProps {
  dimensions: Dimensions;
  size?: number;
}

function point(value: number, angle: number, radius: number, center: number) {
  const scaled = (clampPct(value) / 100) * radius;
  return [center + Math.cos(angle) * scaled, center + Math.sin(angle) * scaled];
}

export function DimensionRadar({ dimensions, size = 240 }: DimensionRadarProps) {
  const labels: [string, number][] = [
    ['AIEO', dimensions.aieo],
    ['SEO', dimensions.seo],
    ['Read', dimensions.readability],
    ['Human', dimensions.humanity],
    ['CRO', dimensions.cro],
  ];
  const center = size / 2;
  const radius = size / 2 - 34;
  const step = (Math.PI * 2) / labels.length;
  const angle = (i: number) => -Math.PI / 2 + i * step;

  const polygon = labels
    .map(([, v], i) => point(v, angle(i), radius, center).join(','))
    .join(' ');

  const rings = [0.25, 0.5, 0.75, 1];

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label="content dimensions radar"
      className="mx-auto"
    >
      {rings.map((r) => (
        <polygon
          key={r}
          points={labels
            .map((_, i) => point(100 * r, angle(i), radius, center).join(','))
            .join(' ')}
          fill="none"
          stroke="var(--color-line)"
          strokeWidth={1}
        />
      ))}
      {labels.map((_, i) => {
        const [x, y] = point(100, angle(i), radius, center);
        return <line key={i} x1={center} y1={center} x2={x} y2={y} stroke="var(--color-line)" strokeWidth={1} />;
      })}
      <polygon points={polygon} fill="var(--color-brand)" fillOpacity={0.22} stroke="var(--color-brand)" strokeWidth={2} />
      {labels.map(([label, v], i) => {
        const [x, y] = point(122, angle(i), radius, center);
        return (
          <text
            key={label}
            x={x}
            y={y}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={11}
            fill="var(--color-muted)"
          >
            {label} {Math.round(clampPct(v))}
          </text>
        );
      })}
    </svg>
  );
}
