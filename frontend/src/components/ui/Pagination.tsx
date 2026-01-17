/**
 * Pagination - Reusable pagination component
 *
 * Provides navigation controls for paginated data.
 */

import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

interface PaginationProps {
  /** Current page (1-indexed) */
  page: number;
  /** Total number of items */
  total: number;
  /** Items per page */
  pageSize: number;
  /** Callback when page changes */
  onPageChange: (page: number) => void;
  /** Show first/last buttons (default: true) */
  showFirstLast?: boolean;
  /** Show page info (default: true) */
  showPageInfo?: boolean;
  /** Custom class name */
  className?: string;
}

export function Pagination({
  page,
  total,
  pageSize,
  onPageChange,
  showFirstLast = true,
  showPageInfo = true,
  className = '',
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const hasPrevious = page > 1;
  const hasNext = page < totalPages;

  // Don't render if there's only one page
  if (totalPages <= 1 && !showPageInfo) {
    return null;
  }

  return (
    <div
      className={`flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700 ${className}`}
    >
      {showPageInfo && (
        <p className="text-sm text-gray-700 dark:text-gray-300">
          Page {page} sur {totalPages}
          {total > 0 && (
            <span className="text-gray-500 dark:text-gray-400">
              {' '}
              ({total} résultat{total > 1 ? 's' : ''})
            </span>
          )}
        </p>
      )}

      <div className="flex gap-1">
        {showFirstLast && (
          <PaginationButton
            onClick={() => onPageChange(1)}
            disabled={!hasPrevious}
            title="Première page"
          >
            <ChevronsLeft className="h-5 w-5" />
          </PaginationButton>
        )}

        <PaginationButton
          onClick={() => onPageChange(page - 1)}
          disabled={!hasPrevious}
          title="Page précédente"
        >
          <ChevronLeft className="h-5 w-5" />
        </PaginationButton>

        <PaginationButton
          onClick={() => onPageChange(page + 1)}
          disabled={!hasNext}
          title="Page suivante"
        >
          <ChevronRight className="h-5 w-5" />
        </PaginationButton>

        {showFirstLast && (
          <PaginationButton
            onClick={() => onPageChange(totalPages)}
            disabled={!hasNext}
            title="Dernière page"
          >
            <ChevronsRight className="h-5 w-5" />
          </PaginationButton>
        )}
      </div>
    </div>
  );
}

interface PaginationButtonProps {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  title?: string;
}

function PaginationButton({
  children,
  onClick,
  disabled,
  title,
}: PaginationButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-gray-700 dark:text-gray-300 transition-colors"
    >
      {children}
    </button>
  );
}

/**
 * SimplePagination - Simpler version with just Previous/Next buttons
 */
interface SimplePaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  className?: string;
}

export function SimplePagination({
  page,
  totalPages,
  onPageChange,
  className = '',
}: SimplePaginationProps) {
  const hasPrevious = page > 1;
  const hasNext = page < totalPages;

  if (totalPages <= 1) {
    return null;
  }

  return (
    <div className={`flex justify-center items-center space-x-4 ${className}`}>
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={!hasPrevious}
        className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Précédent
      </button>

      <span className="text-sm text-gray-600 dark:text-gray-400">
        Page {page} / {totalPages}
      </span>

      <button
        onClick={() => onPageChange(page + 1)}
        disabled={!hasNext}
        className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Suivant
      </button>
    </div>
  );
}
