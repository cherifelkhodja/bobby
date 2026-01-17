/**
 * useSearch - Hook for search state with debouncing
 *
 * Provides both immediate and debounced search values for responsive UX.
 * The immediate value updates the input field instantly while the debounced
 * value is used for API calls.
 *
 * @example
 * const { search, debouncedSearch, setSearch, clear } = useSearch({ delay: 300 });
 *
 * // Input uses immediate value
 * <input value={search} onChange={(e) => setSearch(e.target.value)} />
 *
 * // Query uses debounced value
 * const { data } = useQuery(['items', debouncedSearch], () => fetchItems(debouncedSearch));
 */

import { useState, useCallback } from 'react';
import { useDebounce } from './useDebounce';

interface UseSearchOptions {
  /** Initial search value */
  initialValue?: string;
  /** Debounce delay in milliseconds (default: 300) */
  delay?: number;
}

interface UseSearchResult {
  /** Current search value (immediate) */
  search: string;
  /** Debounced search value (for API calls) */
  debouncedSearch: string;
  /** Update the search value */
  setSearch: (value: string) => void;
  /** Clear the search */
  clear: () => void;
  /** Whether there is an active search */
  hasSearch: boolean;
}

export function useSearch({
  initialValue = '',
  delay = 300,
}: UseSearchOptions = {}): UseSearchResult {
  const [search, setSearchState] = useState(initialValue);
  const debouncedSearch = useDebounce(search, delay);

  const setSearch = useCallback((value: string) => {
    setSearchState(value);
  }, []);

  const clear = useCallback(() => {
    setSearchState('');
  }, []);

  return {
    search,
    debouncedSearch,
    setSearch,
    clear,
    hasSearch: search.length > 0,
  };
}
