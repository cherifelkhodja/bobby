// User types
export type UserRole = 'user' | 'commercial' | 'rh' | 'admin';

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: UserRole;
  phone?: string | null;
  is_verified: boolean;
  is_active: boolean;
  boond_resource_id: string | null;
  manager_boond_id: string | null;
  created_at: string;
  updated_at: string;
}

// Auth types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  boond_resource_id?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginResponse extends AuthTokens {
  user: User;
}

export interface UpdateProfileRequest {
  first_name?: string;
  last_name?: string;
  boond_resource_id?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

// Opportunity types
export interface Opportunity {
  id: string;
  external_id: string;
  title: string;
  reference: string;
  budget: number | null;
  start_date: string | null;
  end_date: string | null;
  response_deadline: string | null;
  manager_name: string | null;
  manager_boond_id: string | null;
  client_name: string | null;
  description: string | null;
  skills: string[];
  location: string | null;
  is_open: boolean;
  is_shared: boolean;
  owner_id: string | null;
  days_until_deadline: number | null;
  synced_at: string;
  created_at: string;
}

// Invitation types
export interface Invitation {
  id: string;
  email: string;
  role: UserRole;
  phone?: string | null;
  invited_by: string;
  expires_at: string;
  is_expired: boolean;
  is_accepted: boolean;
  created_at: string;
}

export interface InvitationValidation {
  email: string;
  role: string;
  phone?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  is_valid: boolean;
  hours_until_expiry: number;
}

export interface CreateInvitationRequest {
  email: string;
  role: UserRole;
  boond_resource_id?: string;
  manager_boond_id?: string;
  phone?: string;
  first_name?: string;
  last_name?: string;
}

export interface BoondResource {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string | null;
  manager_id: string | null;
  manager_name: string | null;
  agency_id: string | null;
  agency_name: string | null;
  resource_type: number | null;
  resource_type_name: string | null;
  state: number | null;
  state_name: string | null;
  suggested_role: UserRole;
}

export interface AcceptInvitationRequest {
  token: string;
  first_name: string;
  last_name: string;
  password: string;
  phone?: string;
}

// Business Lead types
export type BusinessLeadStatus = 'draft' | 'submitted' | 'in_review' | 'qualified' | 'rejected';

export interface BusinessLead {
  id: string;
  title: string;
  description: string;
  submitter_id: string;
  client_name: string;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  estimated_budget: number | null;
  expected_start_date: string | null;
  skills_needed: string[];
  location: string | null;
  status: BusinessLeadStatus;
  rejection_reason: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface OpportunityListResponse {
  items: Opportunity[];
  total: number;
  page: number;
  page_size: number;
}

// Cooptation types
export type CooptationStatus =
  | 'pending'
  | 'in_review'
  | 'interview'
  | 'accepted'
  | 'rejected';

export interface StatusChange {
  from_status: string;
  to_status: string;
  changed_at: string;
  changed_by: string | null;
  comment: string | null;
}

export interface Cooptation {
  id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  candidate_phone: string | null;
  candidate_daily_rate: number | null;
  opportunity_id: string;
  opportunity_title: string;
  opportunity_reference: string;
  status: CooptationStatus;
  status_display: string;
  submitter_id: string;
  submitter_name: string | null;
  external_positioning_id: string | null;
  rejection_reason: string | null;
  status_history: StatusChange[];
  submitted_at: string;
  updated_at: string;
}

export interface CooptationListResponse {
  items: Cooptation[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateCooptationRequest {
  opportunity_id: string;
  candidate_first_name: string;
  candidate_last_name: string;
  candidate_email: string;
  candidate_civility: 'M' | 'Mme';
  candidate_phone?: string;
  candidate_daily_rate?: number;
  candidate_note?: string;
}

export interface CooptationStats {
  total: number;
  pending: number;
  in_review: number;
  interview: number;
  accepted: number;
  rejected: number;
  conversion_rate: number;
}

// Pagination
export interface PaginationParams {
  page?: number;
  page_size?: number;
  search?: string;
}

// CV Transformer types
export interface CvTemplate {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  is_active: boolean;
  updated_at: string;
}

export interface CvTransformationStats {
  total: number;
  by_user: CvTransformationUserStats[];
}

export interface CvTransformationUserStats {
  user_id: string;
  user_email: string;
  user_name: string;
  count: number;
}

// HR Feature types

// Job Posting types
export type JobPostingStatus = 'draft' | 'published' | 'closed';
export type ContractType = 'CDI' | 'CDD' | 'FREELANCE' | 'INTERIM' | 'STAGE' | 'ALTERNANCE';
export type RemotePolicy = 'NONE' | 'PARTIAL' | 'FULL';
export type ExperienceLevel = 'JUNIOR' | 'INTERMEDIATE' | 'SENIOR' | 'EXPERT';

export interface JobPosting {
  id: string;
  opportunity_id: string;
  opportunity_title: string | null;
  opportunity_reference: string | null;
  client_name: string | null;
  title: string;
  description: string;
  qualifications: string;
  location_country: string;
  location_region: string | null;
  location_postal_code: string | null;
  location_city: string | null;
  contract_types: ContractType[];
  skills: string[];
  experience_level: ExperienceLevel | null;
  remote: RemotePolicy | null;
  start_date: string | null;
  duration_months: number | null;
  salary_min_annual: number | null;
  salary_max_annual: number | null;
  salary_min_daily: number | null;
  salary_max_daily: number | null;
  employer_overview: string | null;
  status: JobPostingStatus;
  status_display: string;
  turnoverit_reference: string | null;
  turnoverit_public_url: string | null;
  application_token: string;
  application_url: string | null;
  created_by: string | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
  published_at: string | null;
  closed_at: string | null;
  applications_total: number;
  applications_new: number;
}

export interface JobPostingListResponse {
  items: JobPosting[];
  total: number;
  page: number;
  page_size: number;
}

export interface JobPostingPublic {
  title: string;
  description: string;
  qualifications: string;
  location_country: string;
  location_region: string | null;
  location_city: string | null;
  contract_types: ContractType[];
  skills: string[];
  experience_level: ExperienceLevel | null;
  remote: RemotePolicy | null;
  start_date: string | null;
  duration_months: number | null;
  salary_min_daily: number | null;
  salary_max_daily: number | null;
  employer_overview: string | null;
}

export interface CreateJobPostingRequest {
  opportunity_id: string;
  title: string;
  description: string;
  qualifications: string;
  location_country: string;
  location_region?: string;
  location_postal_code?: string;
  location_city?: string;
  contract_types: string[];
  skills: string[];
  experience_level?: string;
  remote?: string;
  start_date?: string;
  duration_months?: number;
  salary_min_annual?: number;
  salary_max_annual?: number;
  salary_min_daily?: number;
  salary_max_daily?: number;
  employer_overview?: string;
}

export interface UpdateJobPostingRequest {
  title?: string;
  description?: string;
  qualifications?: string;
  location_country?: string;
  location_region?: string;
  location_postal_code?: string;
  location_city?: string;
  contract_types?: string[];
  skills?: string[];
  experience_level?: string;
  remote?: string;
  start_date?: string;
  duration_months?: number;
  salary_min_annual?: number;
  salary_max_annual?: number;
  salary_min_daily?: number;
  salary_max_daily?: number;
  employer_overview?: string;
}

// HR Opportunity (with job posting info)
export interface OpportunityForHR {
  id: string;
  external_id: string;
  title: string;
  reference: string;
  client_name: string | null;
  description: string | null;
  skills: string[];
  location: string | null;
  budget: number | null;
  start_date: string | null;
  end_date: string | null;
  manager_name: string | null;
  synced_at: string;
  has_job_posting: boolean;
  job_posting_id: string | null;
  job_posting_status: JobPostingStatus | null;
  applications_count: number;
  new_applications_count: number;
}

export interface OpportunityForHRListResponse {
  items: OpportunityForHR[];
  total: number;
  page: number;
  page_size: number;
}

// Job Application types
export type ApplicationStatus = 'nouveau' | 'en_cours' | 'entretien' | 'accepte' | 'refuse';

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  nouveau: 'Nouveau',
  en_cours: 'En cours',
  entretien: 'Entretien',
  accepte: 'Accepté',
  refuse: 'Refusé',
};

export const APPLICATION_STATUS_COLORS: Record<ApplicationStatus, string> = {
  nouveau: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  en_cours: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  entretien: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
  accepte: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  refuse: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

export interface MatchingDetails {
  score: number;
  strengths: string[];
  gaps: string[];
  summary: string;
}

export interface ApplicationStatusChange {
  from_status: string;
  to_status: string;
  changed_at: string;
  changed_by: string | null;
  changed_by_name: string | null;
  comment: string | null;
}

export interface JobApplication {
  id: string;
  job_posting_id: string;
  job_posting_title: string | null;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  phone: string;
  job_title: string;
  tjm_min: number;
  tjm_max: number;
  tjm_range: string;
  availability_date: string;
  cv_s3_key: string;
  cv_filename: string;
  cv_download_url: string | null;
  matching_score: number | null;
  matching_details: MatchingDetails | null;
  status: ApplicationStatus;
  status_display: string;
  status_history: ApplicationStatusChange[];
  notes: string | null;
  boond_candidate_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobApplicationListResponse {
  items: JobApplication[];
  total: number;
  page: number;
  page_size: number;
  stats: Record<string, number>;
}

export interface SubmitApplicationRequest {
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

export interface ApplicationSubmissionResult {
  success: boolean;
  application_id: string;
  message: string;
}

export interface CvDownloadUrlResponse {
  url: string;
  filename: string;
  expires_in: number;
}

// Matching score helper
export function getMatchingScoreColor(score: number | null): string {
  if (score === null) return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
  if (score >= 80) return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
  if (score >= 50) return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300';
  return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
}
