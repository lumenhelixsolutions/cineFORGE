import { Show } from 'solid-js';
import { useParams } from '@solidjs/router';
import { onMount } from 'solid-js';
import Storyboard from './components/Storyboard';
import TreatmentView from './components/TreatmentView';
import TimelineView from './components/TimelineView';
import PreviewPlayer from './components/PreviewPlayer';
import { projectStore } from './stores/projectStore';

export default function ProjectView() {
  const params = useParams();

  onMount(() => {
    if (params.id) {
      projectStore.loadProject(params.id);
    }
  });

  return (
    <>
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
    </>
  );
}
