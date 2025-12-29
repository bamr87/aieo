import { useState } from 'react';
import { auditApi } from '../services/api';
import { AuditResult, ApiError } from '../types';
import './AuditPage.css';

export function AuditPage() {
  const [url, setUrl] = useState('');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AuditResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data: { url?: string; content?: string; format?: string } = {};
      if (url) {
        data.url = url;
      } else if (content) {
        data.content = content;
        data.format = 'markdown';
      } else {
        setError('Please provide either a URL or content');
        setLoading(false);
        return;
      }

      const response = await auditApi.audit(data);
      setResult(response);
    } catch (err) {
      const apiError = err as ApiError;
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
    <div className="audit-page">
      <h1>Audit Content</h1>
      <p>Get an AIEO score and identify gaps in your content</p>

      <form onSubmit={handleSubmit} className="audit-form">
        <div className="form-group">
          <label htmlFor="url">URL (optional)</label>
          <input
            id="url"
            type="url"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setContent('');
            }}
            placeholder="https://example.com/article"
            disabled={loading}
          />
        </div>

        <div className="form-divider">OR</div>

        <div className="form-group">
          <label htmlFor="content">Content</label>
          <textarea
            id="content"
            value={content}
            onChange={(e) => {
              setContent(e.target.value);
              setUrl('');
            }}
            placeholder="Paste your markdown content here..."
            rows={10}
            disabled={loading}
          />
        </div>

        <button type="submit" disabled={loading} className="btn btn-primary">
          {loading ? 'Auditing...' : 'Audit Content'}
        </button>
      </form>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className="audit-result">
          <h2>Audit Results</h2>
          <div className="score-display">
            <div className="score-value">{result.score}</div>
            <div className="score-grade">Grade: {result.grade}</div>
          </div>

          {result.gaps && result.gaps.length > 0 && (
            <div className="gaps-section">
              <h3>Gaps Found</h3>
              <ul>
                {result.gaps.slice(0, 5).map((gap: any, index: number) => (
                  <li key={index}>
                    <strong>{gap.category}</strong> ({gap.severity}): {gap.description}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


