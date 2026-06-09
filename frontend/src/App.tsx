import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
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
import './App.css';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/optimize" element={<OptimizePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/patterns" element={<PatternsPage />} />
          <Route path="/workspace" element={<WorkspacePage />} />
          <Route path="/topics" element={<TopicsPage />} />
          <Route path="/research" element={<ResearchPage />} />
          <Route path="/drafts" element={<DraftsPage />} />
          <Route path="/rewrites" element={<RewritesPage />} />
          <Route path="/published" element={<PublishedPage />} />
          <Route path="/landing-pages" element={<LandingPagesPage />} />
          <Route path="/performance" element={<PerformancePage />} />
          <Route path="/agents" element={<AgentsPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
