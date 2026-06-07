import { For, Show, createSignal, createEffect, onCleanup } from 'solid-js';
import { projectStore } from '../stores/projectStore';

const commands = [
  { id: 'treatment', label: 'Generate Treatment', shortcut: 'Cmd+T', action: () => {
    const p = projectStore.state.activeProject;
    if (p) projectStore.generateTreatment(p.id);
  }},
  { id: 'storyboard', label: 'Generate Storyboard', shortcut: 'Cmd+S', action: () => {
    const p = projectStore.state.activeProject;
    if (p) projectStore.generateStoryboard(p.id);
  }},
  { id: 'render', label: 'Render All Shots', shortcut: 'Cmd+R', action: () => {
    const p = projectStore.state.activeProject;
    if (p) projectStore.render(p.id);
  }},
  { id: 'stitch', label: 'Stitch Master', shortcut: 'Cmd+P', action: () => {
    const p = projectStore.state.activeProject;
    if (p) projectStore.stitch(p.id);
  }},
  { id: 'preview', label: 'Toggle Preview Mode', shortcut: '', action: () => {
    const p = projectStore.state.activeProject;
    if (p) projectStore.togglePreviewMode(p.id, !p.preview_mode);
  }},
  { id: 'new', label: 'New Project', shortcut: 'Cmd+N', action: () => {
    const name = prompt('Project name:');
    if (name) projectStore.createProject(name);
  }},
];

export default function CommandPalette() {
  const [query, setQuery] = createSignal('');
  const [selected, setSelected] = createSignal(0);

  const filtered = () => {
    const q = query().toLowerCase();
    return commands.filter((c) => c.label.toLowerCase().includes(q));
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      projectStore.openCommandPalette();
    }
    if (e.key === 'Escape') {
      projectStore.closeCommandPalette();
    }
    if (!projectStore.state.commandPaletteOpen) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelected((prev) => Math.min(prev + 1, filtered().length - 1));
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelected((prev) => Math.max(prev - 1, 0));
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      const cmd = filtered()[selected()];
      if (cmd) {
        cmd.action();
        projectStore.closeCommandPalette();
        setQuery('');
        setSelected(0);
      }
    }
  };

  createEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    onCleanup(() => window.removeEventListener('keydown', handleKeyDown));
  });

  return (
    <Show when={projectStore.state.commandPaletteOpen}>
      <div class="fixed inset-0 z-50 flex items-start justify-center pt-32 bg-black/60 backdrop-blur-sm"
           onClick={() => projectStore.closeCommandPalette()}>
        <div class="w-full max-w-lg bg-panel border border-border rounded-lg shadow-2xl overflow-hidden"
             onClick={(e) => e.stopPropagation()}>
          <input
            type="text"
            class="w-full px-4 py-3 bg-transparent text-sm focus:outline-none placeholder-muted"
            placeholder="Type a command..."
            value={query()}
            onInput={(e) => { setQuery(e.currentTarget.value); setSelected(0); }}
            ref={(el) => { if (el) el.focus(); }}
            aria-label="Command palette search"
            role="combobox"
            aria-expanded={filtered().length > 0}
            aria-autocomplete="list"
          />
          <div class="border-t border-border max-h-64 overflow-y-auto">
            <For each={filtered()}>
              {(cmd, index) => (
                <div
                  class={`
                    px-4 py-2.5 text-sm cursor-pointer flex items-center justify-between
                    ${index() === selected() ? 'bg-accent/20' : 'hover:bg-surface'}
                  `}
                  onMouseEnter={() => setSelected(index())}
                  onClick={() => { cmd.action(); projectStore.closeCommandPalette(); setQuery(''); setSelected(0); }}
                  role="option"
                  aria-selected={index() === selected()}
                  id={`cmd-${cmd.id}`}
                >
                  <span>{cmd.label}</span>
                  <span class="text-xs text-muted font-mono">{cmd.shortcut}</span>
                </div>
              )}
            </For>
          </div>
        </div>
      </div>
    </Show>
  );
}
