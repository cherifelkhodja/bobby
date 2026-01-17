/**
 * useAsync - Hook for handling async operations with loading/error states
 *
 * Wraps async functions with loading and error state management.
 * Useful for form submissions and one-off async operations.
 *
 * @example
 * const { execute, isLoading, error, data } = useAsync(submitForm);
 *
 * const handleSubmit = async (values) => {
 *   const result = await execute(values);
 *   if (result) {
 *     toast.success('Saved!');
 *   }
 * };
 */

import { useState, useCallback } from 'react';

interface UseAsyncState<T> {
  /** Whether the async operation is in progress */
  isLoading: boolean;
  /** Error from the last failed operation */
  error: Error | null;
  /** Data from the last successful operation */
  data: T | null;
}

interface UseAsyncResult<T, Args extends unknown[]> extends UseAsyncState<T> {
  /** Execute the async function */
  execute: (...args: Args) => Promise<T | null>;
  /** Reset state to initial values */
  reset: () => void;
  /** Clear only the error */
  clearError: () => void;
}

export function useAsync<T, Args extends unknown[] = []>(
  asyncFunction: (...args: Args) => Promise<T>
): UseAsyncResult<T, Args> {
  const [state, setState] = useState<UseAsyncState<T>>({
    isLoading: false,
    error: null,
    data: null,
  });

  const execute = useCallback(
    async (...args: Args): Promise<T | null> => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      try {
        const result = await asyncFunction(...args);
        setState({ isLoading: false, error: null, data: result });
        return result;
      } catch (error) {
        const errorObject =
          error instanceof Error ? error : new Error(String(error));
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: errorObject,
        }));
        return null;
      }
    },
    [asyncFunction]
  );

  const reset = useCallback(() => {
    setState({ isLoading: false, error: null, data: null });
  }, []);

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  return {
    ...state,
    execute,
    reset,
    clearError,
  };
}
