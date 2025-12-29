import { Link } from 'react-router-dom';
import './HomePage.css';

export function HomePage() {
  return (
    <div className="home-page">
      <div className="hero">
        <h1>AIEO - AI Engine Optimization</h1>
        <p className="subtitle">
          Optimize your content to be cited by AI engines like Grok, ChatGPT, and Claude
        </p>
        <div className="cta-buttons">
          <Link to="/audit" className="btn btn-primary">
            Audit Content
          </Link>
          <Link to="/optimize" className="btn btn-secondary">
            Optimize Content
          </Link>
        </div>
      </div>

      <div className="features">
        <div className="feature">
          <h2>Audit</h2>
          <p>Get a 0-100 AIEO score and identify gaps in your content</p>
          <Link to="/audit">Try it →</Link>
        </div>
        <div className="feature">
          <h2>Optimize</h2>
          <p>Apply AIEO patterns to improve citation likelihood</p>
          <Link to="/optimize">Try it →</Link>
        </div>
        <div className="feature">
          <h2>Track</h2>
          <p>Monitor citations across AI engines</p>
          <Link to="/dashboard">View Dashboard →</Link>
        </div>
      </div>
    </div>
  );
}


