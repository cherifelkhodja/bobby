/**
 * usePagination - Hook for handling pagination state and controls
 *
 * Provides a consistent pagination interface across components.
 *
 * @example
 * const { page, pageSize, setPage, hasPrevious, hasNext, totalPages } = usePagination({
 *   pageSize: 20,
 *   total: data?.total,
 * });
 */

import { useState, useMemo, useCallback } from 'react';

interface UsePaginationOptions {
  /** Initial page number (default: 1) */
  initialPage?: number;
  /** Number of items per page (default: 20) */
  pageSize?: number;
  /** Total number of items */
  total?: number;
}

interface UsePaginationResult {
  /** Current page number (1-indexed) */
  page: number;
  /** Number of items per page */
  pageSize: number;
  /** Set the current page */
  setPage: (page: number) => void;
  /** Go to next page */
  nextPage: () => void;
  /** Go to previous page */
  prevPage: () => void;
  /** Go to first page */
  firstPage: () => void;
  /** Go to last page */
  lastPage: () => void;
  /** Whether there is a previous page */
  hasPrevious: boolean;
  /** Whether there is a next page */
  hasNext: boolean;
  /** Total number of pages */
  totalPages: number;
  /** Skip value for API calls */
  skip: number;
  /** Offset value for API calls (same as skip) */
  offset: number;
}

export function usePagination({
  initialPage = 1,
  pageSize = 20,
  total = 0,
}: UsePaginationOptions = {}): UsePaginationResult {
  const [page, setPageState] = useState(initialPage);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(total / pageSize)),
    [total, pageSize]
  );

  const hasPrevious = page > 1;
  const hasNext = page < totalPages;

  const setPage = useCallback(
    (newPage: number) => {
      const validPage = Math.max(1, Math.min(newPage, totalPages || 1));
      setPageState(validPage);
    },
    [totalPages]
  );

  const nextPage = useCallback(() => {
    if (hasNext) {
      setPageState((p) => p + 1);
    }
  }, [hasNext]);

  const prevPage = useCallback(() => {
    if (hasPrevious) {
      setPageState((p) => p - 1);
    }
  }, [hasPrevious]);

  const firstPage = useCallback(() => {
    setPageState(1);
  }, []);

  const lastPage = useCallback(() => {
    setPageState(totalPages);
  }, [totalPages]);

  const skip = (page - 1) * pageSize;

  return {
    page,
    pageSize,
    setPage,
    nextPage,
    prevPage,
    firstPage,
    lastPage,
    hasPrevious,
    hasNext,
    totalPages,
    skip,
    offset: skip,
  };
}
