import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { ErrorBoundary } from './components/ErrorBoundary';
import { SettingsProvider } from './hooks/useSettings';
import { ToastProvider } from './hooks/useToast';
import { HomePage } from './pages/HomePage';
import { AuditPage } from './pages/AuditPage';
import { OptimizePage } from './pages/OptimizePage';
import { DashboardPage } from './pages/DashboardPage';
import { PatternsPage } from './pages/PatternsPage';
import { WorkspacePage } from './pages/WorkspacePage';
import { TopicsPage } from './pages/TopicsPage';
import { ResearchPage } from './pages/ResearchPage';
import { DraftsPage } from './pages/DraftsPage';
import { RewritesPage } from './pages/RewritesPage';
import { PublishedPage } from './pages/PublishedPage';
import { LandingPagesPage } from './pages/LandingPagesPage';
import { PerformancePage } from './pages/PerformancePage';
import { AgentsPage } from './pages/AgentsPage';
import { SettingsPage } from './pages/SettingsPage';
import { NotFoundPage } from './pages/NotFoundPage';

function App() {
  return (
    <SettingsProvider>
      <ToastProvider>
        <BrowserRouter>
          <AppShell>
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/audit" element={<AuditPage />} />
                <Route path="/optimize" element={<OptimizePage />} />
                <Route path="/patterns" element={<PatternsPage />} />
                <Route path="/agents" element={<AgentsPage />} />
                <Route path="/topics" element={<TopicsPage />} />
                <Route path="/research" element={<ResearchPage />} />
                <Route path="/drafts" element={<DraftsPage />} />
                <Route path="/rewrites" element={<RewritesPage />} />
                <Route path="/landing-pages" element={<LandingPagesPage />} />
                <Route path="/workspace" element={<WorkspacePage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/performance" element={<PerformancePage />} />
                <Route path="/published" element={<PublishedPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </ErrorBoundary>
          </AppShell>
        </BrowserRouter>
      </ToastProvider>
    </SettingsProvider>
  );
}

export default App;
