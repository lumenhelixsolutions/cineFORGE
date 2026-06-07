import { For, Show, createSignal } from 'solid-js';
import { projectStore } from '../stores/projectStore';

export default function TimelineView() {
  const project = () => projectStore.state.activeProject;
  const shots = () => project()?.shots || [];
  const [draggingId, setDraggingId] = createSignal<string | null>(null);
  const [dragOverId, setDragOverId] = createSignal<string | null>(null);

  const totalDuration = () => shots().reduce((acc: number, s: any) => acc + (s.duration_sec || 0), 0);

  const handleDragStart = (e: DragEvent, shotId: string) => {
    setDraggingId(shotId);
    e.dataTransfer?.setData('text/plain', shotId);
    e.dataTransfer!.effectAllowed = 'move';
  };

  const handleDragOver = (e: DragEvent, shotId: string) => {
    e.preventDefault();
    e.dataTransfer!.dropEffect = 'move';
    setDragOverId(shotId);
  };

  const handleDragLeave = () => {
    setDragOverId(null);
  };

  const handleDrop = async (e: DragEvent, targetId: string) => {
    e.preventDefault();
    const sourceId = e.dataTransfer?.getData('text/plain') || draggingId();
    setDragOverId(null);
    setDraggingId(null);

    if (!sourceId || sourceId === targetId) return;
    const p = project();
    if (!p) return;

    const currentShots = [...p.shots];
    const fromIndex = currentShots.findIndex((s) => s.id === sourceId);
    const toIndex = currentShots.findIndex((s) => s.id === targetId);
    if (fromIndex === -1 || toIndex === -1) return;

    const [moved] = currentShots.splice(fromIndex, 1);
    currentShots.splice(toIndex, 0, moved);

    const orderedIds = currentShots.map((s) => s.id);
    await projectStore.reorderShots(p.id, orderedIds);
  };

  const handleDurationChange = async (shotId: string, value: string) => {
    const duration = parseFloat(value);
    if (Number.isNaN(duration) || duration < 0) return;
    const p = project();
    if (!p) return;
    await projectStore.updateShot(p.id, shotId, { duration_sec: duration });
  };

  return (
    <div class="flex-1 overflow-y-auto p-4">
      <Show when={shots().length > 0} fallback={
        <div class="text-center text-muted text-sm py-12">No shots rendered yet</div>
      }>
        <div class="max-w-4xl mx-auto">
          <div class="flex items-center justify-between mb-4">
            <div class="text-xs text-muted">Total duration: {totalDuration()}s</div>
            <div class="text-xs text-muted">{shots().length} shots</div>
          </div>

          <div class="relative">
            {/* Timeline track */}
            <div class="h-8 bg-surface rounded flex items-center overflow-hidden">
              <For each={shots()}>
                {(shot) => {
                  const width = () => `${(shot.duration_sec / Math.max(totalDuration(), 1)) * 100}%`;
                  const color = () => {
                    if (shot.status === 'done') return 'bg-success/60';
                    if (shot.status === 'rendering') return 'bg-accent/60';
                    if (shot.status === 'failed') return 'bg-danger/60';
                    return 'bg-muted/40';
                  };
                  return (
                    <div
                      class={`h-full ${color()} border-r border-surface/50 relative group cursor-pointer transition-opacity ${draggingId() === shot.id ? 'opacity-40' : ''}`}
                      style={{ width: width() }}
                      title={`Shot #${shot.order_index + 1} — ${shot.duration_sec}s — ${shot.status}`}
                    >
                      <div class="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 hidden group-hover:block bg-panel border border-border rounded px-2 py-1 text-[10px] whitespace-nowrap z-10">
                        #{shot.order_index + 1} · {shot.tier} · {shot.bridge_strategy}
                      </div>
                    </div>
                  );
                }}
              </For>
            </div>

            {/* Shot list below timeline */}
            <div class="mt-4 space-y-2">
              <For each={shots()}>
                {(shot) => (
                  <div
                    class={`panel p-2 flex items-center gap-3 text-xs transition-colors ${dragOverId() === shot.id && dragOverId() !== draggingId() ? 'bg-accent/10 border-accent' : ''}`}
                    draggable
                    onDragStart={(e) => handleDragStart(e, shot.id)}
                    onDragOver={(e) => handleDragOver(e, shot.id)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, shot.id)}
                  >
                    <span class="font-mono text-muted w-8 cursor-grab active:cursor-grabbing">#{shot.order_index + 1}</span>
                    <span class={`w-2 h-2 rounded-full ${
                      shot.status === 'done' ? 'bg-success' :
                      shot.status === 'rendering' ? 'bg-accent animate-pulse' :
                      shot.status === 'failed' ? 'bg-danger' :
                      'bg-muted'
                    }`} />
                    <span class="flex-1 truncate">{shot.prompt_text || 'No prompt'}</span>

                    {/* Trim handles / duration input */}
                    <div class="flex items-center gap-1">
                      <span class="text-muted">In</span>
                      <input
                        type="number"
                        class="w-14 px-1 py-0.5 bg-surface border border-border rounded text-xs text-center"
                        value={0}
                        readOnly
                      />
                      <span class="text-muted">Out</span>
                      <input
                        type="number"
                        class="w-14 px-1 py-0.5 bg-surface border border-border rounded text-xs text-center"
                        value={shot.duration_sec}
                        min={0}
                        step={0.5}
                        onChange={(e) => handleDurationChange(shot.id, e.currentTarget.value)}
                      />
                      <span class="text-muted w-10 text-right">{shot.duration_sec}s</span>
                    </div>

                    <span class="text-muted">{shot.bridge_strategy}</span>
                  </div>
                )}
              </For>
            </div>
          </div>
        </div>
      </Show>
    </div>
  );
}
