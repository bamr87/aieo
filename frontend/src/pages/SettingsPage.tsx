import { useState } from 'react';
import { CheckCircle2, KeyRound, Wifi } from 'lucide-react';
import { Button, Card, CardBody, CardHeader, Field, Input, PageHeader, Select } from '../components/ui';
import { PROVIDERS, useSettings } from '../hooks/useSettings';
import { useToast } from '../hooks/useToast';
import { errorMessage } from '../lib/format';

const DEV_KEY = 'aieo-local-dev-key';

export function SettingsPage() {
  const settings = useSettings();
  const toast = useToast();
  const [keyDraft, setKeyDraft] = useState(settings.apiKey);
  const [health, setHealth] = useState<{ ok: boolean; text: string } | null>(null);
  const [checking, setChecking] = useState(false);

  const healthUrl = settings.baseUrl.replace(/\/api\/v1\/?$/, '') + '/health';

  const saveKey = () => {
    settings.setApiKey(keyDraft);
    toast.success(keyDraft.trim() ? 'API key saved' : 'API key cleared');
  };

  const useDevKey = () => {
    setKeyDraft(DEV_KEY);
    settings.setApiKey(DEV_KEY);
    toast.success('Local dev key set');
  };

  const testConnection = async () => {
    setChecking(true);
    setHealth(null);
    try {
      const res = await fetch(healthUrl);
      const body = await res.json().catch(() => ({}));
      const status = (body as { status?: string }).status || (res.ok ? 'ok' : 'error');
      setHealth({ ok: res.ok, text: `${res.status} · ${status}` });
    } catch (err) {
      setHealth({ ok: false, text: errorMessage(err) });
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Configure how the UI talks to the AIEO backend."
      />

      <Card>
        <CardHeader
          title="API key"
          description="Every backend endpoint requires an X-API-Key header. For local dev any string of 11+ characters is accepted."
        />
        <CardBody className="space-y-4">
          <Field
            label="X-API-Key"
            hint="Stored only in this browser (localStorage). The strict citations/dashboard endpoints need a real key registered in the database."
          >
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                value={keyDraft}
                onChange={(e) => setKeyDraft(e.target.value)}
                placeholder="paste an API key…"
                type="text"
                spellCheck={false}
                className="font-mono"
              />
              <div className="flex gap-2">
                <Button variant="primary" leftIcon={<KeyRound size={15} />} onClick={saveKey}>
                  Save
                </Button>
                <Button variant="ghost" onClick={useDevKey}>
                  Use dev key
                </Button>
              </div>
            </div>
          </Field>
          {settings.hasKey ? (
            <p className="flex items-center gap-1.5 text-xs text-good">
              <CheckCircle2 size={14} /> A key is currently set.
            </p>
          ) : (
            <p className="text-xs text-warn">No key set — API calls will return 401.</p>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Default provider & model"
          description="Used by Audit and Optimize. Claude Code (OAuth) uses your local `claude` CLI on the server — no key required."
        />
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <Field label="Provider" hint={PROVIDERS.find((p) => p.value === settings.provider)?.hint}>
            <Select
              value={settings.provider}
              onChange={(e) => settings.setProvider(e.target.value as typeof settings.provider)}
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Model override (optional)" hint="e.g. gpt-4o, claude-sonnet-4, sonnet. Leave blank for the provider default.">
            <Input
              value={settings.model}
              onChange={(e) => settings.setModel(e.target.value)}
              placeholder="default"
              className="font-mono"
            />
          </Field>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Backend connection" description={settings.baseUrl} />
        <CardBody className="space-y-3">
          <Button variant="secondary" leftIcon={<Wifi size={15} />} loading={checking} onClick={testConnection}>
            Test connection
          </Button>
          {health && (
            <p className={'text-sm ' + (health.ok ? 'text-good' : 'text-bad')}>
              {health.ok ? '✓ Reachable' : '✕ Failed'} — {health.text}
            </p>
          )}
          <p className="text-xs text-muted">
            Override the API base URL with <code className="rounded bg-elevated px-1">VITE_API_BASE_URL</code> in{' '}
            <code className="rounded bg-elevated px-1">frontend/.env.local</code>.
          </p>
        </CardBody>
      </Card>
    </div>
  );
}
