import { useEffect, useState } from 'react';
import { citationsApi } from '../services/api';
import type { DashboardData, ApiError } from '../types';
import './DashboardPage.css';

export function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const response = await citationsApi.getDashboard() as DashboardData;
      setData(response);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.error?.message || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="dashboard-page">Loading...</div>;
  }

  if (error) {
    return (
      <div className="dashboard-page">
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-page">
      <h1>Citation Dashboard</h1>
      <p>Track your content's citations across AI engines</p>

      {data && (
        <div className="dashboard-content">
          <div className="dashboard-section">
            <h2>Citation Rate (Last 30 Days)</h2>
            <p className="placeholder">Chart will be displayed here</p>
          </div>

          <div className="dashboard-section">
            <h2>By Engine</h2>
            <div className="engine-stats">
              {Object.entries(data.citations_by_engine || {}).map(([engine, count]) => (
                <div key={engine} className="engine-stat">
                  <div className="engine-name">{engine}</div>
                  <div className="engine-count">{count}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="dashboard-section">
            <h2>Top Cited Pages</h2>
            <ul className="cited-pages">
              {(data.top_cited_pages || []).map((page, index) => (
                <li key={index}>
                  <a href={page.url} target="_blank" rel="noopener noreferrer">
                    {page.url}
                  </a>
                  <span className="citation-count">{page.citation_count} citations</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}


