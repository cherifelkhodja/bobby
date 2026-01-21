/**
 * HR API client for job postings and applications management.
 */

import { apiClient } from './client';
import type {
  ApplicationStatus,
  CreateJobPostingRequest,
  CvDownloadUrlResponse,
  JobApplication,
  JobApplicationListResponse,
  JobPosting,
  JobPostingListResponse,
  JobPostingPublic,
  JobPostingStatus,
  OpportunityForHRListResponse,
  UpdateJobPostingRequest,
  ApplicationSubmissionResult,
} from '../types';

// Types for anonymization
export interface AnonymizeJobPostingRequest {
  opportunity_id: string;
  title: string;
  description: string;
  client_name?: string | null;
}

export interface AnonymizedJobPostingResponse {
  title: string;
  description: string;
  qualifications: string;
  skills: string[]; // Turnover-IT skill slugs
}

export interface SyncSkillsResponse {
  synced_count: number;
  message: string;
}

export interface TurnoverITSkill {
  name: string;
  slug: string;
}

export interface TurnoverITSkillsResponse {
  skills: TurnoverITSkill[];
  total: number;
}

export interface TurnoverITPlace {
  key: string;           // Unique identifier for persistence (e.g., "fr~ile-de-france~paris~")
  label: string;         // Full display label (e.g., "Paris, France")
  shortLabel: string;    // Short label (e.g., "Paris")
  locality: string;      // City name (from adminLevel2)
  region: string;        // Region name (from adminLevel1)
  postalCode: string;    // Postal code
  country: string;       // Country name
  countryCode: string;   // ISO country code (e.g., "FR")
}

export interface TurnoverITPlacesResponse {
  places: TurnoverITPlace[];
  total: number;
}

export interface OpportunityDetailResponse {
  id: string;
  title: string;
  reference: string;
  description?: string | null;
  criteria?: string | null;
  expertise_area?: string | null;
  place?: string | null;
  duration?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  company_id?: string | null;
  company_name?: string | null;
  manager_id?: string | null;
  manager_name?: string | null;
  contact_id?: string | null;
  contact_name?: string | null;
  agency_id?: string | null;
  agency_name?: string | null;
  state?: number | null;
  state_name?: string | null;
  state_color?: string | null;
}

