import axios from 'axios';
import type { PortalInfo, PortalDocument } from '../types';

const API_URL = import.meta.env.VITE_API_URL || '';

const portalClient = axios.create({
  baseURL: `${API_URL}/api/v1/portal`,
  headers: { 'Content-Type': 'application/json' },
});

export const portalApi = {
  verifyToken: async (token: string): Promise<PortalInfo> => {
    const response = await portalClient.get<PortalInfo>(`/${token}`);
    return response.data;
  },

  getDocuments: async (
    token: string,
  ): Promise<{
    third_party_id: string;
    company_name: string;
    documents: PortalDocument[];
  }> => {
    const response = await portalClient.get(`/${token}/documents`);
    return response.data;
  },

  uploadDocument: async (
    token: string,
    documentId: string,
    file: File,
  ): Promise<{ document_id: string; status: string; message: string }> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await portalClient.post(
      `/${token}/documents/${documentId}/upload`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
    return response.data;
  },

  getContractDraft: async (
    token: string,
  ): Promise<{ contract_request_id: string; status: string; download_url: string | null }> => {
    const response = await portalClient.get(`/${token}/contract-draft`);
    return response.data;
  },

  submitCompanyInfo: async (
    token: string,
    data: {
      entity_category: 'ei' | 'societe';
      company_name: string;
      legal_form: string;
      capital?: string;
      siren: string;
      rcs_city: string;
      rcs_number: string;
      head_office_address: string;
      representative_name: string;
      representative_title: string;
    },
  ): Promise<{ message: string }> => {
    const response = await portalClient.post(`/${token}/company-info`, data);
    return response.data;
  },

  submitContractReview: async (
    token: string,
    decision: 'approved' | 'changes_requested',
    comments?: string,
  ): Promise<{ contract_request_id: string; decision: string; message: string }> => {
    const response = await portalClient.post(`/${token}/contract-review`, {
      decision,
      comments,
    });
    return response.data;
  },
};
