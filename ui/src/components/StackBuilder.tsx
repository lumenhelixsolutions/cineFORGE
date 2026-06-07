import { createSignal, For, Show } from 'solid-js';
import { api } from '../lib/api';

interface ProfileScore {
  name: string;
  overall_score: number;
  dimension_scores: Record<string, number>;
  recommendation: string;
  warnings: string[];
  description: string;
  primary_use_case: string;
}

export default function StackBuilder() {
  const [topic, setTopic] = createSignal('documentary');
  const [duration, setDuration] = createSignal(3);
  const [budget, setBudget] = createSignal(5);
  const [deadline, setDeadline] = createSignal(24);
  const [vram, setVram] = createSignal(0);
  const [prioritize, setPrioritize] = createSignal('balanced');
  const [recommendations, setRecommendations] = createSignal<ProfileScore[]>([]);
  const [defaults, setDefaults] = createSignal<any>(null);
  const [loading, setLoading] = createSignal(false);

  const topics = [
    { id: 'documentary', label: 'Documentary' },
    { id: 'explainer', label: 'Explainer / Educational' },
    { id: 'archival', label: 'Archival / Historical' },
    { id: 'news', label: 'News / Breaking' },
    { id: 'research', label: 'Research / Science' },
    { id: 'tutorial', label: 'Tutorial' },
    { id: 'historical', label: 'Historical' },
    { id: 'cinematic', label: 'Cinematic (Advanced)' },
  ];

  const prioritizeOptions = [
    { id: 'balanced', label: 'Balanced' },
    { id: 'quality', label: 'Quality First' },
    { id: 'speed', label: 'Speed First' },
    { id: 'cost', label: 'Lowest Cost' },
    { id: 'depth', label: 'Depth / Detail' },
  ];

  const runRecommendation = async () => {
    setLoading(true);
    try {
      const result = await api.stackbuilder.recommend({
        topic: topic(),
        target_duration_min: duration(),
        budget_usd: budget(),
        deadline_hours: deadline(),
        vram_available_gb: vram(),
        prioritize: prioritize(),
        source_count: 1,
        word_count: 0,
      });
      setRecommendations(result.recommendations);
      setDefaults(result.defaults);
    } catch (err: any) {
      console.error('StackBuilder failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const recBadge = (rec: string) => {
    if (rec === 'strong_match') return 'bg-success/20 text-success';
    if (rec === 'viable') return 'bg-accent/20 text-accent';
    return 'bg-danger/20 text-danger';
  };

  const recLabel = (rec: string) => {
    if (rec === 'strong_match') return 'Strong Match';
    if (rec === 'viable') return 'Viable';
    return 'Not Recommended';
  };

  return (
    <div class="w-full max-w-3xl mx-auto p-6 space-y-6">
      <div class="border-b border-border pb-4">
        <h2 class="text-lg font-semibold">StackBuilder</h2>
        <p class="text-sm text-muted mt-1">
          Intelligent profile selection based on your project constraints.
          v0.1 is optimized for documentary and informational content.
        </p>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="label">Topic</label>
          <select class="input" value={topic()} onChange={(e) => setTopic(e.currentTarget.value)}>
            <For each={topics}>
              {(t) => <option value={t.id}>{t.label}</option>}
            </For>
          </select>
        </div>
        <div>
          <label class="label">Prioritize</label>
          <select class="input" value={prioritize()} onChange={(e) => setPrioritize(e.currentTarget.value)}>
            <For each={prioritizeOptions}>
              {(p) => <option value={p.id}>{p.label}</option>}
            </For>
          </select>
        </div>
        <div>
          <label class="label">Target Duration (min)</label>
          <input type="number" class="input" min="0.5" max="20" step="0.5"
                 value={duration()} onChange={(e) => setDuration(Number(e.currentTarget.value))} />
        </div>
        <div>
          <label class="label">Budget (USD)</label>
          <input type="number" class="input" min="0" max="50" step="1"
                 value={budget()} onChange={(e) => setBudget(Number(e.currentTarget.value))} />
        </div>
        <div>
          <label class="label">Deadline (hours)</label>
          <input type="number" class="input" min="0.5" max="72" step="0.5"
                 value={deadline()} onChange={(e) => setDeadline(Number(e.currentTarget.value))} />
        </div>
        <div>
          <label class="label">GPU VRAM (GB, 0 = none)</label>
          <input type="number" class="input" min="0" max="48" step="1"
                 value={vram()} onChange={(e) => setVram(Number(e.currentTarget.value))} />
        </div>
      </div>

      <button class="btn-primary w-full" onClick={runRecommendation} disabled={loading()}>
        {loading() ? 'Analyzing...' : 'Recommend Stack'}
      </button>

      <Show when={defaults()}>
        <div class="panel p-3 text-xs">
          <div class="text-muted mb-1">Defaults for <span class="text-white">{topic()}</span>:</div>
          <div class="flex gap-4">
            <span>Style: <span class="text-accent">{defaults().style_pack}</span></span>
            <span>Grammar: <span class="text-accent">{defaults().grammar}</span></span>
          </div>
        </div>
      </Show>

      <Show when={recommendations().length > 0}>
        <div class="space-y-3">
          <h3 class="text-sm font-medium text-muted uppercase tracking-wider">Ranked Recommendations</h3>
          <For each={recommendations()}>
            {(rec, index) => (
              <div class={`panel p-4 ${index() === 0 ? 'border-accent/50' : ''}`}>
                <div class="flex items-center justify-between mb-2">
                  <div class="flex items-center gap-3">
                    <span class="text-lg font-bold text-white">#{index() + 1}</span>
                    <span class="font-medium">{rec.name}</span>
                    <span class={`text-[10px] px-2 py-0.5 rounded font-medium ${recBadge(rec.recommendation)}`}>
                      {recLabel(rec.recommendation)}
                    </span>
                  </div>
                  <span class="text-sm font-mono text-white">{rec.overall_score.toFixed(2)}</span>
                </div>

                <p class="text-xs text-muted mb-2">{rec.description}</p>
                <p class="text-[10px] text-muted mb-2">{rec.primary_use_case}</p>

                <div class="grid grid-cols-5 gap-2 text-[10px] mb-2">
                  <div class="text-center">
                    <div class="text-muted">Quality</div>
                    <div class="text-white">{(rec.dimension_scores.quality * 100).toFixed(0)}%</div>
                  </div>
                  <div class="text-center">
                    <div class="text-muted">Speed</div>
                    <div class="text-white">{(rec.dimension_scores.speed * 100).toFixed(0)}%</div>
                  </div>
                  <div class="text-center">
                    <div class="text-muted">Cost</div>
                    <div class="text-white">{(rec.dimension_scores.cost * 100).toFixed(0)}%</div>
                  </div>
                  <div class="text-center">
                    <div class="text-muted">Depth</div>
                    <div class="text-white">{(rec.dimension_scores.depth * 100).toFixed(0)}%</div>
                  </div>
                  <div class="text-center">
                    <div class="text-muted">Compat</div>
                    <div class="text-white">{(rec.dimension_scores.compat * 100).toFixed(0)}%</div>
                  </div>
                </div>

                <Show when={rec.warnings.length > 0}>
                  <div class="space-y-1">
                    <For each={rec.warnings}>
                      {(w) => (
                        <div class="text-[10px] text-danger flex items-center gap-1">
                          <span>⚠</span> {w}
                        </div>
                      )}
                    </For>
                  </div>
                </Show>
              </div>
            )}
          </For>
        </div>
      </Show>
    </div>
  );
}
