import { Show, createSignal, createEffect, onCleanup } from 'solid-js';

const shortcuts = [
  { key: 'Cmd+K', desc: 'Command palette' },
  { key: 'R', desc: 'Render current project' },
  { key: 'S', desc: 'Stitch current project' },
  { key: 'N', desc: 'New project' },
  { key: '?', desc: 'Show this help' },
  { key: '← / →', desc: 'Navigate shots' },
];

export default function ShortcutsModal() {
  const [open, setOpen] = createSignal(false);

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === '?' && !e.metaKey && !e.ctrlKey && !e.altKey) {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable) {
        return;
      }
      e.preventDefault();
      setOpen(true);
    }
    if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  createEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    onCleanup(() => window.removeEventListener('keydown', handleKeyDown));
  });

  return (
    <Show when={open()}>
      <div
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      >
        <div
          class="w-full max-w-sm bg-panel border border-border rounded-lg shadow-2xl p-6"
          onClick={(e) => e.stopPropagation()}
        >
          <h2 class="text-sm font-semibold uppercase tracking-wider text-muted mb-4">
            Keyboard Shortcuts
          </h2>
          <div class="space-y-2">
            {shortcuts.map((s) => (
              <div class="flex items-center justify-between text-sm">
                <span class="text-muted">{s.desc}</span>
                <kbd class="px-2 py-1 rounded bg-surface border border-border text-xs font-mono text-white">
                  {s.key}
                </kbd>
              </div>
            ))}
          </div>
          <div class="mt-4 pt-4 border-t border-border text-center">
            <button class="btn-secondary text-xs" onClick={() => setOpen(false)}>
              Close
            </button>
          </div>
        </div>
      </div>
    </Show>
  );
}
