# CineForge Recovery Script
# Run this from C:\app\cforge\cineforge in PowerShell
$ErrorActionPreference = "Stop"

Write-Host "=== CineForge Recovery ===" -ForegroundColor Cyan

# --- Fix 1: App.tsx (JSX fragment wrapper) ---
$appTsx = @'
import { createSignal, onMount, Show } from 'solid-js';
import ProjectTree from './components/ProjectTree';
import Storyboard from './components/Storyboard';
import Inspector from './components/Inspector';
import CommandPalette from './components/CommandPalette';
import TreatmentView from './components/TreatmentView';
import TimelineView from './components/TimelineView';
import PreviewPlayer from './components/PreviewPlayer';
import StackBuilder from './components/StackBuilder';
import OnboardingWizard from './components/OnboardingWizard';
import { projectStore } from './stores/projectStore';

type Tab = 'sources' | 'storyboard' | 'timeline' | 'preview' | 'stackbuilder';

export default function App() {
  const [activeTab, setActiveTab] = createSignal<Tab>('storyboard');
  const [onboardingDone, setOnboardingDone] = createSignal(
    localStorage.getItem('cineforge_onboarding_done') === 'true'
  );

  const completeOnboarding = () => {
    localStorage.setItem('cineforge_onboarding_done', 'true');
    setOnboardingDone(true);
    projectStore.loadProjects();
    projectStore.loadCapabilities();
    projectStore.loadStylePacks();
  };

  onMount(() => {
    if (onboardingDone()) {
      projectStore.loadProjects();
      projectStore.loadCapabilities();
      projectStore.loadStylePacks();
    }
  });

  const tabs: { id: Tab; label: string }[] = [
    { id: 'sources', label: 'Sources' },
    { id: 'storyboard', label: 'Storyboard' },
    { id: 'timeline', label: 'Timeline' },
    { id: 'preview', label: 'Preview' },
    { id: 'stackbuilder', label: 'StackBuilder' },
  ];

  return (
    <>
      <Show when={!onboardingDone()}>
        <OnboardingWizard onComplete={completeOnboarding} />
      </Show>
      <div class="flex h-screen w-screen bg-surface text-white overflow-hidden">
        <ProjectTree />
        <div class="flex-1 flex flex-col min-w-0">
          <div class="flex items-center border-b border-border bg-panel px-4">
            {tabs.map((tab) => (
              <button
                class={`px-4 py-2.5 text-xs font-medium transition-colors border-b-2 ${
                  activeTab() === tab.id
                    ? 'text-white border-accent'
                    : 'text-muted border-transparent hover:text-white'
                }`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
            <div class="flex-1" />
            <div class="text-[10px] text-muted font-mono">
              <Show when={projectStore.state.activeProject}>
                {projectStore.state.activeProject!.name}
              </Show>
            </div>
          </div>
          <div class="flex-1 overflow-hidden">
            <Show when={activeTab() === 'sources'}>
              <TreatmentView />
            </Show>
            <Show when={activeTab() === 'storyboard'}>
              <Storyboard />
            </Show>
            <Show when={activeTab() === 'timeline'}>
              <TimelineView />
            </Show>
            <Show when={activeTab() === 'preview'}>
              <PreviewPlayer />
            </Show>
            <Show when={activeTab() === 'stackbuilder'}>
              <StackBuilder />
            </Show>
          </div>
        </div>
        <Inspector />
        <CommandPalette />
      </div>
    </>
  );
}
'@
Set-Content -Path "ui/src/App.tsx" -Value $appTsx -Encoding utf8
Write-Host "Fixed ui/src/App.tsx" -ForegroundColor Green

# --- Fix 2: API client (relative paths + Vite proxy) ---
$apiTs = @'
const API_BASE = "/api";

async function apiFetch(path: string, options?: RequestInit) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  health: () => apiFetch("/health"),
  diagnostics: () => apiFetch("/diagnostics"),
  capabilities: () => apiFetch("/capabilities"),
  getProjects: () => apiFetch("/projects"),
  createProject: (data: any) => apiFetch("/projects", { method: "POST", body: JSON.stringify(data) }),
  getStylePacks: () => apiFetch("/prefabs/style-packs"),
  getGrammars: () => apiFetch("/prefabs/grammars"),
  recommendStack: (data: any) => apiFetch("/stackbuilder/recommend", { method: "POST", body: JSON.stringify(data) }),
  getTopics: () => apiFetch("/stackbuilder/topics"),
  getProfile: (name: string) => apiFetch(`/stackbuilder/profiles/${name}`),
};
'@
Set-Content -Path "ui/src/lib/api.ts" -Value $apiTs -Encoding utf8
Write-Host "Fixed ui/src/lib/api.ts" -ForegroundColor Green

# --- Fix 3: Vite config (add proxy, backup old) ---
Copy-Item "ui/vite.config.ts" "ui/vite.config.ts.backup" -ErrorAction SilentlyContinue
$viteConfig = @'
import { defineConfig } from 'vite';
import solid from 'vite-plugin-solid';

export default defineConfig({
  plugins: [solid()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
'@
Set-Content -Path "ui/vite.config.ts" -Value $viteConfig -Encoding utf8
Write-Host "Fixed ui/vite.config.ts (proxy added)" -ForegroundColor Green

# --- Fix 4: PostCSS / Tailwind config names ---
cd ui
if (Test-Path "postcss.config.js") { Rename-Item "postcss.config.js" "postcss.config.cjs" -Force }
if (Test-Path "tailwind.config.js") { Rename-Item "tailwind.config.js" "tailwind.config.cjs" -Force }
cd ..
Write-Host "Config files renamed to .cjs" -ForegroundColor Green

# --- Fix 5: Patch backend CORS ---
$patchPy = @'
import re, sys

with open('backend/app.py', 'r') as f:
    content = f.read()

if 'from fastapi.middleware.cors import CORSMiddleware' not in content:
    content = content.replace(
        'from fastapi import ',
        'from fastapi.middleware.cors import CORSMiddleware\nfrom fastapi import '
    )

content = re.sub(
    r'app\.add_middleware\(\s*CORSMiddleware,[^)]+\)\s*\n*',
    '',
    content,
    flags=re.DOTALL
)

cors_block = '''app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

''' 

pattern = r'(app\s*=\s*FastAPI\s*\([^)]*\)\n)'
if re.search(pattern, content):
    content = re.sub(pattern, r'\1' + cors_block, content, count=1)
else:
    print("ERROR: Could not find app = FastAPI()")
    sys.exit(1)

with open('backend/app.py', 'w') as f:
    f.write(content)

print("backend/app.py patched successfully")
'@
Set-Content -Path "patch_backend.py" -Value $patchPy -Encoding utf8
.\.venv\Scripts\python.exe patch_backend.py
Write-Host "Patched backend CORS" -ForegroundColor Green

# --- Fix 6: Clear Python cache ---
Get-ChildItem -Recurse -Filter '__pycache__' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Filter '*.pyc' | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "Cleared Python cache" -ForegroundColor Green

Write-Host "`n=== All fixes applied. ===" -ForegroundColor Cyan
Write-Host "Start backend:   .\.venv\Scripts\Activate.ps1 ; python -m backend.app"
Write-Host "Start frontend:  cd ui ; npm run dev"
Write-Host "Open browser:    http://localhost:5173"
Write-Host "`nIf anything fails, your original vite.config.ts is backed up as vite.config.ts.backup"