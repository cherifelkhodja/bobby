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

  lookupSiret: async (
    token: string,
    siret: string,
  ): Promise<{
    siren: string | null;
    company_name: string | null;
    legal_form: string | null;
    entity_category: string | null;
    head_office_street: string | null;
    head_office_postal_code: string | null;
    head_office_city: string | null;
    capital: string | null;
    rcs_city: string | null;
  }> => {
    const response = await portalClient.get(`/${token}/siret/${siret}`);
    return response.data;
  },

  submitCompanyInfo: async (
    token: string,
    data: {
      entity_category: 'ei' | 'societe';
      company_name: string;
      legal_form: string;
      capital?: string;
      siret: string;
      head_office_street: string;
      head_office_postal_code: string;
      head_office_city: string;
      rcs_city?: string;
      representative_civility: 'M.' | 'Mme';
      representative_first_name: string;
      representative_last_name: string;
      representative_email: string;
      representative_phone?: string;
      representative_title: string;
      signatory_same_as_representative: boolean;
      signatory_civility?: 'M.' | 'Mme';
      signatory_first_name?: string;
      signatory_last_name?: string;
      signatory_email?: string;
      signatory_phone?: string;
      adv_contact_same_as_representative: boolean;
      adv_contact_civility?: 'M.' | 'Mme';
      adv_contact_first_name?: string;
      adv_contact_last_name?: string;
      adv_contact_email?: string;
      adv_contact_phone?: string;
      billing_contact_same_as_representative: boolean;
      billing_contact_civility?: 'M.' | 'Mme';
      billing_contact_first_name?: string;
      billing_contact_last_name?: string;
      billing_contact_email?: string;
      billing_contact_phone?: string;
    },
  ): Promise<{ message: string }> => {
    const response = await portalClient.post(`/${token}/company-info`, data);
    return response.data;
  },

  updateDocumentAvailability: async (
    token: string,
    documentId: string,
    isUnavailable: boolean,
    reason?: string | null,
  ): Promise<{ message: string }> => {
    const response = await portalClient.patch(`/${token}/documents/${documentId}/availability`, {
      is_unavailable: isUnavailable,
      unavailability_reason: reason ?? null,
    });
    return response.data;
  },

  deleteDocument: async (token: string, documentId: string): Promise<{ message: string }> => {
    const response = await portalClient.delete(`/${token}/documents/${documentId}`);
    return response.data;
  },

  submitDocuments: async (token: string): Promise<{ message: string }> => {
    const response = await portalClient.post(`/${token}/submit-documents`);
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
