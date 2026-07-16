import type { CooptationStatus } from '../../types';

type BadgeVariant = 'default' | 'primary' | 'success' | 'warning' | 'error';

interface BadgeProps {
  status?: CooptationStatus;
  variant?: BadgeVariant;
  children?: React.ReactNode;
  className?: string;
  /** Affiche le point coloré v2 devant le libellé (défaut : true) */
  dot?: boolean;
}

const statusConfig: Record<
  CooptationStatus,
  { className: string; label: string }
> = {
  pending: {
    className: 'bg-amb-bg text-amb-fg',
    label: 'En attente',
  },
  in_review: {
    className: 'bg-blu-bg text-blu-fg',
    label: "En cours d'examen",
  },
  interview: {
    className: 'bg-ind-bg text-ind-fg',
    label: 'En entretien',
  },
  accepted: {
    className: 'bg-grn-bg text-grn-fg',
    label: 'Accepté',
  },
  rejected: {
    className: 'bg-red-bg text-red-fg',
    label: 'Refusé',
  },
};

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-sla-bg text-sla-fg',
  primary: 'bg-blu-bg text-blu-fg',
  success: 'bg-grn-bg text-grn-fg',
  warning: 'bg-amb-bg text-amb-fg',
  error: 'bg-red-bg text-red-fg',
};

export function Badge({ status, variant, children, className: extraClassName, dot = true }: BadgeProps) {
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
      className={`inline-flex items-center gap-[7px] rounded-full px-[11px] py-1 text-xs font-medium whitespace-nowrap ${className} ${extraClassName || ''}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current shrink-0" aria-hidden="true" />}
      {children || label}
    </span>
  );
}
