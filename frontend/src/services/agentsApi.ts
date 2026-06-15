import { apiClient } from './api';
import type { AgentRunResult, LandingAuditResult } from '../types';

export const agentsApi = {
  run: (
    agentName: string,
    content: string,
    extraInputs?: Record<string, unknown>,
    model?: string,
  ) =>
    apiClient.post<AgentRunResult>('/aieo/agent/run', {
      agent_name: agentName,
      content,
      extra_inputs: extraInputs,
      model,
    }),
  landingAudit: (content: string) =>
    apiClient.post<LandingAuditResult>('/aieo/landing/audit', { content }),
  headline: (topic: string) =>
    apiClient.post<AgentRunResult>('/aieo/agent/run', {
      agent_name: 'headline-generator',
      content: topic,
      extra_inputs: { topic },
    }),
};

/** Canonical agent list (mirrors backend/prompts/agents/*.md). */
export const AGENTS = [
  { id: 'content-analyzer', label: 'Content Analyzer' },
  { id: 'seo-optimizer', label: 'SEO Optimizer' },
  { id: 'editor', label: 'Editor' },
  { id: 'headline-generator', label: 'Headline Generator' },
  { id: 'meta-creator', label: 'Meta Creator' },
  { id: 'internal-linker', label: 'Internal Linker' },
  { id: 'keyword-mapper', label: 'Keyword Mapper' },
  { id: 'cro-analyst', label: 'CRO Analyst' },
  { id: 'landing-page-optimizer', label: 'Landing Page Optimizer' },
  { id: 'performance', label: 'Performance' },
] as const;
