import axios from 'axios';
import type { AcceptInvitationRequest, InvitationValidation, User } from '../types';

const API_URL = import.meta.env.VITE_API_URL || '';

// Client sans auth pour les endpoints publics
const publicClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const invitationsApi = {
  /**
   * Validate an invitation token (public endpoint)
   */
  validateToken: async (token: string): Promise<InvitationValidation> => {
    const response = await publicClient.get<InvitationValidation>(
      `/invitations/validate/${token}`
    );
    return response.data;
  },

  /**
   * Accept an invitation and create user account (public endpoint)
   */
  acceptInvitation: async (data: AcceptInvitationRequest): Promise<User> => {
    const response = await publicClient.post<User>('/invitations/accept', data);
    return response.data;
  },
};
