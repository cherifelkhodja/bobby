import { apiClient } from './client';

export type CharterDocumentType = 'charte' | 'politique' | 'document_unilateral' | 'engagement' | 'autre';

export interface CharterTemplate {
  id: string;
  name: string;
  version: string;
  target: 'partner' | 'consultant';
  document_type: CharterDocumentType;
  requires_acknowledgement: boolean;
  file_name: string;
  ar_file_name: string | null;
  is_active: boolean;
  company_id: string | null;
  created_at: string;
}

export interface CharterUploadParams {
  name: string;
  version: string;
  target: string;
  companyId: string;
  documentType: CharterDocumentType;
  requiresAcknowledgement: boolean;
  file: File;
  arFile?: File;
}

export const chartersApi = {
  list: async (companyId?: string): Promise<CharterTemplate[]> => {
    const response = await apiClient.get<CharterTemplate[]>('/admin/charters', {
      params: companyId ? { company_id: companyId } : undefined,
    });
    return response.data;
  },

  upload: async (params: CharterUploadParams): Promise<CharterTemplate> => {
    const form = new FormData();
    form.append('file', params.file);
    const response = await apiClient.post<CharterTemplate>(
      '/admin/charters',
      form,
      {
        params: {
          name: params.name,
          version: params.version,
          target: params.target,
          company_id: params.companyId,
          document_type: params.documentType,
          requires_acknowledgement: params.requiresAcknowledgement,
        },
      },
    );
    const charter = response.data;

    // Upload AR file in a second request if provided
    if (params.requiresAcknowledgement && params.arFile) {
      const arForm = new FormData();
      arForm.append('file', params.arFile);
      const arResponse = await apiClient.post<CharterTemplate>(
        `/admin/charters/${charter.id}/ar`,
        arForm,
      );
      return arResponse.data;
    }

    return charter;
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

  replaceFile: async (id: string, file: File, version?: string): Promise<CharterTemplate> => {
    const form = new FormData();
    form.append('file', file);
    const response = await apiClient.post<CharterTemplate>(
      `/admin/charters/${id}/replace`,
      form,
      { params: version ? { version } : undefined },
    );
    return response.data;
  },

  getArDownloadUrl: async (id: string): Promise<{ url: string; file_name: string }> => {
    const response = await apiClient.get<{ url: string; file_name: string }>(`/admin/charters/${id}/download-ar`);
    return response.data;
  },
};
