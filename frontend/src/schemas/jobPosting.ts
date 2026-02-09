/**
 * Shared Zod validation schema for job posting create/edit forms.
 */

import { z } from 'zod';

export const jobPostingSchema = z.object({
  title: z
    .string()
    .min(5, 'Le titre doit contenir au moins 5 caractères')
    .max(100, 'Le titre ne peut pas dépasser 100 caractères'),
  description: z
    .string()
    .min(500, 'La description doit contenir au moins 500 caractères')
    .max(3000, 'La description ne peut pas dépasser 3000 caractères'),
  qualifications: z
    .string()
    .min(150, 'Les qualifications doivent contenir au moins 150 caractères')
    .max(3000, 'Les qualifications ne peuvent pas dépasser 3000 caractères'),
  experience_level: z.string().optional(),
  remote: z.string().optional(),
  start_date: z.string().optional(),
  duration_months: z.coerce.number().int().positive().optional().or(z.literal('')),
  salary_min_annual: z.coerce.number().positive().optional().or(z.literal('')),
  salary_max_annual: z.coerce.number().positive().optional().or(z.literal('')),
  salary_min_daily: z.coerce.number().positive().optional().or(z.literal('')),
  salary_max_daily: z.coerce.number().positive().optional().or(z.literal('')),
  employer_overview: z.string().optional(),
});

export type JobPostingFormData = z.infer<typeof jobPostingSchema>;
