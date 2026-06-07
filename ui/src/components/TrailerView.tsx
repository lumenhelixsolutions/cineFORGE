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

  const isIdle = () => !url() && (status() === 'idle' || status() === 'not_started');
  const isLoading = () => status() === 'queued' || status() === 'processing' || polling();

  return (
    <div class="p-6 space-y-6 overflow-auto h-full">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">Trailer Generator</h2>
        <div class="space-x-2">
          <button
            class="px-3 py-1.5 text-xs font-medium bg-accent hover:bg-accent/80 rounded transition-colors disabled:opacity-50"
            onClick={handleGenerate}
            disabled={status() === 'queued' || status() === 'processing' || polling()}
            aria-label="Generate trailer"
          >
            Generate Trailer
          </button>
          <button
            class="px-3 py-1.5 text-xs font-medium bg-panel hover:bg-panel/80 border border-border rounded transition-colors"
            onClick={handleRefresh}
            aria-label="Refresh trailer status"
          >
            Refresh
          </button>
        </div>
      </div>

      <Show when={error()}>
        <div class="text-xs text-red-400 bg-red-950/30 border border-red-900 rounded p-3" role="alert" aria-live="assertive">
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
        <div
          class="h-2 bg-panel rounded-full overflow-hidden border border-border"
          role="progressbar"
          aria-valuenow={Math.min(100, Math.max(0, progress() * 100))}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Trailer generation progress"
        >
          <div
            class="h-full bg-accent transition-all duration-500"
            style={{ width: `${Math.min(100, Math.max(0, progress() * 100))}%` }}
          />
        </div>
      </div>

      <Show when={isIdle()}>
        <div class="flex flex-col items-center justify-center py-12 text-muted text-sm space-y-3" role="status">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 text-muted/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <p>No trailer generated yet.</p>
          <p class="text-xs">Click <span class="text-white font-medium">Generate Trailer</span> to create a preview cut.</p>
        </div>
      </Show>

      <Show when={isLoading() && !url()}>
        <div class="space-y-3" role="status" aria-label="Generating trailer">
          <div class="aspect-video max-w-2xl bg-surface rounded border border-border animate-pulse" />
          <div class="h-4 w-1/3 bg-surface rounded animate-pulse" />
        </div>
      </Show>

      <Show when={url()}>
        <div class="space-y-2">
          <h3 class="text-sm font-medium">Preview</h3>
          <video
            src={url()!}
            controls
            class="w-full max-w-2xl rounded border border-border bg-black"
            aria-label="Trailer preview"
          />
          <a
            href={url()!}
            download=""
            class="inline-block text-xs text-accent hover:underline"
            aria-label="Download trailer"
          >
            Download trailer
          </a>
        </div>
      </Show>
    </div>
  );
}
