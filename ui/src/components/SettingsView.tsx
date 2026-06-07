import { createSignal, onMount } from 'solid-js';
import { projectStore } from '../stores/projectStore';

export default function SettingsView() {
  const [backendUrl, setBackendUrl] = createSignal('http://127.0.0.1:8765');
  const [theme, setTheme] = createSignal('dark');

  onMount(() => {
    const saved = localStorage.getItem('cineforge_backend_url');
    if (saved) setBackendUrl(saved);
    const savedTheme = localStorage.getItem('cineforge_theme') || 'dark';
    setTheme(savedTheme);
  });

  const saveBackendUrl = (value: string) => {
    setBackendUrl(value);
    localStorage.setItem('cineforge_backend_url', value);
  };

  const saveTheme = (value: string) => {
    setTheme(value);
    localStorage.setItem('cineforge_theme', value);
  };

  return (
    <div class="flex-1 overflow-y-auto p-6">
      <div class="max-w-xl mx-auto space-y-6">
        <h1 class="text-lg font-semibold">Settings</h1>

        <section class="panel p-4 space-y-3">
          <h2 class="text-sm font-medium text-muted uppercase tracking-wider">Connection</h2>
          <div>
            <label class="label">Backend URL</label>
            <input
              type="text"
              class="input"
              value={backendUrl()}
              onInput={(e) => saveBackendUrl(e.currentTarget.value)}
              aria-label="Backend URL"
            />
            <p class="text-[11px] text-muted mt-1">
              The base URL of the CineForge backend API.
            </p>
          </div>
        </section>

        <section class="panel p-4 space-y-3">
          <h2 class="text-sm font-medium text-muted uppercase tracking-wider">Appearance</h2>
          <div>
            <label class="label">Theme</label>
            <div class="flex gap-2">
              <button
                class={`btn-secondary text-xs ${theme() === 'dark' ? 'ring-1 ring-accent' : ''}`}
                onClick={() => saveTheme('dark')}
                aria-pressed={theme() === 'dark'}
              >
                Dark
              </button>
              <button
                class={`btn-secondary text-xs ${theme() === 'light' ? 'ring-1 ring-accent' : ''}`}
                onClick={() => saveTheme('light')}
                aria-pressed={theme() === 'light'}
              >
                Light
              </button>
              <button
                class={`btn-secondary text-xs ${theme() === 'system' ? 'ring-1 ring-accent' : ''}`}
                onClick={() => saveTheme('system')}
                aria-pressed={theme() === 'system'}
              >
                System
              </button>
            </div>
          </div>
        </section>

        <section class="panel p-4 space-y-3">
          <h2 class="text-sm font-medium text-muted uppercase tracking-wider">Project Defaults</h2>
          <div class="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span class="text-muted">Default Profile</span>
              <div class="text-white">{projectStore.state.stackDefaults?.routing_profile || 'hybrid'}</div>
            </div>
            <div>
              <span class="text-muted">Style Packs Loaded</span>
              <div class="text-white">{projectStore.state.stylePacks.length}</div>
            </div>
          </div>
        </section>

        <section class="panel p-4 space-y-3">
          <h2 class="text-sm font-medium text-muted uppercase tracking-wider">About</h2>
          <div class="text-sm text-muted space-y-1">
            <p>CineForge v0.1.0</p>
            <p>MIT License</p>
            <p>
              <a
                href="https://github.com/lumenhelix/cineforge"
                target="_blank"
                rel="noopener noreferrer"
                class="text-accent hover:underline"
              >
                GitHub Repository
              </a>
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
