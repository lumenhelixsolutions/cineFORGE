import { Show } from 'solid-js';
import { useParams } from '@solidjs/router';
import { onMount } from 'solid-js';
import Storyboard from './components/Storyboard';
import TreatmentView from './components/TreatmentView';
import TimelineView from './components/TimelineView';
import PreviewPlayer from './components/PreviewPlayer';
import TrailerView from './components/TrailerView';
import ExportPanel from './components/ExportPanel';
import { projectStore } from './stores/projectStore';

export default function ProjectView() {
  const params = useParams();

  onMount(() => {
    if (params.id) {
      projectStore.loadProject(params.id);
    }
  });

  return (
    <div class="relative flex-1 overflow-hidden" role="main" aria-live="polite">
      <Show when={projectStore.state.activeTab === 'sources'}>
        <TreatmentView />
      </Show>
      <Show when={projectStore.state.activeTab === 'storyboard'}>
        <Storyboard />
      </Show>
      <Show when={projectStore.state.activeTab === 'timeline'}>
        <TimelineView />
      </Show>
      <Show when={projectStore.state.activeTab === 'preview'}>
        <PreviewPlayer />
      </Show>
      <Show when={projectStore.state.activeTab === 'trailer'}>
        <TrailerView />
      </Show>
      <Show when={projectStore.state.activeTab === 'export'}>
        <ExportPanel />
      </Show>

      {/* Keyboard shortcut hint */}
      <div class="absolute bottom-3 right-3 text-[10px] text-muted/60 bg-panel/80 border border-border/50 rounded px-2 py-1 pointer-events-none select-none hidden md:block" aria-hidden="true">
        Press <kbd class="font-mono text-muted">?</kbd> for shortcuts
      </div>
    </div>
  );
}
