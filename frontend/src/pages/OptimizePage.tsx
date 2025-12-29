import { useState } from 'react';
import { optimizeApi } from '../services/api';
import './OptimizePage.css';

export function OptimizePage() {
  const [content, setContent] = useState('');
  const [style, setStyle] = useState('preserve');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) {
      setError('Please provide content to optimize');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await optimizeApi.optimize({
        content,
        style,
      });
      setResult(response);
    } catch (err: any) {
      const errorMessage = apiError.error?.message || 'An error occurred';
      const errorCode = apiError.error?.code || 'UNKNOWN_ERROR';
      
      // Handle specific error codes
      if (errorCode === 'RATE_LIMITED') {
        const retryAfter = apiError.error?.retry_after || 60;
        setError(`${errorMessage} Please wait ${retryAfter} seconds before trying again.`);
      } else if (errorCode === 'NETWORK_ERROR') {
        setError('Unable to connect to server. Please check your connection and try again.');
      } else if (errorCode === 'CONTENT_TOO_LARGE') {
        setError('Content is too large. Please split into smaller sections.');
      } else {
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="optimize-page">
      <h1>Optimize Content</h1>
      <p>Apply AIEO patterns to improve your content's citation likelihood</p>

      <form onSubmit={handleSubmit} className="optimize-form">
        <div className="form-group">
          <label htmlFor="content">Content</label>
          <textarea
            id="content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Paste your content here..."
            rows={15}
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="style">Style</label>
          <select
            id="style"
            value={style}
            onChange={(e) => setStyle(e.target.value)}
            disabled={loading}
          >
            <option value="preserve">Preserve original style</option>
            <option value="aggressive">Aggressive optimization</option>
          </select>
        </div>

        <button type="submit" disabled={loading} className="btn btn-primary">
          {loading ? 'Optimizing...' : 'Optimize Content'}
        </button>
      </form>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className="optimize-result">
          <h2>Optimization Results</h2>
          <div className="score-comparison">
            <div className="score-before">
              <div className="score-label">Before</div>
              <div className="score-value">{result.score_before}</div>
            </div>
            <div className="score-arrow">→</div>
            <div className="score-after">
              <div className="score-label">After</div>
              <div className="score-value">{result.score_after}</div>
            </div>
            <div className="score-uplift">
              +{result.uplift} points
            </div>
          </div>

          {result.optimized_content && (
            <div className="optimized-content">
              <h3>Optimized Content</h3>
              <pre>{result.optimized_content}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


