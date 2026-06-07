import { createEffect, onCleanup } from 'solid-js';
import { useLocation, useNavigate } from '@solidjs/router';
import { projectStore } from '../stores/projectStore';
import { toastStore } from '../stores/toastStore';

export default function KeyboardShortcuts() {
  const location = useLocation();
  const navigate = useNavigate();

  const handleKeyDown = (e: KeyboardEvent) => {
    const tag = (e.target as HTMLElement)?.tagName;
    const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable;

    // Cmd+K is handled by CommandPalette

    if (isInput) return;

    const activeProject = projectStore.state.activeProject;
    const shots = activeProject?.shots || [];
    const selectedShotId = projectStore.state.selectedShotId;

    if (e.key === 'r' || e.key === 'R') {
      e.preventDefault();
      if (activeProject) {
        projectStore.render(activeProject.id);
      } else {
        toastStore.warning('No project selected');
      }
    }

    if (e.key === 's' || e.key === 'S') {
      e.preventDefault();
      if (activeProject) {
        projectStore.stitch(activeProject.id);
      } else {
        toastStore.warning('No project selected');
      }
    }

    if (e.key === 'n' || e.key === 'N') {
      e.preventDefault();
      const name = prompt('Project name:');
      if (name) projectStore.createProject(name);
    }

    if (e.key === 'ArrowRight') {
      e.preventDefault();
      if (shots.length > 0) {
        const idx = shots.findIndex((s) => s.id === selectedShotId);
        const next = shots[Math.min(idx + 1, shots.length - 1)];
        projectStore.selectShot(next.id);
      }
    }

    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      if (shots.length > 0) {
        const idx = shots.findIndex((s) => s.id === selectedShotId);
        const prev = shots[Math.max(idx - 1, 0)];
        projectStore.selectShot(prev.id);
      }
    }
  };

  createEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    onCleanup(() => window.removeEventListener('keydown', handleKeyDown));
  });

  return null;
}
