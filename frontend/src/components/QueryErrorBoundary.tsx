/**
 * QueryErrorBoundary - Error boundary specifically for React Query errors
 *
 * Handles API errors and provides retry functionality integrated with React Query.
 */

import { useQueryErrorResetBoundary } from '@tanstack/react-query';
import { ErrorBoundary } from './ErrorBoundary';
import { AlertCircle, RefreshCw, WifiOff } from 'lucide-react';
import { ReactNode } from 'react';

interface QueryErrorBoundaryProps {
  children: ReactNode;
  /** Level of the error boundary */
  level?: 'page' | 'section' | 'component';
}

export function QueryErrorBoundary({
  children,
  level = 'section',
}: QueryErrorBoundaryProps) {
  const { reset } = useQueryErrorResetBoundary();

  return (
    <ErrorBoundary
      onError={() => {
        // React Query will handle retry logic, but we can log here
        console.warn('QueryErrorBoundary caught an error');
      }}
      fallback={<QueryErrorFallback onReset={reset} level={level} />}
    >
      {children}
    </ErrorBoundary>
  );
}

interface QueryErrorFallbackProps {
  onReset: () => void;
  level: 'page' | 'section' | 'component';
}

function QueryErrorFallback({ onReset, level }: QueryErrorFallbackProps) {
  if (level === 'component') {
    return (
      <div className="alert !mt-0">
        <WifiOff className="h-4 w-4 shrink-0" />
        <span>Erreur de chargement</span>
        <button onClick={onReset} className="alink hover:underline">
          Réessayer
        </button>
      </div>
    );
  }

  return (
    <div className="card p-8">
      <div className="flex flex-col items-center text-center">
        <div className="p-3 bg-amb-bg rounded-full mb-4">
          <AlertCircle className="h-7 w-7 text-amb-fg" />
        </div>
        <h3 className="text-[15px] font-bold text-ink mb-2">
          Impossible de charger les données
        </h3>
        <p className="notec mb-4">Vérifiez votre connexion internet et réessayez.</p>
        <button onClick={onReset} className="btn">
          <RefreshCw className="h-3.5 w-3.5" />
          Réessayer
        </button>
      </div>
    </div>
  );
}

/**
 * SuspenseQueryBoundary - Combines Suspense and Error Boundary for React Query
 */
import { Suspense } from 'react';
import { PageSpinner, Spinner } from './ui/Spinner';

interface SuspenseQueryBoundaryProps {
  children: ReactNode;
  /** Level determines loading and error UI */
  level?: 'page' | 'section' | 'component';
  /** Custom loading fallback */
  loadingFallback?: ReactNode;
}

export function SuspenseQueryBoundary({
  children,
  level = 'section',
  loadingFallback,
}: SuspenseQueryBoundaryProps) {
  const fallback = loadingFallback ?? (
    level === 'page' ? (
      <PageSpinner />
    ) : level === 'section' ? (
      <div className="flex items-center justify-center p-8">
        <Spinner size="lg" />
      </div>
    ) : (
      <div className="flex items-center justify-center p-4">
        <Spinner size="sm" />
      </div>
    )
  );

  return (
    <QueryErrorBoundary level={level}>
      <Suspense fallback={fallback}>{children}</Suspense>
    </QueryErrorBoundary>
  );
}
