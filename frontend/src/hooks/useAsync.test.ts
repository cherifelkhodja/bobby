import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useAsync } from './useAsync';

describe('useAsync', () => {
  it('should initialize with idle state', () => {
    const asyncFn = vi.fn();
    const { result } = renderHook(() => useAsync(asyncFn));

    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.data).toBeNull();
  });

  it('should set loading state when executing', async () => {
    let resolvePromise: (value: string) => void;
    const asyncFn = vi.fn(
      () =>
        new Promise<string>((resolve) => {
          resolvePromise = resolve;
        })
    );

    const { result } = renderHook(() => useAsync(asyncFn));

    act(() => {
      result.current.execute();
    });

    expect(result.current.isLoading).toBe(true);

    // Resolve and wait for completion
    await act(async () => {
      resolvePromise!('done');
    });

    expect(result.current.isLoading).toBe(false);
  });

  it('should set data on success', async () => {
    const asyncFn = vi.fn().mockResolvedValue('success data');

    const { result } = renderHook(() => useAsync(asyncFn));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toBe('success data');
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it('should set error on failure', async () => {
    const error = new Error('test error');
    const asyncFn = vi.fn().mockRejectedValue(error);

    const { result } = renderHook(() => useAsync(asyncFn));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.error).toEqual(error);
    expect(result.current.data).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it('should convert non-Error rejections to Error', async () => {
    const asyncFn = vi.fn().mockRejectedValue('string error');

    const { result } = renderHook(() => useAsync(asyncFn));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe('string error');
  });

  it('should return result from execute', async () => {
    const asyncFn = vi.fn().mockResolvedValue('result');

    const { result } = renderHook(() => useAsync(asyncFn));

    let executeResult: string | null = null;
    await act(async () => {
      executeResult = await result.current.execute();
    });

    expect(executeResult).toBe('result');
  });

  it('should return null from execute on error', async () => {
    const asyncFn = vi.fn().mockRejectedValue(new Error('fail'));

    const { result } = renderHook(() => useAsync(asyncFn));

    let executeResult: string | null = 'initial';
    await act(async () => {
      executeResult = await result.current.execute();
    });

    expect(executeResult).toBeNull();
  });

  it('should pass arguments to async function', async () => {
    const asyncFn = vi.fn().mockResolvedValue('done');

    const { result } = renderHook(() =>
      useAsync<string, [string, number]>(asyncFn)
    );

    await act(async () => {
      await result.current.execute('arg1', 42);
    });

    expect(asyncFn).toHaveBeenCalledWith('arg1', 42);
  });

  it('should reset state', async () => {
    const asyncFn = vi.fn().mockResolvedValue('data');

    const { result } = renderHook(() => useAsync(asyncFn));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toBe('data');

    act(() => {
      result.current.reset();
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it('should clear only error', async () => {
    const asyncFn = vi.fn().mockRejectedValue(new Error('fail'));

    const { result } = renderHook(() => useAsync(asyncFn));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.error).not.toBeNull();

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it('should clear error when executing again', async () => {
    const asyncFn = vi
      .fn()
      .mockRejectedValueOnce(new Error('fail'))
      .mockResolvedValueOnce('success');

    const { result } = renderHook(() => useAsync(asyncFn));

    // First call fails
    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.error).not.toBeNull();

    // Second call starts - error should be cleared
    let secondExecutePromise: Promise<string | null>;
    act(() => {
      secondExecutePromise = result.current.execute();
    });

    expect(result.current.error).toBeNull();

    await act(async () => {
      await secondExecutePromise;
    });

    expect(result.current.data).toBe('success');
  });

  it('should handle multiple executions', async () => {
    let callCount = 0;
    const asyncFn = vi.fn().mockImplementation(async () => {
      callCount++;
      return `result ${callCount}`;
    });

    const { result } = renderHook(() => useAsync(asyncFn));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toBe('result 1');

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toBe('result 2');
  });

  it('should preserve data on error', async () => {
    const asyncFn = vi
      .fn()
      .mockResolvedValueOnce('initial data')
      .mockRejectedValueOnce(new Error('fail'));

    const { result } = renderHook(() => useAsync(asyncFn));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toBe('initial data');

    await act(async () => {
      await result.current.execute();
    });

    // Data is preserved when error occurs (hook uses ...prev in catch)
    expect(result.current.data).toBe('initial data');
    expect(result.current.error).not.toBeNull();
  });
});
