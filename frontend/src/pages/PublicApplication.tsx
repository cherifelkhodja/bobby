/**
 * Public application form page (no authentication required).
 */

import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
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
} from 'lucide-react';
import { publicApplicationApi } from '../api/hr';

// Validation schema
const applicationSchema = z.object({
  first_name: z.string().min(1, 'Le prénom est requis').max(100),
  last_name: z.string().min(1, 'Le nom est requis').max(100),
  email: z.string().email('Email invalide'),
  phone: z
    .string()
    .min(10, 'Numéro de téléphone invalide')
    .regex(/^\+?[0-9\s-]+$/, 'Format de téléphone invalide'),
  job_title: z.string().min(1, 'Le titre du poste est requis').max(200),
  tjm_min: z.number().min(0, 'Le TJM minimum doit être positif'),
  tjm_max: z.number().min(0, 'Le TJM maximum doit être positif'),
  availability_date: z.string().min(1, 'La date de disponibilité est requise'),
});

type ApplicationFormData = z.infer<typeof applicationSchema>;

const CONTRACT_TYPE_LABELS: Record<string, string> = {
  CDI: 'CDI',
  CDD: 'CDD',
  FREELANCE: 'Freelance',
  INTERIM: 'Intérim',
  STAGE: 'Stage',
  ALTERNANCE: 'Alternance',
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

  // Fetch job posting info
  const { data: posting, isLoading, error } = useQuery({
    queryKey: ['public-job-posting', token],
    queryFn: () => publicApplicationApi.getJobPosting(token!),
    enabled: !!token,
  });

  // Form setup
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ApplicationFormData>({
    resolver: zodResolver(applicationSchema),
    defaultValues: {
      phone: '+33',
    },
  });

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: async (data: ApplicationFormData) => {
      if (!cvFile) throw new Error('CV requis');
      if (!token) throw new Error('Token invalide');

      return publicApplicationApi.submitApplication(token, {
        ...data,
        cv: cvFile,
      });
    },
    onSuccess: (result) => {
      setSubmitted(true);
      setSubmissionMessage(result.message);
    },
    onError: (error: Error) => {
      setSubmissionMessage(error.message || 'Une erreur est survenue');
    },
  });

  const onSubmit = (data: ApplicationFormData) => {
    // Validate TJM range
    if (data.tjm_max < data.tjm_min) {
      alert('Le TJM maximum doit être supérieur ou égal au TJM minimum');
      return;
    }

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
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
            Postuler à cette offre
          </h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
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
                <input
                  type="tel"
                  {...register('phone')}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="+33 6 12 34 56 78"
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

            {/* TJM Range */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  TJM minimum (€/jour) *
                </label>
                <input
                  type="number"
                  {...register('tjm_min', { valueAsNumber: true })}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="400"
                  min={0}
                />
                {errors.tjm_min && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    {errors.tjm_min.message}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  TJM maximum (€/jour) *
                </label>
                <input
                  type="number"
                  {...register('tjm_max', { valueAsNumber: true })}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="550"
                  min={0}
                />
                {errors.tjm_max && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                    {errors.tjm_max.message}
                  </p>
                )}
              </div>
            </div>

            {/* Availability Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Date de disponibilité *
              </label>
              <input
                type="date"
                {...register('availability_date')}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {errors.availability_date && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.availability_date.message}
                </p>
              )}
            </div>

            {/* CV Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                CV (PDF ou DOCX) *
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
                      PDF ou DOCX (max 10 Mo)
                    </p>
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
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
    </div>
  );
}
