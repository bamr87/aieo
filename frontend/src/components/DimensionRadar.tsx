type Dimensions = {
  aieo: number;
  seo: number;
  readability: number;
  humanity: number;
  cro: number;
};

interface DimensionRadarProps {
  dimensions: Dimensions;
}

function pointFor(value: number, angle: number, radius: number, center: number) {
  const scaled = (Math.max(0, Math.min(100, value)) / 100) * radius;
  const x = center + Math.cos(angle) * scaled;
  const y = center + Math.sin(angle) * scaled;
  return `${x},${y}`;
}

export function DimensionRadar({ dimensions }: DimensionRadarProps) {
  const labels = [
    ['AIEO', dimensions.aieo],
    ['SEO', dimensions.seo],
    ['Readability', dimensions.readability],
    ['Humanity', dimensions.humanity],
    ['CRO', dimensions.cro],
  ] as const;
  const center = 110;
  const radius = 80;
  const step = (Math.PI * 2) / labels.length;
  const points = labels
    .map(([, value], idx) => pointFor(value, -Math.PI / 2 + idx * step, radius, center))
    .join(' ');

  return (
    <div style={{ display: 'grid', placeItems: 'center', gap: 8 }}>
      <svg width={220} height={220} role="img" aria-label="content dimensions radar">
        <circle cx={center} cy={center} r={radius} fill="none" stroke="currentColor" opacity={0.2} />
        <polygon points={points} fill="rgba(100,108,255,0.25)" stroke="rgb(100,108,255)" />
      </svg>
      <div style={{ fontSize: 12 }}>
        {labels.map(([label, value]) => (
          <span key={label} style={{ marginRight: 10 }}>
            {label}: {Math.round(value)}
          </span>
        ))}
      </div>
    </div>
  );
}
