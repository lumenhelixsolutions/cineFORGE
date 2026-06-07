import { createSignal } from 'solid-js';
import { projectStore } from '../stores/projectStore';

export default function SourceUploader() {
  const [dragOver, setDragOver] = createSignal(false);
  const project = () => projectStore.state.activeProject;

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer?.files;
    if (!files || !project()) return;
    for (let i = 0; i < files.length; i++) {
      await projectStore.uploadSource(project()!.id, files[i]);
    }
  };

  const handleFileInput = async (e: Event) => {
    const target = e.target as HTMLInputElement;
    const files = target.files;
    if (!files || !project()) return;
    for (let i = 0; i < files.length; i++) {
      await projectStore.uploadSource(project()!.id, files[i]);
    }
    target.value = '';
  };

  return (
    <div
      class={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
        dragOver() ? 'border-accent bg-accent/10' : 'border-border hover:border-muted'
      }`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      <div class="text-sm text-muted mb-2">
        Drop PDF, Markdown, or text files here
      </div>
      <label class="btn-secondary text-xs cursor-pointer inline-block">
        Browse files
        <input
          type="file"
          class="hidden"
          accept=".pdf,.md,.txt,.markdown"
          onChange={handleFileInput}
          multiple
        />
      </label>
    </div>
  );
}
