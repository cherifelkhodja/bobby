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
      end_date?: string;
      contact_email: string;
      client_name?: string;
      mission_title?: string;
      mission_description?: string;
      consultant_civility?: string;
      consultant_first_name?: string;
      consultant_last_name?: string;
      mission_site_name?: string;
      mission_address?: string;
      mission_postal_code?: string;
      mission_city?: string;
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
      start_date?: string;
      end_date?: string;
      daily_rate?: number;
      estimated_days?: number;
      payment_terms?: string;
      invoice_submission_method?: string;
      invoice_email?: string;
      tacit_renewal_months?: number;
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

  syncFromBoond: async (id: string): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/sync-from-boond`,
    );
    return response.data;
  },

  cancel: async (id: string): Promise<ContractRequest> => {
    const response = await apiClient.delete<ContractRequest>(
      `/contract-requests/${id}`,
    );
    return response.data;
  },

  resendCollectionEmail: async (id: string): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/resend-collection-email`,
    );
    return response.data;
  },

  startComplianceReview: async (id: string): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/start-compliance-review`,
    );
    return response.data;
  },

  blockCompliance: async (id: string, reason: string): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/block-compliance`,
      { reason },
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

export interface ArticleTemplate {
  article_key: string;
  article_number: number;
  title: string;
  content: string;
  is_editable: boolean;
  is_active: boolean;
}

export const contractArticlesApi = {
  list: async (): Promise<ArticleTemplate[]> => {
    const response = await apiClient.get<ArticleTemplate[]>('/admin/contract-articles');
    return response.data;
  },

  update: async (
    articleKey: string,
    data: Partial<Pick<ArticleTemplate, 'content' | 'title' | 'is_editable' | 'is_active'>>,
  ): Promise<ArticleTemplate> => {
    const response = await apiClient.patch<ArticleTemplate>(
      `/admin/contract-articles/${articleKey}`,
      data,
    );
    return response.data;
  },
};
