import { createStore } from 'solid-js/store';
import { api } from '../lib/api';
import { toastStore } from './toastStore';

export interface ExportJob {
  id: string;
  project_id: string;
  type: 'mp4' | 'archive' | 'stills' | 'edl';
  status: string;
  progress: number;
  output_url: string | null;
  output_size: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

interface ExportStoreState {
  jobs: ExportJob[];
  loading: boolean;
  error: string | null;
}

export const [exportState, setExportState] = createStore<ExportStoreState>({
  jobs: [],
  loading: false,
  error: null,
});

export const exportStore = {
  state: exportState,

  async loadExports(projectId: string) {
    setExportState('loading', true);
    try {
      const jobs = await api.exports.list(projectId);
      setExportState('jobs', jobs);
    } catch (err: any) {
      setExportState('error', err.message);
      toastStore.error(`Failed to load exports: ${err.message}`);
    } finally {
      setExportState('loading', false);
    }
  },

  async startExport(projectId: string, type: ExportJob['type']) {
    setExportState('loading', true);
    try {
      const result = await api.exports.create(projectId, type);
      toastStore.info(`Export queued: ${type}`);
      await this.loadExports(projectId);
      return result;
    } catch (err: any) {
      setExportState('error', err.message);
      toastStore.error(`Export failed: ${err.message}`);
      throw err;
    } finally {
      setExportState('loading', false);
    }
  },

  async cancelExport(jobId: string, projectId: string) {
    try {
      await api.exports.delete(jobId);
      toastStore.success('Export cancelled');
      await this.loadExports(projectId);
    } catch (err: any) {
      toastStore.error(`Failed to cancel export: ${err.message}`);
    }
  },

  getDownloadUrl(jobId: string) {
    return api.exports.downloadUrl(jobId);
  },

  pollExports(projectId: string) {
    const interval = setInterval(async () => {
      try {
        const jobs = await api.exports.list(projectId);
        setExportState('jobs', jobs);
        const hasActive = jobs.some(
          (j: ExportJob) => j.status === 'queued' || j.status === 'processing'
        );
        if (!hasActive) {
          clearInterval(interval);
        }
      } catch {
        // silently fail poll
      }
    }, 1500);
    return () => clearInterval(interval);
  },
};
