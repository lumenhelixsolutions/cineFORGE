import { describe, it, expect, beforeEach, vi } from 'vitest';
import { projectStore, setState, state } from '../projectStore';

vi.mock('../../lib/api', () => ({
  api: {
    projects: {
      list: vi.fn().mockResolvedValue([
        { id: 'p1', name: 'Alpha', shots: [], sources: [], aspect_ratio: '16:9', target_duration_sec: 60, style_pack_id: null, routing_profile: 'hybrid', preview_mode: false, budget_usd: 5, tokens_used_input: 0, tokens_used_output: 0, tokens_used_cached: 0 },
      ]),
      get: vi.fn().mockResolvedValue({
        id: 'p1', name: 'Alpha', shots: [], sources: [], aspect_ratio: '16:9', target_duration_sec: 60, style_pack_id: null, routing_profile: 'hybrid', preview_mode: false, budget_usd: 5, tokens_used_input: 0, tokens_used_output: 0, tokens_used_cached: 0,
      }),
      create: vi.fn().mockResolvedValue({ id: 'p2', name: 'Beta' }),
      update: vi.fn().mockResolvedValue({}),
      delete: vi.fn().mockResolvedValue({}),
    },
    shots: {
      update: vi.fn().mockResolvedValue({}),
    },
    capabilities: vi.fn().mockResolvedValue({}),
    prefabs: {
      stylePacks: vi.fn().mockResolvedValue([]),
    },
    sources: {
      upload: vi.fn().mockResolvedValue({}),
    },
    director: {
      treatment: vi.fn().mockResolvedValue({}),
      storyboard: vi.fn().mockResolvedValue({}),
    },
    render: {
      shots: vi.fn().mockResolvedValue({}),
      stitch: vi.fn().mockResolvedValue({}),
    },
    stackbuilder: {
      recommend: vi.fn().mockResolvedValue({ recommendations: [], defaults: {} }),
    },
  },
}));

describe('projectStore', () => {
  beforeEach(() => {
    setState({
      projects: [],
      activeProject: null,
      selectedShotId: null,
      loading: false,
      error: null,
      capabilities: {},
      stylePacks: [],
      commandPaletteOpen: false,
      stackRecommendations: [],
      stackDefaults: null,
    });
  });

  it('loads projects into state', async () => {
    await projectStore.loadProjects();
    expect(state.projects.length).toBe(1);
    expect(state.projects[0].name).toBe('Alpha');
  });

  it('selects a shot', () => {
    projectStore.selectShot('shot-1');
    expect(state.selectedShotId).toBe('shot-1');
  });

  it('updates active project when loaded', async () => {
    await projectStore.loadProject('p1');
    expect(state.activeProject).not.toBeNull();
    expect(state.activeProject?.name).toBe('Alpha');
  });
});
