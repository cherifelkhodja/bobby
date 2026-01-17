import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useSearch } from './useSearch';

describe('useSearch', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should initialize with empty search by default', () => {
    const { result } = renderHook(() => useSearch());

    expect(result.current.search).toBe('');
    expect(result.current.debouncedSearch).toBe('');
    expect(result.current.hasSearch).toBe(false);
  });

  it('should initialize with provided initial value', () => {
    const { result } = renderHook(() =>
      useSearch({ initialValue: 'initial' })
    );

    expect(result.current.search).toBe('initial');
    expect(result.current.debouncedSearch).toBe('initial');
    expect(result.current.hasSearch).toBe(true);
  });

  it('should update search immediately', () => {
    const { result } = renderHook(() => useSearch());

    act(() => {
      result.current.setSearch('test');
    });

    expect(result.current.search).toBe('test');
    expect(result.current.hasSearch).toBe(true);
  });

  it('should debounce search value', () => {
    const { result } = renderHook(() => useSearch({ delay: 300 }));

    act(() => {
      result.current.setSearch('test');
    });

    // Immediate value updated
    expect(result.current.search).toBe('test');
    // Debounced value not yet updated
    expect(result.current.debouncedSearch).toBe('');

    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Now debounced value should be updated
    expect(result.current.debouncedSearch).toBe('test');
  });

  it('should use default delay of 300ms', () => {
    const { result } = renderHook(() => useSearch());

    act(() => {
      result.current.setSearch('test');
    });

    act(() => {
      vi.advanceTimersByTime(299);
    });

    expect(result.current.debouncedSearch).toBe('');

    act(() => {
      vi.advanceTimersByTime(1);
    });

    expect(result.current.debouncedSearch).toBe('test');
  });

  it('should clear search', () => {
    const { result } = renderHook(() =>
      useSearch({ initialValue: 'initial' })
    );

    act(() => {
      result.current.clear();
    });

    expect(result.current.search).toBe('');
    expect(result.current.hasSearch).toBe(false);
  });

  it('should clear debounced value after delay', () => {
    const { result } = renderHook(() =>
      useSearch({ initialValue: 'initial', delay: 300 })
    );

    act(() => {
      result.current.clear();
    });

    expect(result.current.search).toBe('');
    expect(result.current.debouncedSearch).toBe('initial');

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current.debouncedSearch).toBe('');
  });

  it('should handle rapid input changes', () => {
    const { result } = renderHook(() => useSearch({ delay: 300 }));

    act(() => {
      result.current.setSearch('t');
    });

    act(() => {
      vi.advanceTimersByTime(100);
    });

    act(() => {
      result.current.setSearch('te');
    });

    act(() => {
      vi.advanceTimersByTime(100);
    });

    act(() => {
      result.current.setSearch('tes');
    });

    act(() => {
      vi.advanceTimersByTime(100);
    });

    act(() => {
      result.current.setSearch('test');
    });

    // Immediate value should be "test"
    expect(result.current.search).toBe('test');
    // Debounced should still be empty
    expect(result.current.debouncedSearch).toBe('');

    // Wait for full delay after last change
    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Now should be "test"
    expect(result.current.debouncedSearch).toBe('test');
  });

  it('should work with custom delay', () => {
    const { result } = renderHook(() => useSearch({ delay: 500 }));

    act(() => {
      result.current.setSearch('test');
    });

    act(() => {
      vi.advanceTimersByTime(400);
    });

    expect(result.current.debouncedSearch).toBe('');

    act(() => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current.debouncedSearch).toBe('test');
  });

  it('should track hasSearch correctly', () => {
    const { result } = renderHook(() => useSearch());

    expect(result.current.hasSearch).toBe(false);

    act(() => {
      result.current.setSearch('a');
    });

    expect(result.current.hasSearch).toBe(true);

    act(() => {
      result.current.setSearch('');
    });

    expect(result.current.hasSearch).toBe(false);
  });
});
