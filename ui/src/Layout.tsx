import { Show, createSignal, onMount } from 'solid-js';
import type { RouteSectionProps } from '@solidjs/router';
import { useLocation, useNavigate } from '@solidjs/router';
import ProjectTree from './components/ProjectTree';
import Inspector from './components/Inspector';
import CommandPalette from './components/CommandPalette';
import OnboardingWizard from './components/OnboardingWizard';
import ToastContainer from './components/ToastContainer';
import AppErrorBoundary from './components/ErrorBoundary';
import ShortcutsModal from './components/ShortcutsModal';
import KeyboardShortcuts from './components/KeyboardShortcuts';
import { projectStore } from './stores/projectStore';

type Tab = 'sources' | 'storyboard' | 'timeline' | 'preview' | 'trailer' | 'stackbuilder' | 'export';

const tabs: { id: Tab; label: string }[] = [
  { id: 'sources', label: 'Sources' },
  { id: 'storyboard', label: 'Storyboard' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'preview', label: 'Preview' },
  { id: 'trailer', label: 'Trailer' },
  { id: 'export', label: 'Export' },
  { id: 'stackbuilder', label: 'StackBuilder' },
];

export default function Layout(props: RouteSectionProps) {
  const location = useLocation();
  const navigate = useNavigate();

  const [onboardingDone, setOnboardingDone] = createSignal(
    localStorage.getItem('cineforge_onboarding_done') === 'true'
  );

  const [mobileMenuOpen, setMobileMenuOpen] = createSignal(false);

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

  const isStackBuilderRoute = () => location.pathname === '/stackbuilder';
  const isSettingsRoute = () => location.pathname === '/settings';

  const currentTab = () => {
    if (isStackBuilderRoute()) return 'stackbuilder' as Tab;
    return projectStore.state.activeTab;
  };

  const handleTabClick = (tab: Tab) => {
    setMobileMenuOpen(false);
    if (tab === 'stackbuilder') {
      navigate('/stackbuilder');
      return;
    }
    if (isStackBuilderRoute() || isSettingsRoute()) {
      const projectId = projectStore.state.activeProject?.id;
      if (projectId) {
        navigate(`/project/${projectId}`);
      }
    }
    projectStore.setActiveTab(tab);
  };

  return (
    <AppErrorBoundary>
      <KeyboardShortcuts />
      <ShortcutsModal />
      <Show when={!onboardingDone()}>
        <OnboardingWizard onComplete={completeOnboarding} />
      </Show>
      <div class="flex h-screen w-screen bg-surface text-white overflow-hidden">
        <ProjectTree />
        <div class="flex-1 flex flex-col min-w-0">
          {/* Desktop nav */}
          <div class="hidden md:flex items-center border-b border-border bg-panel px-4" role="tablist" aria-label="Main tabs">
            {tabs.map((tab) => (
              <button
                class={`px-4 py-2.5 text-xs font-medium transition-colors border-b-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:rounded ${
                  currentTab() === tab.id
                    ? 'text-white border-accent'
                    : 'text-muted border-transparent hover:text-white'
                }`}
                onClick={() => handleTabClick(tab.id)}
                role="tab"
                aria-selected={currentTab() === tab.id}
                aria-label={tab.label}
              >
                {tab.label}
              </button>
            ))}
            <div class="flex-1" />
            <button
              class="text-[10px] text-muted font-mono hover:text-white transition-colors mr-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:rounded"
              onClick={() => navigate('/settings')}
              aria-label="Open settings"
              title="Settings (⌘,)"
            >
              ⚙ Settings
            </button>
            <div class="text-[10px] text-muted font-mono" aria-label={`Active project: ${projectStore.state.activeProject?.name || 'None'}`}>
              <Show when={projectStore.state.activeProject}>
                {projectStore.state.activeProject!.name}
              </Show>
            </div>
          </div>

          {/* Mobile nav */}
          <div class="md:hidden flex items-center justify-between border-b border-border bg-panel px-3 py-2">
            <button
              class="p-2 rounded hover:bg-panel/80 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen())}
              aria-label="Toggle navigation menu"
              aria-expanded={mobileMenuOpen()}
              aria-controls="mobile-menu"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <Show when={!mobileMenuOpen()}>
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                </Show>
                <Show when={mobileMenuOpen()}>
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </Show>
              </svg>
            </button>
            <span class="text-xs font-medium truncate" aria-label={`Active project: ${projectStore.state.activeProject?.name || 'None'}`}>
              {projectStore.state.activeProject?.name || 'cineFORGE'}
            </span>
            <button
              class="p-2 rounded hover:bg-panel/80 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              onClick={() => navigate('/settings')}
              aria-label="Open settings"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          </div>

          {/* Mobile menu dropdown */}
          <Show when={mobileMenuOpen()}>
            <div id="mobile-menu" class="md:hidden border-b border-border bg-panel px-3 py-2 space-y-1" role="menu">
              {tabs.map((tab) => (
                <button
                  class={`block w-full text-left px-3 py-2 text-xs font-medium rounded transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                    currentTab() === tab.id
                      ? 'text-white bg-accent/10'
                      : 'text-muted hover:text-white hover:bg-panel/80'
                  }`}
                  onClick={() => handleTabClick(tab.id)}
                  role="menuitem"
                  aria-label={tab.label}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </Show>

          <div class="flex-1 overflow-hidden">
            {props.children}
          </div>
        </div>
        <Inspector />
        <CommandPalette />
        <ToastContainer />
      </div>
    </AppErrorBoundary>
  );
}
