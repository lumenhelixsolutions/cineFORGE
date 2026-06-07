import { Show, For } from 'solid-js';
import SourceUploader from './SourceUploader';
import { projectStore } from '../stores/projectStore';

export default function TreatmentView() {
  const project = () => projectStore.state.activeProject;

  return (
    <div class="flex-1 overflow-y-auto p-4">
      <Show when={project()} fallback={
        <div class="text-center text-muted text-sm py-12">No project selected</div>
      }>
        <div class="max-w-2xl mx-auto space-y-6">
          <div class="panel p-4">
            <h3 class="text-xs font-medium text-muted uppercase tracking-wider mb-2">Sources</h3>
            <SourceUploader />
            <div class="mt-3 space-y-1">
              <For each={project()?.sources || []}>
                {(source) => (
                  <div class="flex items-center justify-between text-xs py-1 px-2 rounded bg-surface">
                    <span class="text-white">{source.kind}</span>
                    <span class="text-muted">{source.word_count} words</span>
                  </div>
                )}
              </For>
            </div>
          </div>

          <div class="panel p-4">
            <h3 class="text-xs font-medium text-muted uppercase tracking-wider mb-2">Treatment</h3>
            <Show when={(project()?.treatments?.length ?? 0) > 0} fallback={
              <div class="text-sm text-muted">No treatment generated yet.</div>
            }>
              <div class="text-sm text-white space-y-3">
                <div class="text-muted text-xs">Treatment generated. View in storyboard.</div>
              </div>
            </Show>
          </div>
        </div>
      </Show>
    </div>
  );
}
