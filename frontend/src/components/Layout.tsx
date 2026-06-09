import { Link, useLocation } from 'react-router-dom';
import './Layout.css';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="layout">
      <nav className="navbar">
        <div className="nav-container">
          <Link to="/" className="nav-logo">
            AIEO
          </Link>
          <div className="nav-links">
            <Link
              to="/audit"
              className={isActive('/audit') ? 'active' : ''}
            >
              Audit
            </Link>
            <Link
              to="/optimize"
              className={isActive('/optimize') ? 'active' : ''}
            >
              Optimize
            </Link>
            <Link
              to="/dashboard"
              className={isActive('/dashboard') ? 'active' : ''}
            >
              Dashboard
            </Link>
            <Link
              to="/patterns"
              className={isActive('/patterns') ? 'active' : ''}
            >
              Patterns
            </Link>
            <Link to="/workspace" className={isActive('/workspace') ? 'active' : ''}>
              Workspace
            </Link>
            <Link to="/topics" className={isActive('/topics') ? 'active' : ''}>
              Topics
            </Link>
            <Link to="/research" className={isActive('/research') ? 'active' : ''}>
              Research
            </Link>
            <Link to="/drafts" className={isActive('/drafts') ? 'active' : ''}>
              Drafts
            </Link>
            <Link to="/rewrites" className={isActive('/rewrites') ? 'active' : ''}>
              Rewrites
            </Link>
            <Link to="/published" className={isActive('/published') ? 'active' : ''}>
              Published
            </Link>
            <Link to="/landing-pages" className={isActive('/landing-pages') ? 'active' : ''}>
              Landing
            </Link>
            <Link to="/performance" className={isActive('/performance') ? 'active' : ''}>
              Performance
            </Link>
            <Link to="/agents" className={isActive('/agents') ? 'active' : ''}>
              Agents
            </Link>
          </div>
        </div>
      </nav>
      <main className="main-content">{children}</main>
    </div>
  );
}


