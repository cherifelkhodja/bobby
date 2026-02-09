/**
 * ThemeProvider - Initializes and listens for theme changes on app load.
 *
 * Delegates all theme logic to useTheme hook (single source of truth).
 */

import { useTheme } from '../hooks/useTheme';

interface ThemeProviderProps {
  children: React.ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  // useTheme applies the theme class on mount and listens for system changes
  useTheme();

  return <>{children}</>;
}
