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
  is_published: boolean;
}

export interface BoondOpportunityListResponse {
  items: BoondOpportunity[];
  total: number;
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

export interface PublishedOpportunityListResponse {
  items: PublishedOpportunity[];
  total: number;
  page: number;
  page_size: number;
}
