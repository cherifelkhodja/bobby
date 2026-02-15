import { apiClient } from './client';
import type {
  ContractRequest,
  ContractRequestListResponse,
  ContractRequestStatus,
  Contract,
} from '../types';

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

  get: async (id: string): Promise<ContractRequest> => {
    const response = await apiClient.get<ContractRequest>(
      `/contract-requests/${id}`,
    );
    return response.data;
  },

  validateCommercial: async (
    id: string,
    data: {
      third_party_type: string;
      daily_rate: number;
      start_date: string;
      contact_email: string;
      client_name?: string;
      mission_description?: string;
      mission_location?: string;
    },
  ): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/validate-commercial`,
      data,
    );
    return response.data;
  },

  configure: async (
    id: string,
    data: {
      mission_description?: string;
      mission_location?: string;
      start_date?: string;
      end_date?: string;
      daily_rate?: number;
      estimated_days?: number;
      payment_terms?: string;
      invoice_submission_method?: string;
      invoice_email?: string;
      include_confidentiality?: boolean;
      include_non_compete?: boolean;
      non_compete_duration_months?: number;
      non_compete_geographic_scope?: string;
      include_intellectual_property?: boolean;
      include_liability?: boolean;
      special_conditions?: string;
    },
  ): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/configure`,
      data,
    );
    return response.data;
  },

  complianceOverride: async (
    id: string,
    reason: string,
  ): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/compliance-override`,
      { reason },
    );
    return response.data;
  },

  generateDraft: async (id: string): Promise<Contract> => {
    const response = await apiClient.post<Contract>(
      `/contract-requests/${id}/generate-draft`,
    );
    return response.data;
  },

  sendDraftToPartner: async (id: string): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/send-draft-to-partner`,
    );
    return response.data;
  },

  sendForSignature: async (id: string): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/send-for-signature`,
    );
    return response.data;
  },

  pushToCrm: async (id: string): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/push-to-crm`,
    );
    return response.data;
  },

  listContracts: async (id: string): Promise<Contract[]> => {
    const response = await apiClient.get<Contract[]>(
      `/contract-requests/${id}/contracts`,
    );
    return response.data;
  },
};
