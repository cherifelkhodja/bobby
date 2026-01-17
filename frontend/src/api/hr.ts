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

export const hrApi = {
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
