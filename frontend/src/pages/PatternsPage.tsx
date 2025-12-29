import { useEffect, useState } from 'react';
import { patternsApi } from '../services/api';
import type { Pattern, ApiError } from '../types';
import './PatternsPage.css';

export function PatternsPage() {
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPatterns();
  }, []);

  const loadPatterns = async () => {
    try {
      const response = await patternsApi.listPatterns() as { patterns: Pattern[] };
      setPatterns(response.patterns || []);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.error?.message || 'Failed to load patterns');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="patterns-page">Loading...</div>;
  }

  if (error) {
    return (
      <div className="patterns-page">
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      </div>
    );
  }

  return (
    <div className="patterns-page">
      <h1>AIEO Pattern Library</h1>
      <p>Browse proven patterns that increase citation likelihood</p>

      {patterns.length === 0 ? (
        <div className="no-patterns">
          <p>No patterns available yet. Patterns will be displayed here.</p>
        </div>
      ) : (
        <div className="patterns-grid">
          {patterns.map((pattern) => (
            <div key={pattern.id} className="pattern-card">
              <h3>{pattern.name}</h3>
              <p className="pattern-description">{pattern.description}</p>
              {pattern.citation_boost && (
                <div className="pattern-boost">
                  Citation boost: {pattern.citation_boost.min}% - {pattern.citation_boost.max}%
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


