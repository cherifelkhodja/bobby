import { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    const baseClasses =
      'inline-flex items-center justify-center whitespace-nowrap rounded-[9px] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-pri focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-45';

    const variantClasses = {
      primary: 'bg-pri text-white font-semibold hover:brightness-110',
      secondary: 'bg-sur text-ink font-medium border border-lin hover:bg-srf2',
      outline:
        'bg-transparent text-prit font-semibold border border-pri hover:bg-pris',
      danger: 'bg-redt text-white font-semibold hover:brightness-110',
      ghost: 'text-mut font-medium hover:bg-srf2 hover:text-ink',
    };

    const sizeClasses = {
      sm: 'h-[30px] px-3 gap-1.5 text-xs',
      md: 'h-9 px-3.5 gap-2 text-[13px]',
      lg: 'h-11 px-5 gap-2 text-sm',
    };

    return (
      <button
        ref={ref}
        className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
        ) : leftIcon ? (
          <span className="inline-flex shrink-0">{leftIcon}</span>
        ) : null}
        {children}
        {rightIcon && !isLoading && <span className="inline-flex shrink-0">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';
