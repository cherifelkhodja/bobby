/**
 * CreateJobPosting - Page to create a job posting from an opportunity.
 */

import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  ChevronLeft,
  Loader2,
  AlertCircle,
  Building2,
  MapPin,
  Briefcase,
  Calendar,
  Plus,
  X,
} from 'lucide-react';
import { hrApi } from '../api/hr';
import type { CreateJobPostingRequest } from '../types';

// Validation schema
const createJobPostingSchema = z.object({
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
  location_country: z.string().min(1, 'Le pays est requis'),
  location_region: z.string().optional(),
  location_postal_code: z.string().optional(),
  location_city: z.string().optional(),
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

type CreateJobPostingFormData = z.infer<typeof createJobPostingSchema>;

const CONTRACT_TYPES = [
  { value: 'CDI', label: 'CDI' },
  { value: 'CDD', label: 'CDD' },
  { value: 'FREELANCE', label: 'Freelance' },
  { value: 'INTERIM', label: 'Intérim' },
  { value: 'STAGE', label: 'Stage' },
  { value: 'ALTERNANCE', label: 'Alternance' },
];

const REMOTE_POLICIES = [
  { value: 'NONE', label: 'Pas de télétravail' },
  { value: 'PARTIAL', label: 'Télétravail partiel' },
  { value: 'FULL', label: '100% télétravail' },
];

const EXPERIENCE_LEVELS = [
  { value: 'JUNIOR', label: 'Junior (0-2 ans)' },
  { value: 'INTERMEDIATE', label: 'Intermédiaire (2-5 ans)' },
  { value: 'SENIOR', label: 'Senior (5-10 ans)' },
  { value: 'EXPERT', label: 'Expert (+10 ans)' },
];

export default function CreateJobPosting() {
  const { oppId } = useParams<{ oppId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState('');
  const [selectedContractTypes, setSelectedContractTypes] = useState<string[]>(['FREELANCE']);

  // Fetch opportunities to find the current one
  const { data: opportunitiesData, isLoading: loadingOpps } = useQuery({
    queryKey: ['hr-opportunities'],
    queryFn: () => hrApi.getOpportunities({ page_size: 1000 }),
    enabled: !!oppId,
  });

  const opportunity = opportunitiesData?.items.find((o) => o.id === oppId);

  // Form setup
  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<CreateJobPostingFormData>({
    resolver: zodResolver(createJobPostingSchema),
    defaultValues: {
      title: '',
      description: '',
      qualifications: '',
      location_country: 'France',
      location_region: '',
      location_city: '',
      employer_overview: '',
    },
  });

  const titleWatch = watch('title');
  const descriptionWatch = watch('description');
  const qualificationsWatch = watch('qualifications');

  // Initialize form with opportunity data when loaded
  // Note: We use defaultValues but they don't update after mount
  // So we'll display opportunity info separately

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async (data: CreateJobPostingFormData) => {
      if (!oppId) throw new Error('ID opportunité manquant');
      if (selectedContractTypes.length === 0) {
        throw new Error('Sélectionnez au moins un type de contrat');
      }

      const request: CreateJobPostingRequest = {
        opportunity_id: oppId,
        title: data.title,
        description: data.description,
        qualifications: data.qualifications,
        location_country: data.location_country,
        location_region: data.location_region || undefined,
        location_postal_code: data.location_postal_code || undefined,
        location_city: data.location_city || undefined,
        contract_types: selectedContractTypes,
        skills: selectedSkills,
        experience_level: data.experience_level || undefined,
        remote: data.remote || undefined,
        start_date: data.start_date || undefined,
        duration_months: typeof data.duration_months === 'number' ? data.duration_months : undefined,
        salary_min_annual:
          typeof data.salary_min_annual === 'number' ? data.salary_min_annual : undefined,
        salary_max_annual:
          typeof data.salary_max_annual === 'number' ? data.salary_max_annual : undefined,
        salary_min_daily:
          typeof data.salary_min_daily === 'number' ? data.salary_min_daily : undefined,
        salary_max_daily:
          typeof data.salary_max_daily === 'number' ? data.salary_max_daily : undefined,
        employer_overview: data.employer_overview || undefined,
      };

      return hrApi.createJobPosting(request);
    },
    onSuccess: (posting) => {
      queryClient.invalidateQueries({ queryKey: ['hr-opportunities'] });
      queryClient.invalidateQueries({ queryKey: ['hr-job-postings'] });
      navigate(`/rh?posting=${posting.id}`);
    },
  });

  const onSubmit = (data: CreateJobPostingFormData) => {
    createMutation.mutate(data);
  };

  const addSkill = () => {
    const skill = skillInput.trim();
    if (skill && !selectedSkills.includes(skill)) {
      setSelectedSkills([...selectedSkills, skill]);
      setSkillInput('');
    }
  };

  const removeSkill = (skill: string) => {
    setSelectedSkills(selectedSkills.filter((s) => s !== skill));
  };

  const toggleContractType = (type: string) => {
    setSelectedContractTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  // Initialize skills from opportunity when data loads
  if (opportunity?.skills && selectedSkills.length === 0 && opportunity.skills.length > 0) {
    setSelectedSkills([...opportunity.skills]);
  }

  if (loadingOpps) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <p className="ml-2 text-gray-600 dark:text-gray-400">Chargement...</p>
      </div>
    );
  }

  if (!opportunity) {
    return (
      <div className="space-y-6">
        <Link
          to="/rh"
          className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline"
        >
          <ChevronLeft className="h-5 w-5" />
          Retour
        </Link>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400 flex-shrink-0" />
            <div>
              <h3 className="font-semibold text-red-800 dark:text-red-300">Erreur</h3>
              <p className="text-red-700 dark:text-red-400">
                Opportunité non trouvée. Veuillez réessayer.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          to="/rh"
          className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline mb-4"
        >
          <ChevronLeft className="h-5 w-5" />
          Retour aux opportunités
        </Link>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Créer une annonce</h1>
        <p className="mt-1 text-gray-600 dark:text-gray-400">
          Remplissez les détails pour publier cette opportunité sur Turnover-IT
        </p>
      </div>

      {/* Opportunity Info Card */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
        <h2 className="font-semibold text-blue-900 dark:text-blue-100 mb-4">
          Opportunité source
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="flex items-start gap-3">
            <Briefcase className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-blue-600 dark:text-blue-400">Titre</p>
              <p className="font-medium text-blue-900 dark:text-blue-100">{opportunity.title}</p>
            </div>
          </div>
          {opportunity.client_name && (
            <div className="flex items-start gap-3">
              <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-blue-600 dark:text-blue-400">Client</p>
                <p className="font-medium text-blue-900 dark:text-blue-100">
                  {opportunity.client_name}
                </p>
              </div>
            </div>
          )}
          {opportunity.location && (
            <div className="flex items-start gap-3">
              <MapPin className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-blue-600 dark:text-blue-400">Localisation</p>
                <p className="font-medium text-blue-900 dark:text-blue-100">
                  {opportunity.location}
                </p>
              </div>
            </div>
          )}
          {opportunity.start_date && (
            <div className="flex items-start gap-3">
              <Calendar className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-blue-600 dark:text-blue-400">Date début</p>
                <p className="font-medium text-blue-900 dark:text-blue-100">
                  {new Date(opportunity.start_date).toLocaleDateString('fr-FR')}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
        {/* Basic Info */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-3">
            Informations principales
          </h3>

          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Titre de l'annonce *
            </label>
            <input
              type="text"
              {...register('title')}
              placeholder="Ex: Développeur Senior React/Node.js"
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <div className="mt-2 flex justify-between">
              {errors.title && (
                <p className="text-sm text-red-600 dark:text-red-400">{errors.title.message}</p>
              )}
              <p className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
                {titleWatch?.length || 0}/100
              </p>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Description du poste *
            </label>
            <textarea
              {...register('description')}
              placeholder="Décrivez les missions, responsabilités et contexte du poste..."
              rows={8}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <div className="mt-2 flex justify-between">
              {errors.description && (
                <p className="text-sm text-red-600 dark:text-red-400">
                  {errors.description.message}
                </p>
              )}
              <p className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
                {descriptionWatch?.length || 0}/3000 (min 500)
              </p>
            </div>
          </div>

          {/* Qualifications */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Profil recherché *
            </label>
            <textarea
              {...register('qualifications')}
              placeholder="Décrivez le profil idéal, les compétences requises, expérience attendue..."
              rows={6}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <div className="mt-2 flex justify-between">
              {errors.qualifications && (
                <p className="text-sm text-red-600 dark:text-red-400">
                  {errors.qualifications.message}
                </p>
              )}
              <p className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
                {qualificationsWatch?.length || 0}/3000 (min 150)
              </p>
            </div>
          </div>
        </div>

        {/* Location */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-3">
            Localisation
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Pays *
              </label>
              <input
                type="text"
                {...register('location_country')}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {errors.location_country && (
                <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                  {errors.location_country.message}
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Région/Département
              </label>
              <input
                type="text"
                {...register('location_region')}
                placeholder="Île-de-France, Provence..."
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Ville
              </label>
              <input
                type="text"
                {...register('location_city')}
                placeholder="Paris, Lyon..."
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Code postal
              </label>
              <input
                type="text"
                {...register('location_postal_code')}
                placeholder="75001"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Contract & Work */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-3">
            Contrat et conditions
          </h3>

          {/* Contract Types */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Types de contrat *
            </label>
            <div className="flex flex-wrap gap-2">
              {CONTRACT_TYPES.map((type) => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => toggleContractType(type.value)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    selectedContractTypes.includes(type.value)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {type.label}
                </button>
              ))}
            </div>
            {selectedContractTypes.length === 0 && (
              <p className="text-sm text-red-600 dark:text-red-400 mt-2">
                Sélectionnez au moins un type de contrat
              </p>
            )}
          </div>

          {/* Remote Policy */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Mode de travail
            </label>
            <select
              {...register('remote')}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">-- Sélectionner --</option>
              {REMOTE_POLICIES.map((policy) => (
                <option key={policy.value} value={policy.value}>
                  {policy.label}
                </option>
              ))}
            </select>
          </div>

          {/* Experience Level */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Niveau d'expérience
            </label>
            <select
              {...register('experience_level')}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">-- Sélectionner --</option>
              {EXPERIENCE_LEVELS.map((level) => (
                <option key={level.value} value={level.value}>
                  {level.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Skills */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-3">
            Compétences techniques
          </h3>

          <div className="flex gap-2">
            <input
              type="text"
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addSkill();
                }
              }}
              placeholder="Ajouter une compétence (React, Java, AWS...)"
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              type="button"
              onClick={addSkill}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors inline-flex items-center gap-1"
            >
              <Plus className="h-4 w-4" />
              Ajouter
            </button>
          </div>

          {selectedSkills.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-2">
              {selectedSkills.map((skill) => (
                <span
                  key={skill}
                  className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 rounded-full text-sm flex items-center gap-2"
                >
                  {skill}
                  <button
                    type="button"
                    onClick={() => removeSkill(skill)}
                    className="hover:text-blue-600 dark:hover:text-blue-400"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Dates & Duration */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-3">
            Dates et durée
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Date de début souhaitée
              </label>
              <input
                type="date"
                {...register('start_date')}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Durée (mois)
              </label>
              <input
                type="number"
                {...register('duration_months')}
                placeholder="6"
                min={1}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Salary */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-3">
            Rémunération
          </h3>

          <p className="text-sm text-gray-600 dark:text-gray-400 -mt-2">
            Renseignez les salaires annuels (CDI/CDD) et/ou les TJM (freelance)
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Salaire minimum annuel (€)
              </label>
              <input
                type="number"
                {...register('salary_min_annual')}
                placeholder="35000"
                min={0}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Salaire maximum annuel (€)
              </label>
              <input
                type="number"
                {...register('salary_max_annual')}
                placeholder="50000"
                min={0}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                TJM minimum (€/jour)
              </label>
              <input
                type="number"
                {...register('salary_min_daily')}
                placeholder="400"
                min={0}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                TJM maximum (€/jour)
              </label>
              <input
                type="number"
                {...register('salary_max_daily')}
                placeholder="550"
                min={0}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Employer Overview */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              À propos de l'entreprise
            </label>
            <textarea
              {...register('employer_overview')}
              placeholder="Présentez brièvement votre entreprise, sa culture, ses valeurs..."
              rows={4}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Error Message */}
        {createMutation.isError && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0" />
              <p className="text-red-800 dark:text-red-200">
                {createMutation.error instanceof Error
                  ? createMutation.error.message
                  : "Erreur lors de la création de l'annonce"}
              </p>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={createMutation.isPending || selectedContractTypes.length === 0}
            className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {createMutation.isPending ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Création en cours...
              </>
            ) : (
              'Créer le brouillon'
            )}
          </button>
          <Link
            to="/rh"
            className="px-6 py-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white font-medium rounded-lg transition-colors text-center"
          >
            Annuler
          </Link>
        </div>
      </form>
    </div>
  );
}
