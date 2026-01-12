import { apiClient } from './client';
import type { User, UpdateProfileRequest, ChangePasswordRequest } from '../types';

export const usersApi = {
  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>('/users/me');
    return response.data;
  },

  updateMe: async (data: UpdateProfileRequest): Promise<User> => {
    const response = await apiClient.patch<User>('/users/me', data);
    return response.data;
  },

  changePassword: async (data: ChangePasswordRequest): Promise<void> => {
    await apiClient.post('/users/me/password', data);
  },
};
