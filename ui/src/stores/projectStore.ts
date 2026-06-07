import { createStore } from 'solid-js/store';
import { api } from '../lib/api';
import { toastStore } from './toastStore';

export interface Project {
  id: string;
  name: string;
  created_at: string;
  status?: string;
  shot_count?: number;
  aspect_ratio: string;
  target_duration_sec: number;
  style_pack_id: string | null;
  routing_profile: string;
  preview_mode: boolean;
  budget_usd: number;
  tokens_used_input: number;
  tokens_used_output: number;
  tokens_used_cached: number;
  shots: Shot[];
  sources: Source[];
  treatments?: unknown[];
}

export interface Source {
  id: string;
  kind: string;
  word_count: number;
}

export interface Shot {
  id: string;
  order_index: number;
  duration_sec: number;
  tier: string;
  status: string;
  prompt_text: string;
  bridge_strategy: string;
  clip_path: string | null;
  cost_usd: number;
}

export interface BrollClip {
  id: string;
  shot_id: string;
  project_id: string;
  status: string;
  clip_path: string | null;
  thumbnail_path: string | null;
  prompt_text: string;
  cost_usd: number;
  provider_id: string | null;
  duration_sec: number;
  metadata: Record<string, any>;
  created_at: string;
}

interface StoreState {
  projects: Project[];
  activeProject: Project | null;
  selectedShotId: string | null;
  loading: boolean;
  error: string | null;
  capabilities: Record<string, any>;
  stylePacks: any[];
  commandPaletteOpen: boolean;
  stackRecommendations: any[];
  stackDefaults: any | null;
  activeTab: 'sources' | 'storyboard' | 'timeline' | 'preview' | 'trailer' | 'stackbuilder' | 'export';
  brollClips: Record<string, BrollClip[]>;
}

export const [state, setState] = createStore<StoreState>({
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
  activeTab: 'storyboard',
  brollClips: {},
});

