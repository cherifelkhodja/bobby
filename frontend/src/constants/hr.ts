/**
 * HR domain constants shared across job posting pages.
 *
 * Single source of truth for contract types, remote policies,
 * experience levels, status badges, and filter options.
 */

import type { LucideIcon } from 'lucide-react';
import { Square, PanelRight, Columns, Layout } from 'lucide-react';

// --- Contract Types ---

export const CONTRACT_TYPES = [
  { value: 'PERMANENT', label: 'CDI' },
  { value: 'TEMPORARY', label: 'CDD' },
  { value: 'FREELANCE', label: 'Freelance' },
] as const;

/** Contract types that enable annual salary fields */
export const SALARY_CONTRACT_TYPES = ['PERMANENT', 'TEMPORARY'];

/** Contract types that enable TJM (daily rate) fields */
export const TJM_CONTRACT_TYPES = ['FREELANCE'];

/** Contract types that allow employee status in public forms */
export const EMPLOYEE_CONTRACT_TYPES = ['PERMANENT', 'FIXED-TERM'];

/** Contract types that allow freelance status in public forms */
export const FREELANCE_CONTRACT_TYPES = ['FREELANCE', 'INTERCONTRACT'];

/** Labels for contract types displayed in public pages */
export const CONTRACT_TYPE_LABELS: Record<string, string> = {
  PERMANENT: 'CDI',
  TEMPORARY: 'CDD',
  FREELANCE: 'Freelance',
};

// --- Remote Policies ---

export const REMOTE_POLICIES = [
  { value: 'NONE', label: 'Pas de télétravail' },
  { value: 'PARTIAL', label: 'Télétravail partiel' },
  { value: 'FULL', label: '100% télétravail' },
] as const;

export const REMOTE_LABELS: Record<string, string> = {
  NONE: 'Pas de télétravail',
  PARTIAL: 'Télétravail partiel',
  FULL: '100% télétravail',
};

// --- Experience Levels ---

export const EXPERIENCE_LEVELS = [
  { value: 'JUNIOR', label: 'Junior (0-2 ans)' },
  { value: 'INTERMEDIATE', label: 'Intermédiaire (2-5 ans)' },
  { value: 'SENIOR', label: 'Senior (5-10 ans)' },
  { value: 'EXPERT', label: 'Expert (+10 ans)' },
] as const;

export const EXPERIENCE_LABELS: Record<string, string> = {
  JUNIOR: 'Junior (0-2 ans)',
  INTERMEDIATE: 'Intermédiaire (2-5 ans)',
  SENIOR: 'Senior (5-10 ans)',
  EXPERT: 'Expert (+10 ans)',
};

// --- Job Posting Status ---

export const JOB_POSTING_STATUS_BADGES = {
  draft: {
    label: 'Brouillon',
    color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
  },
  published: {
    label: 'Publiée',
    color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  },
  closed: {
    label: 'Fermée',
    color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  },
} as const;

// --- Filter Options (for JobPostingDetails) ---

export const EMPLOYMENT_STATUS_OPTIONS = [
  { value: '', label: 'Tous statuts pro' },
  { value: 'freelance', label: 'Freelance' },
  { value: 'employee', label: 'Salarié' },
] as const;

export const AVAILABILITY_FILTER_OPTIONS = [
  { value: '', label: 'Toutes dispos' },
  { value: 'asap', label: 'ASAP' },
  { value: '1_month', label: 'Sous 1 mois' },
  { value: '2_months', label: 'Sous 2 mois' },
  { value: '3_months', label: 'Sous 3 mois' },
  { value: 'more_3_months', label: '+3 mois' },
] as const;

export const SORT_OPTIONS = [
  { value: 'score', label: 'Score matching' },
  { value: 'tjm', label: 'TJM' },
  { value: 'salary', label: 'Salaire' },
  { value: 'date', label: 'Date candidature' },
] as const;

// --- Public Application Form Options ---

export const AVAILABILITY_OPTIONS = [
  { value: 'asap', label: 'ASAP (immédiat)' },
  { value: '1_month', label: 'Sous 1 mois' },
  { value: '2_months', label: 'Sous 2 mois' },
  { value: '3_months', label: 'Sous 3 mois' },
  { value: 'more_3_months', label: 'Plus de 3 mois' },
] as const;

export const ENGLISH_LEVELS = [
  {
    value: 'notions',
    label: 'Notions',
    description: 'Vocabulaire basique, phrases simples. Peut comprendre des consignes écrites.',
  },
  {
    value: 'intermediate',
    label: 'Intermédiaire (B1)',
    description: 'Peut comprendre les points essentiels et se débrouiller dans la plupart des situations.',
  },
  {
    value: 'professional',
    label: 'Professionnel (B2)',
    description: 'Peut communiquer avec aisance dans un contexte professionnel. Réunions, emails, présentations.',
  },
  {
    value: 'fluent',
    label: 'Courant (C1)',
    description: 'Expression fluide et spontanée. Peut utiliser la langue de façon efficace en contexte social et professionnel.',
  },
  {
    value: 'bilingual',
    label: 'Bilingue (C2)',
    description: "Maîtrise parfaite équivalente à un natif. Peut comprendre et s'exprimer sans effort.",
  },
] as const;

// --- CV Quality Labels ---

export const EXPERIENCE_LEVEL_LABELS: Record<string, string> = {
  JUNIOR: 'Junior',
  CONFIRME: 'Confirmé',
  SENIOR: 'Senior',
};

export const CLASSIFICATION_LABELS: Record<string, string> = {
  EXCELLENT: 'Excellent',
  BON: 'Bon',
  MOYEN: 'Moyen',
  FAIBLE: 'Faible',
};

// --- Display Modes ---

export type DisplayMode = 'modal' | 'drawer' | 'split' | 'inline';

export const DISPLAY_MODE_OPTIONS: { value: DisplayMode; label: string; icon: LucideIcon }[] = [
  { value: 'modal', label: 'Pop-up', icon: Square },
  { value: 'drawer', label: 'Panel latéral', icon: PanelRight },
  { value: 'split', label: 'Vue split', icon: Columns },
  { value: 'inline', label: 'Expansion', icon: Layout },
];
