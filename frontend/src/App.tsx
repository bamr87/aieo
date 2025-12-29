import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { HomePage } from './pages/HomePage';
import { AuditPage } from './pages/AuditPage';
import { OptimizePage } from './pages/OptimizePage';
import { DashboardPage } from './pages/DashboardPage';
import { PatternsPage } from './pages/PatternsPage';
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
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
