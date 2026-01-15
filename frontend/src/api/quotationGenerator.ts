/**
 * API client for quotation generator endpoints.
 */

import { apiClient } from './client';

// Types

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
  // Period
  period: {
    start: string;
    end: string;
  };
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
  zip_file_path: string | null;
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
   * Download batch ZIP file.
   */
  downloadBatch: async (batchId: string): Promise<Blob> => {
    const response = await apiClient.get(
      `/quotation-generator/batches/${batchId}/download`,
      {
        responseType: 'blob',
      }
    );
    return response.data;
  },

  /**
   * Download batch and trigger browser download.
   */
  downloadBatchAsFile: async (batchId: string, filename?: string): Promise<void> => {
    const blob = await quotationGeneratorApi.downloadBatch(batchId);
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
