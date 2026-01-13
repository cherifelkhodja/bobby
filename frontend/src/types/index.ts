// User types
export type UserRole = 'user' | 'commercial' | 'admin';

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: UserRole;
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
  invited_by: string;
  expires_at: string;
  is_expired: boolean;
  is_accepted: boolean;
  created_at: string;
}

export interface InvitationValidation {
  email: string;
  role: string;
  is_valid: boolean;
  hours_until_expiry: number;
}

export interface CreateInvitationRequest {
  email: string;
  role: UserRole;
}

export interface AcceptInvitationRequest {
  token: string;
  first_name: string;
  last_name: string;
  password: string;
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
