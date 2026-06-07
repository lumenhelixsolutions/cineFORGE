import { Show, createSignal, createEffect } from 'solid-js';
import { projectStore } from '../stores/projectStore';

type PreviewMode = 'master' | 'shot';

export default function PreviewPlayer() {
  const [mode, setMode] = createSignal<PreviewMode>('master');
  const [src, setSrc] = createSignal<string | null>(null);
  const project = () => projectStore.state.activeProject;
  const selectedShot = () => projectStore.getSelectedShot();

  createEffect(() => {
    const p = project();
    if (!p) {
      setSrc(null);
      return;
    }
    if (mode() === 'master') {
      setSrc(`http://127.0.0.1:8765/media/${p.id}/master.mp4`);
    } else {
      const shot = selectedShot();
      if (shot?.clip_path) {
        setSrc(`http://127.0.0.1:8765${shot.clip_path}`);
      } else {
        setSrc(null);
      }
    }
  });

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
        </div>
      </div>
      <div class="flex-1 flex items-center justify-center bg-black">
        <Show when={src()} fallback={
          <div class="text-sm text-muted">
            {mode() === 'master'
              ? 'Click "Master" to preview rendered video'
              : 'Select a shot with a rendered clip to preview'}
          </div>
        }>
          <video
            src={src()!}
            controls
            class="max-w-full max-h-full"
            preload="metadata"
          />
        </Show>
      </div>
    </div>
  );
}
