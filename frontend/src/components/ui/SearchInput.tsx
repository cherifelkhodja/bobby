/**
 * SearchInput - Reusable search input component
 *
 * Provides a styled search input with optional submit button.
 */

import { Search, X } from 'lucide-react';
import { useCallback } from 'react';

interface SearchInputProps {
  /** Current search value */
  value: string;
  /** Callback when value changes */
  onChange: (value: string) => void;
  /** Callback when form is submitted */
  onSubmit?: () => void;
  /** Placeholder text */
  placeholder?: string;
  /** Show submit button (default: false) */
  showSubmitButton?: boolean;
  /** Submit button text */
  submitText?: string;
  /** Show clear button when there's text (default: true) */
  showClearButton?: boolean;
  /** Disabled state */
  disabled?: boolean;
  /** Custom class name */
  className?: string;
}

export function SearchInput({
  value,
  onChange,
  onSubmit,
  placeholder = 'Rechercher...',
  showSubmitButton = false,
  submitText = 'Rechercher',
  showClearButton = true,
  disabled = false,
  className = '',
}: SearchInputProps) {
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      onSubmit?.();
    },
    [onSubmit]
  );

  const handleClear = useCallback(() => {
    onChange('');
    onSubmit?.();
  }, [onChange, onSubmit]);

  return (
    <form onSubmit={handleSubmit} className={`flex gap-2 ${className}`}>
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
        <input
          type="text"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="w-full pl-10 pr-10 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
        />
        {showClearButton && value && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
      {showSubmitButton && (
        <button
          type="submit"
          disabled={disabled}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitText}
        </button>
      )}
    </form>
  );
}

/**
 * InlineSearchInput - Simpler inline version without form
 */
interface InlineSearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export function InlineSearchInput({
  value,
  onChange,
  placeholder = 'Rechercher...',
  className = '',
}: InlineSearchInputProps) {
  return (
    <div className={`relative ${className}`}>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full pl-9 pr-4 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
      />
    </div>
  );
}
