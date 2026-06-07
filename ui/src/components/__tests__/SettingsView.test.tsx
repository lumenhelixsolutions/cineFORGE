import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@solidjs/testing-library';
import SettingsView from '../SettingsView';

describe('SettingsView', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders settings sections', () => {
    render(() => <SettingsView />);
    expect(screen.getByText('Settings')).toBeTruthy();
    expect(screen.getByLabelText('Backend URL')).toBeTruthy();
    expect(screen.getByText('Theme')).toBeTruthy();
    expect(screen.getByText('About')).toBeTruthy();
  });

  it('has dark theme selected by default', () => {
    render(() => <SettingsView />);
    const darkBtn = screen.getByText('Dark') as HTMLButtonElement;
    expect(darkBtn.getAttribute('aria-pressed')).toBe('true');
  });
});
