/**
 * useClickOutside - Hook for detecting clicks outside an element
 *
 * Triggers a callback when a click occurs outside the referenced element.
 * Useful for closing dropdowns, modals, and popovers.
 *
 * @example
 * const dropdownRef = useClickOutside<HTMLDivElement>(() => setIsOpen(false));
 *
 * <div ref={dropdownRef}>
 *   <button onClick={() => setIsOpen(true)}>Toggle</button>
 *   {isOpen && <DropdownMenu />}
 * </div>
 */

import { useEffect, useRef, useCallback } from 'react';

export function useClickOutside<T extends HTMLElement = HTMLElement>(
  callback: () => void,
  enabled: boolean = true
): React.RefObject<T> {
  const ref = useRef<T>(null);
  const callbackRef = useRef(callback);

  // Update callback ref on change
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  const handleClick = useCallback((event: MouseEvent | TouchEvent) => {
    if (ref.current && !ref.current.contains(event.target as Node)) {
      callbackRef.current();
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;

    document.addEventListener('mousedown', handleClick);
    document.addEventListener('touchstart', handleClick);

    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('touchstart', handleClick);
    };
  }, [enabled, handleClick]);

  return ref;
}
