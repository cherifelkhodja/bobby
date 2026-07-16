/**
 * StatCard - Reusable statistics card component (KPI v2)
 *
 * Displays a statistic value with label and optional subtext,
 * following the Bobby v2 KPI card design.
 */

import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  /** Label for the statistic */
  label: string;
  /** Value to display */
  value: string | number;
  /** Optional icon */
  icon?: LucideIcon;
  /** Color theme applied to the value */
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'gray';
  /** Optional subtext */
  subtext?: string;
  /** Optional loading state */
  isLoading?: boolean;
}

const valueColorClasses = {
  blue: 'text-ink',
  green: 'text-grn-fg',
  yellow: 'text-amb-fg',
  red: 'text-redt',
  purple: 'text-ind-fg',
  gray: 'text-ink',
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
    <div className="bg-sur border border-lin rounded-xl px-[18px] py-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[12.5px] font-medium text-mut m-0">{label}</p>
        {Icon && <Icon className="h-4 w-4 text-mut2 shrink-0 mt-0.5" />}
      </div>
      <p className={`text-[26px] font-bold tracking-[-0.02em] mt-1.5 mb-[3px] ${valueColorClasses[color]}`}>
        {isLoading ? (
          <span className="inline-block w-12 h-8 bg-lin2 rounded animate-pulse" />
        ) : (
          value ?? '-'
        )}
      </p>
      {subtext && <p className="text-[11.5px] text-mut2 m-0">{subtext}</p>}
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
    <div className={`grid grid-cols-1 ${columnClasses[columns]} gap-3.5`}>
      {children}
    </div>
  );
}
