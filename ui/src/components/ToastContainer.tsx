import { For } from 'solid-js';
import { toastStore } from '../stores/toastStore';

const typeClasses: Record<string, string> = {
  success: 'bg-success/20 border-success text-success',
  error: 'bg-danger/20 border-danger text-danger',
  info: 'bg-accent/20 border-accent text-accent',
  warning: 'bg-yellow-500/20 border-yellow-500 text-yellow-400',
};

export default function ToastContainer() {
  return (
    <div class="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
      <For each={toastStore.state.toasts}>
        {(toast) => (
          <div
            class={`pointer-events-auto px-4 py-3 rounded-lg border shadow-lg text-sm backdrop-blur-sm ${typeClasses[toast.type] || typeClasses.info}`}
            role="alert"
          >
            <div class="flex items-center gap-2">
              <span class="font-medium">{toast.message}</span>
              <button
                class="ml-2 opacity-70 hover:opacity-100 text-xs"
                onClick={() => toastStore.remove(toast.id)}
                aria-label="Dismiss"
              >
                ✕
              </button>
            </div>
          </div>
        )}
      </For>
    </div>
  );
}
