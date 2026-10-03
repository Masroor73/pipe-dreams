import { BrowserRouter } from 'react-router';
import { AppShell } from './components/AppShell/AppShell';
import { MetaProvider } from './lib/synthetic';

export default function App() {
  return (
    <MetaProvider>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </MetaProvider>
  );
}
