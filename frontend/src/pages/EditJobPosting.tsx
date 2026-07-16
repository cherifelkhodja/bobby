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
import { AlertCircle, Check, MapPin, Search, X } from 'lucide-react';
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
import { Button } from '../components/ui/Button';
import { PageSpinner, Spinner } from '../components/ui/Spinner';

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
    return <PageSpinner />;
  }

  // Error state
  if (step === 'error') {
    return (
      <div className="max-w-[840px]">
        <Link to="/rh" className="bc block cursor-pointer !text-mut2 hover:!text-mut">
          ← RH / Gestion des annonces
        </Link>
        <h1 className="h1">Modifier l'annonce</h1>
        <div className="alert red">
          <AlertCircle className="h-[18px] w-[18px] shrink-0" />
          <span>{errorMessage || 'Une erreur est survenue'}</span>
        </div>
        <div className="flex justify-end mt-4">
          <Button type="button" variant="secondary" onClick={() => navigate('/rh')}>
            Retour aux annonces
          </Button>
        </div>
      </div>
    );
  }

  // Publishing state
  if (step === 'publishing') {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <Spinner size="lg" />
        <p className="mt-4 text-[14.5px] font-semibold text-ink">
          Publication vers Turnover-IT…
        </p>
        <p className="notec mt-1">L'annonce sera visible sur les jobboards partenaires</p>
      </div>
    );
  }

  // Form state
  const salaryDisabled = !hasSalaryContractType || isSalaryByProfile;
  const tjmDisabled = !hasTjmContractType || isSalaryByProfile;
  const actionsDisabled =
    saveMutation.isPending ||
    publishMutation.isPending ||
    selectedContractTypes.length === 0 ||
    !selectedPlace;
  const boondInfo = posting
    ? [posting.opportunity_reference, posting.client_name].filter(Boolean).join(' · ')
    : '';

  return (
    <div className="max-w-[840px]">
      <Link to="/rh" className="bc block cursor-pointer !text-mut2 hover:!text-mut">
        ← RH / Gestion des annonces
      </Link>
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="h1">Modifier l'annonce</h1>
        {posting?.status && JOB_POSTING_STATUS_BADGES[posting.status] && (
          <span
            className={`st ${
              posting.status === 'published'
                ? 'st-grn'
                : posting.status === 'closed'
                ? 'st-red'
                : 'st-sla'
            }`}
          >
            <span className="dot" />
            {JOB_POSTING_STATUS_BADGES[posting.status].label}
          </span>
        )}
      </div>
      <p className="sub">
        {posting?.status === 'draft'
          ? 'Modifiez les informations puis enregistrez ou publiez directement'
          : 'Les modifications seront synchronisées avec Turnover-IT'}
      </p>

      {boondInfo && (
        <div className="infob mt-3.5">
          <b>Opportunité BoondManager :</b> {boondInfo} — les champs sont pré-remplis depuis
          l'annonce enregistrée.
        </div>
      )}

      <form onSubmit={(e) => e.preventDefault()}>
        {/* Informations générales */}
        <div className="card mt-4">
          <h3 className="ct">Informations générales</h3>
          <div className="f-grid mt-3.5">
            <div className="col-span-full">
              <label className="f-lab" htmlFor="jp-title">
                Titre de l'annonce *
              </label>
              <input
                id="jp-title"
                type="text"
                className="f-in"
                placeholder="Ex : Développeur Senior React/Node.js (H/F)"
                {...register('title')}
              />
              <div className="flex justify-between gap-3">
                {errors.title && <p className="f-hint !text-redt">{errors.title.message}</p>}
                <p className="f-hint ml-auto">{titleWatch?.length || 0}/100</p>
              </div>
            </div>

            <div className="relative">
              <label className="f-lab" htmlFor="jp-place">
                Lieu d'exécution *
              </label>
              <div className="relative">
                <MapPin className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-mut2" />
                <input
                  id="jp-place"
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
                  className="f-in !pl-9 !pr-9"
                />
                {selectedPlace && (
                  <button
                    type="button"
                    onClick={clearPlace}
                    aria-label="Effacer le lieu"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-mut2 hover:text-mut"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
              {showPlaceDropdown && placeSearch.length >= 2 && (
                <div
                  ref={placeDropdownRef}
                  className="absolute z-10 mt-1 w-full max-h-60 overflow-y-auto rounded-[10px] border border-lin bg-sur shadow-lg"
                >
                  {!placesData?.places.length ? (
                    <p className="px-3 py-2.5 text-[12.5px] text-mut">Aucun lieu trouvé</p>
                  ) : (
                    placesData.places.map((place) => (
                      <button
                        key={place.key}
                        type="button"
                        onClick={() => selectPlace(place)}
                        className="block w-full px-3 py-2 text-left text-[13px] text-ink hover:bg-srf2 transition-colors"
                      >
                        {place.label}
                      </button>
                    ))
                  )}
                </div>
              )}
              {selectedPlace ? (
                <p className="f-hint !text-grn-fg">
                  Lieu sélectionné : {selectedPlace.label}
                  {selectedPlace.postalCode && ` (${selectedPlace.postalCode})`}
                </p>
              ) : (
                <p className="f-hint">France uniquement — ville, code postal ou région</p>
              )}
            </div>

            <div>
              <label className="f-lab" htmlFor="jp-start-date">
                Date de démarrage
              </label>
              <input
                id="jp-start-date"
                type="date"
                disabled={isAsap}
                className="f-in"
                {...register('start_date')}
              />
              <div
                className="ckrow mt-2.5"
                role="checkbox"
                aria-checked={isAsap}
                tabIndex={0}
                onClick={() => setIsAsap(!isAsap)}
                onKeyDown={(e) => {
                  if (e.key === ' ' || e.key === 'Enter') {
                    e.preventDefault();
                    setIsAsap(!isAsap);
                  }
                }}
              >
                <span className={`ck ${isAsap ? 'on' : ''}`}>
                  <Check className="h-3 w-3" />
                </span>
                <span>ASAP (dès que possible)</span>
              </div>
            </div>

            <div>
              <label className="f-lab" htmlFor="jp-duration">
                Durée de la mission
              </label>
              <div className="flex gap-2">
                <input
                  id="jp-duration"
                  type="number"
                  min={1}
                  placeholder="6"
                  value={durationValue}
                  onChange={(e) =>
                    setDurationValue(e.target.value ? parseInt(e.target.value, 10) : '')
                  }
                  className="f-in"
                />
                <select
                  aria-label="Unité de durée"
                  value={durationUnit}
                  onChange={(e) => setDurationUnit(e.target.value as 'months' | 'years')}
                  className="f-in !px-2.5 !w-28 shrink-0"
                >
                  <option value="months">Mois</option>
                  <option value="years">Années</option>
                </select>
              </div>
              {typeof durationValue === 'number' && durationUnit === 'years' && (
                <p className="f-hint">= {durationValue * 12} mois</p>
              )}
            </div>
          </div>
        </div>

        {/* Contrat et conditions */}
        <div className="card mt-4">
          <h3 className="ct">Contrat et conditions</h3>
          <p className="f-lab mt-3.5">Types de contrat *</p>
          <div className="flex flex-wrap gap-2">
            {CONTRACT_TYPES.map((type) => (
              <button
                key={type.value}
                type="button"
                aria-pressed={selectedContractTypes.includes(type.value)}
                onClick={() => toggleContractType(type.value)}
                className={`tg ${selectedContractTypes.includes(type.value) ? 'on' : ''}`}
              >
                {type.label}
              </button>
            ))}
          </div>
          {selectedContractTypes.length === 0 && (
            <p className="f-hint !text-redt">Sélectionnez au moins un type de contrat</p>
          )}
          <div className="f-grid mt-3.5">
            <div>
              <label className="f-lab" htmlFor="jp-remote">
                Télétravail
              </label>
              <select id="jp-remote" className="f-in !px-2.5" {...register('remote')}>
                <option value="">— Sélectionner —</option>
                {REMOTE_POLICIES.map((policy) => (
                  <option key={policy.value} value={policy.value}>
                    {policy.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="f-lab" htmlFor="jp-experience">
                Niveau d'expérience
              </label>
              <select
                id="jp-experience"
                className="f-in !px-2.5"
                {...register('experience_level')}
              >
                <option value="">— Sélectionner —</option>
                {EXPERIENCE_LEVELS.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Rémunération */}
        <div className="card mt-4">
          <h3 className="ct">Rémunération</h3>
          <p className="cs">Les champs sont activés selon les types de contrat sélectionnés</p>
          <div className="f-grid mt-3.5">
            <div className={salaryDisabled ? 'dis' : ''}>
              <label className="f-lab" htmlFor="jp-salary-min">
                Salaire annuel min (€) — CDI, CDD
              </label>
              <input
                id="jp-salary-min"
                type="number"
                min={0}
                placeholder="35000"
                disabled={salaryDisabled}
                className="f-in"
                {...register('salary_min_annual')}
              />
            </div>
            <div className={salaryDisabled ? 'dis' : ''}>
              <label className="f-lab" htmlFor="jp-salary-max">
                Salaire annuel max (€) — CDI, CDD
              </label>
              <input
                id="jp-salary-max"
                type="number"
                min={0}
                placeholder="50000"
                disabled={salaryDisabled}
                className="f-in"
                {...register('salary_max_annual')}
              />
            </div>
            <div className={tjmDisabled ? 'dis' : ''}>
              <label className="f-lab" htmlFor="jp-tjm-min">
                TJM min (€/jour) — Freelance
              </label>
              <input
                id="jp-tjm-min"
                type="number"
                min={0}
                placeholder="400"
                disabled={tjmDisabled}
                className="f-in"
                {...register('salary_min_daily')}
              />
            </div>
            <div className={tjmDisabled ? 'dis' : ''}>
              <label className="f-lab" htmlFor="jp-tjm-max">
                TJM max (€/jour) — Freelance
              </label>
              <input
                id="jp-tjm-max"
                type="number"
                min={0}
                placeholder="550"
                disabled={tjmDisabled}
                className="f-in"
                {...register('salary_max_daily')}
              />
            </div>
          </div>
          <div
            className="ckrow mt-3.5"
            role="checkbox"
            aria-checked={isSalaryByProfile}
            tabIndex={0}
            onClick={() => setIsSalaryByProfile(!isSalaryByProfile)}
            onKeyDown={(e) => {
              if (e.key === ' ' || e.key === 'Enter') {
                e.preventDefault();
                setIsSalaryByProfile(!isSalaryByProfile);
              }
            }}
          >
            <span className={`ck ${isSalaryByProfile ? 'on' : ''}`}>
              <Check className="h-3 w-3" />
            </span>
            <span>
              Rémunération selon profil (masque les fourchettes sur l'annonce publique)
            </span>
          </div>
        </div>

        {/* Description */}
        <div className="card mt-4">
          <h3 className="ct">Description</h3>
          <div className="mt-3.5">
            <label className="f-lab" htmlFor="jp-description">
              Description du poste *
            </label>
            <textarea
              id="jp-description"
              rows={10}
              className="f-ta"
              placeholder="Décrivez les missions, responsabilités et contexte du poste…"
              {...register('description')}
            />
            <div className="flex justify-between gap-3">
              {errors.description && (
                <p className="f-hint !text-redt">{errors.description.message}</p>
              )}
              <p className="f-hint ml-auto">{descriptionWatch?.length || 0}/3000 (min 500)</p>
            </div>
          </div>
          <div className="mt-3.5">
            <label className="f-lab" htmlFor="jp-qualifications">
              Profil recherché *
            </label>
            <textarea
              id="jp-qualifications"
              rows={6}
              className="f-ta"
              placeholder="Décrivez le profil idéal, les compétences requises, l'expérience attendue…"
              {...register('qualifications')}
            />
            <div className="flex justify-between gap-3">
              {errors.qualifications && (
                <p className="f-hint !text-redt">{errors.qualifications.message}</p>
              )}
              <p className="f-hint ml-auto">
                {qualificationsWatch?.length || 0}/3000 (min 150)
              </p>
            </div>
          </div>
          <div className="mt-3.5">
            <label className="f-lab" htmlFor="jp-employer">
              À propos de l'entreprise
            </label>
            <textarea
              id="jp-employer"
              rows={4}
              className="f-ta"
              placeholder="Présentez brièvement votre entreprise, sa culture, ses valeurs…"
              {...register('employer_overview')}
            />
          </div>
        </div>

        {/* Compétences */}
        <div className="card mt-4">
          <h3 className="ct">Compétences techniques</h3>
          <div className="relative mt-3.5">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-mut2" />
              <input
                ref={skillInputRef}
                type="text"
                value={skillSearch}
                onChange={(e) => {
                  setSkillSearch(e.target.value);
                  setShowSkillDropdown(true);
                }}
                onFocus={() => setShowSkillDropdown(true)}
                placeholder="Rechercher une compétence Turnover-IT…"
                aria-label="Rechercher une compétence Turnover-IT"
                className="f-in !pl-9"
              />
            </div>
            {showSkillDropdown && skillSearch.length >= 1 && (
              <div
                ref={skillDropdownRef}
                className="absolute z-10 mt-1 w-full max-h-60 overflow-y-auto rounded-[10px] border border-lin bg-sur shadow-lg"
              >
                {filteredSkills.length === 0 ? (
                  <p className="px-3 py-2.5 text-[12.5px] text-mut">
                    {skillsData?.total === 0
                      ? 'Aucune compétence trouvée. Vérifiez la synchronisation des skills.'
                      : 'Aucune compétence correspondante'}
                  </p>
                ) : (
                  filteredSkills.map((skill) => (
                    <button
                      key={skill.slug}
                      type="button"
                      onClick={() => selectSkill(skill)}
                      className="block w-full px-3 py-2 text-left text-[13px] text-ink hover:bg-srf2 transition-colors"
                    >
                      {skill.name}
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
          <p className="f-hint">
            Sélectionnez uniquement des compétences de la nomenclature Turnover-IT
          </p>
          {selectedSkills.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {selectedSkills.map((slug) => (
                <span key={slug} className="sk !inline-flex items-center gap-1.5">
                  {slug}
                  <button
                    type="button"
                    onClick={() => removeSkill(slug)}
                    aria-label={`Retirer ${slug}`}
                    className="hover:opacity-70"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Message d'erreur */}
        {(saveMutation.isError || publishMutation.isError) && (
          <div className="alert red">
            <AlertCircle className="h-[18px] w-[18px] shrink-0" />
            <span>
              {saveMutation.error
                ? getErrorMessage(saveMutation.error, "Erreur lors de la sauvegarde")
                : publishMutation.error
                ? getErrorMessage(publishMutation.error, "Erreur lors de la publication")
                : "Erreur lors de l'opération"}
            </span>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 mt-[18px]">
          <Button
            type="button"
            variant="ghost"
            onClick={() => navigate(`/rh/annonces/${postingId}`)}
          >
            Annuler
          </Button>
          {posting?.status === 'draft' ? (
            <>
              <Button
                type="button"
                variant="secondary"
                onClick={handleSubmit(onSaveDraft)}
                isLoading={saveMutation.isPending}
                disabled={actionsDisabled}
              >
                Enregistrer le brouillon
              </Button>
              <Button
                type="button"
                onClick={handleSubmit(onPublish)}
                isLoading={publishMutation.isPending}
                disabled={actionsDisabled}
              >
                Publier l'annonce
              </Button>
            </>
          ) : (
            <Button
              type="button"
              onClick={handleSubmit(onSaveDraft)}
              isLoading={saveMutation.isPending}
              disabled={actionsDisabled}
            >
              Enregistrer les modifications
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}
