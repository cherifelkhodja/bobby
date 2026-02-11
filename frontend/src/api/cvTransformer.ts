import { apiClient } from './client';
import type { CvTemplate, CvTransformationStats } from '../types';

export interface TemplatesListResponse {
  templates: CvTemplate[];
}

export const cvTransformerApi = {
  /**
   * Get list of available CV templates
   */
  getTemplates: async (): Promise<TemplatesListResponse> => {
    const response = await apiClient.get<TemplatesListResponse>('/cv-transformer/templates');
    return response.data;
  },

  /**
   * Upload or update a CV template (admin only)
   */
  uploadTemplate: async (
    templateName: string,
    file: File,
    displayName: string,
    description?: string
  ): Promise<CvTemplate> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('display_name', displayName);
    if (description) {
      formData.append('description', description);
    }

    const response = await apiClient.post<CvTemplate>(
      `/cv-transformer/templates/${templateName}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  /**
   * Get CV transformation statistics (admin only)
   */
  getStats: async (): Promise<CvTransformationStats> => {
    const response = await apiClient.get<CvTransformationStats>('/cv-transformer/stats');
    return response.data;
  },
};
