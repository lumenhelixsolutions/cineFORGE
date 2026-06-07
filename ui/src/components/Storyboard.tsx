import { For, Show, createSignal } from 'solid-js';
import { projectStore } from '../stores/projectStore';
import { api } from '../lib/api';

const statusDot = (status: string) => {
  const colors: Record<string, string> = {
    draft: 'bg-muted',
    queued: 'bg-accent',
    rendering: 'bg-accent animate-pulse',
    done: 'bg-success',
    failed: 'bg-danger',
  };
  return colors[status] || 'bg-muted';
};

const tierBadge = (tier: string) => {
  const colors: Record<string, string> = {
    hero: 'bg-accent/20 text-accent',
    standard: 'bg-panel text-muted',
    broll: 'bg-surface text-muted',
    title: 'bg-panel border border-border text-muted',
  };
  return colors[tier] || 'bg-panel text-muted';
};

export default function Storyboard() {
  const project = () => projectStore.state.activeProject;
  const shots = () => project()?.shots || [];
  const brollForSelected = () => {
    const sid = projectStore.state.selectedShotId;
    return sid ? (projectStore.state.brollClips[sid] || []) : [];
  };

  return (
    <div class="flex-1 flex flex-col h-full overflow-hidden">
      <Show when={project()} fallback={
        <div class="flex-1 flex items-center justify-center text-muted text-sm">
          Select a project or create one to begin
        </div>
      }>
        <div class="p-4 border-b border-border flex items-center justify-between bg-panel">
          <div>
            <h1 class="text-lg font-semibold">{project()?.name}</h1>
            <div class="text-xs text-muted mt-0.5">
              {project()?.aspect_ratio} · {project()?.target_duration_sec}s target · {project()?.routing_profile}
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Show when={project()?.preview_mode}>
              <span class="px-2 py-1 rounded bg-accent/20 text-accent text-xs font-medium">Preview Mode</span>
            </Show>
            <button
              class="btn-secondary text-xs"
              onClick={() => projectStore.togglePreviewMode(project()!.id, !project()?.preview_mode)}
            >
              {project()?.preview_mode ? 'Disable Preview' : 'Enable Preview'}
            </button>
            <button class="btn-primary text-xs" onClick={() => projectStore.generateTreatment(project()!.id)}>
              Generate Treatment
            </button>
            <button class="btn-primary text-xs" onClick={() => projectStore.generateStoryboard(project()!.id)}>
              Generate Storyboard
            </button>
            <button class="btn-primary text-xs" onClick={() => projectStore.render(project()!.id)}>
              Render
            </button>
            <button class="btn-secondary text-xs" onClick={() => projectStore.stitch(project()!.id)}>
              Stitch
            </button>
            <button class="btn-secondary text-xs" onClick={() => projectStore.generateAllBroll(project()!.id)}>
              Generate All B-Roll
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-4">
          <Show when={shots().length === 0}>
            <div class="text-center text-muted text-sm py-12">
              No shots yet. Upload sources and generate a treatment to begin.
            </div>
          </Show>

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <For each={shots()}>
              {(shot) => (
                <div
                  class={`
                    panel p-3 cursor-pointer transition-all hover:border-accent/40
                    ${projectStore.state.selectedShotId === shot.id ? 'ring-1 ring-accent' : ''}
                  `}
                  onClick={() => projectStore.selectShot(shot.id)}
                >
                  <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                      <span class={`w-2 h-2 rounded-full ${statusDot(shot.status)}`} />
                      <span class="text-xs font-mono text-muted">#{shot.order_index + 1}</span>
                      <span class={`text-[10px] px-1.5 py-0.5 rounded ${tierBadge(shot.tier)}`}>
                        {shot.tier}
                      </span>
                    </div>
                    <span class="text-xs text-muted">{shot.duration_sec}s</span>
                  </div>

                  <div class="aspect-video bg-surface rounded mb-2 flex items-center justify-center">
                    <Show when={shot.clip_path} fallback={
                      <span class="text-xs text-muted">No preview</span>
                    }>
                      <video
                        src={`http://127.0.0.1:8765${shot.clip_path}`}
                        class="w-full h-full object-cover rounded"
                        preload="metadata"
                        muted
                        aria-label={`Preview for shot ${shot.order_index + 1}`}
                      />
                    </Show>
                  </div>

                  <div class="text-xs text-muted mb-1">
                    Bridge: <span class="text-white">{shot.bridge_strategy}</span>
                  </div>

                  <details class="text-xs">
                    <summary class="cursor-pointer text-muted hover:text-white select-none">
                      Prompt
                    </summary>
                    <p class="mt-1 text-muted leading-relaxed font-mono text-[11px]">
                      {shot.prompt_text || 'Not forged yet'}
                    </p>
                  </details>

                  <Show when={projectStore.state.selectedShotId === shot.id}>
                    <div class="mt-2 pt-2 border-t border-border flex gap-2">
                      <button
                        class="btn-primary text-xs flex-1"
                        onClick={(e) => { e.stopPropagation(); projectStore.render(project()!.id, [shot.id]); }}
                        aria-label={`Regenerate shot ${shot.order_index + 1}`}
                      >
                        Regenerate
                      </button>
                      <button
                        class="btn-secondary text-xs flex-1"
                        onClick={(e) => { e.stopPropagation(); projectStore.generateBroll(project()!.id, shot.id); }}
                        aria-label={`Generate B-roll for shot ${shot.order_index + 1}`}
                      >
                        Generate B-Roll
                      </button>
                    </div>

                    {/* B-Roll thumbnail grid */}
                    <Show when={brollForSelected().length > 0}>
                      <div class="mt-3">
                        <div class="text-[10px] uppercase tracking-wider text-muted mb-1.5">Generated B-Roll</div>
                        <div class="grid grid-cols-2 gap-2">
                          <For each={brollForSelected()}>
                            {(clip) => (
                              <div class="bg-surface rounded overflow-hidden border border-border">
                                <Show when={clip.thumbnail_path} fallback={
                                  <div class="aspect-video flex items-center justify-center text-[10px] text-muted">
                                    {clip.status}
                                  </div>
                                }>
                                  <img
                                    src={`http://127.0.0.1:8765${clip.thumbnail_path}`}
                                    class="w-full aspect-video object-cover"
                                    alt="B-roll thumbnail"
                                  />
                                </Show>
                                <div class="p-1.5 flex items-center justify-between">
                                  <span class={`w-1.5 h-1.5 rounded-full ${statusDot(clip.status)}`} />
                                  <a
                                    href={api.broll.download(clip.id)}
                                    download=""
                                    class="text-[10px] text-accent hover:underline"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    Download
                                  </a>
                                </div>
                              </div>
                            )}
                          </For>
                        </div>
                      </div>
                    </Show>
                  </Show>
                </div>
              )}
            </For>
          </div>
        </div>
      </Show>
    </div>
  );
}
