import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useLocalStorage } from './useLocalStorage';

describe('useLocalStorage', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    // Suppress console warnings
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should return initial value when localStorage is empty', () => {
    const { result } = renderHook(() =>
      useLocalStorage('test-key', 'default')
    );

    expect(result.current[0]).toBe('default');
  });

  it('should return stored value when localStorage has data', () => {
    localStorage.setItem('test-key', JSON.stringify('stored value'));

    const { result } = renderHook(() =>
      useLocalStorage('test-key', 'default')
    );

    expect(result.current[0]).toBe('stored value');
  });

  it('should update localStorage when value changes', () => {
    const { result } = renderHook(() =>
      useLocalStorage('test-key', 'default')
    );

    act(() => {
      result.current[1]('new value');
    });

    expect(result.current[0]).toBe('new value');
    expect(localStorage.getItem('test-key')).toBe(JSON.stringify('new value'));
  });

  it('should support updater function', () => {
    const { result } = renderHook(() =>
      useLocalStorage<number>('counter', 0)
    );

    act(() => {
      result.current[1]((prev) => prev + 1);
    });

    expect(result.current[0]).toBe(1);

    act(() => {
      result.current[1]((prev) => prev + 1);
    });

    expect(result.current[0]).toBe(2);
  });

  it('should reset value to initial value when remove is called', () => {
    localStorage.setItem('test-key', JSON.stringify('stored'));

    const { result } = renderHook(() =>
      useLocalStorage('test-key', 'default')
    );

    expect(result.current[0]).toBe('stored');

    act(() => {
      result.current[2](); // remove function
    });

    // Value is reset to initial value
    expect(result.current[0]).toBe('default');
    // Note: useEffect will re-persist the initial value to localStorage
    // So localStorage won't be empty but will have the default value
    expect(localStorage.getItem('test-key')).toBe(JSON.stringify('default'));
  });

  it('should handle object values', () => {
    interface Settings {
      theme: string;
      fontSize: number;
    }

    const defaultSettings: Settings = { theme: 'light', fontSize: 14 };

    const { result } = renderHook(() =>
      useLocalStorage<Settings>('settings', defaultSettings)
    );

    expect(result.current[0]).toEqual(defaultSettings);

    const newSettings: Settings = { theme: 'dark', fontSize: 16 };
    act(() => {
      result.current[1](newSettings);
    });

    expect(result.current[0]).toEqual(newSettings);
    expect(localStorage.getItem('settings')).toBe(JSON.stringify(newSettings));
  });

  it('should handle array values', () => {
    const { result } = renderHook(() =>
      useLocalStorage<string[]>('items', [])
    );

    act(() => {
      result.current[1](['a', 'b', 'c']);
    });

    expect(result.current[0]).toEqual(['a', 'b', 'c']);
  });

  it('should handle boolean values', () => {
    const { result } = renderHook(() =>
      useLocalStorage('enabled', false)
    );

    act(() => {
      result.current[1](true);
    });

    expect(result.current[0]).toBe(true);
    expect(localStorage.getItem('enabled')).toBe('true');
  });

  it('should handle null values', () => {
    const { result } = renderHook(() =>
      useLocalStorage<string | null>('nullable', null)
    );

    expect(result.current[0]).toBeNull();

    act(() => {
      result.current[1]('not null');
    });

    expect(result.current[0]).toBe('not null');

    act(() => {
      result.current[1](null);
    });

    expect(result.current[0]).toBeNull();
  });

  it('should handle JSON parse errors gracefully', () => {
    // Set invalid JSON in localStorage
    localStorage.setItem('corrupted', 'not valid json{');

    const { result } = renderHook(() =>
      useLocalStorage('corrupted', 'default')
    );

    expect(result.current[0]).toBe('default');
    expect(console.warn).toHaveBeenCalled();
  });

  it('should use same key for different hook instances', () => {
    const { result: result1 } = renderHook(() =>
      useLocalStorage('shared-key', 'default1')
    );

    act(() => {
      result1.current[1]('from hook 1');
    });

    // New hook with same key should read the updated value from localStorage
    const { result: result2 } = renderHook(() =>
      useLocalStorage('shared-key', 'default2')
    );

    expect(result2.current[0]).toBe('from hook 1');
  });
});
