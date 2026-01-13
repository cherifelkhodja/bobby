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
    className: 'bg-warning-light text-warning-dark',
    label: 'En attente',
  },
  in_review: {
    className: 'bg-primary-100 text-primary-700',
    label: "En cours d'examen",
  },
  interview: {
    className: 'bg-primary-100 text-primary-700',
    label: 'En entretien',
  },
  accepted: {
    className: 'bg-success-light text-success-dark',
    label: 'Accepté',
  },
  rejected: {
    className: 'bg-error-light text-error-dark',
    label: 'Refusé',
  },
};

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-gray-100 text-gray-700',
  primary: 'bg-primary-100 text-primary-700',
  success: 'bg-success-light text-success-dark',
  warning: 'bg-warning-light text-warning-dark',
  error: 'bg-error-light text-error-dark',
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
