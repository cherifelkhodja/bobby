import { apiClient } from './client';
import type { ContractRequestListResponse, ContractRequestStatus } from '../types';

export const contractsApi = {
  list: async (params?: {
    skip?: number;
    limit?: number;
    status_filter?: ContractRequestStatus;
  }): Promise<ContractRequestListResponse> => {
    const response = await apiClient.get<ContractRequestListResponse>(
      '/contract-requests',
      { params },
    );
    return response.data;
  },
};
