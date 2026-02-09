/**
 * Tests for HR API client.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { hrApi, publicApplicationApi } from './hr';
import { apiClient } from './client';

// Mock the API client
vi.mock('./client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('hrApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getOpportunities', () => {
    it('should fetch opportunities from BoondManager', async () => {
      const mockResponse = {
        data: {
          items: [
            {
              id: 'BOOND-123',
              title: 'Dev Python',
              reference: 'REF-001',
              client_name: 'Client A',
              state_name: 'En cours',
              state_color: 'blue',
              has_job_posting: false,
              job_posting_id: null,
              applications_count: 0,
              new_applications_count: 0,
            },
          ],
          total: 1,
          page: 1,
          page_size: 1,
        },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await hrApi.getOpportunities();

      expect(apiClient.get).toHaveBeenCalledWith('/hr/opportunities', {
        params: undefined,
      });
      expect(result.items).toHaveLength(1);
      expect(result.items[0].id).toBe('BOOND-123');
      expect(result.items[0].state_name).toBe('En cours');
    });

    it('should filter opportunities with search param', async () => {
      const mockResponse = { data: { items: [], total: 0, page: 1, page_size: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      await hrApi.getOpportunities({ search: 'Python' });

      expect(apiClient.get).toHaveBeenCalledWith('/hr/opportunities', {
        params: { search: 'Python' },
      });
    });
  });

  describe('createJobPosting', () => {
    it('should create a job posting', async () => {
      const postingData = {
        opportunity_id: 'opp-123',
        title: 'Dev Python',
        description: 'D'.repeat(500),
        qualifications: 'Q'.repeat(150),
        location_country: 'France',
        contract_types: ['FREELANCE'],
        skills: ['Python'],
      };
      const mockResponse = { data: { id: 'posting-123', ...postingData } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await hrApi.createJobPosting(postingData as unknown);

      expect(apiClient.post).toHaveBeenCalledWith('/hr/job-postings', postingData);
      expect(result.id).toBe('posting-123');
    });
  });

  describe('getJobPostings', () => {
    it('should fetch job postings list', async () => {
      const mockResponse = { data: { items: [], total: 0, page: 1, page_size: 20 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await hrApi.getJobPostings();

      expect(apiClient.get).toHaveBeenCalledWith('/hr/job-postings', { params: undefined });
      expect(result).toEqual(mockResponse.data);
    });

    it('should filter by status', async () => {
      const mockResponse = { data: { items: [], total: 0, page: 1, page_size: 20 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      await hrApi.getJobPostings({ status: 'published' });

      expect(apiClient.get).toHaveBeenCalledWith('/hr/job-postings', {
        params: { status: 'published' },
      });
    });
  });

  describe('getJobPosting', () => {
    it('should fetch a single job posting', async () => {
      const mockResponse = { data: { id: 'posting-123', title: 'Dev Python' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await hrApi.getJobPosting('posting-123');

      expect(apiClient.get).toHaveBeenCalledWith('/hr/job-postings/posting-123');
      expect(result.id).toBe('posting-123');
    });
  });

  describe('updateJobPosting', () => {
    it('should update a job posting', async () => {
      const updateData = { title: 'Updated Title' };
      const mockResponse = { data: { id: 'posting-123', title: 'Updated Title' } };
      vi.mocked(apiClient.patch).mockResolvedValue(mockResponse);

      const result = await hrApi.updateJobPosting('posting-123', updateData);

      expect(apiClient.patch).toHaveBeenCalledWith('/hr/job-postings/posting-123', updateData);
      expect(result.title).toBe('Updated Title');
    });
  });

  describe('publishJobPosting', () => {
    it('should publish a job posting', async () => {
      const mockResponse = { data: { id: 'posting-123', status: 'published' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await hrApi.publishJobPosting('posting-123');

      expect(apiClient.post).toHaveBeenCalledWith('/hr/job-postings/posting-123/publish');
      expect(result.status).toBe('published');
    });
  });

  describe('closeJobPosting', () => {
    it('should close a job posting', async () => {
      const mockResponse = { data: { id: 'posting-123', status: 'closed' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await hrApi.closeJobPosting('posting-123');

      expect(apiClient.post).toHaveBeenCalledWith('/hr/job-postings/posting-123/close');
      expect(result.status).toBe('closed');
    });
  });

  describe('getApplications', () => {
    it('should fetch applications for a posting', async () => {
      const mockResponse = { data: { items: [], total: 0, page: 1, page_size: 20, stats: {} } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await hrApi.getApplications('posting-123');

      expect(apiClient.get).toHaveBeenCalledWith('/hr/job-postings/posting-123/applications', {
        params: undefined,
      });
      expect(result).toEqual(mockResponse.data);
    });

    it('should filter by status and sort by score', async () => {
      const mockResponse = { data: { items: [], total: 0, page: 1, page_size: 20, stats: {} } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      await hrApi.getApplications('posting-123', {
        status: 'nouveau',
        sort_by_score: true,
      });

      expect(apiClient.get).toHaveBeenCalledWith('/hr/job-postings/posting-123/applications', {
        params: { status: 'nouveau', sort_by_score: true },
      });
    });
  });

  describe('getApplication', () => {
    it('should fetch a single application', async () => {
      const mockResponse = { data: { id: 'app-123', first_name: 'Jean' } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await hrApi.getApplication('app-123');

      expect(apiClient.get).toHaveBeenCalledWith('/hr/applications/app-123', { params: { mark_viewed: false } });
      expect(result.id).toBe('app-123');
    });
  });

  describe('updateApplicationStatus', () => {
    it('should update application status', async () => {
      const mockResponse = { data: { id: 'app-123', status: 'en_cours' } };
      vi.mocked(apiClient.patch).mockResolvedValue(mockResponse);

      const result = await hrApi.updateApplicationStatus('app-123', 'en_cours', 'Profil intéressant');

      expect(apiClient.patch).toHaveBeenCalledWith('/hr/applications/app-123/status', {
        status: 'en_cours',
        comment: 'Profil intéressant',
      });
      expect(result.status).toBe('en_cours');
    });
  });

  describe('updateApplicationNote', () => {
    it('should update application notes', async () => {
      const mockResponse = { data: { id: 'app-123', notes: 'Updated notes' } };
      vi.mocked(apiClient.patch).mockResolvedValue(mockResponse);

      const result = await hrApi.updateApplicationNote('app-123', 'Updated notes');

      expect(apiClient.patch).toHaveBeenCalledWith('/hr/applications/app-123/note', {
        notes: 'Updated notes',
      });
      expect(result.notes).toBe('Updated notes');
    });
  });

  describe('getCvDownloadUrl', () => {
    it('should get CV download URL', async () => {
      const mockResponse = {
        data: { url: 'https://presigned-url', filename: 'cv.pdf', expires_in: 3600 },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await hrApi.getCvDownloadUrl('app-123');

      expect(apiClient.get).toHaveBeenCalledWith('/hr/applications/app-123/cv');
      expect(result.url).toBe('https://presigned-url');
    });
  });

  describe('createCandidateInBoond', () => {
    it('should create candidate in BoondManager', async () => {
      const mockResponse = { data: { id: 'app-123', boond_candidate_id: 'BOOND-456' } };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const result = await hrApi.createCandidateInBoond('app-123');

      expect(apiClient.post).toHaveBeenCalledWith('/hr/applications/app-123/create-in-boond');
      expect(result.boond_candidate_id).toBe('BOOND-456');
    });
  });
});

describe('publicApplicationApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getJobPosting', () => {
    it('should fetch public job posting by token', async () => {
      const mockResponse = {
        data: {
          title: 'Dev Python',
          description: 'Description',
          qualifications: 'Qualifications',
        },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await publicApplicationApi.getJobPosting('test-token');

      expect(apiClient.get).toHaveBeenCalledWith('/postuler/test-token');
      expect(result.title).toBe('Dev Python');
    });
  });

  describe('submitApplication', () => {
    it('should submit application with CV', async () => {
      const mockResponse = {
        data: { success: true, application_id: 'app-123', message: 'Success' },
      };
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

      const cvFile = new File(['PDF content'], 'cv.pdf', { type: 'application/pdf' });
      const result = await publicApplicationApi.submitApplication('test-token', {
        first_name: 'Jean',
        last_name: 'Dupont',
        email: 'jean@example.com',
        phone: '+33612345678',
        job_title: 'Dev Python',
        availability: 'immediate',
        employment_status: 'freelance',
        english_level: 'B2',
        tjm_current: 400,
        tjm_desired: 500,
        salary_current: null,
        salary_desired: null,
        cv: cvFile,
      });

      expect(apiClient.post).toHaveBeenCalled();
      const [url, formData, config] = vi.mocked(apiClient.post).mock.calls[0];
      expect(url).toBe('/postuler/test-token');
      expect(formData).toBeInstanceOf(FormData);
      expect(config).toEqual({ headers: { 'Content-Type': 'multipart/form-data' } });
      expect(result.success).toBe(true);
    });
  });
});
