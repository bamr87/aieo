import { apiClient } from './api';

export const agentsApi = {
  run: (agentName: string, content: string, extraInputs?: Record<string, unknown>) =>
    apiClient.post('/aieo/agent/run', {
      agent_name: agentName,
      content,
      extra_inputs: extraInputs,
    }),
  landingAudit: (content: string) =>
    apiClient.post('/aieo/landing/audit', { content }),
  headline: (topic: string) =>
    apiClient.post('/aieo/agent/run', {
      agent_name: 'headline-generator',
      content: topic,
      extra_inputs: { topic },
    }),
};
