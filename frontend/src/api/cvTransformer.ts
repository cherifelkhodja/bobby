import { apiClient } from './client';
import type { CvTransformationStats } from '../types';

export const cvTransformerApi = {
  /**
   * Get CV transformation statistics (admin only)
   */
  getStats: async (): Promise<CvTransformationStats> => {
    const response = await apiClient.get<CvTransformationStats>('/cv-transformer/stats');
    return response.data;
  },
};
