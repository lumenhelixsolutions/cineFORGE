import { For, Show, createSignal, createEffect } from 'solid-js';
import { projectStore } from '../stores/projectStore';

export default function Inspector() {
  const project = () => projectStore.state.activeProject;
  const selectedShot = () => projectStore.getSelectedShot();
  const stylePacks = () => projectStore.state.stylePacks;

  const [promptText, setPromptText] = createSignal('');
  const [tier, setTier] = createSignal('standard');
  const [budgetOverride, setBudgetOverride] = createSignal<number | ''>('');
  const [stylePack, setStylePack] = createSignal('');
  const [saving, setSaving] = createSignal(false);

  createEffect(() => {
    const shot = selectedShot();
    if (shot) {
      setPromptText(shot.prompt_text || '');
      setTier(shot.tier || 'standard');
      setBudgetOverride(shot.cost_usd ?? '');
      setStylePack(project()?.style_pack_id || '');
    }
  });

  const tokenRate = () => {
    const p = project();
    if (!p || p.tokens_used_input === 0) return 0;
    return (p.tokens_used_cached / p.tokens_used_input).toFixed(2);
  };

  const handleSave = async () => {
    const p = project();
    const shot = selectedShot();
    if (!p || !shot) return;
    setSaving(true);
    try {
      await projectStore.updateShot(p.id, shot.id, {
        prompt_text: promptText(),
        tier: tier(),
        cost_usd: budgetOverride() === '' ? undefined : Number(budgetOverride()),
      });
      if (stylePack()) {
        await projectStore.togglePreviewMode(p.id, p.preview_mode);
        // Update project style pack via project update if desired
        // We skip full project update to avoid side effects; shot update is primary goal
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div class="w-80 border-l border-border bg-panel flex flex-col h-full">
      <div class="p-4 border-b border-border">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-muted">Inspector</h2>
      </div>

      <Show when={project()} fallback={
        <div class="flex-1 flex items-center justify-center text-muted text-xs">
          No project selected
        </div>
      }>
        <div class="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Selected Shot Editor */}
          <Show when={selectedShot()}>
            <div>
              <div class="label">Selected Shot</div>
              <div class="panel p-3 space-y-3">
                <div>
                  <label class="label">Prompt</label>
                  <textarea
                    class="input min-h-[80px] resize-none text-xs"
                    value={promptText()}
                    onInput={(e) => setPromptText(e.currentTarget.value)}
                  />
                </div>
                <div>
                  <label class="label">Tier</label>
                  <select class="input text-xs" value={tier()} onChange={(e) => setTier(e.currentTarget.value)}>
                    <option value="hero">Hero</option>
                    <option value="standard">Standard</option>
                    <option value="broll">B-Roll</option>
                    <option value="title">Title</option>
                  </select>
                </div>
                <div>
                  <label class="label">Budget Override (USD)</label>
                  <input
                    type="number"
                    class="input text-xs"
                    min={0}
                    step={0.01}
                    value={budgetOverride()}
                    onChange={(e) => setBudgetOverride(e.currentTarget.value === '' ? '' : Number(e.currentTarget.value))}
                  />
                </div>
                <div>
                  <label class="label">Style Pack</label>
                  <select class="input text-xs" value={stylePack()} onChange={(e) => setStylePack(e.currentTarget.value)}>
                    <option value="">Default</option>
                    <For each={stylePacks()}>
                      {(pack) => <option value={pack.id || pack.name}>{pack.name || pack.id}</option>}
                    </For>
                  </select>
                </div>
                <button
                  class="btn-primary text-xs w-full"
                  onClick={handleSave}
                  disabled={saving()}
                >
                  {saving() ? 'Saving…' : 'Save'}
                </button>
              </div>
            </div>
          </Show>

          {/* Token Meter */}
          <div>
            <div class="label">Token Ledger</div>
            <div class="panel p-3 space-y-2 text-xs">
              <div class="flex justify-between">
                <span class="text-muted">Input</span>
                <span>{project()?.tokens_used_input?.toLocaleString() || 0}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted">Output</span>
                <span>{project()?.tokens_used_output?.toLocaleString() || 0}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted">Cached</span>
                <span class="text-success">{project()?.tokens_used_cached?.toLocaleString() || 0}</span>
              </div>
              <div class="border-t border-border pt-2 flex justify-between font-medium">
                <span class="text-muted">Cache rate</span>
                <span>{tokenRate()}</span>
              </div>
            </div>
          </div>

          {/* Sources */}
          <div>
            <div class="label">Sources</div>
            <div class="space-y-1">
              <Show when={project()?.sources?.length === 0}>
                <div class="text-xs text-muted">No sources uploaded</div>
              </Show>
              {project()?.sources?.map((s) => (
                <div class="panel p-2 text-xs flex justify-between items-center">
                  <span class="truncate">{s.kind}</span>
                  <span class="text-muted">{s.word_count} words</span>
                </div>
              ))}
            </div>
          </div>

          {/* Style Pack */}
          <div>
            <div class="label">Style Pack</div>
            <div class="text-xs text-white">{project()?.style_pack_id || 'Default'}</div>
          </div>

          {/* Routing Profile */}
          <div>
            <div class="label">Routing Profile</div>
            <div class="text-xs text-white">{project()?.routing_profile}</div>
          </div>

          {/* Budget */}
          <div>
            <div class="label">Budget</div>
            <div class="panel p-2 text-xs flex justify-between">
              <span class="text-muted">Remaining</span>
              <span>${(project()?.budget_usd || 1).toFixed(2)}</span>
            </div>
          </div>

          {/* StackBuilder Quick View */}
          <div>
            <div class="label">StackBuilder</div>
            <Show when={projectStore.state.stackRecommendations.length > 0}>
              <div class="panel p-2 space-y-1">
                <div class="text-[10px] text-muted">Top recommendation:</div>
                <div class="text-xs text-white font-medium">
                  {projectStore.state.stackRecommendations[0]?.name}
                </div>
                <div class="text-[10px] text-accent">
                  Score: {projectStore.state.stackRecommendations[0]?.overall_score}
                </div>
              </div>
            </Show>
            <Show when={projectStore.state.stackRecommendations.length === 0}>
              <div class="text-xs text-muted">Run StackBuilder to see recommendations</div>
            </Show>
          </div>

          {/* Render Queue */}
          <div>
            <div class="label">Render Queue</div>
            <div class="space-y-1">
              {project()?.shots?.filter((s: any) => s.status === 'rendering' || s.status === 'queued').map((s: any) => (
                <div class="panel p-2 text-xs flex items-center gap-2">
                  <span class={`w-1.5 h-1.5 rounded-full ${s.status === 'rendering' ? 'bg-accent animate-pulse' : 'bg-muted'}`} />
                  <span>Shot #{s.order_index + 1}</span>
                  <span class="text-muted ml-auto">{s.status}</span>
                </div>
              )) || <div class="text-xs text-muted">Queue empty</div>}
            </div>
          </div>
        </div>
      </Show>
    </div>
  );
}
