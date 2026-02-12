import { apiClient } from './client';
import type {
  Cooptation,
  CooptationListResponse,
  CooptationStats,
  CvDownloadUrlResponse,
  PaginationParams,
} from '../types';

export interface CreateCooptationData {
  opportunity_id: string;
  candidate_first_name: string;
  candidate_last_name: string;
  candidate_email: string;
  candidate_civility: 'M' | 'Mme';
  candidate_phone?: string;
  candidate_daily_rate?: number;
  candidate_note?: string;
  cv: File;
}

export const cooptationsApi = {
  create: async (data: CreateCooptationData): Promise<Cooptation> => {
    const formData = new FormData();
    formData.append('opportunity_id', data.opportunity_id);
    formData.append('candidate_first_name', data.candidate_first_name);
    formData.append('candidate_last_name', data.candidate_last_name);
    formData.append('candidate_email', data.candidate_email);
    formData.append('candidate_civility', data.candidate_civility);
    if (data.candidate_phone) {
      formData.append('candidate_phone', data.candidate_phone);
    }
    if (data.candidate_daily_rate !== undefined && data.candidate_daily_rate !== null) {
      formData.append('candidate_daily_rate', String(data.candidate_daily_rate));
    }
    if (data.candidate_note) {
      formData.append('candidate_note', data.candidate_note);
    }
    formData.append('cv', data.cv);

    const response = await apiClient.post<Cooptation>('/cooptations', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
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

  getCvDownloadUrl: async (cooptationId: string): Promise<CvDownloadUrlResponse> => {
    const response = await apiClient.get<CvDownloadUrlResponse>(
      `/cooptations/${cooptationId}/cv`
    );
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
