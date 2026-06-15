import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@solidjs/testing-library';
import { setState } from '../../stores/projectStore';
import PreviewPlayer from '../PreviewPlayer';

vi.mock('../../lib/api', () => ({
  api: {
    lookbook: {
      review: vi.fn(),
      reviewUrl: vi.fn((projectId: string) => `http://127.0.0.1:8765/projects/${projectId}/lookbook/review?format=html`),
    },
  },
}));

import { api } from '../../lib/api';

describe('PreviewPlayer', () => {
  beforeEach(() => {
    vi.mocked(api.lookbook.review).mockReset();
    setState({
      activeProject: {
        id: 'proj-1',
        name: 'Demo',
        created_at: new Date().toISOString(),
        aspect_ratio: '16:9',
        target_duration_sec: 60,
        style_pack_id: null,
        routing_profile: 'hybrid',
        preview_mode: false,
        budget_usd: 10,
        tokens_used_input: 0,
        tokens_used_output: 0,
        tokens_used_cached: 0,
        shots: [],
        sources: [],
      },
      lookbookReview: null,
      selectedShotId: null,
    });
  });

  it('renders Living preview mode button', () => {
    render(() => <PreviewPlayer />);
    expect(screen.getByText('Living')).toBeTruthy();
  });

  it('shows empty state when living review is unavailable', async () => {
    vi.mocked(api.lookbook.review).mockResolvedValue({
      available: false,
      message: 'No lookBOOK choreography found.',
    });

    render(() => <PreviewPlayer />);
    fireEvent.click(screen.getByText('Living'));

    expect(await screen.findByText('No lookBOOK choreography found.')).toBeTruthy();
  });

  it('embeds living review iframe when choreography is available', async () => {
    vi.mocked(api.lookbook.review).mockResolvedValue({
      available: true,
      title: 'Demo',
    });

    render(() => <PreviewPlayer />);
    fireEvent.click(screen.getByText('Living'));

    const iframe = await screen.findByTitle('Living panels review');
    expect(iframe).toBeTruthy();
    expect((iframe as HTMLIFrameElement).src).toContain('/projects/proj-1/lookbook/review?format=html');
  });
});