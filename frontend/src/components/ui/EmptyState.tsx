/**
 * EmptyState - Reusable empty state component
 *
 * Displays a centered message when there is no data to show.
 */

import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Button } from './Button';

interface EmptyStateProps {
  /** Icon to display */
  icon?: LucideIcon;
  /** Main title */
  title: string;
  /** Optional description */
  description?: string;
  /** Optional action button */
  action?: {
    label: string;
    onClick: () => void;
  };
  /** Custom children to render */
  children?: ReactNode;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  children,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      {Icon && (
        <div className="mb-4 h-12 w-12 rounded-xl bg-lin2 flex items-center justify-center">
          <Icon className="h-6 w-6 text-mut2" />
        </div>
      )}

      <h3 className="text-[13.5px] font-semibold text-ink mb-1">
        {title}
      </h3>

      {description && (
        <p className="text-xs text-mut max-w-sm leading-relaxed">
          {description}
        </p>
      )}

      {action && (
        <div className="mt-6">
          <Button onClick={action.onClick}>{action.label}</Button>
        </div>
      )}

      {children && <div className="mt-6">{children}</div>}
    </div>
  );
}
