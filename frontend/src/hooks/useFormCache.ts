/**
 * Hook for caching form data in localStorage with TTL expiration.
 *
 * Used by PublicApplication to persist form progress across page reloads.
 */

import { useState, useEffect, useCallback } from 'react';

const DEFAULT_CACHE_DURATION_MS = 48 * 60 * 60 * 1000; // 48 hours

interface CachedEntry<T> {
  data: T;
  timestamp: number;
}

function buildCacheKey(prefix: string, token: string): string {
  return `${prefix}_${token}`;
}

export function useFormCache<T extends Record<string, unknown>>(
  token: string | undefined,
  prefix: string,
  cacheDurationMs = DEFAULT_CACHE_DURATION_MS,
) {
  const [hasCachedData, setHasCachedData] = useState(false);

  const cacheKey = token ? buildCacheKey(prefix, token) : null;

  const load = useCallback((): T | null => {
    if (!cacheKey) return null;
    try {
      const raw = localStorage.getItem(cacheKey);
      if (!raw) return null;

      const parsed: CachedEntry<T> = JSON.parse(raw);
      if (Date.now() - parsed.timestamp > cacheDurationMs) {
        localStorage.removeItem(cacheKey);
        return null;
      }

      return parsed.data;
    } catch {
      return null;
    }
  }, [cacheKey, cacheDurationMs]);

  const save = useCallback(
    (data: T) => {
      if (!cacheKey) return;
      try {
        const entry: CachedEntry<T> = { data, timestamp: Date.now() };
        localStorage.setItem(cacheKey, JSON.stringify(entry));
      } catch {
        // Ignore localStorage errors (quota exceeded, etc.)
      }
    },
    [cacheKey],
  );

  const clear = useCallback(() => {
    if (!cacheKey) return;
    try {
      localStorage.removeItem(cacheKey);
    } catch {
      // Ignore errors
    }
  }, [cacheKey]);

  // Show indicator briefly when cached data is restored
  useEffect(() => {
    const cached = load();
    if (cached && Object.values(cached).some(Boolean)) {
      setHasCachedData(true);
      const timer = setTimeout(() => setHasCachedData(false), 5000);
      return () => clearTimeout(timer);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { load, save, clear, hasCachedData };
}
