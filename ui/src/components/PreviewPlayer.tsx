import { Show, createSignal, createEffect } from 'solid-js';
import { projectStore } from '../stores/projectStore';
import { api } from '../lib/api';

type PreviewMode = 'master' | 'shot' | 'living';

export default function PreviewPlayer() {
  const [mode, setMode] = createSignal<PreviewMode>('master');
  const [src, setSrc] = createSignal<string | null>(null);
  const [livingLoading, setLivingLoading] = createSignal(false);
  const project = () => projectStore.state.activeProject;
  const selectedShot = () => projectStore.getSelectedShot();
  const lookbookReview = () => projectStore.state.lookbookReview;

  createEffect(() => {
    const p = project();
    if (!p) {
      setSrc(null);
      return;
    }
    if (mode() === 'master') {
      setSrc(`http://127.0.0.1:8765/media/${p.id}/master.mp4`);
    } else if (mode() === 'shot') {
      const shot = selectedShot();
      if (shot?.clip_path) {
        setSrc(`http://127.0.0.1:8765${shot.clip_path}`);
      } else {
        setSrc(null);
      }
    } else {
      setSrc(null);
    }
  });

  createEffect(() => {
    const p = project();
    if (mode() !== 'living' || !p) {
      return;
    }
    setLivingLoading(true);
    void projectStore.fetchLookbookReview(p.id).finally(() => setLivingLoading(false));
  });

  const livingReviewUrl = () => {
    const p = project();
    return p ? api.lookbook.reviewUrl(p.id) : null;
  };

  return (
    <div class="flex-1 flex flex-col overflow-hidden">
      <div class="p-4 border-b border-border flex items-center justify-between">
        <h3 class="text-xs font-medium text-muted uppercase tracking-wider">Preview</h3>
        <div class="flex items-center gap-2">
          <button
            class={`text-xs px-2 py-1 rounded border transition-colors ${mode() === 'master' ? 'bg-accent/20 border-accent text-accent' : 'border-border text-muted hover:text-white'}`}
            onClick={() => setMode('master')}
          >
            Master
          </button>
          <button
            class={`text-xs px-2 py-1 rounded border transition-colors ${mode() === 'shot' ? 'bg-accent/20 border-accent text-accent' : 'border-border text-muted hover:text-white'}`}
            onClick={() => setMode('shot')}
          >
            Selected Shot
          </button>
          <button
            class={`text-xs px-2 py-1 rounded border transition-colors ${mode() === 'living' ? 'bg-accent/20 border-accent text-accent' : 'border-border text-muted hover:text-white'}`}
            onClick={() => setMode('living')}
          >
            Living
          </button>
        </div>
      </div>
      <div class="flex-1 flex items-center justify-center bg-black">
        <Show
          when={mode() !== 'living'}
          fallback={
            <Show
              when={!livingLoading() && lookbookReview()?.available && livingReviewUrl()}
              fallback={
                <div class="text-sm text-muted text-center px-6 max-w-md">
                  {livingLoading()
                    ? 'Loading living panels review…'
                    : lookbookReview()?.message
                      ?? 'Import a lookBOOK shot graph with choreography to preview living panels.'}
                </div>
              }
            >
              <iframe
                src={livingReviewUrl()!}
                title="Living panels review"
                class="w-full h-full border-0"
                sandbox="allow-scripts allow-same-origin"
              />
            </Show>
          }
        >
          <Show
            when={src()}
            fallback={
              <div class="text-sm text-muted">
                {mode() === 'master'
                  ? 'Click "Master" to preview rendered video'
                  : 'Select a shot with a rendered clip to preview'}
              </div>
            }
          >
            <video
              src={src()!}
              controls
              class="max-w-full max-h-full"
              preload="metadata"
            />
          </Show>
        </Show>
      </div>
    </div>
  );
}