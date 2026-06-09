import { useState } from 'react';
import { apiClient } from '../services/api';

export function LandingPagesPage() {
  const [topic, setTopic] = useState('');
  const [content, setContent] = useState('');
  const [output, setOutput] = useState('');

  return (
    <div style={{ textAlign: 'left' }}>
      <h1>Landing Pages</h1>
      <p>Run landing write, audit, research, and competitor workflows.</p>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Landing topic" />
        <button
          onClick={async () => {
            const out = await apiClient.post('/aieo/landing/write', { topic });
            setOutput(JSON.stringify(out, null, 2));
          }}
        >
          Write
        </button>
        <button
          onClick={async () => {
            const out = await apiClient.post('/aieo/landing/research', { topic });
            setOutput(JSON.stringify(out, null, 2));
          }}
        >
          Research
        </button>
        <button
          onClick={async () => {
            const out = await apiClient.post('/aieo/landing/competitor', { url: topic });
            setOutput(JSON.stringify(out, null, 2));
          }}
        >
          Competitor
        </button>
      </div>
      <textarea
        rows={10}
        style={{ width: '100%' }}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Paste landing page content for CRO audit"
      />
      <button
        onClick={async () => {
          const out = await apiClient.post('/aieo/landing/audit', { content });
          setOutput(JSON.stringify(out, null, 2));
        }}
      >
        Audit content
      </button>
      <pre>{output}</pre>
    </div>
  );
}
