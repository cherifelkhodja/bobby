import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'sonner';

import App from './App';
import { ThemeProvider } from './components/ThemeProvider';
import { useTheme } from './hooks/useTheme';
import './styles/index.css';

// eslint-disable-next-line react-refresh/only-export-components
function ThemedToaster() {
  const { resolvedTheme } = useTheme();
  return (
    <Toaster
      position="top-right"
      richColors
      theme={resolvedTheme}
      toastOptions={{
        style: { borderRadius: '12px', fontFamily: "'Inter', system-ui, sans-serif" },
      }}
    />
  );
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: (failureCount, error) => {
        // Don't retry on 401 (auth errors) or 403 (forbidden)
        if (error && typeof error === 'object' && 'response' in error) {
          const status = (error as { response?: { status?: number } }).response?.status;
          if (status === 401 || status === 403) {
            return false;
          }
        }
        return failureCount < 1;
      },
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
          <ThemedToaster />
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  </React.StrictMode>
);
