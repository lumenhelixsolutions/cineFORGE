import { Route } from '@solidjs/router';
import Layout from './Layout';
import ProjectView from './ProjectView';
import SettingsView from './components/SettingsView';
import StackBuilder from './components/StackBuilder';

export default function App() {
  return (
    <>
      <Route path="/" component={Layout}>
        <Route path="/settings" component={SettingsView} />
        <Route path="/stackbuilder" component={StackBuilder} />
        <Route path="/project/:id" component={ProjectView} />
        <Route path="/" component={ProjectView} />
      </Route>
    </>
  );
}
