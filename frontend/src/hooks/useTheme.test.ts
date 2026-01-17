/**
 * Tests for useTheme hook
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTheme } from './useTheme';

// Helper to create matchMedia mock
const createMatchMediaMock = (prefersDark: boolean = false) => {
  return vi.fn().mockImplementation((query: string) => ({
    matches: prefersDark && query === '(prefers-color-scheme: dark)',
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
};

describe('useTheme', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    // Reset document classList
    document.documentElement.classList.remove('dark');
    // Set up matchMedia mock (prefer light by default)
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: createMatchMediaMock(false),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initial state', () => {
    it('should default to system theme when no stored preference', () => {
      const { result } = renderHook(() => useTheme());

      expect(result.current.theme).toBe('system');
    });

    it('should load stored theme from localStorage', () => {
      localStorage.setItem('theme', 'dark');

      const { result } = renderHook(() => useTheme());

      expect(result.current.theme).toBe('dark');
    });

    it('should resolve system theme based on media query', () => {
      // Mock matchMedia to prefer dark
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: createMatchMediaMock(true),
      });

      const { result } = renderHook(() => useTheme());

      expect(result.current.resolvedTheme).toBe('dark');
      expect(result.current.isDark).toBe(true);
    });
  });

  describe('setTheme', () => {
    it('should update theme to light', () => {
      const { result } = renderHook(() => useTheme());

      act(() => {
        result.current.setTheme('light');
      });

      expect(result.current.theme).toBe('light');
      expect(result.current.resolvedTheme).toBe('light');
      expect(result.current.isDark).toBe(false);
    });

    it('should update theme to dark', () => {
      const { result } = renderHook(() => useTheme());

      act(() => {
        result.current.setTheme('dark');
      });

      expect(result.current.theme).toBe('dark');
      expect(result.current.resolvedTheme).toBe('dark');
      expect(result.current.isDark).toBe(true);
    });

    it('should persist theme to localStorage', () => {
      const { result } = renderHook(() => useTheme());

      act(() => {
        result.current.setTheme('dark');
      });

      expect(localStorage.getItem('theme')).toBe('dark');
    });

    it('should add dark class to document when theme is dark', () => {
      const { result } = renderHook(() => useTheme());

      act(() => {
        result.current.setTheme('dark');
      });

      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should remove dark class when theme is light', () => {
      document.documentElement.classList.add('dark');

      const { result } = renderHook(() => useTheme());

      act(() => {
        result.current.setTheme('light');
      });

      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });
  });

  describe('toggleTheme', () => {
    it('should cycle from system to light', () => {
      const { result } = renderHook(() => useTheme());

      act(() => {
        result.current.toggleTheme();
      });

      expect(result.current.theme).toBe('light');
    });

    it('should cycle from light to dark', () => {
      localStorage.setItem('theme', 'light');
      const { result } = renderHook(() => useTheme());

      act(() => {
        result.current.toggleTheme();
      });

      expect(result.current.theme).toBe('dark');
    });

    it('should cycle from dark to system', () => {
      localStorage.setItem('theme', 'dark');
      const { result } = renderHook(() => useTheme());

      act(() => {
        result.current.toggleTheme();
      });

      expect(result.current.theme).toBe('system');
    });

    it('should complete full cycle', () => {
      const { result } = renderHook(() => useTheme());

      // Start at system
      expect(result.current.theme).toBe('system');

      // Toggle to light
      act(() => {
        result.current.toggleTheme();
      });
      expect(result.current.theme).toBe('light');

      // Toggle to dark
      act(() => {
        result.current.toggleTheme();
      });
      expect(result.current.theme).toBe('dark');

      // Toggle back to system
      act(() => {
        result.current.toggleTheme();
      });
      expect(result.current.theme).toBe('system');
    });
  });
});
