import { createStore } from 'solid-js/store';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

interface ToastState {
  toasts: Toast[];
}

const [state, setState] = createStore<ToastState>({
  toasts: [],
});

let idCounter = 0;

export const toastStore = {
  state,

  add(message: string, type: ToastType = 'info', duration = 4000) {
    const id = `toast-${++idCounter}`;
    setState('toasts', (prev) => [...prev, { id, message, type, duration }]);
    if (duration > 0) {
      setTimeout(() => {
        this.remove(id);
      }, duration);
    }
    return id;
  },

  remove(id: string) {
    setState('toasts', (prev) => prev.filter((t) => t.id !== id));
  },

  success(message: string, duration?: number) {
    return this.add(message, 'success', duration);
  },

  error(message: string, duration?: number) {
    return this.add(message, 'error', duration);
  },

  info(message: string, duration?: number) {
    return this.add(message, 'info', duration);
  },

  warning(message: string, duration?: number) {
    return this.add(message, 'warning', duration);
  },
};
