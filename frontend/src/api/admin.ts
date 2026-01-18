import { apiClient } from './client';
import type { User, UserRole, Invitation, CreateInvitationRequest, AcceptInvitationRequest, InvitationValidation, BoondResource } from '../types';

export interface BoondStatus {
  connected: boolean;
  configured: boolean;
  api_url: string;
  last_sync: string | null;
  opportunities_count: number;
  error: string | null;
}

export interface SyncResponse {
  success: boolean;
  synced_count: number;
  message: string;
}

export interface TestConnectionResponse {
  success: boolean;
  status_code: number;
  message: string;
  candidates_count: number | null;
}

export interface BoondResourcesListResponse {
  resources: BoondResource[];
  total: number;
}

export interface UsersListResponse {
  users: User[];
  total: number;
}

export interface InvitationsListResponse {
  invitations: Invitation[];
  total: number;
}

export interface UpdateUserRequest {
  first_name?: string;
  last_name?: string;
  phone?: string | null;
  is_active?: boolean;
  role?: UserRole;
  boond_resource_id?: string | null;
  manager_boond_id?: string | null;
}

export interface GeminiSettings {
  current_model: string;
  available_models: string[];
  default_model: string;
}

export interface GeminiTestResponse {
  success: boolean;
  model: string;
  response_time_ms: number;
  message: string;
}

export interface TurnoverITSkill {
  name: string;
  slug: string;
}

export interface TurnoverITSkillsResponse {
  skills: TurnoverITSkill[];
  total: number;
  last_synced_at: string | null;
  sync_interval_days: number;
}

export interface TurnoverITSyncResponse {
  success: boolean;
  synced_count: number;
  message: string;
}

export const adminApi = {
  // BoondManager
  getBoondStatus: async (): Promise<BoondStatus> => {
    const response = await apiClient.get<BoondStatus>('/admin/boond/status');
    return response.data;
  },

  triggerSync: async (): Promise<SyncResponse> => {
    const response = await apiClient.post<SyncResponse>('/admin/boond/sync');
    return response.data;
  },

  testConnection: async (): Promise<TestConnectionResponse> => {
    const response = await apiClient.post<TestConnectionResponse>('/admin/boond/test');
    return response.data;
  },

  getBoondResources: async (): Promise<BoondResourcesListResponse> => {
    const response = await apiClient.get<BoondResourcesListResponse>('/admin/boond/resources');
    return response.data;
  },

  // Users management
  getUsers: async (skip = 0, limit = 50): Promise<UsersListResponse> => {
    const response = await apiClient.get<UsersListResponse>('/admin/users', {
      params: { skip, limit },
    });
    return response.data;
  },

  getUser: async (userId: string): Promise<User> => {
    const response = await apiClient.get<User>(`/admin/users/${userId}`);
    return response.data;
  },

  updateUser: async (userId: string, data: UpdateUserRequest): Promise<User> => {
    const response = await apiClient.patch<User>(`/admin/users/${userId}`, data);
    return response.data;
  },

  changeUserRole: async (userId: string, role: UserRole): Promise<User> => {
    const response = await apiClient.post<User>(`/admin/users/${userId}/role`, { role });
    return response.data;
  },

  activateUser: async (userId: string): Promise<void> => {
    await apiClient.post(`/admin/users/${userId}/activate`);
  },

  deactivateUser: async (userId: string): Promise<void> => {
    await apiClient.post(`/admin/users/${userId}/deactivate`);
  },

  deleteUser: async (userId: string): Promise<void> => {
    await apiClient.delete(`/admin/users/${userId}`);
  },

  // Invitations
  getInvitations: async (skip = 0, limit = 50): Promise<InvitationsListResponse> => {
    const response = await apiClient.get<InvitationsListResponse>('/invitations', {
      params: { skip, limit },
    });
    return response.data;
  },

  createInvitation: async (data: CreateInvitationRequest): Promise<Invitation> => {
    const response = await apiClient.post<Invitation>('/invitations', data);
    return response.data;
  },

  validateInvitation: async (token: string): Promise<InvitationValidation> => {
    const response = await apiClient.get<InvitationValidation>(`/invitations/validate/${token}`);
    return response.data;
  },

  acceptInvitation: async (data: AcceptInvitationRequest): Promise<User> => {
    const response = await apiClient.post<User>('/invitations/accept', data);
    return response.data;
  },

  resendInvitation: async (invitationId: string): Promise<Invitation> => {
    const response = await apiClient.post<Invitation>(`/invitations/${invitationId}/resend`);
    return response.data;
  },

  deleteInvitation: async (invitationId: string): Promise<void> => {
    await apiClient.delete(`/invitations/${invitationId}`);
  },

  // Gemini settings
  getGeminiSettings: async (): Promise<GeminiSettings> => {
    const response = await apiClient.get<GeminiSettings>('/admin/gemini/settings');
    return response.data;
  },

  setGeminiModel: async (model: string): Promise<GeminiSettings> => {
    const response = await apiClient.post<GeminiSettings>('/admin/gemini/settings', { model });
    return response.data;
  },

  testGeminiModel: async (model: string): Promise<GeminiTestResponse> => {
    const response = await apiClient.post<GeminiTestResponse>('/admin/gemini/test', { model });
    return response.data;
  },

  // Turnover-IT skills
  getTurnoverITSkills: async (search?: string): Promise<TurnoverITSkillsResponse> => {
    const response = await apiClient.get<TurnoverITSkillsResponse>('/admin/turnoverit/skills', {
      params: search ? { search } : undefined,
    });
    return response.data;
  },

  syncTurnoverITSkills: async (): Promise<TurnoverITSyncResponse> => {
    const response = await apiClient.post<TurnoverITSyncResponse>('/admin/turnoverit/skills/sync');
    return response.data;
  },
};
