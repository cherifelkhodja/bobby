/**
 * Skeleton - Loading placeholder components
 *
 * Displays animated placeholders while content is loading.
 * Provides better perceived performance than spinners.
 */

import { ReactNode } from 'react';

interface SkeletonProps {
  /** Custom class name */
  className?: string;
  /** Width (can be Tailwind class or CSS value) */
  width?: string;
  /** Height (can be Tailwind class or CSS value) */
  height?: string;
}

export function Skeleton({ className = '', width, height }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-gray-200 dark:bg-gray-700 rounded ${className}`}
      style={{ width, height }}
    />
  );
}

/**
 * SkeletonText - Text line skeleton
 */
interface SkeletonTextProps {
  /** Number of lines */
  lines?: number;
  /** Width variations for each line */
  widths?: string[];
  /** Spacing between lines */
  spacing?: 'tight' | 'normal' | 'loose';
}

export function SkeletonText({
  lines = 1,
  widths = ['100%'],
  spacing = 'normal',
}: SkeletonTextProps) {
  const spacingClasses = {
    tight: 'space-y-1',
    normal: 'space-y-2',
    loose: 'space-y-3',
  };

  return (
    <div className={spacingClasses[spacing]}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          className="h-4"
          width={widths[index % widths.length]}
        />
      ))}
    </div>
  );
}

/**
 * SkeletonCard - Card skeleton for loading states
 */
interface SkeletonCardProps {
  /** Show header section */
  showHeader?: boolean;
  /** Number of content lines */
  contentLines?: number;
  /** Show footer section */
  showFooter?: boolean;
}

export function SkeletonCard({
  showHeader = true,
  contentLines = 3,
  showFooter = false,
}: SkeletonCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      {showHeader && (
        <div className="flex items-center mb-4">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="ml-4 flex-1">
            <Skeleton className="h-4 w-1/3 mb-2" />
            <Skeleton className="h-3 w-1/4" />
          </div>
        </div>
      )}

      <SkeletonText
        lines={contentLines}
        widths={['100%', '90%', '70%']}
        spacing="normal"
      />

      {showFooter && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-2">
          <Skeleton className="h-8 w-20 rounded" />
          <Skeleton className="h-8 w-20 rounded" />
        </div>
      )}
    </div>
  );
}

/**
 * SkeletonTable - Table skeleton for loading states
 */
interface SkeletonTableProps {
  /** Number of rows */
  rows?: number;
  /** Number of columns */
  columns?: number;
  /** Show header row */
  showHeader?: boolean;
}

export function SkeletonTable({
  rows = 5,
  columns = 4,
  showHeader = true,
}: SkeletonTableProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        {showHeader && (
          <thead className="bg-gray-50 dark:bg-gray-900/50">
            <tr>
              {Array.from({ length: columns }).map((_, index) => (
                <th key={index} className="px-6 py-3">
                  <Skeleton className="h-4 w-20" />
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr key={rowIndex}>
              {Array.from({ length: columns }).map((_, colIndex) => (
                <td key={colIndex} className="px-6 py-4">
                  <Skeleton
                    className="h-4"
                    width={colIndex === 0 ? '60%' : '40%'}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * SkeletonList - List skeleton for loading states
 */
interface SkeletonListProps {
  /** Number of items */
  items?: number;
  /** Show icon/avatar */
  showIcon?: boolean;
  /** Layout direction */
  direction?: 'horizontal' | 'vertical';
}

export function SkeletonList({
  items = 3,
  showIcon = true,
  direction = 'vertical',
}: SkeletonListProps) {
  const containerClass =
    direction === 'horizontal'
      ? 'flex gap-4 overflow-x-auto'
      : 'space-y-4';

  return (
    <div className={containerClass}>
      {Array.from({ length: items }).map((_, index) => (
        <div
          key={index}
          className={`flex items-center ${
            direction === 'horizontal' ? 'flex-shrink-0' : ''
          }`}
        >
          {showIcon && <Skeleton className="h-12 w-12 rounded-full" />}
          <div className={`flex-1 ${showIcon ? 'ml-4' : ''}`}>
            <Skeleton className="h-4 w-32 mb-2" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * SkeletonWrapper - Conditionally show skeleton or content
 */
interface SkeletonWrapperProps {
  /** Whether to show skeleton */
  isLoading: boolean;
  /** Skeleton element to show while loading */
  skeleton: ReactNode;
  /** Content to show when loaded */
  children: ReactNode;
}

export function SkeletonWrapper({
  isLoading,
  skeleton,
  children,
}: SkeletonWrapperProps) {
  if (isLoading) {
    return <>{skeleton}</>;
  }
  return <>{children}</>;
}
