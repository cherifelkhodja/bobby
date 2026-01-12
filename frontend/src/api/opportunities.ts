import { apiClient } from './client';
import type { Opportunity, OpportunityListResponse, PaginationParams } from '../types';

export const opportunitiesApi = {
  list: async (params?: PaginationParams): Promise<OpportunityListResponse> => {
    const response = await apiClient.get<OpportunityListResponse>('/opportunities', {
      params,
    });
    return response.data;
  },

  getById: async (id: string): Promise<Opportunity> => {
    const response = await apiClient.get<Opportunity>(`/opportunities/${id}`);
    return response.data;
  },

  sync: async (): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>('/opportunities/sync');
    return response.data;
  },
};
