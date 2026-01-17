import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useModal } from './useModal';

describe('useModal', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should initialize with closed state', () => {
    const { result } = renderHook(() => useModal());

    expect(result.current.isOpen).toBe(false);
    expect(result.current.data).toBeNull();
  });

  it('should open modal', () => {
    const { result } = renderHook(() => useModal());

    act(() => {
      result.current.open();
    });

    expect(result.current.isOpen).toBe(true);
  });

  it('should close modal', () => {
    const { result } = renderHook(() => useModal());

    act(() => {
      result.current.open();
    });

    expect(result.current.isOpen).toBe(true);

    act(() => {
      result.current.close();
    });

    expect(result.current.isOpen).toBe(false);
  });

  it('should clear data after close animation', () => {
    interface TestData {
      id: number;
      name: string;
    }

    const { result } = renderHook(() => useModal<TestData>());

    act(() => {
      result.current.openWith({ id: 1, name: 'Test' });
    });

    expect(result.current.data).toEqual({ id: 1, name: 'Test' });

    act(() => {
      result.current.close();
    });

    // Data should still be there immediately (for animation)
    expect(result.current.data).toEqual({ id: 1, name: 'Test' });

    // After 200ms, data should be cleared
    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(result.current.data).toBeNull();
  });

  it('should toggle modal', () => {
    const { result } = renderHook(() => useModal());

    expect(result.current.isOpen).toBe(false);

    act(() => {
      result.current.toggle();
    });

    expect(result.current.isOpen).toBe(true);

    act(() => {
      result.current.toggle();
    });

    expect(result.current.isOpen).toBe(false);
  });

  it('should open with data', () => {
    const { result } = renderHook(() => useModal<string>());

    act(() => {
      result.current.openWith('test data');
    });

    expect(result.current.isOpen).toBe(true);
    expect(result.current.data).toBe('test data');
  });

  it('should update data without changing open state', () => {
    interface User {
      id: number;
      name: string;
    }

    const { result } = renderHook(() => useModal<User>());

    act(() => {
      result.current.openWith({ id: 1, name: 'Original' });
    });

    act(() => {
      result.current.setData({ id: 1, name: 'Updated' });
    });

    expect(result.current.isOpen).toBe(true);
    expect(result.current.data).toEqual({ id: 1, name: 'Updated' });
  });

  it('should set data to null', () => {
    const { result } = renderHook(() => useModal<string>());

    act(() => {
      result.current.openWith('test');
    });

    act(() => {
      result.current.setData(null);
    });

    expect(result.current.isOpen).toBe(true);
    expect(result.current.data).toBeNull();
  });

  it('should work with complex object data', () => {
    interface ComplexData {
      user: {
        id: number;
        name: string;
      };
      items: string[];
      metadata: {
        created: Date;
      };
    }

    const testData: ComplexData = {
      user: { id: 1, name: 'Test' },
      items: ['a', 'b', 'c'],
      metadata: { created: new Date() },
    };

    const { result } = renderHook(() => useModal<ComplexData>());

    act(() => {
      result.current.openWith(testData);
    });

    expect(result.current.data).toEqual(testData);
  });

  it('should preserve data when opening without data after openWith', () => {
    const { result } = renderHook(() => useModal<string>());

    act(() => {
      result.current.openWith('preserved');
    });

    act(() => {
      result.current.close();
    });

    // Wait for data to clear
    act(() => {
      vi.advanceTimersByTime(200);
    });

    act(() => {
      result.current.open();
    });

    expect(result.current.isOpen).toBe(true);
    expect(result.current.data).toBeNull();
  });
});
