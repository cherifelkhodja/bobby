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
      <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center text-yellow-700 dark:text-yellow-400">
            <WifiOff className="h-4 w-4 mr-2" />
            <span className="text-sm">Erreur de chargement</span>
          </div>
          <button
            onClick={onReset}
            className="text-sm text-yellow-600 dark:text-yellow-400 hover:underline"
          >
            Réessayer
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="flex flex-col items-center text-center">
        <div className="p-3 bg-yellow-100 dark:bg-yellow-900/30 rounded-full mb-4">
          <AlertCircle className="h-8 w-8 text-yellow-600 dark:text-yellow-400" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Impossible de charger les données
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          Vérifiez votre connexion internet et réessayez.
        </p>
        <button
          onClick={onReset}
          className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
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
