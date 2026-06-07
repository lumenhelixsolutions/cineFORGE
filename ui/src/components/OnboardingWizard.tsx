import { createSignal, For, Show, onMount } from 'solid-js';
import { api } from '../lib/api';

interface Check {
  name: string;
  status: string;
  message: string;
  fix: string;
}

interface DiagnosticReport {
  overall_status: string;
  summary: { ok: number; warning: number; error: number; total: number };
  checks: Check[];
  next_steps: string[];
}

export default function OnboardingWizard(props: { onComplete: () => void }) {
  const [report, setReport] = createSignal<DiagnosticReport | null>(null);
  const [loading, setLoading] = createSignal(true);
  const [expanded, setExpanded] = createSignal<string | null>(null);

  onMount(async () => {
    await runDiagnostics();
  });

  const runDiagnostics = async () => {
    setLoading(true);
    try {
      const result = await api.diagnostics();
      setReport(result);
    } catch (err: any) {
      setReport({
        overall_status: "blocked",
        summary: { ok: 0, warning: 0, error: 1, total: 1 },
        checks: [{
          name: "Diagnostics Endpoint",
          status: "error",
          message: `Cannot reach backend: ${err.message}`,
          fix: "Ensure backend is running: python -m backend.app",
        }],
        next_steps: ["Ensure backend is running: python -m backend.app"],
      });
    } finally {
      setLoading(false);
    }
  };

  const statusColor = (status: string) => {
    if (status === "ok") return "bg-success";
    if (status === "warning") return "bg-accent";
    return "bg-danger";
  };

  const statusIcon = (status: string) => {
    if (status === "ok") return "✓";
    if (status === "warning") return "⚠";
    return "✗";
  };

  const overallColor = () => {
    const s = report()?.overall_status;
    if (s === "ready") return "border-success text-success";
    if (s === "needs_attention") return "border-accent text-accent";
    return "border-danger text-danger";
  };

  return (
    <div class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="w-full max-w-2xl bg-panel border border-border rounded-lg shadow-2xl overflow-hidden">
        {/* Header */}
        <div class="p-6 border-b border-border">
          <div class="flex items-center justify-between">
            <div>
              <h1 class="text-xl font-semibold">CineForge Setup</h1>
              <p class="text-sm text-muted mt-1">
                Running system diagnostics before first use...
              </p>
            </div>
            <Show when={report()}>
              <div class={`px-3 py-1 rounded border text-xs font-medium uppercase ${overallColor()}`}>
                {report()!.overall_status.replace("_", " ")}
              </div>
            </Show>
          </div>
        </div>

        {/* Progress / Loading */}
        <Show when={loading()}>
          <div class="p-8 text-center">
            <div class="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p class="text-sm text-muted">Checking system components...</p>
          </div>
        </Show>

        {/* Results */}
        <Show when={!loading() && report()}>
          <div class="p-4 space-y-2 max-h-96 overflow-y-auto">
            <For each={report()!.checks}>
              {(check) => (
                <div
                  class={`panel p-3 cursor-pointer transition-colors hover:bg-surface ${
                    expanded() === check.name ? 'ring-1 ring-accent/40' : ''
                  }`}
                  onClick={() => setExpanded(expanded() === check.name ? null : check.name)}
                >
                  <div class="flex items-center gap-3">
                    <span class={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white ${statusColor(check.status)}`}>
                      {statusIcon(check.status)}
                    </span>
                    <span class="font-medium text-sm">{check.name}</span>
                    <span class={`text-xs ml-auto ${check.status === 'ok' ? 'text-muted' : check.status === 'warning' ? 'text-accent' : 'text-danger'}`}>
                      {check.status}
                    </span>
                  </div>
                  <Show when={expanded() === check.name}>
                    <div class="mt-2 pl-9 text-xs space-y-1">
                      <p class="text-muted">{check.message}</p>
                      <Show when={check.fix}>
                        <div class="mt-2 p-2 bg-surface rounded border border-border">
                          <div class="text-muted mb-1">Fix:</div>
                          <code class="text-accent font-mono">{check.fix}</code>
                        </div>
                      </Show>
                    </div>
                  </Show>
                </div>
              )}
            </For>
          </div>

          {/* Summary & Actions */}
          <div class="p-4 border-t border-border bg-surface/50">
            <div class="flex items-center justify-between mb-3">
              <div class="text-xs text-muted">
                {report()!.summary.ok} passed · {report()!.summary.warning} warnings · {report()!.summary.error} errors
              </div>
              <button
                class="btn-secondary text-xs"
                onClick={runDiagnostics}
              >
                Re-run Diagnostics
              </button>
            </div>

            <Show when={report()!.next_steps.length > 0}>
              <div class="mb-3">
                <div class="text-xs text-muted mb-1">Required fixes:</div>
                <div class="space-y-1">
                  <For each={report()!.next_steps}>
                    {(step) => (
                      <div class="text-xs text-danger font-mono bg-danger/10 p-2 rounded">
                        {step}
                      </div>
                    )}
                  </For>
                </div>
              </div>
            </Show>

            <div class="flex gap-2">
              <Show when={report()!.overall_status !== "blocked"}>
                <button
                  class="btn-primary flex-1"
                  onClick={props.onComplete}
                >
                  Continue to App
                </button>
              </Show>
              <Show when={report()!.overall_status === "blocked"}>
                <button
                  class="btn-secondary flex-1 opacity-50 cursor-not-allowed"
                  disabled
                >
                  Fix Errors Above to Continue
                </button>
              </Show>
            </div>
          </div>
        </Show>
      </div>
    </div>
  );
}
