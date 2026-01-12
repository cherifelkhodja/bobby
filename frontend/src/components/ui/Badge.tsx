import type { CooptationStatus } from '../../types';

interface BadgeProps {
  status: CooptationStatus;
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

export function Badge({ status, children }: BadgeProps) {
  const config = statusConfig[status];

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className}`}
    >
      {children || config.label}
    </span>
  );
}
