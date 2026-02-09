/**
 * Public application form page (no authentication required).
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

// Cache duration: 48 hours in milliseconds
const CACHE_DURATION_MS = 48 * 60 * 60 * 1000;

interface CachedFormDataValues extends Partial<ApplicationFormData> {
  employment_status?: string;
}

interface CachedFormData {
  data: CachedFormDataValues;
  timestamp: number;
}

function getCacheKey(token: string): string {
  return `bobby_application_form_${token}`;
}

function loadCachedFormData(token: string): CachedFormDataValues | null {
  try {
    const cached = localStorage.getItem(getCacheKey(token));
    if (!cached) return null;

    const parsed: CachedFormData = JSON.parse(cached);
    const now = Date.now();

    // Check if cache is expired (48h)
    if (now - parsed.timestamp > CACHE_DURATION_MS) {
      localStorage.removeItem(getCacheKey(token));
      return null;
    }

    return parsed.data;
  } catch {
    return null;
  }
}

function saveCachedFormData(token: string, data: CachedFormDataValues): void {
  try {
    const cacheEntry: CachedFormData = {
      data,
      timestamp: Date.now(),
    };
    localStorage.setItem(getCacheKey(token), JSON.stringify(cacheEntry));
  } catch {
    // Ignore localStorage errors (quota exceeded, etc.)
  }
}

function clearCachedFormData(token: string): void {
  try {
    localStorage.removeItem(getCacheKey(token));
  } catch {
    // Ignore errors
  }
}
import PhoneInput, { isValidPhoneNumber } from 'react-phone-number-input';
import 'react-phone-number-input/style.css';
import {
  Briefcase,
  MapPin,
  Calendar,
  Upload,
  Check,
  AlertCircle,
  Loader2,
  FileText,
  X,
  HelpCircle,
} from 'lucide-react';
import { publicApplicationApi } from '../api/hr';

// Availability options
const AVAILABILITY_OPTIONS = [
  { value: 'asap', label: 'ASAP (immédiat)' },
  { value: '1_month', label: 'Sous 1 mois' },
  { value: '2_months', label: 'Sous 2 mois' },
  { value: '3_months', label: 'Sous 3 mois' },
  { value: 'more_3_months', label: 'Plus de 3 mois' },
];

// Employment status - no longer dropdown, using checkboxes
// Contract types that allow employee status (CDI/CDD)
const EMPLOYEE_CONTRACT_TYPES = ['PERMANENT', 'FIXED-TERM'];
// Contract types that allow freelance status
const FREELANCE_CONTRACT_TYPES = ['FREELANCE', 'INTERCONTRACT'];

// English level options with descriptions
const ENGLISH_LEVELS = [
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
    description: 'Maîtrise parfaite équivalente à un natif. Peut comprendre et s\'exprimer sans effort.',
  },
];

// Validation schema
const applicationSchema = z.object({
  civility: z.enum(['M', 'Mme']).optional(),
  first_name: z.string().min(1, 'Le prénom est requis').max(100),
  last_name: z.string().min(1, 'Le nom est requis').max(100),
  email: z.string().email('Email invalide'),
  phone: z
    .string()
    .min(1, 'Le numéro de téléphone est requis')
    .refine((val) => isValidPhoneNumber(val || ''), 'Numéro de téléphone invalide'),
  job_title: z.string().min(1, 'Le titre du poste est requis').max(200),
  availability: z.string().min(1, 'La disponibilité est requise'),
  // employment_status is handled separately via checkboxes
  english_level: z.string().min(1, "Le niveau d'anglais est requis"),
  // Freelance fields (optional based on status)
  tjm_current: z.number().min(0).optional().nullable(),
  tjm_desired: z.number().min(0).optional().nullable(),
  // Employee fields (optional based on status)
  salary_current: z.number().min(0).optional().nullable(),
  salary_desired: z.number().min(0).optional().nullable(),
});

type ApplicationFormData = z.infer<typeof applicationSchema>;

const CONTRACT_TYPE_LABELS: Record<string, string> = {
  PERMANENT: 'CDI',
  TEMPORARY: 'CDD',
  FREELANCE: 'Freelance',
};

const REMOTE_LABELS: Record<string, string> = {
  NONE: 'Pas de télétravail',
  PARTIAL: 'Télétravail partiel',
  FULL: '100% télétravail',
};

const EXPERIENCE_LABELS: Record<string, string> = {
  JUNIOR: 'Junior (0-2 ans)',
  INTERMEDIATE: 'Intermédiaire (2-5 ans)',
  SENIOR: 'Senior (5-10 ans)',
  EXPERT: 'Expert (+10 ans)',
};

export default function PublicApplication() {
  const { token } = useParams<{ token: string }>();
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [submissionMessage, setSubmissionMessage] = useState('');
  const [showEnglishTooltip, setShowEnglishTooltip] = useState<string | null>(null);
  const [hasCachedData, setHasCachedData] = useState(false);
  // Employment status checkboxes
  const [isFreelance, setIsFreelance] = useState(false);
  const [isEmployee, setIsEmployee] = useState(false);
  // Track if checkboxes have been initialized to prevent resetting on re-renders
  const checkboxesInitializedRef = useRef(false);

  // Load cached form data
  const cachedData = token ? loadCachedFormData(token) : null;

  // Fetch job posting info
  const { data: posting, isLoading, error } = useQuery({
    queryKey: ['public-job-posting', token],
    queryFn: () => publicApplicationApi.getJobPosting(token!),
    enabled: !!token,
  });

  // Form setup with cached values
  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = useForm<ApplicationFormData>({
    resolver: zodResolver(applicationSchema),
    defaultValues: {
      first_name: cachedData?.first_name || '',
      last_name: cachedData?.last_name || '',
      email: cachedData?.email || '',
      phone: cachedData?.phone || '',
      job_title: cachedData?.job_title || '',
      availability: cachedData?.availability || '',
      english_level: cachedData?.english_level || '',
      tjm_current: cachedData?.tjm_current ?? undefined,
      tjm_desired: cachedData?.tjm_desired ?? undefined,
      salary_current: cachedData?.salary_current ?? undefined,
      salary_desired: cachedData?.salary_desired ?? undefined,
    },
  });

  // Determine allowed employment statuses based on contract types
  const allowsEmployee = posting?.contract_types?.some((ct) => EMPLOYEE_CONTRACT_TYPES.includes(ct)) ?? false;
  const allowsFreelance = posting?.contract_types?.some((ct) => FREELANCE_CONTRACT_TYPES.includes(ct)) ?? false;

  // Initialize checkboxes from cached data or posting (only once)
  useEffect(() => {
    // Skip if already initialized to prevent resetting user selections
    if (checkboxesInitializedRef.current) return;
    // Wait until posting is loaded to know which options are available
    if (!posting) return;

    if (cachedData?.employment_status) {
      const statuses = cachedData.employment_status.split(',');
      setIsFreelance(statuses.includes('freelance') && allowsFreelance);
      setIsEmployee(statuses.includes('employee') && allowsEmployee);
    } else {
      // Auto-select if only one option available
      if (allowsFreelance && !allowsEmployee) {
        setIsFreelance(true);
      } else if (allowsEmployee && !allowsFreelance) {
        setIsEmployee(true);
      }
    }
    checkboxesInitializedRef.current = true;
  }, [posting, cachedData, allowsEmployee, allowsFreelance]);

  // Watch all form values for caching
  const watchedValues = watch();

  // Show cache indicator on mount if data was restored
  useEffect(() => {
    if (cachedData && Object.keys(cachedData).some(k => cachedData[k as keyof typeof cachedData])) {
      setHasCachedData(true);
      // Hide indicator after 5 seconds
      const timer = setTimeout(() => setHasCachedData(false), 5000);
      return () => clearTimeout(timer);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Save form data to cache on changes (debounced)
  const saveToCache = useCallback(() => {
    if (token && !submitted) {
      // Build employment_status from checkboxes for caching
      const statuses: string[] = [];
      if (isFreelance) statuses.push('freelance');
      if (isEmployee) statuses.push('employee');
      const employmentStatus = statuses.join(',');

      saveCachedFormData(token, {
        ...watchedValues,
        employment_status: employmentStatus,
      });
    }
  }, [token, watchedValues, submitted, isFreelance, isEmployee]);

  useEffect(() => {
    const timer = setTimeout(saveToCache, 500);
    return () => clearTimeout(timer);
  }, [saveToCache]);

  // Show salary/TJM fields based on checkbox selection
  const showFreelanceFields = isFreelance;
  const showEmployeeFields = isEmployee;

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: async (data: ApplicationFormData) => {
      if (!cvFile) throw new Error('CV requis');
      if (!token) throw new Error('Token invalide');

      // Build employment_status from checkboxes
      const statuses: string[] = [];
      if (isFreelance) statuses.push('freelance');
      if (isEmployee) statuses.push('employee');

      if (statuses.length === 0) {
        throw new Error('Veuillez sélectionner au moins un statut professionnel');
      }

      const employmentStatus = statuses.join(',');

      // Validate salary/TJM based on status
      if (isFreelance && (!data.tjm_current || !data.tjm_desired)) {
        throw new Error('Veuillez renseigner vos TJM actuel et souhaité');
      }
      if (isEmployee && (!data.salary_current || !data.salary_desired)) {
        throw new Error('Veuillez renseigner vos salaires actuel et souhaité');
      }

      return publicApplicationApi.submitApplication(token, {
        first_name: data.first_name,
        last_name: data.last_name,
        email: data.email,
        phone: data.phone,
        job_title: data.job_title,
        civility: data.civility,
        availability: data.availability,
        employment_status: employmentStatus,
        english_level: data.english_level,
        tjm_current: data.tjm_current || null,
        tjm_desired: data.tjm_desired || null,
        salary_current: data.salary_current || null,
        salary_desired: data.salary_desired || null,
        cv: cvFile,
      });
    },
    onSuccess: (result) => {
      setSubmitted(true);
      setSubmissionMessage(result.message);
      // Clear cached form data on successful submission
      if (token) {
        clearCachedFormData(token);
      }
    },
    onError: (error: Error) => {
      setSubmissionMessage(error.message || 'Une erreur est survenue');
    },
  });

  const onSubmit = (data: ApplicationFormData) => {
    if (!cvFile) {
      alert('Veuillez télécharger votre CV');
      return;
    }

    submitMutation.mutate(data);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      const validExtensions = ['.pdf', '.docx'];
      const hasValidExtension = validExtensions.some((ext) => file.name.toLowerCase().endsWith(ext));

      if (!validTypes.includes(file.type) && !hasValidExtension) {
        alert('Format de fichier non supporté. Utilisez PDF ou DOCX.');
        return;
      }

      // Validate file size (10 MB)
      if (file.size > 10 * 1024 * 1024) {
        alert('Le fichier est trop volumineux. Maximum 10 Mo.');
        return;
      }

      setCvFile(file);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-500 mx-auto" />
          <p className="mt-4 text-gray-600 dark:text-gray-400">Chargement de l'offre...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !posting) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 text-center">
          <AlertCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
            Offre non disponible
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Cette offre d'emploi n'existe pas ou n'est plus disponible.
          </p>
        </div>
      </div>
    );
  }

  // Success state
  if (submitted) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 text-center">
          <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <Check className="h-8 w-8 text-green-600 dark:text-green-400" />
          </div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
            Candidature envoyée
          </h1>
          <p className="text-gray-600 dark:text-gray-400">{submissionMessage}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Job Info Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            {posting.title}
          </h1>

          <div className="flex flex-wrap gap-4 mb-6">
            <div className="flex items-center text-gray-600 dark:text-gray-400">
              <MapPin className="h-5 w-5 mr-2" />
              {posting.location_city || posting.location_region || posting.location_country}
            </div>
            {posting.remote && (
              <div className="flex items-center text-gray-600 dark:text-gray-400">
                <Briefcase className="h-5 w-5 mr-2" />
                {REMOTE_LABELS[posting.remote] || posting.remote}
              </div>
            )}
            {posting.start_date && (
              <div className="flex items-center text-gray-600 dark:text-gray-400">
                <Calendar className="h-5 w-5 mr-2" />
                Début: {new Date(posting.start_date).toLocaleDateString('fr-FR')}
              </div>
            )}
          </div>

          {/* Contract Types */}
          <div className="flex flex-wrap gap-2 mb-6">
            {posting.contract_types.map((type) => (
              <span
                key={type}
                className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 rounded-full text-sm"
              >
                {CONTRACT_TYPE_LABELS[type] || type}
              </span>
            ))}
            {posting.experience_level && (
              <span className="px-3 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300 rounded-full text-sm">
                {EXPERIENCE_LABELS[posting.experience_level] || posting.experience_level}
              </span>
            )}
          </div>

          {/* TJM Range */}
          {(posting.salary_min_daily || posting.salary_max_daily) && (
            <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <p className="text-green-800 dark:text-green-300 font-medium">
                TJM: {posting.salary_min_daily}€ - {posting.salary_max_daily}€ / jour
              </p>
            </div>
          )}

          {/* Description */}
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Description
            </h2>
            <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
              {posting.description}
            </p>
          </div>

          {/* Qualifications */}
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Profil recherché
            </h2>
            <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
              {posting.qualifications}
            </p>
          </div>

          {/* Skills */}
          {posting.skills.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Compétences
              </h2>
              <div className="flex flex-wrap gap-2">
                {posting.skills.map((skill, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-sm"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Application Form */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Postuler à cette offre
          </h2>

          {/* Cache restoration indicator */}
          {hasCachedData && (
            <div className="mb-6 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg flex items-center gap-2">
              <Check className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <p className="text-sm text-blue-800 dark:text-blue-300">
                Vos informations précédentes ont été restaurées.
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Civility */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Civilité
              </label>
              <div className="flex gap-6">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    value="M"
                    {...register('civility')}
                    className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700"
                  />
                  <span className="text-sm text-gray-900 dark:text-white">M.</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    value="Mme"
                    {...register('civility')}
                    className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700"
                  />
                  <span className="text-sm text-gray-900 dark:text-white">Mme</span>
                </label>
              </div>
            </div>

            {/* Name Fields */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Prénom *
                </label>
                <input
                  type="text"
                  {...register('first_name')}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Jean"
                />
                {errors.first_name && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    {errors.first_name.message}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Nom *
                </label>
                <input
                  type="text"
                  {...register('last_name')}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="DUPONT"
                />
                {errors.last_name && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    {errors.last_name.message}
                  </p>
                )}
              </div>
            </div>

            {/* Contact Fields */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Email *
                </label>
                <input
                  type="email"
                  {...register('email')}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="jean.dupont@email.com"
                />
                {errors.email && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    {errors.email.message}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Téléphone *
                </label>
                <Controller
                  name="phone"
                  control={control}
                  render={({ field: { onChange, value } }) => (
                    <PhoneInput
                      international
                      defaultCountry="FR"
                      value={value}
                      onChange={(val) => onChange(val || '')}
                      className="phone-input-container"
                      inputClassName="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  )}
                />
                {errors.phone && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    {errors.phone.message}
                  </p>
                )}
              </div>
            </div>

            {/* Job Title */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Titre du poste actuel/recherché *
              </label>
              <input
                type="text"
                {...register('job_title')}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Développeur Full Stack"
              />
              {errors.job_title && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.job_title.message}
                </p>
              )}
            </div>

            {/* Employment Status - Checkboxes */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Statut professionnel *
              </label>
              <div className="space-y-2">
                {/* Freelance checkbox - only show if allowed by contract types */}
                {allowsFreelance && (
                  <label className="flex items-center gap-3 p-3 border border-gray-200 dark:border-gray-600 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                    <input
                      type="checkbox"
                      checked={isFreelance}
                      onChange={(e) => setIsFreelance(e.target.checked)}
                      className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <div>
                      <span className="font-medium text-gray-900 dark:text-white">Freelance</span>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Vous êtes indépendant ou en portage salarial (uniquement les vraies sociétés de portage sont acceptées)
                      </p>
                    </div>
                  </label>
                )}
                {/* Employee checkbox - only show if allowed by contract types */}
                {allowsEmployee && (
                  <label className="flex items-center gap-3 p-3 border border-gray-200 dark:border-gray-600 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                    <input
                      type="checkbox"
                      checked={isEmployee}
                      onChange={(e) => setIsEmployee(e.target.checked)}
                      className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <div>
                      <span className="font-medium text-gray-900 dark:text-white">Salarié</span>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Vous recherchez un contrat CDI ou CDD
                      </p>
                    </div>
                  </label>
                )}
              </div>
              {!isFreelance && !isEmployee && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  Veuillez sélectionner au moins un statut
                </p>
              )}
            </div>

            {/* Freelance Fields - TJM */}
            {showFreelanceFields && (
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg space-y-4">
                <h3 className="font-medium text-blue-900 dark:text-blue-300">
                  Tarif journalier (Freelance)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      TJM actuel (€/jour) *
                    </label>
                    <input
                      type="number"
                      {...register('tjm_current', { valueAsNumber: true })}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="450"
                      min={0}
                    />
                    {errors.tjm_current && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                        {errors.tjm_current.message}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      TJM souhaité (€/jour) *
                    </label>
                    <input
                      type="number"
                      {...register('tjm_desired', { valueAsNumber: true })}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="500"
                      min={0}
                    />
                    {errors.tjm_desired && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                        {errors.tjm_desired.message}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Employee Fields - Salary */}
            {showEmployeeFields && (
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg space-y-4">
                <h3 className="font-medium text-green-900 dark:text-green-300">
                  Salaire annuel brut (Salarié)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Salaire actuel (€/an) *
                    </label>
                    <input
                      type="number"
                      {...register('salary_current', { valueAsNumber: true })}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="45000"
                      min={0}
                    />
                    {errors.salary_current && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                        {errors.salary_current.message}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Salaire souhaité (€/an) *
                    </label>
                    <input
                      type="number"
                      {...register('salary_desired', { valueAsNumber: true })}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="50000"
                      min={0}
                    />
                    {errors.salary_desired && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                        {errors.salary_desired.message}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Availability */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Disponibilité *
              </label>
              <select
                {...register('availability')}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">-- Sélectionner --</option>
                {AVAILABILITY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              {errors.availability && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.availability.message}
                </p>
              )}
            </div>

            {/* English Level */}
            <div>
              <div className="flex items-center gap-2 mb-1">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Niveau d'anglais *
                </label>
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowEnglishTooltip(showEnglishTooltip ? null : 'all')}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    <HelpCircle className="h-4 w-4" />
                  </button>
                  {showEnglishTooltip && (
                    <div className="absolute left-0 top-6 z-50 w-80 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-medium text-gray-900 dark:text-white text-sm">Niveaux d'anglais</span>
                        <button
                          type="button"
                          onClick={() => setShowEnglishTooltip(null)}
                          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                      <div className="space-y-2 text-xs">
                        {ENGLISH_LEVELS.map((level) => (
                          <div key={level.value}>
                            <span className="font-medium text-gray-800 dark:text-gray-200">{level.label}:</span>
                            <span className="text-gray-600 dark:text-gray-400 ml-1">{level.description}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <select
                {...register('english_level')}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">-- Sélectionner --</option>
                {ENGLISH_LEVELS.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </select>
              {errors.english_level && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.english_level.message}
                </p>
              )}
            </div>

            {/* CV Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                CV (PDF ou Word, max 10 Mo) *
              </label>
              <div className="mt-1">
                {cvFile ? (
                  <div className="flex items-center gap-3 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                    <FileText className="h-8 w-8 text-green-600 dark:text-green-400" />
                    <div className="flex-1">
                      <p className="font-medium text-green-800 dark:text-green-300">
                        {cvFile.name}
                      </p>
                      <p className="text-sm text-green-600 dark:text-green-400">
                        {(cvFile.size / 1024 / 1024).toFixed(2)} Mo
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setCvFile(null)}
                      className="p-1 hover:bg-green-100 dark:hover:bg-green-800/30 rounded"
                    >
                      <X className="h-5 w-5 text-green-600 dark:text-green-400" />
                    </button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:border-blue-500 dark:hover:border-blue-400 transition-colors">
                    <Upload className="h-8 w-8 text-gray-400 mb-2" />
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Cliquez pour télécharger ou glissez-déposez
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-500">
                      PDF ou Word (max 10 Mo)
                    </p>
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                      onChange={handleFileChange}
                    />
                  </label>
                )}
              </div>
            </div>

            {/* Error Message */}
            {submitMutation.isError && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-red-800 dark:text-red-200">{submissionMessage}</p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitMutation.isPending || !cvFile}
              className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {submitMutation.isPending ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Envoi en cours...
                </>
              ) : (
                <>
                  <Check className="h-5 w-5" />
                  Envoyer ma candidature
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Custom styles for phone input */}
      <style>{`
        .PhoneInput {
          display: flex;
          align-items: center;
        }
        .PhoneInputCountry {
          padding: 0.5rem;
          border: 1px solid #d1d5db;
          border-right: none;
          border-radius: 0.5rem 0 0 0.5rem;
          background: white;
        }
        .dark .PhoneInputCountry {
          border-color: #4b5563;
          background: #374151;
        }
        .PhoneInputInput {
          flex: 1;
          padding: 0.5rem 1rem;
          border: 1px solid #d1d5db;
          border-radius: 0 0.5rem 0.5rem 0;
          background: white;
          color: #111827;
        }
        .dark .PhoneInputInput {
          border-color: #4b5563;
          background: #374151;
          color: white;
        }
        .PhoneInputInput:focus {
          outline: none;
          ring: 2px;
          ring-color: #3b82f6;
          border-color: transparent;
        }
      `}</style>
    </div>
  );
}
