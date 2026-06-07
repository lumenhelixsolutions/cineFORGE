import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@solidjs/testing-library';
import { setState, projectStore } from '../../stores/projectStore';
import Inspector from '../Inspector';

vi.mock('../../lib/api', () => ({
  api: {
    shots: {
      update: vi.fn().mockResolvedValue({}),
    },
    projects: {
      get: vi.fn().mockResolvedValue({}),
    },
  },
}));

describe('Inspector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setState({
      activeProject: {
        id: 'test-proj',
        name: 'Test Project',
        created_at: new Date().toISOString(),
        aspect_ratio: '16:9',
        target_duration_sec: 60,
        style_pack_id: null,
        routing_profile: 'hybrid',
        preview_mode: false,
        budget_usd: 10,
        tokens_used_input: 100,
        tokens_used_output: 50,
        tokens_used_cached: 20,
        shots: [
          { id: 's1', order_index: 0, duration_sec: 5, tier: 'hero', status: 'done', prompt_text: 'Original prompt', bridge_strategy: 'cut', clip_path: null, cost_usd: 0.5 },
        ],
        sources: [],
      },
      selectedShotId: 's1',
      stylePacks: [{ id: 'sp1', name: 'Cinematic' }],
    });
  });

  it('renders editable fields for selected shot', () => {
    render(() => <Inspector />);
    expect(screen.getByText('Selected Shot')).toBeTruthy();
    expect(screen.getByDisplayValue('Original prompt')).toBeTruthy();
  });

  it('calls updateShot when Save is clicked', async () => {
    const updateSpy = vi.spyOn(projectStore, 'updateShot').mockResolvedValue(undefined);
    render(() => <Inspector />);

    const textarea = screen.getByDisplayValue('Original prompt') as HTMLTextAreaElement;
    fireEvent.input(textarea, { target: { value: 'Updated prompt' } });

    const saveBtn = screen.getByText('Save');
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith('test-proj', 's1', expect.objectContaining({ prompt_text: 'Updated prompt' }));
    });
  });
});
