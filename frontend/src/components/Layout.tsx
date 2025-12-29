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
          </div>
        </div>
      </nav>
      <main className="main-content">{children}</main>
    </div>
  );
}


