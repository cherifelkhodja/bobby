/**
 * ErrorBoundary - Catches JavaScript errors in child component tree
 *
 * Prevents the entire application from crashing when an error occurs.
 * Displays a fallback UI and logs errors for debugging.
 */

import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface ErrorBoundaryProps {
  /** Child components to render */
  children: ReactNode;
  /** Custom fallback component */
  fallback?: ReactNode;
  /** Callback when error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Whether to show the reset button (default: true) */
  showReset?: boolean;
  /** Level of the error boundary (for nested boundaries) */
  level?: 'page' | 'section' | 'component';
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });

    // Log error to console
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // Call optional error handler
    this.props.onError?.(error, errorInfo);

    // In production, you could send this to an error tracking service
    // e.g., Sentry, LogRocket, etc.
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    const { hasError, error, errorInfo } = this.state;
    const { children, fallback, showReset = true, level = 'page' } = this.props;

    if (hasError) {
      // Custom fallback provided
      if (fallback) {
        return fallback;
      }

      // Default error UI based on level
      return (
        <ErrorFallback
          error={error}
          errorInfo={errorInfo}
          onReset={showReset ? this.handleReset : undefined}
          onGoHome={level === 'page' ? this.handleGoHome : undefined}
          level={level}
        />
      );
    }

    return children;
  }
}

/**
 * ErrorFallback - Default error UI component
 */
interface ErrorFallbackProps {
  error: Error | null;
  errorInfo: ErrorInfo | null;
  onReset?: () => void;
  onGoHome?: () => void;
  level: 'page' | 'section' | 'component';
}

function ErrorFallback({
  error,
  errorInfo,
  onReset,
  onGoHome,
  level,
}: ErrorFallbackProps) {
  const isDevMode = import.meta.env.DEV;

  // Compact view for component-level errors
  if (level === 'component') {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <div className="flex items-center text-red-700 dark:text-red-400">
          <AlertTriangle className="h-5 w-5 mr-2" />
          <span className="text-sm font-medium">Une erreur est survenue</span>
        </div>
        {onReset && (
          <button
            onClick={onReset}
            className="mt-2 text-sm text-red-600 dark:text-red-400 hover:underline"
          >
            Réessayer
          </button>
        )}
      </div>
    );
  }

  // Section-level error
  if (level === 'section') {
    return (
      <div className="p-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm">
        <div className="flex flex-col items-center text-center">
          <div className="p-3 bg-red-100 dark:bg-red-900/30 rounded-full mb-4">
            <AlertTriangle className="h-8 w-8 text-red-600 dark:text-red-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Erreur de chargement
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Cette section n'a pas pu être chargée correctement.
          </p>
          {onReset && (
            <button
              onClick={onReset}
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Réessayer
            </button>
          )}
        </div>
      </div>
    );
  }

  // Page-level error (full screen)
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <div className="max-w-lg w-full bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 text-center">
        <div className="mx-auto w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-6">
          <AlertTriangle className="h-8 w-8 text-red-600 dark:text-red-400" />
        </div>

        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Oups ! Une erreur est survenue
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          L'application a rencontré un problème inattendu.
          Veuillez réessayer ou retourner à l'accueil.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          {onReset && (
            <button
              onClick={onReset}
              className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Réessayer
            </button>
          )}
          {onGoHome && (
            <button
              onClick={onGoHome}
              className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
            >
              <Home className="h-4 w-4 mr-2" />
              Retour à l'accueil
            </button>
          )}
        </div>

        {/* Show error details in dev mode */}
        {isDevMode && error && (
          <div className="mt-6 p-4 bg-gray-100 dark:bg-gray-900 rounded-lg text-left overflow-auto">
            <p className="text-sm font-mono text-red-600 dark:text-red-400 mb-2">
              {error.name}: {error.message}
            </p>
            {errorInfo && (
              <pre className="text-xs font-mono text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                {errorInfo.componentStack}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * withErrorBoundary - HOC to wrap components with error boundary
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  return function WithErrorBoundary(props: P) {
    return (
      <ErrorBoundary {...errorBoundaryProps}>
        <WrappedComponent {...props} />
      </ErrorBoundary>
    );
  };
}
