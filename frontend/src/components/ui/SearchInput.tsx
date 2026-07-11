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
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-mut2" />
        <input
          type="text"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="w-full h-9 pl-9 pr-9 rounded-[9px] border border-lin bg-srf2 text-[13px] text-ink placeholder:text-mut2 focus:border-pri focus:outline-none focus:ring-2 focus:ring-pris disabled:opacity-50 disabled:cursor-not-allowed"
        />
        {showClearButton && value && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-mut2 hover:text-ink"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
      {showSubmitButton && (
        <button type="submit" disabled={disabled} className="btn">
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
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-mut2" />
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-[34px] pl-9 pr-3 rounded-[9px] border border-lin bg-srf2 text-[13px] text-ink placeholder:text-mut2 focus:border-pri focus:outline-none focus:ring-2 focus:ring-pris"
      />
    </div>
  );
}
