import { lazy } from 'solid-js';

export const SettingsView = lazy(() => import('../components/SettingsView'));
export { default as StackBuilder } from '../components/StackBuilder';
export { default as Storyboard } from '../components/Storyboard';
export { default as TimelineView } from '../components/TimelineView';
export { default as PreviewPlayer } from '../components/PreviewPlayer';
export { default as TreatmentView } from '../components/TreatmentView';
