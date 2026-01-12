import { apiClient } from './client';

export interface BoondStatus {
  connected: boolean;
  configured: boolean;
  api_url: string;
  last_sync: string | null;
  opportunities_count: number;
  error: string | null;
}

export interface SyncResponse {
  success: boolean;
  synced_count: number;
  message: string;
}

export const adminApi = {
  getBoondStatus: async (): Promise<BoondStatus> => {
    const response = await apiClient.get<BoondStatus>('/admin/boond/status');
    return response.data;
  },

  triggerSync: async (): Promise<SyncResponse> => {
    const response = await apiClient.post<SyncResponse>('/admin/boond/sync');
    return response.data;
  },
};
