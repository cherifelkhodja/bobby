import { apiClient } from './client';

export interface CvGeneratorParseResponse {
  success: boolean;
  data: Record<string, unknown>;
  model_used: string;
}

export const cvGeneratorApi = {
  /**
   * Upload a CV file and get parsed section-based JSON.
   * The JSON is designed for frontend DOCX generation.
   */
  parseCv: async (file: File): Promise<CvGeneratorParseResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<CvGeneratorParseResponse>(
      '/cv-generator/parse',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
    return response.data;
  },
};
