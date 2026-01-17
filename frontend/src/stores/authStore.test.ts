/**
 * Tests for authStore
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { act } from '@testing-library/react';
import { useAuthStore } from './authStore';

// Mock user and tokens
const mockUser = {
  id: 'test-user-id',
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  full_name: 'Test User',
  role: 'user' as const,
  is_verified: true,
  is_active: true,
  boond_resource_id: null,
  manager_boond_id: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const mockTokens = {
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
  token_type: 'bearer',
};

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    const { logout } = useAuthStore.getState();
    logout();
    // Clear localStorage
    localStorage.clear();
  });

  describe('initial state', () => {
    it('should have null user initially', () => {
      const state = useAuthStore.getState();

      expect(state.user).toBeNull();
    });

    it('should have null tokens initially', () => {
      const state = useAuthStore.getState();

      expect(state.tokens).toBeNull();
    });

    it('should not be authenticated initially', () => {
      const state = useAuthStore.getState();

      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe('setAuth', () => {
    it('should set user and tokens', () => {
      const { setAuth } = useAuthStore.getState();

      act(() => {
        setAuth(mockUser, mockTokens);
      });

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.tokens).toEqual(mockTokens);
    });

    it('should mark as authenticated', () => {
      const { setAuth } = useAuthStore.getState();

      act(() => {
        setAuth(mockUser, mockTokens);
      });

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
    });
  });

  describe('logout', () => {
    it('should clear user and tokens', () => {
      const { setAuth, logout } = useAuthStore.getState();

      // First, set auth
      act(() => {
        setAuth(mockUser, mockTokens);
      });

      // Then, logout
      act(() => {
        logout();
      });

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.tokens).toBeNull();
    });

    it('should mark as not authenticated', () => {
      const { setAuth, logout } = useAuthStore.getState();

      act(() => {
        setAuth(mockUser, mockTokens);
      });

      act(() => {
        logout();
      });

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe('updateUser', () => {
    it('should update user fields', () => {
      const { setAuth, updateUser } = useAuthStore.getState();

      act(() => {
        setAuth(mockUser, mockTokens);
      });

      act(() => {
        updateUser({ first_name: 'Updated', last_name: 'Name' });
      });

      const state = useAuthStore.getState();
      expect(state.user?.first_name).toBe('Updated');
      expect(state.user?.last_name).toBe('Name');
      // Other fields should remain unchanged
      expect(state.user?.email).toBe(mockUser.email);
    });

    it('should not update if no user is set', () => {
      const { updateUser } = useAuthStore.getState();

      act(() => {
        updateUser({ first_name: 'Updated' });
      });

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
    });

    it('should preserve unspecified fields', () => {
      const { setAuth, updateUser } = useAuthStore.getState();

      act(() => {
        setAuth(mockUser, mockTokens);
      });

      act(() => {
        updateUser({ first_name: 'NewName' });
      });

      const state = useAuthStore.getState();
      expect(state.user?.first_name).toBe('NewName');
      expect(state.user?.email).toBe(mockUser.email);
      expect(state.user?.role).toBe(mockUser.role);
      expect(state.user?.is_verified).toBe(mockUser.is_verified);
    });
  });

  describe('persistence', () => {
    it('should persist state to localStorage', () => {
      const { setAuth } = useAuthStore.getState();

      act(() => {
        setAuth(mockUser, mockTokens);
      });

      // Check localStorage
      const stored = localStorage.getItem('auth-storage');
      expect(stored).not.toBeNull();

      const parsed = JSON.parse(stored!);
      expect(parsed.state.user).toEqual(mockUser);
      expect(parsed.state.isAuthenticated).toBe(true);
    });
  });
});