export const hrApi = {
  // ========== Anonymization ==========

  /**
   * Anonymize opportunity content for a job posting.
   *
   * Uses Gemini AI to:
   * - Anonymize client names and internal references
   * - Structure content for Turnover-IT (title, description, qualifications)
   * - Extract and match skills to Turnover-IT nomenclature
   */
  anonymizeJobPosting: async (
    data: AnonymizeJobPostingRequest
  ): Promise<AnonymizedJobPostingResponse> => {
    const response = await apiClient.post<AnonymizedJobPostingResponse>(
      '/hr/anonymize-job-posting',
      data
    );
    return response.data;
  },

  /**
   * Manually sync Turnover-IT skills (admin only)
   */
  syncSkills: async (): Promise<SyncSkillsResponse> => {
    const response = await apiClient.post<SyncSkillsResponse>('/hr/sync-skills');
    return response.data;
  },

  /**
   * Get Turnover-IT skills from the database cache.
   * Used for skill autocomplete in job posting form.
   */
  getSkills: async (search?: string): Promise<TurnoverITSkillsResponse> => {
    const response = await apiClient.get<TurnoverITSkillsResponse>('/hr/skills', {
      params: search ? { search } : undefined,
    });
    return response.data;
  },

  /**
   * Get Turnover-IT places for location autocomplete.
   * Search by city, postal code, or region.
   */
  getPlaces: async (query: string): Promise<TurnoverITPlacesResponse> => {
    const response = await apiClient.get<TurnoverITPlacesResponse>('/hr/places', {
      params: { q: query },
    });
    return response.data;
  },

  // ========== Opportunities ==========

  /**
   * Get list of opportunities from BoondManager where user is HR manager.
   *
   * For admin users: Returns ALL opportunities
   * For RH users: Returns only opportunities where they are HR manager
   *
   * Note: No pagination - all opportunities are returned from BoondManager API
   */
  getOpportunities: async (params?: {
    search?: string;
  }): Promise<OpportunityForHRListResponse> => {
    const response = await apiClient.get<OpportunityForHRListResponse>('/hr/opportunities', {
      params,
    });
    return response.data;
  },

  /**
   * Get detailed opportunity information from BoondManager.
   */
  getOpportunityDetail: async (opportunityId: string): Promise<OpportunityDetailResponse> => {
    const response = await apiClient.get<OpportunityDetailResponse>(
      `/hr/opportunities/${opportunityId}`
    );
    return response.data;
  },

  // ========== Job Postings ==========

  /**
   * Create a new job posting draft
   */
  createJobPosting: async (data: CreateJobPostingRequest): Promise<JobPosting> => {
    const response = await apiClient.post<JobPosting>('/hr/job-postings', data);
    return response.data;
  },

  /**
   * Get list of job postings
   */
  getJobPostings: async (params?: {
    page?: number;
    page_size?: number;
    status?: JobPostingStatus;
  }): Promise<JobPostingListResponse> => {
    const response = await apiClient.get<JobPostingListResponse>('/hr/job-postings', {
      params,
    });
    return response.data;
  },

  /**
   * Get a single job posting by ID
   */
  getJobPosting: async (postingId: string): Promise<JobPosting> => {
    const response = await apiClient.get<JobPosting>(`/hr/job-postings/${postingId}`);
    return response.data;
  },

  /**
   * Update a draft job posting
   */
  updateJobPosting: async (
    postingId: string,
    data: UpdateJobPostingRequest
  ): Promise<JobPosting> => {
    const response = await apiClient.patch<JobPosting>(`/hr/job-postings/${postingId}`, data);
    return response.data;
  },

  /**
   * Publish a job posting to Turnover-IT
   */
  publishJobPosting: async (postingId: string): Promise<JobPosting> => {
    const response = await apiClient.post<JobPosting>(`/hr/job-postings/${postingId}/publish`);
    return response.data;
  },

  /**
   * Close a published job posting
   */
  closeJobPosting: async (postingId: string): Promise<JobPosting> => {
    const response = await apiClient.post<JobPosting>(`/hr/job-postings/${postingId}/close`);
    return response.data;
  },

  /**
   * Reactivate a closed job posting
   */
  reactivateJobPosting: async (postingId: string): Promise<JobPosting> => {
    const response = await apiClient.post<JobPosting>(`/hr/job-postings/${postingId}/reactivate`);
    return response.data;
  },

  /**
   * Delete a draft job posting
   */
  deleteJobPosting: async (postingId: string): Promise<void> => {
    await apiClient.delete(`/hr/job-postings/${postingId}`);
  },

  // ========== Applications ==========

  /**
   * Get list of applications for a job posting
   */
  getApplications: async (
    postingId: string,
    params?: {
      page?: number;
      page_size?: number;
      status?: ApplicationStatus;
      sort_by_score?: boolean;
    }
  ): Promise<JobApplicationListResponse> => {
    const response = await apiClient.get<JobApplicationListResponse>(
      `/hr/job-postings/${postingId}/applications`,
      { params }
    );
    return response.data;
  },

  /**
   * Get a single application by ID
   */
  getApplication: async (applicationId: string): Promise<JobApplication> => {
    const response = await apiClient.get<JobApplication>(`/hr/applications/${applicationId}`);
    return response.data;
  },

  /**
   * Update application status
   */
  updateApplicationStatus: async (
    applicationId: string,
    status: ApplicationStatus,
    comment?: string
  ): Promise<JobApplication> => {
    const response = await apiClient.patch<JobApplication>(
      `/hr/applications/${applicationId}/status`,
      { status, comment }
    );
    return response.data;
  },

  /**
   * Update application notes
   */
  updateApplicationNote: async (
    applicationId: string,
    notes: string
  ): Promise<JobApplication> => {
    const response = await apiClient.patch<JobApplication>(
      `/hr/applications/${applicationId}/note`,
      { notes }
    );
    return response.data;
  },

  /**
   * Get presigned URL for CV download
   */
  getCvDownloadUrl: async (applicationId: string): Promise<CvDownloadUrlResponse> => {
    const response = await apiClient.get<CvDownloadUrlResponse>(
      `/hr/applications/${applicationId}/cv`
    );
    return response.data;
  },

  /**
   * Create candidate in BoondManager from application
   */
  createCandidateInBoond: async (applicationId: string): Promise<JobApplication> => {
    const response = await apiClient.post<JobApplication>(
      `/hr/applications/${applicationId}/create-in-boond`
    );
    return response.data;
  },
};

/**
 * Public API client for job applications (no authentication required).
 */
export const publicApplicationApi = {
  /**
   * Get public job posting info by token
   */
  getJobPosting: async (token: string): Promise<JobPostingPublic> => {
    const response = await apiClient.get<JobPostingPublic>(`/postuler/${token}`);
    return response.data;
  },

  /**
   * Submit a job application
   */
  submitApplication: async (
    token: string,
    data: {
      first_name: string;
      last_name: string;
      email: string;
      phone: string;
      job_title: string;
      tjm_min: number;
      tjm_max: number;
      availability_date: string;
      cv: File;
    }
  ): Promise<ApplicationSubmissionResult> => {
    const formData = new FormData();
    formData.append('first_name', data.first_name);
    formData.append('last_name', data.last_name);
    formData.append('email', data.email);
    formData.append('phone', data.phone);
    formData.append('job_title', data.job_title);
    formData.append('tjm_min', data.tjm_min.toString());
    formData.append('tjm_max', data.tjm_max.toString());
    formData.append('availability_date', data.availability_date);
    formData.append('cv', data.cv);

    const response = await apiClient.post<ApplicationSubmissionResult>(
      `/postuler/${token}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },
};
