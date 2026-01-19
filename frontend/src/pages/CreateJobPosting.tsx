/**
 * CreateJobPosting - Page to create a job posting from an opportunity.
 *
 * Flow:
 * 1. Load opportunity detail from BoondManager
 * 2. User clicks "Anonymiser avec l'IA"
 * 3. AI anonymizes content and extracts skills
 * 4. User reviews/edits the anonymized content
 * 5. User saves as draft
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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
  X,
  Sparkles,
  RefreshCw,
  FileText,
  Search,
} from 'lucide-react';
import {
  hrApi,
  type OpportunityDetailResponse,
  type AnonymizedJobPostingResponse,
  type TurnoverITSkill,
} from '../api/hr';
import { getErrorMessage } from '../api/client';
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

type ViewStep = 'loading' | 'ready' | 'anonymizing' | 'form' | 'saving' | 'error';

const CONTRACT_TYPES = [
  { value: 'CDI', label: 'CDI' },
  { value: 'CDD', label: 'CDD' },
  { value: 'FREELANCE', label: 'Freelance' },
  { value: 'INTERCONTRACT', label: 'Sous-traitance' },
];

// Contract types that enable salary fields (annual)
const SALARY_CONTRACT_TYPES = ['CDI', 'CDD'];
// Contract types that enable TJM fields (daily rate)
const TJM_CONTRACT_TYPES = ['FREELANCE', 'INTERCONTRACT'];

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

  const [step, setStep] = useState<ViewStep>('loading');
  const [opportunity, setOpportunity] = useState<OpportunityDetailResponse | null>(null);
  const [anonymizedData, setAnonymizedData] = useState<AnonymizedJobPostingResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [skillSearch, setSkillSearch] = useState('');
  const [showSkillDropdown, setShowSkillDropdown] = useState(false);
  const [selectedContractTypes, setSelectedContractTypes] = useState<string[]>(['FREELANCE']);
  const [isAsap, setIsAsap] = useState(false);
  const [durationUnit, setDurationUnit] = useState<'months' | 'years'>('months');
  const [durationValue, setDurationValue] = useState<number | ''>('');
  const skillInputRef = useRef<HTMLInputElement>(null);
  const skillDropdownRef = useRef<HTMLDivElement>(null);

  // Check if salary fields should be enabled (CDI, CDD, Intérim selected)
  const hasSalaryContractType = selectedContractTypes.some((type) =>
    SALARY_CONTRACT_TYPES.includes(type)
  );
  // Check if TJM fields should be enabled (Freelance, Sous-traitance selected)
  const hasTjmContractType = selectedContractTypes.some((type) =>
    TJM_CONTRACT_TYPES.includes(type)
  );

  // Form setup
  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    reset,
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

  // Fetch Turnover-IT skills for autocomplete
  const { data: skillsData } = useQuery({
    queryKey: ['turnoverit-skills', skillSearch],
    queryFn: () => hrApi.getSkills(skillSearch || undefined),
    enabled: showSkillDropdown && skillSearch.length >= 1,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Filter out already selected skills
  const filteredSkills = skillsData?.skills.filter(
    (skill) => !selectedSkills.includes(skill.slug)
  ) ?? [];

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        skillDropdownRef.current &&
        !skillDropdownRef.current.contains(event.target as Node) &&
        skillInputRef.current &&
        !skillInputRef.current.contains(event.target as Node)
      ) {
        setShowSkillDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Load opportunity detail on mount
  useEffect(() => {
    if (!oppId) {
      setErrorMessage('ID opportunité manquant');
      setStep('error');
      return;
    }

    const loadOpportunity = async () => {
      try {
        const detail = await hrApi.getOpportunityDetail(oppId);
        setOpportunity(detail);
        setStep('ready');
      } catch (error) {
        setErrorMessage(getErrorMessage(error));
        setStep('error');
      }
    };

    loadOpportunity();
  }, [oppId]);

  // Anonymize mutation
  const anonymizeMutation = useMutation({
    mutationFn: async () => {
      if (!opportunity) throw new Error('Opportunité non chargée');

      // Build full description from description + criteria
      const fullDescription = [opportunity.description, opportunity.criteria]
        .filter(Boolean)
        .join('\n\nCritères:\n');

      return hrApi.anonymizeJobPosting({
        opportunity_id: opportunity.id,
        title: opportunity.title,
        description: fullDescription,
        client_name: opportunity.company_name,
      });
    },
    onSuccess: (result) => {
      setAnonymizedData(result);

      // Pre-fill form with anonymized data
      reset({
        title: result.title,
        description: result.description,
        qualifications: result.qualifications,
        location_country: 'France',
        location_region: opportunity?.place || '',
        location_city: '',
        employer_overview: '',
      });

      // Set skills
      setSelectedSkills(result.skills);

      setStep('form');
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error));
      setStep('error');
    },
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async (data: CreateJobPostingFormData) => {
      if (!oppId) throw new Error('ID opportunité manquant');
      if (selectedContractTypes.length === 0) {
        throw new Error('Sélectionnez au moins un type de contrat');
      }

      // Calculate start date: today if ASAP, otherwise form value
      let startDate: string | undefined;
      if (isAsap) {
        startDate = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format
      } else {
        startDate = data.start_date || undefined;
      }

      // Calculate duration in months (convert from years if needed)
      let durationMonths: number | undefined;
      if (typeof durationValue === 'number' && durationValue > 0) {
        durationMonths = durationUnit === 'years' ? durationValue * 12 : durationValue;
      }

      // Only include salary fields if salary contract types are selected
      const salaryMinAnnual = hasSalaryContractType && typeof data.salary_min_annual === 'number'
        ? data.salary_min_annual
        : undefined;
      const salaryMaxAnnual = hasSalaryContractType && typeof data.salary_max_annual === 'number'
        ? data.salary_max_annual
        : undefined;

      // Only include TJM fields if TJM contract types are selected
      const salaryMinDaily = hasTjmContractType && typeof data.salary_min_daily === 'number'
        ? data.salary_min_daily
        : undefined;
      const salaryMaxDaily = hasTjmContractType && typeof data.salary_max_daily === 'number'
        ? data.salary_max_daily
        : undefined;

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
        start_date: startDate,
        duration_months: durationMonths,
        salary_min_annual: salaryMinAnnual,
        salary_max_annual: salaryMaxAnnual,
        salary_min_daily: salaryMinDaily,
        salary_max_daily: salaryMaxDaily,
        employer_overview: data.employer_overview || undefined,
      };

      return hrApi.createJobPosting(request);
    },
    onSuccess: (posting) => {
      queryClient.invalidateQueries({ queryKey: ['hr-opportunities'] });
      queryClient.invalidateQueries({ queryKey: ['hr-job-postings'] });
      navigate(`/rh/annonces/${posting.id}`);
    },
  });

  const handleAnonymize = () => {
    setStep('anonymizing');
    setErrorMessage(null);
    anonymizeMutation.mutate();
  };

  const handleRegenerate = () => {
    setStep('anonymizing');
    setErrorMessage(null);
    anonymizeMutation.mutate();
  };

  const onSubmit = (data: CreateJobPostingFormData) => {
    setStep('saving');
    createMutation.mutate(data);
  };

  const selectSkill = useCallback((skill: TurnoverITSkill) => {
    if (!selectedSkills.includes(skill.slug)) {
      setSelectedSkills([...selectedSkills, skill.slug]);
    }
    setSkillSearch('');
    setShowSkillDropdown(false);
    skillInputRef.current?.focus();
  }, [selectedSkills]);

  const removeSkill = (slug: string) => {
    setSelectedSkills(selectedSkills.filter((s) => s !== slug));
  };

  const toggleContractType = (type: string) => {
    setSelectedContractTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  // Loading state
  if (step === 'loading') {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <p className="ml-2 text-gray-600 dark:text-gray-400">
          Chargement de l'opportunité...
        </p>
      </div>
    );
  }

  // Error state
  if (step === 'error') {
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
                {errorMessage || 'Une erreur est survenue'}
              </p>
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <Link
              to="/rh"
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg transition-colors"
            >
              Retour aux opportunités
            </Link>
            {opportunity && (
              <button
                onClick={handleRegenerate}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors inline-flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Réessayer
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Ready state - show opportunity info and anonymize button
  if (step === 'ready' && opportunity) {
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
            L'IA va anonymiser et structurer le contenu pour Turnover-IT
          </p>
        </div>

        {/* Opportunity Info Card */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
          <h2 className="font-semibold text-blue-900 dark:text-blue-100 mb-4">
            Opportunité source
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="flex items-start gap-3">
              <Briefcase className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-blue-600 dark:text-blue-400">Titre</p>
                <p className="font-medium text-blue-900 dark:text-blue-100">{opportunity.title}</p>
              </div>
            </div>
            {opportunity.company_name && (
              <div className="flex items-start gap-3">
                <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-blue-600 dark:text-blue-400">Client</p>
                  <p className="font-medium text-blue-900 dark:text-blue-100">
                    {opportunity.company_name}
                  </p>
                </div>
              </div>
            )}
            {opportunity.state_name && (
              <div className="flex items-start gap-3">
                <MapPin className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-blue-600 dark:text-blue-400">État</p>
                  <p className="font-medium text-blue-900 dark:text-blue-100">
                    {opportunity.state_name}
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

          {/* Original content preview */}
          {(opportunity.description || opportunity.criteria) && (
            <div className="mt-4 pt-4 border-t border-blue-200 dark:border-blue-700">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                <p className="text-sm font-medium text-blue-700 dark:text-blue-300">
                  Contenu original (sera anonymisé)
                </p>
              </div>
              <div className="max-h-48 overflow-y-auto text-sm text-blue-800 dark:text-blue-200 bg-blue-100/50 dark:bg-blue-900/50 p-3 rounded-md whitespace-pre-wrap">
                {opportunity.description}
                {opportunity.criteria && (
                  <>
                    {'\n\n'}
                    <strong>Critères:</strong>
                    {'\n'}
                    {opportunity.criteria}
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex gap-3">
          <button
            onClick={handleAnonymize}
            className="flex-1 px-6 py-4 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-medium rounded-lg transition-all flex items-center justify-center gap-3 shadow-lg hover:shadow-xl"
          >
            <Sparkles className="h-5 w-5" />
            Anonymiser avec l'IA
          </button>
          <Link
            to="/rh"
            className="px-6 py-4 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white font-medium rounded-lg transition-colors text-center"
          >
            Annuler
          </Link>
        </div>
      </div>
    );
  }

  // Anonymizing state
  if (step === 'anonymizing') {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <div className="relative">
          <Loader2 className="h-16 w-16 animate-spin text-purple-500" />
          <Sparkles className="h-6 w-6 text-yellow-500 absolute -top-1 -right-1 animate-pulse" />
        </div>
        <p className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
          L'IA anonymise l'opportunité...
        </p>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Structuration selon le format Turnover-IT
        </p>
      </div>
    );
  }

  // Form state (after anonymization)
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
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Prévisualisation</h1>
          <span className="px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-sm rounded-full">
            Anonymisé
          </span>
        </div>
        <p className="mt-1 text-gray-600 dark:text-gray-400">
          Vérifiez et ajustez le contenu avant de créer le brouillon
        </p>
      </div>

      {/* Regenerate button */}
      <div className="flex justify-end">
        <button
          onClick={handleRegenerate}
          disabled={anonymizeMutation.isPending}
          className="px-4 py-2 bg-purple-100 dark:bg-purple-900/30 hover:bg-purple-200 dark:hover:bg-purple-900/50 text-purple-700 dark:text-purple-400 rounded-lg transition-colors inline-flex items-center gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${anonymizeMutation.isPending ? 'animate-spin' : ''}`} />
          Régénérer
        </button>
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
              placeholder="Ex: Développeur Senior React/Node.js (H/F)"
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
              rows={10}
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

        {/* Skills - Pre-filled from AI */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 pb-3">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Compétences techniques
            </h3>
            {anonymizedData && anonymizedData.skills.length > 0 && (
              <span className="text-sm text-green-600 dark:text-green-400">
                {anonymizedData.skills.length} extraites par l'IA
              </span>
            )}
          </div>

          {/* Skill autocomplete */}
          <div className="relative">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                ref={skillInputRef}
                type="text"
                value={skillSearch}
                onChange={(e) => {
                  setSkillSearch(e.target.value);
                  setShowSkillDropdown(true);
                }}
                onFocus={() => setShowSkillDropdown(true)}
                placeholder="Rechercher une compétence Turnover-IT..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Dropdown */}
            {showSkillDropdown && skillSearch.length >= 1 && (
              <div
                ref={skillDropdownRef}
                className="absolute z-10 mt-1 w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto"
              >
                {filteredSkills.length === 0 ? (
                  <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {skillsData?.total === 0
                      ? 'Aucune compétence trouvée. Vérifiez la synchronisation des skills.'
                      : 'Aucune compétence correspondante'}
                  </div>
                ) : (
                  filteredSkills.map((skill) => (
                    <button
                      key={skill.slug}
                      type="button"
                      onClick={() => selectSkill(skill)}
                      className="w-full px-4 py-2 text-left hover:bg-blue-50 dark:hover:bg-blue-900/30 text-gray-900 dark:text-white text-sm transition-colors"
                    >
                      {skill.name}
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400">
            Sélectionnez uniquement des compétences de la nomenclature Turnover-IT
          </p>

          {selectedSkills.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-2">
              {selectedSkills.map((slug) => (
                <span
                  key={slug}
                  className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 rounded-full text-sm flex items-center gap-2"
                >
                  {slug}
                  <button
                    type="button"
                    onClick={() => removeSkill(slug)}
                    className="hover:text-blue-600 dark:hover:text-blue-400"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
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
              Télétravail
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
              <div className="space-y-2">
                <input
                  type="date"
                  {...register('start_date')}
                  disabled={isAsap}
                  className={`w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    isAsap ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                />
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isAsap}
                    onChange={(e) => setIsAsap(e.target.checked)}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">ASAP (dès que possible)</span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Durée
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  value={durationValue}
                  onChange={(e) => setDurationValue(e.target.value ? parseInt(e.target.value, 10) : '')}
                  placeholder="6"
                  min={1}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <select
                  value={durationUnit}
                  onChange={(e) => setDurationUnit(e.target.value as 'months' | 'years')}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="months">Mois</option>
                  <option value="years">Années</option>
                </select>
              </div>
              {typeof durationValue === 'number' && durationUnit === 'years' && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  = {durationValue * 12} mois
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Salary */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-3">
            Rémunération
          </h3>

          <p className="text-sm text-gray-600 dark:text-gray-400 -mt-2">
            Les champs sont activés selon les types de contrat sélectionnés
          </p>

          {/* Salary fields (CDI, CDD) */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Salaire annuel (CDI, CDD)
              </h4>
              {!hasSalaryContractType && (
                <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                  Désactivé
                </span>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Minimum annuel (EUR)
                </label>
                <input
                  type="number"
                  {...register('salary_min_annual')}
                  placeholder="35000"
                  min={0}
                  disabled={!hasSalaryContractType}
                  className={`w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    !hasSalaryContractType ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Maximum annuel (EUR)
                </label>
                <input
                  type="number"
                  {...register('salary_max_annual')}
                  placeholder="50000"
                  min={0}
                  disabled={!hasSalaryContractType}
                  className={`w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    !hasSalaryContractType ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                />
              </div>
            </div>
          </div>

          {/* TJM fields (Freelance, Sous-traitance) */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                TJM (Freelance, Sous-traitance)
              </h4>
              {!hasTjmContractType && (
                <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                  Désactivé
                </span>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  TJM minimum (EUR/jour)
                </label>
                <input
                  type="number"
                  {...register('salary_min_daily')}
                  placeholder="400"
                  min={0}
                  disabled={!hasTjmContractType}
                  className={`w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    !hasTjmContractType ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  TJM maximum (EUR/jour)
                </label>
                <input
                  type="number"
                  {...register('salary_max_daily')}
                  placeholder="550"
                  min={0}
                  disabled={!hasTjmContractType}
                  className={`w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    !hasTjmContractType ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                />
              </div>
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
            {createMutation.isPending || step === 'saving' ? (
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
