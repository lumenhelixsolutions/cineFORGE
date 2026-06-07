import { For, Show } from 'solid-js';
import { useNavigate } from '@solidjs/router';
import { projectStore } from '../stores/projectStore';

export default function ProjectTree() {
  const navigate = useNavigate();

  const handleCreate = async () => {
    const name = prompt('Project name:');
    if (name) {
      const project = await projectStore.createProject(name);
      if (project) {
        navigate(`/project/${project.id}`);
      }
    }
  };

  const handleSelect = (id: string) => {
    navigate(`/project/${id}`);
    projectStore.loadProject(id);
  };

  return (
    <div class="flex flex-col h-full w-64 border-r border-border bg-panel">
      <div class="p-4 border-b border-border flex items-center justify-between">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-muted">Projects</h2>
        <button onClick={handleCreate} class="btn-primary text-xs px-2 py-1" aria-label="Create new project" title="New project (N)">New</button>
      </div>
      <div class="flex-1 overflow-y-auto p-2 space-y-1">
        <For each={projectStore.state.projects}>
          {(project) => (
            <div
              class={`
                px-3 py-2 rounded-md cursor-pointer text-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent
                ${projectStore.state.activeProject?.id === project.id ? 'bg-accent/20 border border-accent/40' : 'hover:bg-surface'}
              `}
              onClick={() => handleSelect(project.id)}
              role="button"
              tabindex="0"
              aria-label={`Open project ${project.name}`}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSelect(project.id); } }}
            >
              <div class="font-medium truncate">{project.name}</div>
              <div class="text-xs text-muted mt-0.5">
                {project.shot_count || 0} shots · {project.status || 'draft'}
              </div>
            </div>
          )}
        </For>
      </div>
      <Show when={projectStore.state.loading}>
        <div class="p-2 text-xs text-muted text-center">Loading...</div>
      </Show>
    </div>
  );
}
