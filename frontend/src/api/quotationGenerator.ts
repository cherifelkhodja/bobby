/**
 * API client for quotation generator endpoints.
 */

import { apiClient } from './client';

// Types

export interface ContactInfo {
  id: string;
  name: string;
}

export interface QuotationPreviewItem {
  row_index: number;
  // Resource info
  resource_name: string;
  resource_trigramme: string;
  resource_id: string;
  // BoondManager relationships
  opportunity_id: string;
  company_name: string;
  company_id: string;
  company_detail_id: string;
  contact_name: string;
  contact_id: string;
  available_contacts: ContactInfo[];
  // Period
  period: {
    start: string;
    end: string;
  };
  period_name: string; // Human-readable period name (e.g., "Janvier 2026")
  // Pricing
  tjm: number;
  quantity: number;
  total_ht: number;
  total_ttc: number;
  // Thales C22 fields
  c22_domain: string;
  c22_activity: string;
  complexity: string;
  max_price: number; // GFA
  // Other Thales fields
  sow_reference: string;
  object_of_need: string;
  need_title: string;
  comments: string | null;
  start_project: string;
  // Additional Thales fields
  eacq_number: string;
  is_renewal: boolean;
  in_situ_ratio: string;
  subcontracting: boolean;
  tier2_supplier: string;
  tier3_supplier: string;
  // Validation
  is_valid: boolean;
  validation_errors: string[];
}

export interface PreviewBatchResponse {
  batch_id: string;
  total_quotations: number;
  valid_count: number;
  invalid_count: number;
  quotations: QuotationPreviewItem[];
  validation_errors: Record<string, string[]>;
}

export interface StartGenerationRequest {
  batch_id: string;
  template_name?: string;
}

export interface StartGenerationResponse {
  batch_id: string;
  status: string;
  total_quotations: number;
}

