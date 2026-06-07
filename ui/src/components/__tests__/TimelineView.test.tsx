import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@solidjs/testing-library';
import { setState } from '../../stores/projectStore';
import TimelineView from '../TimelineView';

describe('TimelineView', () => {
  beforeEach(() => {
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
          { id: 's1', order_index: 0, duration_sec: 5, tier: 'hero', status: 'done', prompt_text: 'Shot one', bridge_strategy: 'cut', clip_path: null, cost_usd: 0.5 },
          { id: 's2', order_index: 1, duration_sec: 3, tier: 'standard', status: 'rendering', prompt_text: 'Shot two', bridge_strategy: 'dissolve', clip_path: null, cost_usd: 0.3 },
        ],
        sources: [],
      },
      selectedShotId: null,
    });
  });

  it('renders shots in the timeline', () => {
    render(() => <TimelineView />);
    expect(screen.getByText('Shot one')).toBeTruthy();
    expect(screen.getByText('Shot two')).toBeTruthy();
    expect(screen.getByText('Total duration: 8s')).toBeTruthy();
  });

  it('renders duration inputs for trimming', () => {
    render(() => <TimelineView />);
    const inputs = screen.getAllByDisplayValue('5');
    expect(inputs.length).toBeGreaterThan(0);
  });
});
