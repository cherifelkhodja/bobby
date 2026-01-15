/**
 * Admin module constants and type definitions.
 */

import type { UserRole } from '../../types';

export const ROLE_LABELS: Record<UserRole, string> = {
  user: 'Utilisateur',
  commercial: 'Commercial',
  rh: 'RH',
  admin: 'Administrateur',
};

export const ROLE_COLORS: Record<UserRole, 'default' | 'primary' | 'success' | 'warning' | 'error'> = {
  user: 'default',
  commercial: 'primary',
  rh: 'success',
  admin: 'warning',
};

export const STATE_NAMES: Record<number, string> = {
  0: 'Sortie',
  1: 'En cours',
  2: 'Intercontrat',
  3: 'Arrivée prochaine',
  7: 'Sortie prochaine',
};

export const PREDEFINED_TEMPLATES = [
  { name: 'gemini', displayName: 'Template Gemini', description: 'Format standard Gemini Consulting' },
  { name: 'craftmania', displayName: 'Template Craftmania', description: 'Format standard Craftmania' },
] as const;

export const QUOTATION_TEMPLATES = [
  { name: 'thales_pstf', displayName: 'Template Thales PSTF', description: 'Devis Prestation de Service Thales' },
] as const;
