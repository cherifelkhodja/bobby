import { renderHook } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useFormatDate } from './useFormatDate';

describe('useFormatDate', () => {
  beforeEach(() => {
    // Mock the current date to 2024-06-15T12:00:00Z
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-06-15T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('formatDate', () => {
    it('should format date string', () => {
      const { result } = renderHook(() => useFormatDate());

      const formatted = result.current.formatDate('2024-01-15');
      expect(formatted).toMatch(/15.*janvier.*2024/i);
    });

    it('should format Date object', () => {
      const { result } = renderHook(() => useFormatDate());

      const formatted = result.current.formatDate(new Date('2024-03-20'));
      expect(formatted).toMatch(/20.*mars.*2024/i);
    });

    it('should return "-" for null', () => {
      const { result } = renderHook(() => useFormatDate());

      expect(result.current.formatDate(null)).toBe('-');
    });

    it('should return "-" for undefined', () => {
      const { result } = renderHook(() => useFormatDate());

      expect(result.current.formatDate(undefined)).toBe('-');
    });

    it('should return "-" for invalid date', () => {
      const { result } = renderHook(() => useFormatDate());

      expect(result.current.formatDate('invalid-date')).toBe('-');
    });
  });

  describe('formatShortDate', () => {
    it('should format date in short format', () => {
      const { result } = renderHook(() => useFormatDate());

      const formatted = result.current.formatShortDate('2024-01-15');
      expect(formatted).toMatch(/15\/01\/2024/);
    });

    it('should return "-" for null', () => {
      const { result } = renderHook(() => useFormatDate());

      expect(result.current.formatShortDate(null)).toBe('-');
    });
  });

  describe('formatDateTime', () => {
    it('should format datetime', () => {
      const { result } = renderHook(() => useFormatDate());

      const formatted = result.current.formatDateTime('2024-01-15T14:30:00');
      expect(formatted).toMatch(/15.*janvier.*2024/i);
      // Time may vary by timezone, just check it's there
      expect(formatted).toMatch(/\d{2}:\d{2}/);
    });

    it('should return "-" for null', () => {
      const { result } = renderHook(() => useFormatDate());

      expect(result.current.formatDateTime(null)).toBe('-');
    });
  });

  describe('formatRelative', () => {
    it('should format seconds ago', () => {
      const { result } = renderHook(() => useFormatDate());

      const tenSecondsAgo = new Date('2024-06-15T11:59:50Z');
      const formatted = result.current.formatRelative(tenSecondsAgo);
      expect(formatted).toMatch(/seconde/i);
    });

    it('should format minutes ago', () => {
      const { result } = renderHook(() => useFormatDate());

      const thirtyMinutesAgo = new Date('2024-06-15T11:30:00Z');
      const formatted = result.current.formatRelative(thirtyMinutesAgo);
      expect(formatted).toMatch(/minute/i);
    });

    it('should format hours ago', () => {
      const { result } = renderHook(() => useFormatDate());

      const twoHoursAgo = new Date('2024-06-15T10:00:00Z');
      const formatted = result.current.formatRelative(twoHoursAgo);
      expect(formatted).toMatch(/heure/i);
    });

    it('should format days ago', () => {
      const { result } = renderHook(() => useFormatDate());

      const threeDaysAgo = new Date('2024-06-12T12:00:00Z');
      const formatted = result.current.formatRelative(threeDaysAgo);
      expect(formatted).toMatch(/jour/i);
    });

    it('should format weeks ago', () => {
      const { result } = renderHook(() => useFormatDate());

      const twoWeeksAgo = new Date('2024-06-01T12:00:00Z');
      const formatted = result.current.formatRelative(twoWeeksAgo);
      expect(formatted).toMatch(/semaine/i);
    });

    it('should format months ago', () => {
      const { result } = renderHook(() => useFormatDate());

      const twoMonthsAgo = new Date('2024-04-15T12:00:00Z');
      const formatted = result.current.formatRelative(twoMonthsAgo);
      expect(formatted).toMatch(/mois/i);
    });

    it('should format years ago', () => {
      const { result } = renderHook(() => useFormatDate());

      const twoYearsAgo = new Date('2022-06-15T12:00:00Z');
      const formatted = result.current.formatRelative(twoYearsAgo);
      expect(formatted).toMatch(/an/i);
    });

    it('should format future dates', () => {
      const { result } = renderHook(() => useFormatDate());

      const tomorrow = new Date('2024-06-16T12:00:00Z');
      const formatted = result.current.formatRelative(tomorrow);
      // Should contain "dans" for future
      expect(formatted).toMatch(/jour|demain/i);
    });

    it('should return "-" for null', () => {
      const { result } = renderHook(() => useFormatDate());

      expect(result.current.formatRelative(null)).toBe('-');
    });
  });

  describe('formatISO', () => {
    it('should format date to ISO string', () => {
      const { result } = renderHook(() => useFormatDate());

      const formatted = result.current.formatISO('2024-01-15T14:30:00Z');
      expect(formatted).toBe('2024-01-15');
    });

    it('should return empty string for null', () => {
      const { result } = renderHook(() => useFormatDate());

      expect(result.current.formatISO(null)).toBe('');
    });

    it('should return empty string for invalid date', () => {
      const { result } = renderHook(() => useFormatDate());

      expect(result.current.formatISO('invalid')).toBe('');
    });
  });
});
