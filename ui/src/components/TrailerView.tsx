import { createSignal, onCleanup, Show } from 'solid-js';
import { projectStore } from '../stores/projectStore';
import { api } from '../lib/api';

export default function TrailerView() {
  const [status, setStatus] = createSignal<string>('idle');
  const [progress, setProgress] = createSignal<number>(0);
  const [url, setUrl] = createSignal<string | null>(null);
  const [error, setError] = createSignal<string | null>(null);
  const [polling, setPolling] = createSignal<boolean>(false);

  const projectId = () => projectStore.state.activeProject?.id;

  let pollInterval: ReturnType<typeof setInterval> | null = null;

  const startPolling = () => {
    if (pollInterval) return;
    setPolling(true);
    pollInterval = setInterval(async () => {
      const id = projectId();
      if (!id) return;
      try {
        const resp = await api.trailer.status(id);
        setStatus(resp.status);
        setProgress(resp.progress ?? 0);
        setUrl(resp.url ?? null);
        if (resp.status === 'completed' || resp.status === 'failed' || resp.status === 'not_started') {
          stopPolling();
        }
      } catch (err: any) {
        setError(err.message);
        stopPolling();
      }
    }, 2000);
  };

  const stopPolling = () => {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    setPolling(false);
  };

  onCleanup(() => {
    stopPolling();
  });

  const handleGenerate = async () => {
    const id = projectId();
    if (!id) return;
    setError(null);
    setStatus('queued');
    setProgress(0);
    setUrl(null);
    try {
      const resp = await api.trailer.generate(id);
      setStatus('queued');
      startPolling();
    } catch (err: any) {
      setError(err.message);
      setStatus('failed');
    }
  };

  const handleRefresh = async () => {
    const id = projectId();
    if (!id) return;
    try {
      const resp = await api.trailer.status(id);
      setStatus(resp.status);
      setProgress(resp.progress ?? 0);
      setUrl(resp.url ?? null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div class="p-6 space-y-6 overflow-auto h-full">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">Trailer Generator</h2>
        <div class="space-x-2">
          <button
            class="px-3 py-1.5 text-xs font-medium bg-accent hover:bg-accent/80 rounded transition-colors disabled:opacity-50"
            onClick={handleGenerate}
            disabled={status() === 'queued' || status() === 'processing' || polling()}
          >
            Generate Trailer
          </button>
          <button
            class="px-3 py-1.5 text-xs font-medium bg-panel hover:bg-panel/80 border border-border rounded transition-colors"
            onClick={handleRefresh}
          >
            Refresh
          </button>
        </div>
      </div>

      <Show when={error()}>
        <div class="text-xs text-red-400 bg-red-950/30 border border-red-900 rounded p-3">
          {error()}
        </div>
      </Show>

      <div class="space-y-2">
        <div class="flex justify-between text-xs text-muted">
          <span>Status: <span class="text-white capitalize">{status()}</span></span>
          <Show when={polling()}>
            <span class="animate-pulse">Polling…</span>
          </Show>
        </div>
        <div class="h-2 bg-panel rounded-full overflow-hidden border border-border">
          <div
            class="h-full bg-accent transition-all duration-500"
            style={{ width: `${Math.min(100, Math.max(0, progress() * 100))}%` }}
          />
        </div>
      </div>

      <Show when={url()}>
        <div class="space-y-2">
          <h3 class="text-sm font-medium">Preview</h3>
          <video
            src={url()!}
            controls
            class="w-full max-w-2xl rounded border border-border bg-black"
          />
          <a
            href={url()!}
            download
            class="inline-block text-xs text-accent hover:underline"
          >
            Download trailer
          </a>
        </div>
      </Show>
    </div>
  );
}
