/**
 * Test utilities for rendering components with providers
 */

import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

// Create a new QueryClient for each test
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

interface AllProvidersProps {
  children: React.ReactNode;
}

// eslint-disable-next-line react-refresh/only-export-components
function AllProviders({ children }: AllProvidersProps): JSX.Element {
  const queryClient = createTestQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, { wrapper: AllProviders, ...options });
}

// Re-export everything
// eslint-disable-next-line react-refresh/only-export-components
export * from '@testing-library/react';
export { customRender as render };

// Mock user for testing
export const mockUser = {
  id: 'test-user-id',
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  full_name: 'Test User',
  role: 'user' as const,
  is_verified: true,
  is_active: true,
};

export const mockAdminUser = {
  ...mockUser,
  id: 'admin-user-id',
  email: 'admin@example.com',
  first_name: 'Admin',
  last_name: 'User',
  full_name: 'Admin User',
  role: 'admin' as const,
};

export const mockCommercialUser = {
  ...mockUser,
  id: 'commercial-user-id',
  email: 'commercial@example.com',
  first_name: 'Commercial',
  last_name: 'User',
  full_name: 'Commercial User',
  role: 'commercial' as const,
};

export const mockRHUser = {
  ...mockUser,
  id: 'rh-user-id',
  email: 'rh@example.com',
  first_name: 'RH',
  last_name: 'User',
  full_name: 'RH User',
  role: 'rh' as const,
};

export const mockTokens = {
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
  token_type: 'bearer',
};
