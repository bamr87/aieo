/* eslint-disable react-refresh/only-export-components -- context provider co-located with its hook and constants */
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { apiClient } from '../services/api';
import type { Provider } from '../types';

const PROVIDER_KEY = 'aieo_provider';
const MODEL_KEY = 'aieo_model';

export const PROVIDERS: { value: Provider; label: string; hint: string }[] = [
  { value: 'auto', label: 'Auto (server default)', hint: 'Server resolves from its env keys; falls back to heuristic.' },
  { value: 'claude-cli', label: 'Claude Code (OAuth)', hint: 'Uses the local `claude` CLI — no API key needed server-side.' },
  { value: 'openai', label: 'OpenAI', hint: 'Requires OPENAI_API_KEY on the server.' },
  { value: 'anthropic', label: 'Anthropic', hint: 'Requires ANTHROPIC_API_KEY on the server.' },
  { value: 'heuristic', label: 'Heuristic (offline)', hint: 'Fast structural scoring with no AI call.' },
];

interface SettingsValue {
  apiKey: string;
  hasKey: boolean;
  provider: Provider;
  model: string;
  baseUrl: string;
  setApiKey: (key: string) => void;
  clearApiKey: () => void;
  setProvider: (p: Provider) => void;
  setModel: (m: string) => void;
  /** provider value to send to the API, or undefined for 'auto'. */
  providerParam: string | undefined;
}

const SettingsContext = createContext<SettingsValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKeyState] = useState<string>(() => apiClient.getApiKey() || '');
  const [provider, setProviderState] = useState<Provider>(
    () => (localStorage.getItem(PROVIDER_KEY) as Provider) || 'auto',
  );
  const [model, setModelState] = useState<string>(() => localStorage.getItem(MODEL_KEY) || '');

  const setApiKey = useCallback((key: string) => {
    const trimmed = key.trim();
    if (trimmed) apiClient.setApiKey(trimmed);
    else apiClient.clearApiKey();
    setApiKeyState(trimmed);
  }, []);

  const clearApiKey = useCallback(() => {
    apiClient.clearApiKey();
    setApiKeyState('');
  }, []);

  const setProvider = useCallback((p: Provider) => {
    localStorage.setItem(PROVIDER_KEY, p);
    setProviderState(p);
  }, []);

  const setModel = useCallback((m: string) => {
    if (m) localStorage.setItem(MODEL_KEY, m);
    else localStorage.removeItem(MODEL_KEY);
    setModelState(m);
  }, []);

  const value = useMemo<SettingsValue>(
    () => ({
      apiKey,
      hasKey: !!apiKey,
      provider,
      model,
      baseUrl: apiClient.baseURL,
      setApiKey,
      clearApiKey,
      setProvider,
      setModel,
      providerParam: provider === 'auto' ? undefined : provider,
    }),
    [apiKey, provider, model, setApiKey, clearApiKey, setProvider, setModel],
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): SettingsValue {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('useSettings must be used within <SettingsProvider>');
  return ctx;
}
