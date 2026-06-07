import { For, Show, createSignal, onCleanup, onMount } from 'solid-js';
import { projectStore } from '../stores/projectStore';
import { exportStore, exportState, type ExportJob } from '../stores/exportStore';

const typeLabels: Record<string, string> = {
  mp4: 'MP4 Video',
  archive: 'Project Archive',
  stills: 'Keyframe Stills',
  edl: 'EDL (CMX3600)',
};

const typeIcons: Record<string, string> = {
  mp4: '🎬',
  archive: '📦',
  stills: '🖼️',
  edl: '📄',
};

export default function ExportPanel() {
  const [selectedType, setSelectedType] = createSignal<ExportJob['type']>('mp4');
  const [polling, setPolling] = createSignal(false);

  const projectId = () => projectStore.state.activeProject?.id;

  const activeJobs = () =>
    exportState.jobs.filter((j) => j.status === 'queued' || j.status === 'processing');
  const completedJobs = () => exportState.jobs.filter((j) => j.status === 'completed');

  let stopPoll: (() => void) | null = null;

  const startPolling = () => {
    if (stopPoll) return;
    setPolling(true);
    const id = projectId();
    if (id) {
      stopPoll = exportStore.pollExports(id);
    }
  };

  onCleanup(() => {
    if (stopPoll) stopPoll();
  });

  onMount(() => {
    const id = projectId();
    if (id) {
      exportStore.loadExports(id);
      startPolling();
    }
  });

  const handleStartExport = async () => {
    const id = projectId();
    if (!id) return;
    try {
      await exportStore.startExport(id, selectedType());
      startPolling();
    } catch {
      // error handled in store
    }
  };

  const handleCancel = async (jobId: string) => {
    const id = projectId();
    if (!id) return;
    await exportStore.cancelExport(jobId, id);
  };

  const handleDownload = (jobId: string) => {
    const url = exportStore.getDownloadUrl(jobId);
    window.open(url, '_blank');
  };

  return (
    <div class="p-6 space-y-6 overflow-auto h-full">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">Export &amp; Distribution</h2>
      </div>

      <Show when={!projectId()}>
        <div class="text-muted text-sm">Select a project to begin exporting.</div>
      </Show>

      <Show when={projectId()}>
        <div class="space-y-4">
          <div class="flex items-center gap-3">
            <select
              class="bg-panel border border-border rounded px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-accent"
              value={selectedType()}
              onChange={(e) => setSelectedType(e.currentTarget.value as ExportJob['type'])}
            >
              <option value="mp4">MP4 Video</option>
              <option value="archive">Project Archive</option>
              <option value="stills">Keyframe Stills</option>
              <option value="edl">EDL (CMX3600)</option>
            </select>
            <button
              class="px-3 py-1.5 text-xs font-medium bg-accent hover:bg-accent/80 rounded transition-colors disabled:opacity-50"
              onClick={handleStartExport}
              disabled={exportState.loading}
            >
              Start Export
            </button>
          </div>

          <Show when={activeJobs().length > 0}>
            <div class="space-y-3">
              <h3 class="text-sm font-medium text-muted">Active Exports</h3>
              <For each={activeJobs()}>
                {(job) => (
                  <div class="bg-panel border border-border rounded p-3 space-y-2">
                    <div class="flex items-center justify-between">
                      <div class="flex items-center gap-2">
                        <span>{typeIcons[job.type]}</span>
                        <span class="text-sm font-medium">{typeLabels[job.type]}</span>
                        <span class="text-[10px] uppercase text-muted bg-surface px-1.5 py-0.5 rounded">
                          {job.status}
                        </span>
                      </div>
                      <button
                        class="text-xs text-red-400 hover:text-red-300 transition-colors"
                        onClick={() => handleCancel(job.id)}
                      >
                        Cancel
                      </button>
                    </div>
                    <div class="h-2 bg-surface rounded-full overflow-hidden">
                      <div
                        class="h-full bg-accent transition-all duration-500"
                        style={{ width: `${Math.min(100, Math.max(0, job.progress))}%` }}
                      />
                    </div>
                    <div class="text-[10px] text-muted text-right">{Math.round(job.progress)}%</div>
                  </div>
                )}
              </For>
            </div>
          </Show>

          <Show when={completedJobs().length > 0}>
            <div class="space-y-3">
              <h3 class="text-sm font-medium text-muted">Completed Exports</h3>
              <For each={completedJobs()}>
                {(job) => (
                  <div class="bg-panel border border-border rounded p-3 flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      <span>{typeIcons[job.type]}</span>
                      <span class="text-sm font-medium">{typeLabels[job.type]}</span>
                      <span class="text-[10px] text-muted">
                        {job.output_size ? `${(job.output_size / 1024).toFixed(1)} KB` : ''}
                      </span>
                    </div>
                    <button
                      class="px-3 py-1 text-xs font-medium bg-success/20 text-success hover:bg-success/30 rounded transition-colors"
                      onClick={() => handleDownload(job.id)}
                    >
                      Download
                    </button>
                  </div>
                )}
              </For>
            </div>
          </Show>

          <Show when={exportState.jobs.length === 0 && !exportState.loading}>
            <div class="text-muted text-sm py-8 text-center">
              No exports yet. Choose a format and click Start Export.
            </div>
          </Show>
        </div>
      </Show>
    </div>
  );
}
