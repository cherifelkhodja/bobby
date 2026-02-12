/**
 * EditJobPosting - Page to edit an existing draft job posting.
 *
 * Flow:
 * 1. Load existing job posting data
 * 2. Pre-fill form with saved values
 * 3. User edits and saves or publishes
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  ChevronLeft,
  Loader2,
  AlertCircle,
  MapPin,
  X,
  Search,
} from 'lucide-react';
import {
  hrApi,
  type TurnoverITSkill,
  type TurnoverITPlace,
} from '../api/hr';
import { getErrorMessage } from '../api/client';
import { jobPostingSchema, type JobPostingFormData } from '../schemas/jobPosting';
import {
  CONTRACT_TYPES,
  SALARY_CONTRACT_TYPES,
  TJM_CONTRACT_TYPES,
  REMOTE_POLICIES,
  EXPERIENCE_LEVELS,
  JOB_POSTING_STATUS_BADGES,
} from '../constants/hr';

type ViewStep = 'loading' | 'form' | 'saving' | 'publishing' | 'error';

export default function EditJobPosting() {
  const { postingId } = useParams<{ postingId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [step, setStep] = useState<ViewStep>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [skillSearch, setSkillSearch] = useState('');
  const [showSkillDropdown, setShowSkillDropdown] = useState(false);
  const [selectedContractTypes, setSelectedContractTypes] = useState<string[]>([]);
  const [isAsap, setIsAsap] = useState(false);
  const [durationUnit, setDurationUnit] = useState<'months' | 'years'>('months');
  const [durationValue, setDurationValue] = useState<number | ''>('');
  const [isSalaryByProfile, setIsSalaryByProfile] = useState(false);
  const [selectedPlace, setSelectedPlace] = useState<TurnoverITPlace | null>(null);
  const [placeSearch, setPlaceSearch] = useState('');
  const [showPlaceDropdown, setShowPlaceDropdown] = useState(false);
  const skillInputRef = useRef<HTMLInputElement>(null);
  const skillDropdownRef = useRef<HTMLDivElement>(null);
  const placeInputRef = useRef<HTMLInputElement>(null);
  const placeDropdownRef = useRef<HTMLDivElement>(null);

  const hasSalaryContractType = selectedContractTypes.some((type) =>
    SALARY_CONTRACT_TYPES.includes(type)
  );
  const hasTjmContractType = selectedContractTypes.some((type) =>
    TJM_CONTRACT_TYPES.includes(type)
  );

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    reset,
  } = useForm<JobPostingFormData>({
    resolver: zodResolver(jobPostingSchema),
    defaultValues: {
      title: '',
      description: '',
      qualifications: '',
      employer_overview: '',
    },
  });

  const titleWatch = watch('title');
  const descriptionWatch = watch('description');
  const qualificationsWatch = watch('qualifications');

  // Fetch existing job posting
  const { data: posting, isLoading: postingLoading, error: postingError } = useQuery({
    queryKey: ['job-posting', postingId],
    queryFn: () => hrApi.getJobPosting(postingId!),
    enabled: !!postingId,
  });

  // Pre-fill form when posting loads
  useEffect(() => {
    if (posting) {
      // Pre-fill form fields
      reset({
        title: posting.title,
        description: posting.description,
        qualifications: posting.qualifications,
        experience_level: posting.experience_level || '',
        remote: posting.remote || '',
        start_date: posting.start_date || '',
        salary_min_annual: posting.salary_min_annual || '',
        salary_max_annual: posting.salary_max_annual || '',
        salary_min_daily: posting.salary_min_daily || '',
        salary_max_daily: posting.salary_max_daily || '',
      });

      // Set skills
      setSelectedSkills(posting.skills || []);

      // Set contract types
      setSelectedContractTypes(posting.contract_types || []);

      // Set duration
      if (posting.duration_months) {
        if (posting.duration_months >= 12 && posting.duration_months % 12 === 0) {
          setDurationUnit('years');
          setDurationValue(posting.duration_months / 12);
        } else {
          setDurationUnit('months');
          setDurationValue(posting.duration_months);
        }
      }

      // Set location
      if (posting.location_key) {
        // Build a TurnoverITPlace-like object from saved data
        const locationLabel = [posting.location_city, posting.location_region, posting.location_country]
          .filter(Boolean)
          .join(', ');
        setSelectedPlace({
          key: posting.location_key,
          label: locationLabel || posting.location_country,
          shortLabel: posting.location_city || posting.location_region || posting.location_country,
          locality: posting.location_city || '',
          region: posting.location_region || '',
          postalCode: posting.location_postal_code || '',
          country: posting.location_country,
          countryCode: posting.location_country === 'France' ? 'FR' : '',
        });
        setPlaceSearch(locationLabel || posting.location_country);
      } else if (posting.location_city || posting.location_country) {
        const locationLabel = [posting.location_city, posting.location_region, posting.location_country]
          .filter(Boolean)
          .join(', ');
        setPlaceSearch(locationLabel);
      }

      // Check if ASAP (no start date)
      setIsAsap(!posting.start_date);

      // Check if salary by profile
      const hasSalary = posting.salary_min_annual || posting.salary_max_annual ||
                        posting.salary_min_daily || posting.salary_max_daily;
      setIsSalaryByProfile(!hasSalary && posting.contract_types?.length > 0);

      setStep('form');
    }
  }, [posting, reset]);

  // Handle loading/error states and closed postings
  useEffect(() => {
    if (postingError) {
      setErrorMessage(getErrorMessage(postingError));
      setStep('error');
    }
    // Closed postings cannot be edited directly
    if (posting?.status === 'closed') {
      setErrorMessage("Cette annonce est fermée. Réactivez-la depuis la page de détails avant de la modifier.");
      setStep('error');
    }
  }, [postingError, posting?.status]);

  // Fetch Turnover-IT skills for autocomplete
  const { data: skillsData } = useQuery({
    queryKey: ['turnoverit-skills', skillSearch],
    queryFn: () => hrApi.getSkills(skillSearch || undefined),
    enabled: showSkillDropdown && skillSearch.length >= 1,
    staleTime: 5 * 60 * 1000,
  });

  const filteredSkills = skillsData?.skills.filter(
    (skill) => !selectedSkills.includes(skill.slug)
  ) ?? [];

  // Fetch Turnover-IT places for location autocomplete
  const { data: placesData } = useQuery({
    queryKey: ['turnoverit-places', placeSearch],
    queryFn: () => hrApi.getPlaces(placeSearch),
    enabled: showPlaceDropdown && placeSearch.length >= 2,
    staleTime: 5 * 60 * 1000,
  });

  // Handle click outside to close dropdowns
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
      if (
        placeDropdownRef.current &&
        !placeDropdownRef.current.contains(event.target as Node) &&
        placeInputRef.current &&
        !placeInputRef.current.contains(event.target as Node)
      ) {
        setShowPlaceDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Save mutation - updates draft
  const saveMutation = useMutation({
    mutationFn: async (data: JobPostingFormData) => {
      if (!postingId) throw new Error('ID annonce manquant');
      if (selectedContractTypes.length === 0) {
        throw new Error('Sélectionnez au moins un type de contrat');
      }
      if (!selectedPlace) {
        throw new Error('Sélectionnez un lieu d\'exécution');
      }

      let startDate: string | null | undefined;
      if (isAsap) {
        startDate = null;
      } else {
        startDate = data.start_date || undefined;
      }

      let durationMonths: number | undefined;
      if (typeof durationValue === 'number' && durationValue > 0) {
        durationMonths = durationUnit === 'years' ? durationValue * 12 : durationValue;
      }

      let salaryMinAnnual: number | null | undefined;
      let salaryMaxAnnual: number | null | undefined;
      let salaryMinDaily: number | null | undefined;
      let salaryMaxDaily: number | null | undefined;

      if (isSalaryByProfile) {
        if (hasSalaryContractType) {
          salaryMinAnnual = null;
          salaryMaxAnnual = null;
        }
        if (hasTjmContractType) {
          salaryMinDaily = null;
          salaryMaxDaily = null;
        }
      } else {
        salaryMinAnnual = hasSalaryContractType && typeof data.salary_min_annual === 'number'
          ? data.salary_min_annual
          : undefined;
        salaryMaxAnnual = hasSalaryContractType && typeof data.salary_max_annual === 'number'
          ? data.salary_max_annual
          : undefined;
        salaryMinDaily = hasTjmContractType && typeof data.salary_min_daily === 'number'
          ? data.salary_min_daily
          : undefined;
        salaryMaxDaily = hasTjmContractType && typeof data.salary_max_daily === 'number'
          ? data.salary_max_daily
          : undefined;
      }

      const requestData = {
        title: data.title,
        description: data.description,
        qualifications: data.qualifications,
        location_country: selectedPlace.countryCode === 'FR' ? 'France' : selectedPlace.country,
        location_region: selectedPlace.region || undefined,
        location_postal_code: selectedPlace.postalCode || undefined,
        location_city: selectedPlace.locality || undefined,
        location_key: selectedPlace.key || undefined,
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

      return hrApi.updateJobPosting(postingId, requestData);
    },
    onSuccess: (posting) => {
      queryClient.invalidateQueries({ queryKey: ['hr-opportunities'] });
      queryClient.invalidateQueries({ queryKey: ['hr-job-postings'] });
      queryClient.invalidateQueries({ queryKey: ['job-posting', postingId] });
      navigate(`/rh/annonces/${posting.id}`);
    },
  });

  // Publish mutation
  const publishMutation = useMutation({
    mutationFn: async (data: JobPostingFormData) => {
      if (!postingId) throw new Error('ID annonce manquant');
      if (selectedContractTypes.length === 0) {
        throw new Error('Sélectionnez au moins un type de contrat');
      }
      if (!selectedPlace) {
        throw new Error('Sélectionnez un lieu d\'exécution');
      }

      let startDate: string | null | undefined;
      if (isAsap) {
        startDate = null;
      } else {
        startDate = data.start_date || undefined;
      }

      let durationMonths: number | undefined;
      if (typeof durationValue === 'number' && durationValue > 0) {
        durationMonths = durationUnit === 'years' ? durationValue * 12 : durationValue;
      }

      let salaryMinAnnual: number | null | undefined;
      let salaryMaxAnnual: number | null | undefined;
      let salaryMinDaily: number | null | undefined;
      let salaryMaxDaily: number | null | undefined;

      if (isSalaryByProfile) {
        if (hasSalaryContractType) {
          salaryMinAnnual = null;
          salaryMaxAnnual = null;
        }
        if (hasTjmContractType) {
          salaryMinDaily = null;
          salaryMaxDaily = null;
        }
      } else {
        salaryMinAnnual = hasSalaryContractType && typeof data.salary_min_annual === 'number'
          ? data.salary_min_annual : undefined;
        salaryMaxAnnual = hasSalaryContractType && typeof data.salary_max_annual === 'number'
          ? data.salary_max_annual : undefined;
        salaryMinDaily = hasTjmContractType && typeof data.salary_min_daily === 'number'
          ? data.salary_min_daily : undefined;
        salaryMaxDaily = hasTjmContractType && typeof data.salary_max_daily === 'number'
          ? data.salary_max_daily : undefined;
      }

      const requestData = {
        title: data.title,
        description: data.description,
        qualifications: data.qualifications,
        location_country: selectedPlace.countryCode === 'FR' ? 'France' : selectedPlace.country,
        location_region: selectedPlace.region || undefined,
        location_postal_code: selectedPlace.postalCode || undefined,
        location_city: selectedPlace.locality || undefined,
        location_key: selectedPlace.key || undefined,
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

      // First update the draft
      await hrApi.updateJobPosting(postingId, requestData);

      // Then publish
      return hrApi.publishJobPosting(postingId);
    },
    onSuccess: (posting) => {
      queryClient.invalidateQueries({ queryKey: ['hr-opportunities'] });
      queryClient.invalidateQueries({ queryKey: ['hr-job-postings'] });
      queryClient.invalidateQueries({ queryKey: ['job-posting', postingId] });
      navigate(`/rh/annonces/${posting.id}`);
    },
    onError: () => {
      setStep('form');
    },
  });

  const onSaveDraft = (data: JobPostingFormData) => {
    setStep('saving');
    saveMutation.mutate(data);
  };

  const onPublish = (data: JobPostingFormData) => {
    setStep('publishing');
    publishMutation.mutate(data);
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

  const selectPlace = useCallback((place: TurnoverITPlace) => {
    setSelectedPlace(place);
    setPlaceSearch(place.label);
    setShowPlaceDropdown(false);
  }, []);

  const clearPlace = () => {
    setSelectedPlace(null);
    setPlaceSearch('');
    placeInputRef.current?.focus();
  };

  // Loading state
  if (step === 'loading' || postingLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <p className="ml-2 text-gray-600 dark:text-gray-400">
          Chargement du brouillon...
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
          <div className="mt-4">
            <Link
              to="/rh"
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg transition-colors"
            >
              Retour aux opportunités
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Publishing state
  if (step === 'publishing') {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <Loader2 className="h-16 w-16 animate-spin text-green-500" />
        <p className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
          Publication vers Turnover-IT...
        </p>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          L'annonce sera visible sur les jobboards partenaires
        </p>
      </div>
    );
  }

  // Form state
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
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            {posting?.status === 'draft' ? "Modifier le brouillon" : "Modifier l'annonce"}
          </h1>
          {posting?.status && JOB_POSTING_STATUS_BADGES[posting.status] && (
            <span className={`px-2 py-1 text-sm rounded-full ${JOB_POSTING_STATUS_BADGES[posting.status].color}`}>
              {JOB_POSTING_STATUS_BADGES[posting.status].label}
            </span>
          )}
        </div>
        <p className="mt-1 text-gray-600 dark:text-gray-400">
          {posting?.status === 'draft'
            ? "Modifiez les informations puis enregistrez ou publiez directement"
            : "Les modifications seront synchronisées avec Turnover-IT"}
        </p>
      </div>

      {/* Form */}
      <form onSubmit={(e) => e.preventDefault()} className="space-y-8">
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

        {/* Skills */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-3">
            Compétences techniques
          </h3>

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

          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Lieu d'exécution *
            </label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                ref={placeInputRef}
                type="text"
                value={placeSearch}
                onChange={(e) => {
                  setPlaceSearch(e.target.value);
                  setShowPlaceDropdown(true);
                  if (selectedPlace && e.target.value !== selectedPlace.label) {
                    setSelectedPlace(null);
                  }
                }}
                onFocus={() => setShowPlaceDropdown(true)}
                placeholder="Code postal / Ville / Département / Région"
                className={`w-full pl-10 pr-10 py-2 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  selectedPlace
                    ? 'border-green-500 dark:border-green-500'
                    : 'border-gray-300 dark:border-gray-600'
                }`}
              />
              {selectedPlace && (
                <button
                  type="button"
                  onClick={clearPlace}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {showPlaceDropdown && placeSearch.length >= 2 && (
              <div
                ref={placeDropdownRef}
                className="absolute z-10 mt-1 w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto"
              >
                {!placesData?.places.length ? (
                  <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {placeSearch.length < 2
                      ? 'Tapez au moins 2 caractères'
                      : 'Aucun lieu trouvé'}
                  </div>
                ) : (
                  placesData.places.map((place) => (
                    <button
                      key={place.key}
                      type="button"
                      onClick={() => selectPlace(place)}
                      className="w-full px-4 py-2 text-left hover:bg-blue-50 dark:hover:bg-blue-900/30 text-gray-900 dark:text-white text-sm transition-colors"
                    >
                      {place.label}
                    </button>
                  ))
                )}
              </div>
            )}

            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              France uniquement. Recherchez par ville, code postal ou région.
            </p>

            {selectedPlace && (
              <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                <p className="text-sm text-green-800 dark:text-green-300">
                  <span className="font-medium">Lieu sélectionné :</span> {selectedPlace.label}
                </p>
                {selectedPlace.postalCode && (
                  <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                    Code postal : {selectedPlace.postalCode}
                  </p>
                )}
              </div>
            )}
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
                  disabled={!hasSalaryContractType || isSalaryByProfile}
                  className={`w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    !hasSalaryContractType || isSalaryByProfile ? 'opacity-50 cursor-not-allowed' : ''
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
                  disabled={!hasSalaryContractType || isSalaryByProfile}
                  className={`w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    !hasSalaryContractType || isSalaryByProfile ? 'opacity-50 cursor-not-allowed' : ''
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
                  disabled={!hasTjmContractType || isSalaryByProfile}
                  className={`w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    !hasTjmContractType || isSalaryByProfile ? 'opacity-50 cursor-not-allowed' : ''
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
                  disabled={!hasTjmContractType || isSalaryByProfile}
                  className={`w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    !hasTjmContractType || isSalaryByProfile ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                />
              </div>
            </div>
          </div>

          {/* Salary by profile checkbox */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={isSalaryByProfile}
                onChange={(e) => setIsSalaryByProfile(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Rémunération selon profil
              </span>
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-7">
              La rémunération sera déterminée en fonction du profil du candidat
            </p>
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
        {(saveMutation.isError || publishMutation.isError) && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0" />
              <p className="text-red-800 dark:text-red-200">
                {saveMutation.error
                  ? getErrorMessage(saveMutation.error, "Erreur lors de la sauvegarde")
                  : publishMutation.error
                  ? getErrorMessage(publishMutation.error, "Erreur lors de la publication")
                  : "Erreur lors de l'opération"}
              </p>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          {posting?.status === 'draft' ? (
            <>
              <button
                type="button"
                onClick={handleSubmit(onSaveDraft)}
                disabled={saveMutation.isPending || publishMutation.isPending || selectedContractTypes.length === 0 || !selectedPlace}
                className="flex-1 px-6 py-3 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {saveMutation.isPending ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Enregistrement...
                  </>
                ) : (
                  '💾 Enregistrer brouillon'
                )}
              </button>
              <button
                type="button"
                onClick={handleSubmit(onPublish)}
                disabled={saveMutation.isPending || publishMutation.isPending || selectedContractTypes.length === 0 || !selectedPlace}
                className="flex-1 px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-green-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {publishMutation.isPending ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Publication...
                  </>
                ) : (
                  '🚀 Publier sur Turnover-IT'
                )}
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={handleSubmit(onSaveDraft)}
              disabled={saveMutation.isPending || selectedContractTypes.length === 0 || !selectedPlace}
              className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {saveMutation.isPending ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Enregistrement...
                </>
              ) : (
                '💾 Enregistrer les modifications'
              )}
            </button>
          )}
          <Link
            to={`/rh/annonces/${postingId}`}
            className="px-6 py-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white font-medium rounded-lg transition-colors text-center"
          >
            Annuler
          </Link>
        </div>
      </form>
    </div>
  );
}
