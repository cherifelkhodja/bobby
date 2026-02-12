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
  candidate_cv_filename: string | null;
  candidate_note: string | null;
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

export interface CvDownloadUrlResponse {
  url: string;
  filename: string;
  expires_in: number;
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

// Published Opportunity types
export type PublishedOpportunityStatus = 'draft' | 'published' | 'closed';

export interface BoondOpportunity {
  id: string;
  title: string;
  reference: string;
  description: string | null;
  start_date: string | null;
  end_date: string | null;
  company_name: string | null;
  state: number | null;
  state_name: string | null;
  state_color: string | null;
  manager_id: string | null;
  manager_name: string | null;
  is_published: boolean;
  published_opportunity_id: string | null;
  published_status: PublishedOpportunityStatus | null;
  cooptations_count: number;
}

export interface BoondOpportunityListResponse {
  items: BoondOpportunity[];
  total: number;
}

export interface BoondOpportunityDetail {
  id: string;
  title: string;
  reference: string;
  description: string | null;
  criteria: string | null;
  expertise_area: string | null;
  place: string | null;
  duration: number | null;
  start_date: string | null;
  end_date: string | null;
  closing_date: string | null;
  answer_date: string | null;
  company_id: string | null;
  company_name: string | null;
  manager_id: string | null;
  manager_name: string | null;
  contact_id: string | null;
  contact_name: string | null;
  agency_id: string | null;
  agency_name: string | null;
  state: number | null;
  state_name: string | null;
  state_color: string | null;
  is_published: boolean;
}

export interface AnonymizeRequest {
  boond_opportunity_id: string;
  title: string;
  description?: string | null;
}

export interface AnonymizedPreview {
  boond_opportunity_id: string;
  original_title: string;
  anonymized_title: string;
  anonymized_description: string;
  skills: string[];
}

export interface PublishRequest {
  boond_opportunity_id: string;
  title: string;
  description: string;
  skills: string[];
  original_title: string;
  original_data?: Record<string, unknown> | null;
  end_date?: string | null;
}

export interface PublishedOpportunity {
  id: string;
  boond_opportunity_id: string;
  title: string;
  description: string;
  skills: string[];
  end_date: string | null;
  status: PublishedOpportunityStatus;
  status_display: string;
  created_at: string;
  updated_at: string;
}

export interface UpdatePublishedOpportunityData {
  title: string;
  description: string;
  skills: string[];
  end_date?: string | null;
}

export interface PublishedOpportunityListResponse {
  items: PublishedOpportunity[];
  total: number;
  page: number;
  page_size: number;
}

// HR Feature - Job Postings & Applications
export type JobPostingStatus = 'draft' | 'published' | 'closed';
export type ApplicationStatus = 'en_cours' | 'valide' | 'refuse';

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  en_cours: 'En cours',
  valide: 'Validé',
  refuse: 'Refusé',
};

