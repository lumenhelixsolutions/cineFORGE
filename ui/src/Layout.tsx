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

type Tab = 'sources' | 'storyboard' | 'timeline' | 'preview' | 'stackbuilder';

const tabs: { id: Tab; label: string }[] = [
  { id: 'sources', label: 'Sources' },
  { id: 'storyboard', label: 'Storyboard' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'preview', label: 'Preview' },
  { id: 'stackbuilder', label: 'StackBuilder' },
];

export default function Layout(props: RouteSectionProps) {
  const location = useLocation();
  const navigate = useNavigate();

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

  const isStackBuilderRoute = () => location.pathname === '/stackbuilder';
  const isSettingsRoute = () => location.pathname === '/settings';

  const currentTab = () => {
    if (isStackBuilderRoute()) return 'stackbuilder' as Tab;
    return projectStore.state.activeTab;
  };

  const handleTabClick = (tab: Tab) => {
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
          <div class="flex items-center border-b border-border bg-panel px-4" role="tablist" aria-label="Main tabs">
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
            <div class="text-[10px] text-muted font-mono">
              <Show when={projectStore.state.activeProject}>
                {projectStore.state.activeProject!.name}
              </Show>
            </div>
          </div>
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
