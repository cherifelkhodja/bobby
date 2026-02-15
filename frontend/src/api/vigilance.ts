import { apiClient } from './client';
import type {
  ThirdPartyListResponse,
  ThirdPartyWithDocuments,
  ComplianceDashboard,
  VigilanceDocument,
  ComplianceStatus,
} from '../types';

export const vigilanceApi = {
  listThirdParties: async (params?: {
    skip?: number;
    limit?: number;
    compliance_status?: ComplianceStatus;
    search?: string;
    third_party_type?: string;
  }): Promise<ThirdPartyListResponse> => {
    const response = await apiClient.get<ThirdPartyListResponse>(
      '/vigilance/third-parties',
      { params },
    );
    return response.data;
  },

  getThirdPartyDocuments: async (
    thirdPartyId: string,
  ): Promise<ThirdPartyWithDocuments> => {
    const response = await apiClient.get<ThirdPartyWithDocuments>(
      `/vigilance/third-parties/${thirdPartyId}/documents`,
    );
    return response.data;
  },

  requestDocuments: async (
    thirdPartyId: string,
  ): Promise<VigilanceDocument[]> => {
    const response = await apiClient.post<VigilanceDocument[]>(
      `/vigilance/third-parties/${thirdPartyId}/request-documents`,
    );
    return response.data;
  },

  validateDocument: async (documentId: string): Promise<VigilanceDocument> => {
    const response = await apiClient.post<VigilanceDocument>(
      `/vigilance/documents/${documentId}/validate`,
    );
    return response.data;
  },

  rejectDocument: async (
    documentId: string,
    reason: string,
  ): Promise<VigilanceDocument> => {
    const response = await apiClient.post<VigilanceDocument>(
      `/vigilance/documents/${documentId}/reject`,
      { reason },
    );
    return response.data;
  },

  getDashboard: async (): Promise<ComplianceDashboard> => {
    const response = await apiClient.get<ComplianceDashboard>(
      '/compliance/dashboard',
    );
    return response.data;
  },
};
