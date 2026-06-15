import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}
interface State {
  error: Error | null;
}

/** Catches render errors so a single broken page doesn't blank the whole app. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Render error:', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="mx-auto max-w-lg p-10 text-center">
          <div className="rounded-xl border border-bad/30 bg-bad/10 p-8">
            <p className="text-lg font-semibold text-bad">Something broke on this page</p>
            <p className="mt-2 text-sm text-muted">{this.state.error.message}</p>
            <button
              onClick={() => this.setState({ error: null })}
              className="mt-5 rounded-lg border border-line bg-elevated px-4 py-2 text-sm font-medium text-ink hover:border-line-strong"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
