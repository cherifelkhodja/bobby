import { apiClient } from './client';

export interface CharterTemplate {
  id: string;
  name: string;
  version: string;
  target: 'partner' | 'consultant';
  file_name: string;
  is_active: boolean;
  created_at: string;
}

export const chartersApi = {
  list: async (): Promise<CharterTemplate[]> => {
    const response = await apiClient.get<CharterTemplate[]>('/admin/charters');
    return response.data;
  },

  upload: async (name: string, version: string, target: string, file: File): Promise<CharterTemplate> => {
    const form = new FormData();
    form.append('file', file);
    const response = await apiClient.post<CharterTemplate>(
      '/admin/charters',
      form,
      { params: { name, version, target } },
    );
    return response.data;
  },

  update: async (id: string, data: { is_active?: boolean; name?: string; version?: string }): Promise<CharterTemplate> => {
    const response = await apiClient.patch<CharterTemplate>(`/admin/charters/${id}`, null, { params: data });
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/admin/charters/${id}`);
  },

  getDownloadUrl: async (id: string): Promise<{ url: string; file_name: string }> => {
    const response = await apiClient.get<{ url: string; file_name: string }>(`/admin/charters/${id}/download`);
    return response.data;
  },
};
