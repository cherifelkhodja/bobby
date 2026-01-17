/**
 * useFormatDate - Hook for consistent French date formatting
 *
 * Provides memoized date formatting functions for French locale.
 *
 * @example
 * const { formatDate, formatDateTime, formatRelative } = useFormatDate();
 *
 * formatDate('2024-01-15') // "15 janvier 2024"
 * formatDateTime('2024-01-15T14:30:00') // "15 janvier 2024 à 14:30"
 * formatRelative('2024-01-15T14:30:00') // "il y a 2 jours"
 */

import { useCallback, useMemo } from 'react';

interface UseFormatDateResult {
  /** Format date as "15 janvier 2024" */
  formatDate: (date: string | Date | null | undefined) => string;
  /** Format date as "15/01/2024" */
  formatShortDate: (date: string | Date | null | undefined) => string;
  /** Format datetime as "15 janvier 2024 à 14:30" */
  formatDateTime: (date: string | Date | null | undefined) => string;
  /** Format relative time as "il y a 2 jours" */
  formatRelative: (date: string | Date | null | undefined) => string;
  /** Format as ISO date "2024-01-15" */
  formatISO: (date: string | Date | null | undefined) => string;
}

export function useFormatDate(): UseFormatDateResult {
  const dateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat('fr-FR', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      }),
    []
  );

  const shortDateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      }),
    []
  );

  const dateTimeFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat('fr-FR', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }),
    []
  );

  const relativeFormatter = useMemo(
    () => new Intl.RelativeTimeFormat('fr-FR', { numeric: 'auto' }),
    []
  );

  const parseDate = useCallback(
    (date: string | Date | null | undefined): Date | null => {
      if (!date) return null;
      const parsed = date instanceof Date ? date : new Date(date);
      return isNaN(parsed.getTime()) ? null : parsed;
    },
    []
  );

  const formatDate = useCallback(
    (date: string | Date | null | undefined): string => {
      const parsed = parseDate(date);
      if (!parsed) return '-';
      return dateFormatter.format(parsed);
    },
    [parseDate, dateFormatter]
  );

  const formatShortDate = useCallback(
    (date: string | Date | null | undefined): string => {
      const parsed = parseDate(date);
      if (!parsed) return '-';
      return shortDateFormatter.format(parsed);
    },
    [parseDate, shortDateFormatter]
  );

  const formatDateTime = useCallback(
    (date: string | Date | null | undefined): string => {
      const parsed = parseDate(date);
      if (!parsed) return '-';
      return dateTimeFormatter.format(parsed);
    },
    [parseDate, dateTimeFormatter]
  );

  const formatRelative = useCallback(
    (date: string | Date | null | undefined): string => {
      const parsed = parseDate(date);
      if (!parsed) return '-';

      const now = new Date();
      const diffMs = parsed.getTime() - now.getTime();
      const diffSeconds = Math.round(diffMs / 1000);
      const diffMinutes = Math.round(diffSeconds / 60);
      const diffHours = Math.round(diffMinutes / 60);
      const diffDays = Math.round(diffHours / 24);
      const diffWeeks = Math.round(diffDays / 7);
      const diffMonths = Math.round(diffDays / 30);
      const diffYears = Math.round(diffDays / 365);

      if (Math.abs(diffSeconds) < 60) {
        return relativeFormatter.format(diffSeconds, 'second');
      } else if (Math.abs(diffMinutes) < 60) {
        return relativeFormatter.format(diffMinutes, 'minute');
      } else if (Math.abs(diffHours) < 24) {
        return relativeFormatter.format(diffHours, 'hour');
      } else if (Math.abs(diffDays) < 7) {
        return relativeFormatter.format(diffDays, 'day');
      } else if (Math.abs(diffWeeks) < 4) {
        return relativeFormatter.format(diffWeeks, 'week');
      } else if (Math.abs(diffMonths) < 12) {
        return relativeFormatter.format(diffMonths, 'month');
      } else {
        return relativeFormatter.format(diffYears, 'year');
      }
    },
    [parseDate, relativeFormatter]
  );

  const formatISO = useCallback(
    (date: string | Date | null | undefined): string => {
      const parsed = parseDate(date);
      if (!parsed) return '';
      return parsed.toISOString().split('T')[0];
    },
    [parseDate]
  );

  return {
    formatDate,
    formatShortDate,
    formatDateTime,
    formatRelative,
    formatISO,
  };
}
