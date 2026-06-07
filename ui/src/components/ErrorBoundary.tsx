import { ErrorBoundary as SolidErrorBoundary, JSX } from 'solid-js';
import { toastStore } from '../stores/toastStore';

function Fallback(props: { error: Error; reset: () => void }) {
  return (
    <div class="fixed inset-0 z-[90] bg-surface flex items-center justify-center p-8">
      <div class="max-w-md w-full panel p-6 space-y-4">
        <h2 class="text-lg font-semibold text-danger">Something went wrong</h2>
        <p class="text-sm text-muted">{props.error.message}</p>
        <pre class="text-xs bg-black/30 p-3 rounded overflow-auto max-h-40 text-muted font-mono">
          {props.error.stack}
        </pre>
        <button class="btn-primary text-sm" onClick={() => props.reset()}>
          Reload
        </button>
      </div>
    </div>
  );
}

export default function AppErrorBoundary(props: { children: JSX.Element }) {
  return (
    <SolidErrorBoundary
      fallback={(err, reset) => {
        toastStore.error(`Runtime error: ${err.message}`);
        return <Fallback error={err} reset={reset} />;
      }}
    >
      {props.children}
    </SolidErrorBoundary>
  );
}