export const APPLICATION_STATUS_COLORS: Record<ApplicationStatus, string> = {
  en_cours: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  valide: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  refuse: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

export function getMatchingScoreColor(score: number): string {
  if (score >= 80) return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
  if (score >= 50) return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300';
  return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
}

export interface OpportunityForHR {
  id: string; // Boond opportunity ID
  title: string;
  reference: string;
  client_name: string | null;
  description: string | null;
  start_date: string | null;
  end_date: string | null;
  // Manager info
  manager_name: string | null;
  hr_manager_name: string | null;
  // State info from Boond
  state: number | null;
  state_name: string | null;
  state_color: string | null;
  // Job posting info
  has_job_posting: boolean;
  job_posting_id: string | null;
  job_posting_status: JobPostingStatus | null;
  job_posting_status_display: string | null;
  applications_count: number;
  new_applications_count: number;
}

export interface OpportunityForHRListResponse {
  items: OpportunityForHR[];
  total: number;
  page: number;
  page_size: number;
}

export interface JobPosting {
  id: string;
  opportunity_id: string;
  boond_opportunity_id: string;
  opportunity_reference: string;
  title: string;
  description: string;
  qualifications: string;
  location_country: string;
  location_region: string | null;
  location_postal_code: string | null;
  location_city: string | null;
  location_key: string | null;  // Turnover-IT location key
  client_name: string | null;
  contract_types: string[];
  skills: string[];
  salary_min: number | null;
  salary_max: number | null;
  salary_min_annual: number | null;
  salary_max_annual: number | null;
  salary_min_daily: number | null;
  salary_max_daily: number | null;
  remote: string | null;
  experience_level: string | null;
  start_date: string | null;
  duration_months: number | null;
  status: JobPostingStatus;
  status_display: string;
  turnoverit_reference: string | null;
  turnoverit_public_url: string | null;
  application_token: string;
  application_url: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  published_at: string | null;
  applications_count: number;
  applications_total: number;
  applications_new: number;
  new_applications_count: number;
  view_count: number;
}

export interface JobPostingPublic {
  title: string;
  description: string;
  qualifications: string;
  skills: string[];
  location_country: string;
  location_region: string | null;
  location_city: string | null;
  remote: string | null;
  experience_level: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_min_daily: number | null;
  salary_max_daily: number | null;
  contract_types: string[];
  start_date: string | null;
  duration_months: number | null;
}

export interface JobPostingListResponse {
  items: JobPosting[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateJobPostingRequest {
  opportunity_id?: string;
  boond_opportunity_id?: string;
  client_name?: string | null;  // Client name from Boond
  title: string;
  description: string;
  qualifications: string;
  location_country: string;
  location_region?: string | null;
  location_postal_code?: string | null;
  location_city?: string | null;
  location_key?: string | null;  // Turnover-IT location key for normalization
  contract_types: string[];
  skills?: string[];
  salary_min?: number | null;
  salary_max?: number | null;
  salary_min_annual?: number | null;
  salary_max_annual?: number | null;
  salary_min_daily?: number | null;
  salary_max_daily?: number | null;
  remote?: string | null;
  experience_level?: string | null;
  start_date?: string | null;
  duration_months?: number | null;
  employer_overview?: string | null;
  pushToTop?: boolean;
}

export interface UpdateJobPostingRequest {
  title?: string;
  description?: string;
  qualifications?: string;
  location_country?: string;
  location_region?: string | null;
  location_postal_code?: string | null;
  location_city?: string | null;
  location_key?: string | null;  // Turnover-IT location key for normalization
  contract_types?: string[];
  skills?: string[];
  salary_min?: number | null;
  salary_max?: number | null;
  remote?: string | null;
  experience_level?: string | null;
  start_date?: string | null;
  duration_months?: number | null;
}

export interface ScoresDetails {
  competences_techniques: number;
  experience: number;
  formation: number;
  soft_skills: number;
}

export interface MatchingRecommendation {
  niveau: 'fort' | 'moyen' | 'faible';
  action_suggeree: string;
}

export interface MatchingDetails {
  // Legacy fields (kept for backward compatibility)
  score: number;
  strengths: string[];
  gaps: string[];
  summary: string;
  // Enhanced fields
  score_global?: number;
  scores_details?: ScoresDetails;
  competences_matchees?: string[];
  competences_manquantes?: string[];
  points_forts?: string[];
  points_vigilance?: string[];
  synthese?: string;
  recommandation?: MatchingRecommendation;
}

// CV Quality Evaluation Types (/20)
export interface StabilityScore {
  note: number;
  max: number;
  duree_moyenne_mois: number;
  commentaire: string;
}

export interface AccountQualityScore {
  note: number;
  max: number;
  comptes_identifies: string[];
  commentaire: string;
}

export interface EducationScore {
  note: number;
  max: number;
  formations_identifiees: string[];
  commentaire: string;
}

export interface ContinuityScore {
  note: number;
  max: number;
  trous_identifies: string[];
  commentaire: string;
}

export interface BonusMalus {
  valeur: number;
  raisons: string[];
}

export interface CvQualityDetailsNotes {
  stabilite_missions?: StabilityScore;
  qualite_comptes?: AccountQualityScore;
  parcours_scolaire?: EducationScore;
  continuite_parcours?: ContinuityScore;
  bonus_malus?: BonusMalus;
}

export interface CvQuality {
  niveau_experience: 'JUNIOR' | 'CONFIRME' | 'SENIOR';
  annees_experience: number;
  note_globale: number;
  details_notes?: CvQualityDetailsNotes;
  points_forts: string[];
  points_faibles: string[];
  synthese: string;
  classification: 'EXCELLENT' | 'BON' | 'MOYEN' | 'FAIBLE';
}

export function getCvQualityScoreColor(score: number): string {
  if (score >= 16) return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
  if (score >= 12) return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
  if (score >= 8) return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300';
  return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
}

export function getCvQualityClassificationLabel(classification: string): string {
  const labels: Record<string, string> = {
    EXCELLENT: 'Excellent',
    BON: 'Bon',
    MOYEN: 'Moyen',
    FAIBLE: 'Faible',
  };
  return labels[classification] || classification;
}

export interface JobApplication {
  id: string;
  job_posting_id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  job_title: string;
  phone: string;
  email: string;
  // New fields
  availability: string;
  availability_display: string;
  employment_status: string;
  employment_status_display: string;
  english_level: string;
  english_level_display: string;
  tjm_current: number | null;
  tjm_desired: number | null;
  salary_current: number | null;
  salary_desired: number | null;
  tjm_range: string;
  salary_range: string;
  // Legacy fields
  tjm_min: number | null;
  tjm_max: number | null;
  availability_date: string | null;
  // CV
  cv_filename: string;
  matching_score: number | null;
  matching_details: MatchingDetails | null;
  // CV Quality evaluation (/20)
  cv_quality_score: number | null;
  cv_quality: CvQuality | null;
  // Read state (separate from status)
  is_read: boolean;
  status: ApplicationStatus;
  status_display: string;
  notes: string | null;
  civility: string | null;
  boond_candidate_id: string | null;
  boond_sync_error: string | null;
  boond_synced_at: string | null;
  boond_sync_status: 'synced' | 'error' | 'pending' | 'not_applicable';
  status_history: StatusChange[];
  created_at: string;
  updated_at: string;
}

export interface JobApplicationListResponse {
  items: JobApplication[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApplicationSubmissionResult {
  success: boolean;
  message: string;
  application_id?: string;
}

export interface CvDownloadUrlResponse {
  url: string;
  filename: string;
  expires_in: number;
}