export const projectStore = {
  state,

  async loadProjects() {
    setState('loading', true);
    try {
      const projects = await api.projects.list();
      setState('projects', projects);
    } catch (err: any) {
      setState('error', err.message);
      toastStore.error(`Failed to load projects: ${err.message}`);
    } finally {
      setState('loading', false);
    }
  },

  async loadProject(id: string) {
    setState('loading', true);
    try {
      const project = await api.projects.get(id);
      setState('activeProject', project);
    } catch (err: any) {
      setState('error', err.message);
      toastStore.error(`Failed to load project: ${err.message}`);
    } finally {
      setState('loading', false);
    }
  },

  async createProject(name: string, opts: Partial<Project> = {}) {
    setState('loading', true);
    try {
      const project = await api.projects.create({
        name,
        aspect_ratio: opts.aspect_ratio || '16:9',
        target_duration_sec: opts.target_duration_sec || 60,
        style_pack_id: opts.style_pack_id || null,
        routing_profile: opts.routing_profile || 'hybrid',
      });
      await this.loadProjects();
      toastStore.success(`Project "${name}" created`);
      return project;
    } catch (err: any) {
      setState('error', err.message);
      toastStore.error(`Failed to create project: ${err.message}`);
    } finally {
      setState('loading', false);
    }
  },

  async deleteProject(id: string) {
    try {
      await api.projects.delete(id);
      await this.loadProjects();
      if (state.activeProject?.id === id) {
        setState('activeProject', null);
        setState('selectedShotId', null);
      }
      toastStore.success('Project deleted');
    } catch (err: any) {
      toastStore.error(`Failed to delete project: ${err.message}`);
    }
  },

  async uploadSource(projectId: string, file: File) {
    try {
      await api.sources.upload(projectId, file);
      await this.loadProject(projectId);
      toastStore.success('Source uploaded');
    } catch (err: any) {
      toastStore.error(`Upload failed: ${err.message}`);
    }
  },

  async generateTreatment(projectId: string) {
    setState('loading', true);
    try {
      await api.director.treatment(projectId);
      await this.loadProject(projectId);
      toastStore.success('Treatment generated');
    } catch (err: any) {
      setState('error', err.message);
      toastStore.error(`Treatment failed: ${err.message}`);
    } finally {
      setState('loading', false);
    }
  },

  async generateStoryboard(projectId: string) {
    setState('loading', true);
    try {
      await api.director.storyboard(projectId);
      await this.loadProject(projectId);
      toastStore.success('Storyboard generated');
    } catch (err: any) {
      setState('error', err.message);
      toastStore.error(`Storyboard failed: ${err.message}`);
    } finally {
      setState('loading', false);
    }
  },

  async render(projectId: string, shotIds?: string[]) {
    setState('loading', true);
    try {
      await api.render.shots(projectId, shotIds);
      toastStore.info('Render started');
      await this.loadProject(projectId);
      toastStore.success('Render complete');
    } catch (err: any) {
      setState('error', err.message);
      toastStore.error(`Render failed: ${err.message}`);
    } finally {
      setState('loading', false);
    }
  },

  async stitch(projectId: string, name?: string) {
    setState('loading', true);
    try {
      const result = await api.render.stitch(projectId, name);
      toastStore.success('Stitch complete');
      return result;
    } catch (err: any) {
      setState('error', err.message);
      toastStore.error(`Stitch failed: ${err.message}`);
    } finally {
      setState('loading', false);
    }
  },

  async togglePreviewMode(projectId: string, enabled: boolean) {
    try {
      await api.projects.update(projectId, { preview_mode: enabled });
      await this.loadProject(projectId);
    } catch (err: any) {
      toastStore.error(`Failed to toggle preview mode: ${err.message}`);
    }
  },

  async loadCapabilities() {
    try {
      const caps = await api.capabilities();
      setState('capabilities', caps);
    } catch (err: any) {
      setState('error', err.message);
    }
  },

  async loadStylePacks() {
    try {
      const packs = await api.prefabs.stylePacks();
      setState('stylePacks', packs);
    } catch (err: any) {
      setState('error', err.message);
    }
  },

  openCommandPalette() {
    setState('commandPaletteOpen', true);
  },

  closeCommandPalette() {
    setState('commandPaletteOpen', false);
  },

  setActiveTab(tab: StoreState['activeTab']) {
    setState('activeTab', tab);
  },

  async runStackBuilder(constraints: any) {
    setState('loading', true);
    try {
      const result = await api.stackbuilder.recommend(constraints);
      setState('stackRecommendations', result.recommendations);
      setState('stackDefaults', result.defaults);
      return result;
    } catch (err: any) {
      setState('error', err.message);
      toastStore.error(`StackBuilder failed: ${err.message}`);
    } finally {
      setState('loading', false);
    }
  },

  selectShot(shotId: string | null) {
    setState('selectedShotId', shotId);
    if (shotId) {
      this.loadBroll(shotId);
    }
  },

  getSelectedShot() {
    const project = state.activeProject;
    if (!project || !state.selectedShotId) return null;
    return project.shots.find((s) => s.id === state.selectedShotId) || null;
  },

  async loadBroll(shotId: string) {
    try {
      const clips = await api.broll.list(shotId);
      setState('brollClips', { ...state.brollClips, [shotId]: clips });
    } catch (err: any) {
      // Silently fail — B-roll is supplementary
    }
  },

  async generateBroll(projectId: string, shotId: string) {
    setState('loading', true);
    try {
      await api.broll.generate(shotId);
      toastStore.info('B-roll generation started');
      // Poll for a bit then load
      setTimeout(() => this.loadBroll(shotId), 2000);
      setTimeout(() => this.loadBroll(shotId), 5000);
      return true;
    } catch (err: any) {
      setState('error', err.message);
      toastStore.error(`B-roll generation failed: ${err.message}`);
      return false;
    } finally {
      setState('loading', false);
    }
  },

  async generateAllBroll(projectId: string) {
    setState('loading', true);
    try {
      const result = await api.broll.generateAll(projectId);
      toastStore.info(`Queued ${result.count} B-roll clips`);
    } catch (err: any) {
      setState('error', err.message);
      toastStore.error(`Bulk B-roll generation failed: ${err.message}`);
    } finally {
      setState('loading', false);
    }
  },

  async updateShot(projectId: string, shotId: string, payload: Partial<Shot>) {
    try {
      await api.shots.update(projectId, shotId, payload);
      await this.loadProject(projectId);
      toastStore.success('Shot saved');
    } catch (err: any) {
      toastStore.error(`Failed to save shot: ${err.message}`);
      throw err;
    }
  },

  async reorderShots(projectId: string, orderedShotIds: string[]) {
    try {
      // PATCH each shot's order_index sequentially
      for (let i = 0; i < orderedShotIds.length; i++) {
        await api.shots.update(projectId, orderedShotIds[i], { order_index: i });
      }
      await this.loadProject(projectId);
      toastStore.success('Timeline reordered');
    } catch (err: any) {
      toastStore.error(`Failed to reorder shots: ${err.message}`);
      throw err;
    }
  },

  async generateTrailer(projectId: string) {
    setState('loading', true);
    try {
      const result = await api.trailer.generate(projectId);
      toastStore.info('Trailer generation started');
      return result;
    } catch (err: any) {
      setState('error', err.message);
      toastStore.error(`Trailer generation failed: ${err.message}`);
      throw err;
    } finally {
      setState('loading', false);
    }
  },

  async getTrailerStatus(projectId: string) {
    try {
      return await api.trailer.status(projectId);
    } catch (err: any) {
      setState('error', err.message);
      throw err;
    }
  },

  async getTrailerDownload(projectId: string) {
    try {
      return await api.trailer.download(projectId);
    } catch (err: any) {
      setState('error', err.message);
      throw err;
    }
  },
};
