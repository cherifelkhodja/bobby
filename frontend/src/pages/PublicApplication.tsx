/**
 * Public application form page (no authentication required).
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import PhoneInput, { isValidPhoneNumber } from 'react-phone-number-input';
import 'react-phone-number-input/style.css';
import {
  Check,
  CheckCircle,
  AlertCircle,
  Loader2,
  FileText,
  X,
  HelpCircle,
} from 'lucide-react';
import { publicApplicationApi } from '../api/hr';
import { useFormCache } from '../hooks/useFormCache';
import { Button } from '../components/ui/Button';
import {
  AVAILABILITY_OPTIONS,
  ENGLISH_LEVELS,
  EMPLOYEE_CONTRACT_TYPES,
  FREELANCE_CONTRACT_TYPES,
  CONTRACT_TYPE_LABELS,
  REMOTE_LABELS,
  EXPERIENCE_LABELS,
} from '../constants/hr';

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
  english_level: z.string().min(1, "Le niveau d'anglais est requis"),
  tjm_current: z.number().min(0).optional().nullable(),
  tjm_desired: z.number().min(0).optional().nullable(),
  salary_current: z.number().min(0).optional().nullable(),
  salary_desired: z.number().min(0).optional().nullable(),
});

type ApplicationFormData = z.infer<typeof applicationSchema>;

function PublicShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="p-bg">
      <div className="p-wrap max-w-[640px]">
        <div className="p-top">
          <span className="logo">Gemini Consulting · Carrières</span>
        </div>
        {children}
        <p className="p-foot">
          Candidature sécurisée · vos données ne sont jamais partagées hors du processus de
          recrutement
        </p>
      </div>
    </div>
  );
}

export default function PublicApplication() {
  const { token } = useParams<{ token: string }>();
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [submissionMessage, setSubmissionMessage] = useState('');
  const [showEnglishTooltip, setShowEnglishTooltip] = useState<string | null>(null);
  const [isFreelance, setIsFreelance] = useState(false);
  const [isEmployee, setIsEmployee] = useState(false);
  const [rgpdAccepted, setRgpdAccepted] = useState(false);
  const checkboxesInitializedRef = useRef(false);

  // Form cache (persists data across page reloads for 48h)
  const formCache = useFormCache<Record<string, unknown>>(token, 'bobby_application_form');
  const cachedData = formCache.load();

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
      first_name: (cachedData?.first_name as string) || '',
      last_name: (cachedData?.last_name as string) || '',
      email: (cachedData?.email as string) || '',
      phone: (cachedData?.phone as string) || '',
      job_title: (cachedData?.job_title as string) || '',
      availability: (cachedData?.availability as string) || '',
      english_level: (cachedData?.english_level as string) || '',
      tjm_current: (cachedData?.tjm_current as number) ?? undefined,
      tjm_desired: (cachedData?.tjm_desired as number) ?? undefined,
      salary_current: (cachedData?.salary_current as number) ?? undefined,
      salary_desired: (cachedData?.salary_desired as number) ?? undefined,
    },
  });

  // Determine allowed employment statuses based on contract types
  const allowsEmployee = posting?.contract_types?.some((ct) => EMPLOYEE_CONTRACT_TYPES.includes(ct)) ?? false;
  const allowsFreelance = posting?.contract_types?.some((ct) => FREELANCE_CONTRACT_TYPES.includes(ct)) ?? false;

  // Initialize checkboxes from cached data or posting (only once)
  useEffect(() => {
    if (checkboxesInitializedRef.current) return;
    if (!posting) return;

    const cachedStatus = cachedData?.employment_status as string | undefined;
    if (cachedStatus) {
      const statuses = cachedStatus.split(',');
      setIsFreelance(statuses.includes('freelance') && allowsFreelance);
      setIsEmployee(statuses.includes('employee') && allowsEmployee);
    } else {
      if (allowsFreelance && !allowsEmployee) setIsFreelance(true);
      else if (allowsEmployee && !allowsFreelance) setIsEmployee(true);
    }
    checkboxesInitializedRef.current = true;
  }, [posting, cachedData, allowsEmployee, allowsFreelance]);

  // Watch all form values for caching
  const watchedValues = watch();

  // Save form data to cache on changes (debounced)
  const saveToCache = useCallback(() => {
    if (token && !submitted) {
      const statuses: string[] = [];
      if (isFreelance) statuses.push('freelance');
      if (isEmployee) statuses.push('employee');

      formCache.save({
        ...watchedValues,
        employment_status: statuses.join(','),
      });
    }
  }, [token, watchedValues, submitted, isFreelance, isEmployee, formCache]);

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
      formCache.clear();
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
      <PublicShell>
        <div className="p-card text-center px-[22px] py-9">
          <Loader2 className="h-8 w-8 animate-spin text-prit mx-auto" />
          <p className="notec mt-3.5">Chargement de l'offre…</p>
        </div>
      </PublicShell>
    );
  }

  // Error state
  if (error || !posting) {
    return (
      <PublicShell>
        <div className="p-card text-center px-[22px] py-9">
          <div className="alert red !inline-flex !mt-0">
            <AlertCircle className="h-[18px] w-[18px] flex-shrink-0" />
            <span>Offre non disponible</span>
          </div>
          <p className="notec mt-3.5">
            Cette offre d'emploi n'existe pas ou n'est plus disponible.
          </p>
        </div>
      </PublicShell>
    );
  }

  // Success state
  if (submitted) {
    return (
      <PublicShell>
        <div className="p-card text-center px-[22px] py-9">
          <div className="okbox !inline-flex !m-0 !mb-3.5">
            <CheckCircle className="h-4 w-4 flex-shrink-0" />
            <span>Candidature envoyée !</span>
          </div>
          <p className="notec">
            Votre CV est en cours d'analyse. L'équipe RH revient vers vous sous 5 jours ouvrés.
          </p>
          <Button
            type="button"
            variant="secondary"
            className="mt-4"
            onClick={() => {
              setCvFile(null);
              setRgpdAccepted(false);
              setSubmitted(false);
            }}
          >
            Nouvelle candidature
          </Button>
        </div>
      </PublicShell>
    );
  }

  const locationLabel =
    posting.location_city || posting.location_region || posting.location_country;

  return (
    <PublicShell>
      {/* Annonce */}
      <div className="p-card">
        <h1 className="p-h">{posting.title}</h1>
        <p className="sub mt-1">
          Gemini Consulting
          {locationLabel ? ` · ${locationLabel}` : ''}
          {posting.start_date
            ? ` · démarrage ${new Date(posting.start_date).toLocaleDateString('fr-FR')}`
            : ''}
        </p>

        <div className="flex flex-wrap gap-2 mt-3">
          {posting.contract_types.map((type) => (
            <span key={type} className="st st-sla">
              {CONTRACT_TYPE_LABELS[type] || type}
            </span>
          ))}
          {posting.remote && (
            <span className="st st-sla">{REMOTE_LABELS[posting.remote] || posting.remote}</span>
          )}
          {posting.experience_level && (
            <span className="st st-sla">
              {EXPERIENCE_LABELS[posting.experience_level] || posting.experience_level}
            </span>
          )}
          {(posting.salary_min_daily || posting.salary_max_daily) && (
            <span className="st st-sla">
              TJM {posting.salary_min_daily}–{posting.salary_max_daily} € / jour
            </span>
          )}
        </div>

        <div className="border-t border-lin2 mt-4 pt-4">
          <h2 className="ct">Description</h2>
          <p className="mt-1.5 text-[13px] leading-relaxed text-mut whitespace-pre-wrap">
            {posting.description}
          </p>
        </div>

        <div className="mt-4">
          <h2 className="ct">Profil recherché</h2>
          <p className="mt-1.5 text-[13px] leading-relaxed text-mut whitespace-pre-wrap">
            {posting.qualifications}
          </p>
        </div>

        {posting.skills.length > 0 && (
          <div className="mt-4">
            <h2 className="ct">Compétences</h2>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {posting.skills.map((skill, index) => (
                <span key={index} className="sk">
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Formulaire de candidature */}
      <div className="p-card mt-3.5">
        <h3 className="ct">Vos informations</h3>

        {/* Cache restoration indicator */}
        {formCache.hasCachedData && (
          <div className="infob mt-3.5">Vos informations précédentes ont été restaurées.</div>
        )}

        <form onSubmit={handleSubmit(onSubmit)}>
          {/* Civility */}
          <div className="mt-3.5">
            <span className="f-lab">Civilité</span>
            <div className="flex gap-2">
              {(['M', 'Mme'] as const).map((civ) => (
                <label
                  key={civ}
                  className="tg cursor-pointer has-[:checked]:border-pri has-[:checked]:bg-pris has-[:checked]:text-prit has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-pri"
                >
                  <input type="radio" value={civ} {...register('civility')} className="sr-only" />
                  {civ === 'M' ? 'M.' : 'Mme'}
                </label>
              ))}
            </div>
          </div>

          {/* Identité & contact */}
          <div className="f-grid mt-3.5">
            <div>
              <label className="f-lab" htmlFor="pa-first-name">
                Prénom *
              </label>
              <input
                id="pa-first-name"
                type="text"
                {...register('first_name')}
                className="f-in"
                placeholder="Jean"
              />
              {errors.first_name && (
                <p className="f-hint !text-redt">{errors.first_name.message}</p>
              )}
            </div>
            <div>
              <label className="f-lab" htmlFor="pa-last-name">
                Nom *
              </label>
              <input
                id="pa-last-name"
                type="text"
                {...register('last_name')}
                className="f-in"
                placeholder="DUPONT"
              />
              {errors.last_name && <p className="f-hint !text-redt">{errors.last_name.message}</p>}
            </div>
            <div>
              <label className="f-lab" htmlFor="pa-email">
                Email *
              </label>
              <input
                id="pa-email"
                type="email"
                {...register('email')}
                className="f-in"
                placeholder="jean.dupont@email.com"
              />
              {errors.email && <p className="f-hint !text-redt">{errors.email.message}</p>}
            </div>
            <div>
              <label className="f-lab">Téléphone *</label>
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
                  />
                )}
              />
              {errors.phone && <p className="f-hint !text-redt">{errors.phone.message}</p>}
            </div>
          </div>

          {/* Job Title */}
          <div className="mt-3.5">
            <label className="f-lab" htmlFor="pa-job-title">
              Titre du poste actuel/recherché *
            </label>
            <input
              id="pa-job-title"
              type="text"
              {...register('job_title')}
              className="f-in"
              placeholder="Développeur Full Stack"
            />
            {errors.job_title && <p className="f-hint !text-redt">{errors.job_title.message}</p>}
          </div>

          {/* Statut professionnel */}
          <h3 className="ct mt-5">Votre statut professionnel</h3>
          <div className="f-grid mt-3">
            {allowsFreelance && (
              <button
                type="button"
                onClick={() => setIsFreelance((v) => !v)}
                className={`tcard text-left ${isFreelance ? 'on' : ''}`}
              >
                <p className="tt">Freelance</p>
                <p className="td2">Vous facturez en TJM</p>
              </button>
            )}
            {allowsEmployee && (
              <button
                type="button"
                onClick={() => setIsEmployee((v) => !v)}
                className={`tcard text-left ${isEmployee ? 'on' : ''}`}
              >
                <p className="tt">Salarié</p>
                <p className="td2">Vous visez un CDI</p>
              </button>
            )}
          </div>
          {allowsFreelance && (
            <p className="f-hint">
              Portage salarial accepté (uniquement via une vraie société de portage).
            </p>
          )}
          {!isFreelance && !isEmployee && (
            <p className="f-hint !text-redt">Veuillez sélectionner au moins un statut</p>
          )}

          {/* Freelance Fields - TJM */}
          {showFreelanceFields && (
            <div className="f-grid mt-3.5">
              <div>
                <label className="f-lab" htmlFor="pa-tjm-current">
                  TJM actuel (€ / jour) *
                </label>
                <input
                  id="pa-tjm-current"
                  type="number"
                  {...register('tjm_current', { valueAsNumber: true })}
                  className="f-in"
                  placeholder="450"
                  min={0}
                />
                {errors.tjm_current && (
                  <p className="f-hint !text-redt">{errors.tjm_current.message}</p>
                )}
              </div>
              <div>
                <label className="f-lab" htmlFor="pa-tjm-desired">
                  TJM souhaité (€ / jour) *
                </label>
                <input
                  id="pa-tjm-desired"
                  type="number"
                  {...register('tjm_desired', { valueAsNumber: true })}
                  className="f-in"
                  placeholder="500"
                  min={0}
                />
                {errors.tjm_desired && (
                  <p className="f-hint !text-redt">{errors.tjm_desired.message}</p>
                )}
              </div>
            </div>
          )}

          {/* Employee Fields - Salary */}
          {showEmployeeFields && (
            <div className="f-grid mt-3.5">
              <div>
                <label className="f-lab" htmlFor="pa-salary-current">
                  Salaire actuel (€ / an) *
                </label>
                <input
                  id="pa-salary-current"
                  type="number"
                  {...register('salary_current', { valueAsNumber: true })}
                  className="f-in"
                  placeholder="45000"
                  min={0}
                />
                {errors.salary_current && (
                  <p className="f-hint !text-redt">{errors.salary_current.message}</p>
                )}
              </div>
              <div>
                <label className="f-lab" htmlFor="pa-salary-desired">
                  Salaire souhaité (€ / an) *
                </label>
                <input
                  id="pa-salary-desired"
                  type="number"
                  {...register('salary_desired', { valueAsNumber: true })}
                  className="f-in"
                  placeholder="50000"
                  min={0}
                />
                {errors.salary_desired && (
                  <p className="f-hint !text-redt">{errors.salary_desired.message}</p>
                )}
              </div>
            </div>
          )}

          {/* Disponibilité & anglais */}
          <div className="f-grid mt-3.5">
            <div>
              <label className="f-lab" htmlFor="pa-availability">
                Disponibilité *
              </label>
              <select id="pa-availability" {...register('availability')} className="f-in !px-2.5">
                <option value="">— Sélectionner —</option>
                {AVAILABILITY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              {errors.availability && (
                <p className="f-hint !text-redt">{errors.availability.message}</p>
              )}
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <label className="f-lab" htmlFor="pa-english-level">
                  Niveau d'anglais *
                </label>
                <div className="relative mb-1.5">
                  <button
                    type="button"
                    onClick={() => setShowEnglishTooltip(showEnglishTooltip ? null : 'all')}
                    className="text-mut2 hover:text-ink transition-colors"
                    aria-label="Aide sur les niveaux d'anglais"
                  >
                    <HelpCircle className="h-4 w-4" />
                  </button>
                  {showEnglishTooltip && (
                    <div className="absolute right-0 sm:left-0 sm:right-auto top-6 z-50 w-72 card !p-3.5">
                      <div className="flex justify-between items-center mb-2">
                        <span className="dn">Niveaux d'anglais</span>
                        <button
                          type="button"
                          onClick={() => setShowEnglishTooltip(null)}
                          className="text-mut2 hover:text-ink transition-colors"
                          aria-label="Fermer"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                      <div className="space-y-2">
                        {ENGLISH_LEVELS.map((level) => (
                          <p key={level.value} className="text-[11.5px] leading-relaxed">
                            <span className="font-semibold text-ink">{level.label} :</span>{' '}
                            <span className="text-mut">{level.description}</span>
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <select
                id="pa-english-level"
                {...register('english_level')}
                className="f-in !px-2.5"
              >
                <option value="">— Sélectionner —</option>
                {ENGLISH_LEVELS.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </select>
              {errors.english_level && (
                <p className="f-hint !text-redt">{errors.english_level.message}</p>
              )}
            </div>
          </div>

          {/* CV Upload */}
          <h3 className="ct mt-5">Votre CV *</h3>
          {cvFile ? (
            <div className="filecard mt-3">
              <div className="dico">
                <FileText className="h-4 w-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="dn truncate">{cvFile.name}</p>
                <p className="ds">{(cvFile.size / 1024 / 1024).toFixed(2)} Mo</p>
              </div>
              <Button type="button" variant="secondary" size="sm" onClick={() => setCvFile(null)}>
                Retirer
              </Button>
            </div>
          ) : (
            <label className="drop block !p-6 mt-3 cursor-pointer">
              <p className="dropt !mt-0">
                <b className="text-prit">Cliquez pour choisir</b> ou glissez-déposez
              </p>
              <p className="drops">PDF ou DOCX · 10 Mo max</p>
              <input
                type="file"
                className="hidden"
                accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={handleFileChange}
              />
            </label>
          )}

          {/* Consentement RGPD */}
          <label className="ckrow mt-4 select-none">
            <input
              type="checkbox"
              className="sr-only"
              checked={rgpdAccepted}
              onChange={(e) => setRgpdAccepted(e.target.checked)}
            />
            <span className={`ck ${rgpdAccepted ? 'on' : ''}`}>
              <Check className="h-3 w-3" strokeWidth={3} />
            </span>
            <span>
              J'accepte que mes données soient traitées dans le cadre de ce recrutement (RGPD —
              conservation 2 ans max).
            </span>
          </label>

          {/* Error Message */}
          {submitMutation.isError && (
            <div className="alert red">
              <AlertCircle className="h-[18px] w-[18px] flex-shrink-0" />
              <span>{submissionMessage}</span>
            </div>
          )}

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full mt-[18px]"
            disabled={submitMutation.isPending || !cvFile || !rgpdAccepted}
            isLoading={submitMutation.isPending}
          >
            {submitMutation.isPending ? 'Envoi en cours…' : 'Envoyer ma candidature'}
          </Button>
        </form>
      </div>
    </PublicShell>
  );
}
