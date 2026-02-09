/**
 * Tests for useFormCache hook.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useFormCache } from './useFormCache';

describe('useFormCache', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns null when no cached data exists', () => {
    const { result } = renderHook(() =>
      useFormCache<Record<string, unknown>>('test-token', 'prefix')
    );

    expect(result.current.load()).toBeNull();
  });

  it('saves and loads form data', () => {
    const { result } = renderHook(() =>
      useFormCache<Record<string, unknown>>('test-token', 'prefix')
    );

    act(() => {
      result.current.save({ name: 'Jean', email: 'jean@test.com' });
    });

    const loaded = result.current.load();
    expect(loaded).toEqual({ name: 'Jean', email: 'jean@test.com' });
  });

  it('clears cached data', () => {
    const { result } = renderHook(() =>
      useFormCache<Record<string, unknown>>('test-token', 'prefix')
    );

    act(() => {
      result.current.save({ name: 'Jean' });
    });
    expect(result.current.load()).not.toBeNull();

    act(() => {
      result.current.clear();
    });
    expect(result.current.load()).toBeNull();
  });

  it('returns null when cache is expired', () => {
    const cacheDurationMs = 1000;
    const { result } = renderHook(() =>
      useFormCache<Record<string, unknown>>('test-token', 'prefix', cacheDurationMs)
    );

    act(() => {
      result.current.save({ name: 'Jean' });
    });

    // Advance time beyond cache duration
    vi.advanceTimersByTime(cacheDurationMs + 100);

    expect(result.current.load()).toBeNull();
  });

  it('returns data when cache is not yet expired', () => {
    const cacheDurationMs = 10000;
    const { result } = renderHook(() =>
      useFormCache<Record<string, unknown>>('test-token', 'prefix', cacheDurationMs)
    );

    act(() => {
      result.current.save({ name: 'Jean' });
    });

    vi.advanceTimersByTime(5000);

    expect(result.current.load()).toEqual({ name: 'Jean' });
  });

  it('uses token-specific cache keys', () => {
    const { result: hook1 } = renderHook(() =>
      useFormCache<Record<string, unknown>>('token-1', 'prefix')
    );
    const { result: hook2 } = renderHook(() =>
      useFormCache<Record<string, unknown>>('token-2', 'prefix')
    );

    act(() => {
      hook1.current.save({ name: 'Jean' });
      hook2.current.save({ name: 'Pierre' });
    });

    expect(hook1.current.load()).toEqual({ name: 'Jean' });
    expect(hook2.current.load()).toEqual({ name: 'Pierre' });
  });

  it('returns null when token is undefined', () => {
    const { result } = renderHook(() =>
      useFormCache<Record<string, unknown>>(undefined, 'prefix')
    );

    expect(result.current.load()).toBeNull();
  });

  it('hasCachedData is initially true when data is restored, then becomes false after timeout', async () => {
    // Pre-populate cache
    const key = 'prefix_token-cached';
    const entry = JSON.stringify({ data: { name: 'Jean' }, timestamp: Date.now() });
    localStorage.setItem(key, entry);

    const { result } = renderHook(() =>
      useFormCache<Record<string, unknown>>('token-cached', 'prefix')
    );

    expect(result.current.hasCachedData).toBe(true);

    // After 5s the indicator should disappear
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current.hasCachedData).toBe(false);
  });
});
