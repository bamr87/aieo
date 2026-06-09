import { useState } from 'react';
import { researchApi } from '../services/researchApi';

export function ResearchPage() {
  const [topic, setTopic] = useState('');
  const [target, setTarget] = useState('');
  const [result, setResult] = useState<string>('');

  return (
    <div style={{ textAlign: 'left' }}>
      <h1>Research</h1>
      <p>Generate briefs, analyze existing pages, and build priorities.</p>
      <div style={{ display: 'grid', gap: 10, maxWidth: 900 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic for /research" />
          <button
            onClick={async () => {
              const out = await researchApi.research(topic);
              setResult(JSON.stringify(out, null, 2));
            }}
          >
            Run research
          </button>
          <button
            onClick={async () => {
              const out = await researchApi.priorities();
              setResult(JSON.stringify(out, null, 2));
            }}
          >
            Build priorities
          </button>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="URL or workspace file path" />
          <button
            onClick={async () => {
              const out = await researchApi.analyzeExisting(target);
              setResult(JSON.stringify(out, null, 2));
            }}
          >
            Analyze existing
          </button>
        </div>
        <pre>{result}</pre>
      </div>
    </div>
  );
}
