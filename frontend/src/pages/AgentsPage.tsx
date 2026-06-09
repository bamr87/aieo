import { useState } from 'react';
import { auditApi } from '../services/api';
import { agentsApi } from '../services/agentsApi';
import { DimensionRadar } from '../components/DimensionRadar';
import type { AuditResult } from '../types';

const agentOptions = [
  'content-analyzer',
  'seo-optimizer',
  'meta-creator',
  'internal-linker',
  'keyword-mapper',
  'editor',
  'performance',
  'headline-generator',
  'cro-analyst',
  'landing-page-optimizer',
];

export function AgentsPage() {
  const [agent, setAgent] = useState(agentOptions[0]);
  const [content, setContent] = useState('');
  const [agentOutput, setAgentOutput] = useState('');
  const [audit, setAudit] = useState<AuditResult | null>(null);

  return (
    <div style={{ textAlign: 'left' }}>
      <h1>Agents</h1>
      <p>Invoke specialized agents and inspect multi-dimension scorecards.</p>
      <textarea
        rows={12}
        style={{ width: '100%' }}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Paste draft content"
      />
      <div style={{ display: 'flex', gap: 8, margin: '8px 0' }}>
        <select value={agent} onChange={(e) => setAgent(e.target.value)}>
          {agentOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <button
          onClick={async () => {
            const out = await agentsApi.run(agent, content);
            setAgentOutput(JSON.stringify(out, null, 2));
          }}
        >
          Run agent
        </button>
        <button
          onClick={async () => {
            const out = (await auditApi.audit({ content, format: 'markdown' })) as AuditResult;
            setAudit(out);
          }}
        >
          Score draft
        </button>
      </div>
      {audit?.dimensions && <DimensionRadar dimensions={audit.dimensions} />}
      {audit?.gaps && audit.gaps.length > 0 && (
        <div>
          <h3>Gaps</h3>
          <ul>
            {audit.gaps.map((gap) => (
              <li key={gap.id}>
                <strong>{gap.category}</strong>: {gap.description}{' '}
                <button
                  onClick={async () => {
                    const out = await agentsApi.run('seo-optimizer', content, { gap });
                    setAgentOutput(JSON.stringify(out, null, 2));
                  }}
                >
                  Apply fix
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <pre>{agentOutput}</pre>
    </div>
  );
}
