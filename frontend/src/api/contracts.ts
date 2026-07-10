import { apiClient } from './client';

export interface SignaturePreviewItem {
  charter_template_id: string;
  label: string;
  document_kind: 'charter_ar' | 'charter_engagement';
  signer_role: 'partner' | 'consultant';
}

export interface SignatureChecklistItem {
  id: string;
  label: string;
  document_kind: 'contract' | 'charter_ar' | 'charter_engagement';
  signer_role: 'partner' | 'consultant';
  charter_template_id: string | null;
  uploaded: boolean;
  file_name: string | null;
}

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
      contact_email: string;
      company_id?: string;
      consultant_civility?: string;
      consultant_first_name?: string;
      consultant_last_name?: string;
      consultant_email?: string;
      consultant_phone?: string;
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
      company_id?: string | null;
      mission_description?: string;
      start_date?: string;
      end_date?: string;
      daily_rate?: number;
      estimated_days?: number;
      payment_terms?: string;
      invoice_submission_method?: string;
      invoice_email?: string;
      tacit_renewal_months?: number;
      excluded_optional_article_keys?: string[];
      special_conditions?: string;
    },
  ): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/configure`,
      data,
    );
    return response.data;
  },

  saveArticleOverrides: async (
    id: string,
    data: {
      article_overrides?: Record<string, string>;
      annex_overrides?: Record<string, string>;
      deleted_article_keys?: string[];
      deleted_annex_keys?: string[];
      custom_articles?: CustomArticleItem[];
      custom_annexes?: CustomAnnexItem[];
      article_order?: string[];
      annex_order?: string[];
    },
  ): Promise<ContractRequest> => {
    const response = await apiClient.patch<ContractRequest>(
      `/contract-requests/${id}/article-overrides`,
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

  deleteContract: async (crId: string, contractId: string): Promise<{ status: string; message: string }> => {
    const response = await apiClient.delete(`/contract-requests/${crId}/contracts/${contractId}`);
    return response.data;
  },

  boondUploadSignedDocs: async (id: string): Promise<{ status: string; message: string }> => {
    const response = await apiClient.post(`/contract-requests/${id}/boond/upload-signed-documents`);
    return response.data;
  },

  resendDraftEmail: async (id: string): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/resend-draft-email`,
    );
    return response.data;
  },

  getSignaturePreview: async (id: string): Promise<SignaturePreviewItem[]> => {
    const response = await apiClient.get<SignaturePreviewItem[]>(
      `/contract-requests/${id}/signature-preview`,
    );
    return response.data;
  },

  sendForSignature: async (id: string, excludedCharterIds?: string[]): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/send-for-signature`,
      excludedCharterIds ? { excluded_charter_ids: excludedCharterIds } : undefined,
    );
    return response.data;
  },

  getSignatureChecklist: async (id: string): Promise<SignatureChecklistItem[]> => {
    const response = await apiClient.get<SignatureChecklistItem[]>(
      `/contract-requests/${id}/signature-checklist`,
    );
    return response.data;
  },

  uploadSignatureDocument: async (crId: string, itemId: string, file: File): Promise<SignatureChecklistItem> => {
    const form = new FormData();
    form.append('file', file);
    const response = await apiClient.post<SignatureChecklistItem>(
      `/contract-requests/${crId}/signature-checklist/${itemId}/upload`,
      form,
    );
    return response.data;
  },

  markAsSigned: async (id: string): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/mark-as-signed`,
    );
    return response.data;
  },

  pushToCrm: async (id: string): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/push-to-crm`,
    );
    return response.data;
  },

  retryBoondSync: async (id: string): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/retry-boond-sync`,
    );
    return response.data;
  },

  boondConvertCandidate: async (id: string): Promise<{
    ok: boolean;
    boond_candidate_id: number;
    new_resource_id: number;
    converted: boolean;
    already_resource: boolean;
  }> => {
    const response = await apiClient.post(`/contract-requests/${id}/boond/convert-candidate`);
    return response.data;
  },

  boondCreateContract: async (id: string, resourceId?: number): Promise<{
    ok: boolean;
    contract_created: boolean;
    contract_type_of: number | null;
    provider_linked: boolean;
    reason?: string;
  }> => {
    const params = resourceId ? { resource_id: resourceId } : undefined;
    const response = await apiClient.post(`/contract-requests/${id}/boond/create-contract`, null, { params });
    return response.data;
  },

  boondCreateCompany: async (id: string): Promise<{
    ok: boolean;
    created_company: boolean;
    boond_provider_id: number;
    contacts_created: { label: string; boond_contact_id: number }[];
  }> => {
    const response = await apiClient.post(`/contract-requests/${id}/boond/create-company`);
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

  purge: async (id: string): Promise<{ status: string; message: string }> => {
    const response = await apiClient.post(`/contract-requests/${id}/purge`);
    return response.data;
  },

  rollbackStatus: async (id: string): Promise<ContractRequest> => {
    const response = await apiClient.post<ContractRequest>(
      `/contract-requests/${id}/rollback`,
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

  getContractDownloadUrl: async (contractRequestId: string, contractId: string, which: 'draft' | 'signed' = 'draft'): Promise<string> => {
    const response = await apiClient.get<{ url: string }>(
      `/contract-requests/${contractRequestId}/contracts/${contractId}/download`,
      { params: { which } },
    );
    return response.data.url;
  },

};

// ── Contract companies ──────────────────────────────────────────────────────

export interface ContractCompany {
  id: string;
  name: string;
  code: string;
  legal_form: string;
  capital: string;
  head_office: string;
  rcs_city: string;
  rcs_number: string;
  representative_is_entity: boolean;
  representative_name: string;
  representative_quality: string;
  representative_sub_name?: string | null;
  representative_sub_quality?: string | null;
  signatory_name: string;
  invoices_company_mail?: string | null;
  email_from?: string | null;
  color_code: string;
  boond_agency_id?: number | null;
  has_logo: boolean;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ContractCompanyRequest = Omit<ContractCompany, 'id' | 'created_at' | 'updated_at' | 'has_logo'>;

// ── Contract Consultants ──────────────────────────────────────────────────

export interface ContractConsultant {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  charter_status: 'pending' | 'sent' | 'signed';
  created_at: string;
}

export const contractConsultantsApi = {
  list: async (contractRequestId: string): Promise<ContractConsultant[]> => {
    const response = await apiClient.get<ContractConsultant[]>(
      `/contract-requests/${contractRequestId}/consultants`,
    );
    return response.data;
  },

  add: async (contractRequestId: string, data: {
    first_name: string;
    last_name: string;
    email: string;
    phone?: string;
    boond_candidate_id?: number;
  }): Promise<ContractConsultant> => {
    const response = await apiClient.post<ContractConsultant>(
      `/contract-requests/${contractRequestId}/consultants`,
      data,
    );
    return response.data;
  },

  remove: async (contractRequestId: string, consultantId: string): Promise<void> => {
    await apiClient.delete(`/contract-requests/${contractRequestId}/consultants/${consultantId}`);
  },

  sendCharters: async (contractRequestId: string, consultantId: string): Promise<{
    status: string;
    charter_status: string;
    documents: Record<string, string>;
  }> => {
    const response = await apiClient.post(
      `/contract-requests/${contractRequestId}/consultants/${consultantId}/send-charters`,
    );
    return response.data;
  },
};

export const contractCompaniesApi = {
  list: async (): Promise<ContractCompany[]> => {
    const response = await apiClient.get<ContractCompany[]>('/admin/contract-companies');
    return response.data;
  },
  listActive: async (): Promise<ContractCompany[]> => {
    const response = await apiClient.get<ContractCompany[]>('/contract-requests/companies');
    return response.data;
  },

  create: async (data: ContractCompanyRequest): Promise<ContractCompany> => {
    const response = await apiClient.post<ContractCompany>('/admin/contract-companies', data);
    return response.data;
  },

  update: async (id: string, data: ContractCompanyRequest): Promise<ContractCompany> => {
    const response = await apiClient.patch<ContractCompany>(`/admin/contract-companies/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/admin/contract-companies/${id}`);
  },

  uploadLogo: async (id: string, file: File): Promise<{ logo_s3_key: string }> => {
    const form = new FormData();
    form.append('file', file);
    const response = await apiClient.post<{ logo_s3_key: string }>(
      `/admin/contract-companies/${id}/logo`,
      form,
    );
    return response.data;
  },

  getLogoUrl: async (id: string): Promise<string> => {
    const response = await apiClient.get<{ url: string }>(
      `/admin/contract-companies/${id}/logo`,
    );
    return response.data.url;
  },

  deleteLogo: async (id: string): Promise<void> => {
    await apiClient.delete(`/admin/contract-companies/${id}/logo`);
  },
};

export interface CustomArticleItem {
  key: string;
  title: string;
  content: string;
}

export interface CustomAnnexItem {
  key: string;
  title: string;
  content: string;
}

export interface ArticleTemplate {
  article_key: string;
  article_number: number;
  title: string;
  content: string;
  is_editable: boolean;
  is_active: boolean;
  is_optional: boolean;
}

export interface AnnexTemplate {
  annexe_key: string;
  annexe_number: number;
  title: string;
  content: string;
  is_conditional: boolean;
  condition_field: string | null;
  is_active: boolean;
}

export const contractAnnexesApi = {
  create: async (data: {
    annexe_key: string;
    title: string;
    content?: string;
    is_active?: boolean;
  }): Promise<AnnexTemplate> => {
    const response = await apiClient.post<AnnexTemplate>('/admin/contract-annexes', data);
    return response.data;
  },

  list: async (): Promise<AnnexTemplate[]> => {
    const response = await apiClient.get<AnnexTemplate[]>('/admin/contract-annexes');
    return response.data;
  },

  update: async (
    annexeKey: string,
    data: Partial<Pick<AnnexTemplate, 'content' | 'title' | 'is_active'>>,
  ): Promise<AnnexTemplate> => {
    const response = await apiClient.patch<AnnexTemplate>(
      `/admin/contract-annexes/${annexeKey}`,
      data,
    );
    return response.data;
  },

  reorder: async (orderedKeys: string[]): Promise<void> => {
    await apiClient.post('/admin/contract-annexes/reorder', { ordered_keys: orderedKeys });
  },

  delete: async (annexeKey: string): Promise<void> => {
    await apiClient.delete(`/admin/contract-annexes/${annexeKey}`);
  },
};

export const contractArticlesApi = {
  create: async (data: {
    article_key: string;
    title: string;
    content?: string;
    is_editable?: boolean;
    is_active?: boolean;
  }): Promise<ArticleTemplate> => {
    const response = await apiClient.post<ArticleTemplate>('/admin/contract-articles', data);
    return response.data;
  },

  list: async (): Promise<ArticleTemplate[]> => {
    const response = await apiClient.get<ArticleTemplate[]>('/admin/contract-articles');
    return response.data;
  },

  update: async (
    articleKey: string,
    data: Partial<Pick<ArticleTemplate, 'content' | 'title' | 'is_editable' | 'is_active' | 'is_optional'>>,
  ): Promise<ArticleTemplate> => {
    const response = await apiClient.patch<ArticleTemplate>(
      `/admin/contract-articles/${articleKey}`,
      data,
    );
    return response.data;
  },

  reorder: async (orderedKeys: string[]): Promise<void> => {
    await apiClient.post('/admin/contract-articles/reorder', { ordered_keys: orderedKeys });
  },

  delete: async (articleKey: string): Promise<void> => {
    await apiClient.delete(`/admin/contract-articles/${articleKey}`);
  },
};
