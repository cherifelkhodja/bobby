/**
 * StatCard - Reusable statistics card component
 *
 * Displays a statistic value with label and optional icon.
 */

import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  /** Label for the statistic */
  label: string;
  /** Value to display */
  value: string | number;
  /** Optional icon */
  icon?: LucideIcon;
  /** Color theme for the icon background */
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'gray';
  /** Optional subtext */
  subtext?: string;
  /** Optional loading state */
  isLoading?: boolean;
}

const colorClasses = {
  blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
  green: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
  yellow: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400',
  red: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
  purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
  gray: 'bg-gray-100 dark:bg-gray-900/30 text-gray-600 dark:text-gray-400',
};

export function StatCard({
  label,
  value,
  icon: Icon,
  color = 'blue',
  subtext,
  isLoading,
}: StatCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center">
        {Icon && (
          <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
            <Icon className="h-6 w-6" />
          </div>
        )}
        <div className={Icon ? 'ml-4' : ''}>
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
            {label}
          </p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {isLoading ? (
              <span className="inline-block w-12 h-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
            ) : (
              value ?? '-'
            )}
          </p>
          {subtext && (
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              {subtext}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

interface StatCardGridProps {
  children: React.ReactNode;
  /** Number of columns (default: 3) */
  columns?: 2 | 3 | 4;
}

const columnClasses = {
  2: 'md:grid-cols-2',
  3: 'md:grid-cols-3',
  4: 'md:grid-cols-4',
};

export function StatCardGrid({ children, columns = 3 }: StatCardGridProps) {
  return (
    <div className={`grid grid-cols-1 ${columnClasses[columns]} gap-4`}>
      {children}
    </div>
  );
}
