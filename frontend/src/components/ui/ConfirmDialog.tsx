/**
 * ConfirmDialog - Reusable confirmation dialog component
 *
 * Provides a consistent way to ask for user confirmation before actions.
 */

import { AlertTriangle, Trash2, Info, HelpCircle } from 'lucide-react';
import { Modal } from './Modal';
import { Button } from './Button';

type ConfirmDialogVariant = 'danger' | 'warning' | 'info' | 'default';

interface ConfirmDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Callback when dialog is closed */
  onClose: () => void;
  /** Callback when user confirms */
  onConfirm: () => void;
  /** Dialog title */
  title: string;
  /** Dialog message */
  message: string;
  /** Confirm button text */
  confirmText?: string;
  /** Cancel button text */
  cancelText?: string;
  /** Visual variant */
  variant?: ConfirmDialogVariant;
  /** Whether confirm action is loading */
  isLoading?: boolean;
  /** Whether to close dialog on confirm */
  closeOnConfirm?: boolean;
}

const variantConfig: Record<
  ConfirmDialogVariant,
  {
    icon: typeof AlertTriangle;
    iconBg: string;
    iconColor: string;
    confirmVariant: 'primary' | 'danger' | 'secondary';
  }
> = {
  danger: {
    icon: Trash2,
    iconBg: 'bg-red-100 dark:bg-red-900/30',
    iconColor: 'text-red-600 dark:text-red-400',
    confirmVariant: 'danger',
  },
  warning: {
    icon: AlertTriangle,
    iconBg: 'bg-yellow-100 dark:bg-yellow-900/30',
    iconColor: 'text-yellow-600 dark:text-yellow-400',
    confirmVariant: 'primary',
  },
  info: {
    icon: Info,
    iconBg: 'bg-blue-100 dark:bg-blue-900/30',
    iconColor: 'text-blue-600 dark:text-blue-400',
    confirmVariant: 'primary',
  },
  default: {
    icon: HelpCircle,
    iconBg: 'bg-gray-100 dark:bg-gray-700',
    iconColor: 'text-gray-600 dark:text-gray-400',
    confirmVariant: 'primary',
  },
};

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirmer',
  cancelText = 'Annuler',
  variant = 'default',
  isLoading = false,
  closeOnConfirm = true,
}: ConfirmDialogProps) {
  const config = variantConfig[variant];
  const Icon = config.icon;

  const handleConfirm = () => {
    onConfirm();
    if (closeOnConfirm && !isLoading) {
      onClose();
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="sm">
      <div className="text-center">
        {/* Icon */}
        <div
          className={`mx-auto w-14 h-14 rounded-full flex items-center justify-center mb-4 ${config.iconBg}`}
        >
          <Icon className={`h-7 w-7 ${config.iconColor}`} />
        </div>

        {/* Title */}
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          {title}
        </h3>

        {/* Message */}
        <p className="text-gray-600 dark:text-gray-400 mb-6">{message}</p>

        {/* Actions */}
        <div className="flex gap-3 justify-center">
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={isLoading}
          >
            {cancelText}
          </Button>
          <Button
            variant={config.confirmVariant}
            onClick={handleConfirm}
            isLoading={isLoading}
          >
            {confirmText}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

/**
 * useConfirmDialog - Hook for managing confirm dialog state
 */
import { useState, useCallback } from 'react';

interface UseConfirmDialogOptions {
  onConfirm: () => void | Promise<void>;
  title?: string;
  message?: string;
  variant?: ConfirmDialogVariant;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useConfirmDialog(defaultOptions?: UseConfirmDialogOptions) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [options, setOptions] = useState<UseConfirmDialogOptions | null>(
    defaultOptions ?? null
  );

  const open = useCallback((newOptions?: UseConfirmDialogOptions) => {
    if (newOptions) {
      setOptions(newOptions);
    }
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    setIsLoading(false);
  }, []);

  const confirm = useCallback(async () => {
    if (!options?.onConfirm) return;

    try {
      setIsLoading(true);
      await options.onConfirm();
      close();
    } catch (error) {
      setIsLoading(false);
      throw error;
    }
  }, [options, close]);

  return {
    isOpen,
    isLoading,
    open,
    close,
    confirm,
    title: options?.title ?? 'Confirmer',
    message: options?.message ?? 'Êtes-vous sûr de vouloir continuer ?',
    variant: options?.variant ?? 'default',
  };
}
