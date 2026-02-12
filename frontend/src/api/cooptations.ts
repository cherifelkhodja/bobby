import { apiClient } from './client';
import type {
  Cooptation,
  CooptationListResponse,
  CooptationStats,
  CreateCooptationRequest,
  PaginationParams,
} from '../types';

export const cooptationsApi = {
  create: async (data: CreateCooptationRequest): Promise<Cooptation> => {
    const response = await apiClient.post<Cooptation>('/cooptations', data);
    return response.data;
  },

  list: async (
    params?: PaginationParams & { status?: string }
  ): Promise<CooptationListResponse> => {
    const response = await apiClient.get<CooptationListResponse>('/cooptations', {
      params,
    });
    return response.data;
  },

  listByOpportunity: async (
    opportunityId: string,
    params?: PaginationParams
  ): Promise<CooptationListResponse> => {
    const response = await apiClient.get<CooptationListResponse>('/cooptations', {
      params: { ...params, opportunity_id: opportunityId },
    });
    return response.data;
  },

  listMine: async (params?: PaginationParams): Promise<CooptationListResponse> => {
    const response = await apiClient.get<CooptationListResponse>('/cooptations/me', {
      params,
    });
    return response.data;
  },

  getById: async (id: string): Promise<Cooptation> => {
    const response = await apiClient.get<Cooptation>(`/cooptations/${id}`);
    return response.data;
  },

  updateStatus: async (
    id: string,
    status: string,
    comment?: string
  ): Promise<Cooptation> => {
    const response = await apiClient.patch<Cooptation>(`/cooptations/${id}/status`, {
      status,
      comment,
    });
    return response.data;
  },

  getMyStats: async (): Promise<CooptationStats> => {
    const response = await apiClient.get<CooptationStats>('/cooptations/me/stats');
    return response.data;
  },

  getAllStats: async (): Promise<CooptationStats> => {
    const response = await apiClient.get<CooptationStats>('/cooptations/stats');
    return response.data;
  },
};