export interface BatchProgressResponse {
  batch_id: string;
  status: string;
  total: number;
  completed: number;
  failed: number;
  pending: number;
  progress_percentage: number;
  is_complete: boolean;
  has_errors: boolean;
  merged_pdf_path: string | null;  // Merged PDF with all quotations
  zip_file_path: string | null;     // ZIP archive with individual PDFs
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface QuotationStatusItem {
  row_index: number;
  resource_name: string;
  resource_trigramme: string;
  opportunity_id: string;
  company_name: string;
  status: string;
  boond_quotation_id: string | null;
  boond_reference: string | null;
  pdf_path: string | null;  // Path to individual PDF for download
  error_message: string | null;
  is_valid: boolean;
  validation_errors: string[];
}

export interface BatchDetailsResponse extends BatchProgressResponse {
  user_id: string;
  created_at: string;
  quotations: QuotationStatusItem[];
}

export interface TemplateInfo {
  name: string;
  display_name: string;
  description: string | null;
  updated_at: string | null;
}

export interface TemplateListResponse {
  templates: TemplateInfo[];
}

export interface UploadTemplateResponse {
  name: string;
  is_valid: boolean;
  variables_found: string[];
  missing_variables: string[];
  warnings: string[];
}

export interface BatchSummary {
  batch_id: string;
  status: string;
  total: number;
  completed: number;
  failed: number;
  progress_percentage: number;
  is_complete: boolean;
  created_at: string | null;
}

// API functions

export const quotationGeneratorApi = {
  /**
   * Upload CSV and preview quotations.
   */
  previewBatch: async (file: File): Promise<PreviewBatchResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<PreviewBatchResponse>(
      '/quotation-generator/preview',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  /**
   * Start batch generation.
   */
  startGeneration: async (
    batchId: string,
    templateName: string = 'thales_pstf'
  ): Promise<StartGenerationResponse> => {
    const response = await apiClient.post<StartGenerationResponse>(
      '/quotation-generator/generate',
      {
        batch_id: batchId,
        template_name: templateName,
      }
    );
    return response.data;
  },

  /**
   * Get batch progress.
   */
  getBatchProgress: async (batchId: string): Promise<BatchProgressResponse> => {
    const response = await apiClient.get<BatchProgressResponse>(
      `/quotation-generator/batches/${batchId}/progress`
    );
    return response.data;
  },

  /**
   * Get batch details with quotation statuses.
   */
  getBatchDetails: async (batchId: string): Promise<BatchDetailsResponse> => {
    const response = await apiClient.get<BatchDetailsResponse>(
      `/quotation-generator/batches/${batchId}`
    );
    return response.data;
  },

  /**
   * List user's recent batches.
   */
  listBatches: async (limit: number = 10): Promise<BatchSummary[]> => {
    const response = await apiClient.get<{ batches: BatchSummary[] }>(
      '/quotation-generator/batches',
      { params: { limit } }
    );
    return response.data.batches;
  },

  /**
   * Download merged PDF with all quotations.
   */
  downloadMergedPdf: async (batchId: string): Promise<Blob> => {
    const response = await apiClient.get(
      `/quotation-generator/batches/${batchId}/download`,
      {
        responseType: 'blob',
      }
    );
    return response.data;
  },

  /**
   * Download merged PDF and trigger browser download.
   */
  downloadMergedPdfAsFile: async (batchId: string, filename?: string): Promise<void> => {
    const blob = await quotationGeneratorApi.downloadMergedPdf(batchId);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || `devis_thales_${batchId}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Download ZIP archive with all individual PDFs.
   */
  downloadZip: async (batchId: string): Promise<Blob> => {
    const response = await apiClient.get(
      `/quotation-generator/batches/${batchId}/download/zip`,
      {
        responseType: 'blob',
      }
    );
    return response.data;
  },

  /**
   * Download ZIP and trigger browser download.
   */
  downloadZipAsFile: async (batchId: string, filename?: string): Promise<void> => {
    const blob = await quotationGeneratorApi.downloadZip(batchId);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || `devis_thales_${batchId}.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Download individual quotation PDF.
   */
  downloadIndividualPdf: async (batchId: string, rowIndex: number): Promise<Blob> => {
    const response = await apiClient.get(
      `/quotation-generator/batches/${batchId}/quotations/${rowIndex}/download`,
      {
        responseType: 'blob',
      }
    );
    return response.data;
  },

  /**
   * Download individual quotation PDF and trigger browser download.
   */
  downloadIndividualPdfAsFile: async (
    batchId: string,
    rowIndex: number,
    filename?: string
  ): Promise<void> => {
    const blob = await quotationGeneratorApi.downloadIndividualPdf(batchId, rowIndex);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || `devis_${rowIndex}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  // Legacy aliases for backwards compatibility
  downloadBatch: async (batchId: string): Promise<Blob> => {
    return quotationGeneratorApi.downloadMergedPdf(batchId);
  },

  downloadBatchAsFile: async (batchId: string, filename?: string): Promise<void> => {
    return quotationGeneratorApi.downloadMergedPdfAsFile(batchId, filename);
  },

  /**
   * List available templates.
   */
  listTemplates: async (): Promise<TemplateInfo[]> => {
    const response = await apiClient.get<TemplateListResponse>(
      '/quotation-generator/templates'
    );
    return response.data.templates;
  },

  /**
   * Upload or update a template.
   */
  uploadTemplate: async (
    name: string,
    file: File,
    displayName: string,
    description?: string,
    validateVariables: boolean = true
  ): Promise<UploadTemplateResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('display_name', displayName);
    if (description) {
      formData.append('description', description);
    }
    formData.append('validate_variables', validateVariables.toString());

    const response = await apiClient.post<UploadTemplateResponse>(
      `/quotation-generator/templates/${name}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  /**
   * Update quotation contact.
   */
  updateQuotationContact: async (
    batchId: string,
    rowIndex: number,
    contactId: string,
    contactName: string
  ): Promise<{ success: boolean; contact_id: string; contact_name: string }> => {
    const response = await apiClient.patch<{ success: boolean; contact_id: string; contact_name: string }>(
      `/quotation-generator/batches/${batchId}/quotations/${rowIndex}/contact`,
      { contact_id: contactId, contact_name: contactName }
    );
    return response.data;
  },

  /**
   * Download example CSV file.
   */
  downloadExampleCsv: async (): Promise<void> => {
    const response = await apiClient.get('/quotation-generator/example-csv', {
      responseType: 'blob',
    });
    const blob = response.data;
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'exemple_devis_thales.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};
