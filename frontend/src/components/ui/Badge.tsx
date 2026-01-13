import type { CooptationStatus } from '../../types';

type BadgeVariant = 'default' | 'primary' | 'success' | 'warning' | 'error';

interface BadgeProps {
  status?: CooptationStatus;
  variant?: BadgeVariant;
  children?: React.ReactNode;
}

const statusConfig: Record<
  CooptationStatus,
  { className: string; label: string }
> = {
  pending: {
    className: 'bg-warning-light text-warning-dark dark:bg-warning-dark/20 dark:text-warning',
    label: 'En attente',
  },
  in_review: {
    className: 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400',
    label: "En cours d'examen",
  },
  interview: {
    className: 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400',
    label: 'En entretien',
  },
  accepted: {
    className: 'bg-success-light text-success-dark dark:bg-success-dark/20 dark:text-success',
    label: 'Accepté',
  },
  rejected: {
    className: 'bg-error-light text-error-dark dark:bg-error-dark/20 dark:text-error',
    label: 'Refusé',
  },
};

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  primary: 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400',
  success: 'bg-success-light text-success-dark dark:bg-success-dark/20 dark:text-success',
  warning: 'bg-warning-light text-warning-dark dark:bg-warning-dark/20 dark:text-warning',
  error: 'bg-error-light text-error-dark dark:bg-error-dark/20 dark:text-error',
};

export function Badge({ status, variant, children }: BadgeProps) {
  let className: string;
  let label: string | undefined;

  if (status) {
    const config = statusConfig[status];
    className = config.className;
    label = config.label;
  } else {
    className = variantClasses[variant || 'default'];
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}
    >
      {children || label}
    </span>
  );
}
