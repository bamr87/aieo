import { Link } from 'react-router-dom';
import { Button } from '../components/ui';

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
      <p className="text-6xl font-bold brand-text">404</p>
      <p className="text-sm text-muted">That page doesn’t exist.</p>
      <Link to="/">
        <Button variant="primary">Back to home</Button>
      </Link>
    </div>
  );
}
