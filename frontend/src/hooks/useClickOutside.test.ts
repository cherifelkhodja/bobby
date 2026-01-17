import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useClickOutside } from './useClickOutside';

describe('useClickOutside', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  it('should return a ref', () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useClickOutside(callback));

    expect(result.current).toHaveProperty('current');
  });

  it('should call callback when clicking outside', () => {
    const callback = vi.fn();
    const { result } = renderHook(() =>
      useClickOutside<HTMLDivElement>(callback)
    );

    // Create and attach element
    const element = document.createElement('div');
    container.appendChild(element);
    (result.current as React.MutableRefObject<HTMLDivElement>).current = element;

    // Click outside (on container, not on element)
    act(() => {
      const event = new MouseEvent('mousedown', { bubbles: true });
      container.dispatchEvent(event);
    });

    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should not call callback when clicking inside', () => {
    const callback = vi.fn();
    const { result } = renderHook(() =>
      useClickOutside<HTMLDivElement>(callback)
    );

    // Create and attach element
    const element = document.createElement('div');
    container.appendChild(element);
    (result.current as React.MutableRefObject<HTMLDivElement>).current = element;

    // Click inside the element
    act(() => {
      const event = new MouseEvent('mousedown', { bubbles: true });
      element.dispatchEvent(event);
    });

    expect(callback).not.toHaveBeenCalled();
  });

  it('should not call callback when clicking on child element', () => {
    const callback = vi.fn();
    const { result } = renderHook(() =>
      useClickOutside<HTMLDivElement>(callback)
    );

    // Create parent and child elements
    const parent = document.createElement('div');
    const child = document.createElement('button');
    parent.appendChild(child);
    container.appendChild(parent);
    (result.current as React.MutableRefObject<HTMLDivElement>).current = parent;

    // Click on child
    act(() => {
      const event = new MouseEvent('mousedown', { bubbles: true });
      child.dispatchEvent(event);
    });

    expect(callback).not.toHaveBeenCalled();
  });

  it('should respect enabled flag', () => {
    const callback = vi.fn();
    const { result, rerender } = renderHook(
      ({ enabled }) => useClickOutside<HTMLDivElement>(callback, enabled),
      { initialProps: { enabled: false } }
    );

    // Create and attach element
    const element = document.createElement('div');
    container.appendChild(element);
    (result.current as React.MutableRefObject<HTMLDivElement>).current = element;

    // Click outside when disabled
    act(() => {
      const event = new MouseEvent('mousedown', { bubbles: true });
      document.body.dispatchEvent(event);
    });

    expect(callback).not.toHaveBeenCalled();

    // Enable and click outside
    rerender({ enabled: true });

    act(() => {
      const event = new MouseEvent('mousedown', { bubbles: true });
      document.body.dispatchEvent(event);
    });

    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should handle touch events', () => {
    const callback = vi.fn();
    const { result } = renderHook(() =>
      useClickOutside<HTMLDivElement>(callback)
    );

    // Create and attach element
    const element = document.createElement('div');
    container.appendChild(element);
    (result.current as React.MutableRefObject<HTMLDivElement>).current = element;

    // Touch outside
    act(() => {
      const event = new TouchEvent('touchstart', { bubbles: true });
      container.dispatchEvent(event);
    });

    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should update callback ref when callback changes', () => {
    const callback1 = vi.fn();
    const callback2 = vi.fn();

    const { result, rerender } = renderHook(
      ({ callback }) => useClickOutside<HTMLDivElement>(callback),
      { initialProps: { callback: callback1 } }
    );

    // Create and attach element
    const element = document.createElement('div');
    container.appendChild(element);
    (result.current as React.MutableRefObject<HTMLDivElement>).current = element;

    // Change callback
    rerender({ callback: callback2 });

    // Click outside
    act(() => {
      const event = new MouseEvent('mousedown', { bubbles: true });
      document.body.dispatchEvent(event);
    });

    expect(callback1).not.toHaveBeenCalled();
    expect(callback2).toHaveBeenCalledTimes(1);
  });

  it('should cleanup event listeners on unmount', () => {
    const callback = vi.fn();
    const addEventListenerSpy = vi.spyOn(document, 'addEventListener');
    const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');

    const { unmount } = renderHook(() => useClickOutside(callback));

    expect(addEventListenerSpy).toHaveBeenCalledWith(
      'mousedown',
      expect.any(Function)
    );
    expect(addEventListenerSpy).toHaveBeenCalledWith(
      'touchstart',
      expect.any(Function)
    );

    unmount();

    expect(removeEventListenerSpy).toHaveBeenCalledWith(
      'mousedown',
      expect.any(Function)
    );
    expect(removeEventListenerSpy).toHaveBeenCalledWith(
      'touchstart',
      expect.any(Function)
    );

    addEventListenerSpy.mockRestore();
    removeEventListenerSpy.mockRestore();
  });

  it('should not call callback when ref is not attached', () => {
    const callback = vi.fn();
    renderHook(() => useClickOutside(callback));

    // Click without attaching ref
    act(() => {
      const event = new MouseEvent('mousedown', { bubbles: true });
      document.body.dispatchEvent(event);
    });

    expect(callback).not.toHaveBeenCalled();
  });
});
