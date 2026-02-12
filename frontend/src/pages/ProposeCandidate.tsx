import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import {
  ArrowLeft,
  Calendar,
  Briefcase,
  CheckCircle,
  Clock,
  User,
  Upload,
  X,
  FileText,
} from 'lucide-react';

import { getPublishedOpportunity } from '../api/publishedOpportunities';
import { cooptationsApi } from '../api/cooptations';
import { getErrorMessage } from '../api/client';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { PageSpinner } from '../components/ui/Spinner';

const cooptationSchema = z.object({
  candidate_first_name: z.string().min(1, 'Prenom requis'),
  candidate_last_name: z.string().min(1, 'Nom requis'),
  candidate_email: z.string().email('Email invalide'),
  candidate_civility: z.enum(['M', 'Mme']),
  candidate_phone: z.string().optional(),
  candidate_daily_rate: z.coerce.number().positive().optional(),
  candidate_note: z.string().max(2000).optional(),
});

type CooptationFormData = z.infer<typeof cooptationSchema>;

const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];
const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

export default function ProposeCandidate() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(true);
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [cvError, setCvError] = useState<string | null>(null);

  // Fetch opportunity
  const {
    data: opportunity,
    isLoading: loadingOpportunity,
    error: opportunityError,
  } = useQuery({
    queryKey: ['published-opportunity', id],
    queryFn: () => getPublishedOpportunity(id!),
    enabled: !!id,
  });

  // Form
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CooptationFormData>({
    resolver: zodResolver(cooptationSchema),
    defaultValues: {
      candidate_civility: 'M',
    },
  });

  // Submit mutation
  const mutation = useMutation({
    mutationFn: cooptationsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-cooptations'] });
      queryClient.invalidateQueries({ queryKey: ['my-stats'] });
      toast.success('Cooptation soumise avec succes !');
      reset();
      setCvFile(null);
      setCvError(null);
      setShowForm(false);
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setCvError(null);
    if (!file) return;

    const hasValidExtension = ALLOWED_EXTENSIONS.some((ext) =>
      file.name.toLowerCase().endsWith(ext)
    );
    if (!ALLOWED_TYPES.includes(file.type) && !hasValidExtension) {
      setCvError('Format non supporte. Utilisez PDF ou DOCX.');
      return;
    }
    if (file.size > MAX_SIZE) {
      setCvError('Fichier trop volumineux. Maximum 10 Mo.');
      return;
    }
    setCvFile(file);
  };

  const removeFile = () => {
    setCvFile(null);
    setCvError(null);
  };

  const onSubmit = (data: CooptationFormData) => {
    if (!id) return;
    if (!cvFile) {
      setCvError('Le CV est obligatoire');
      return;
    }
    mutation.mutate({
      opportunity_id: id,
      ...data,
      cv: cvFile,
    });
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  if (loadingOpportunity) {
    return <PageSpinner />;
  }

  if (opportunityError || !opportunity) {
    return (
      <div className="text-center py-16">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Opportunite non trouvee
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mb-6">
          Cette opportunite n'existe pas ou a ete supprimee.
        </p>
        <Button onClick={() => navigate('/opportunities')}>
          Retour aux opportunites
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Back link */}
      <Link
        to={`/opportunities/${id}`}
        className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Retour a l'opportunite
      </Link>

      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Proposer un candidat
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Soumettez un profil pour cette opportunite
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: Opportunity summary */}
        <div className="lg:col-span-1 space-y-4">
          {/* Opportunity Card */}
          <Card className="!p-0 overflow-hidden">
            <div className="h-1.5 bg-gradient-to-r from-primary-500 to-primary-400" />
            <div className="p-5 space-y-4">
              <div>
                <span className={`inline-flex px-2.5 py-1 text-xs font-semibold rounded-full ${
                  opportunity.status === 'published'
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400'
                    : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                }`}>
                  {opportunity.status === 'published' ? 'Active' : opportunity.status_display}
                </span>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mt-2">
                  {opportunity.title}
                </h2>
              </div>

              {/* Meta */}
              <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <div className="flex items-center gap-2">
                  <Briefcase className="h-4 w-4 text-gray-400" />
                  <span>Publiee le {formatDate(opportunity.created_at)}</span>
                </div>
                {opportunity.end_date && (
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-amber-500" />
                    <span>Fin prevue : {formatDate(opportunity.end_date)}</span>
                  </div>
                )}
              </div>

              {/* Description */}
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1 flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5 text-primary-500" />
                  Description
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap line-clamp-6 leading-relaxed">
                  {opportunity.description}
                </p>
                <Link
                  to={`/opportunities/${id}`}
                  className="text-xs text-primary-600 dark:text-primary-400 hover:underline mt-1 inline-block"
                >
                  Voir la description complete
                </Link>
              </div>

              {/* Skills */}
              {opportunity.skills.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2 flex items-center gap-1.5">
                    <CheckCircle className="h-3.5 w-3.5 text-primary-500" />
                    Competences
                  </h3>
                  <div className="flex flex-wrap gap-1.5">
                    {opportunity.skills.map((skill) => (
                      <span
                        key={skill}
                        className="px-2.5 py-1 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-md text-xs font-medium"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Right column: Form + Cooptations list */}
        <div className="lg:col-span-2 space-y-6">
          {/* Cooptation Form */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                <User className="h-5 w-5 text-primary-500" />
                Informations du candidat
              </h2>
              {!showForm && (
                <Button size="sm" onClick={() => setShowForm(true)}>
                  Nouveau candidat
                </Button>
              )}
            </div>

            {showForm ? (
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Civilite
                    </label>
                    <select
                      className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      {...register('candidate_civility')}
                    >
                      <option value="M">M.</option>
                      <option value="Mme">Mme</option>
                    </select>
                  </div>
                  <Input
                    label="Prenom"
                    error={errors.candidate_first_name?.message}
                    {...register('candidate_first_name')}
                  />
                  <Input
                    label="Nom"
                    error={errors.candidate_last_name?.message}
                    {...register('candidate_last_name')}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Email"
                    type="email"
                    error={errors.candidate_email?.message}
                    {...register('candidate_email')}
                  />
                  <Input
                    label="Telephone"
                    placeholder="0612345678"
                    error={errors.candidate_phone?.message}
                    {...register('candidate_phone')}
                  />
                </div>

                <Input
                  label="TJM souhaite (EUR/jour)"
                  type="number"
                  placeholder="500"
                  error={errors.candidate_daily_rate?.message}
                  {...register('candidate_daily_rate')}
                />

                {/* CV Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    CV <span className="text-red-500">*</span>
                  </label>
                  {cvFile ? (
                    <div className="flex items-center gap-3 p-3 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg">
                      <FileText className="h-5 w-5 text-primary-600 dark:text-primary-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {cvFile.name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {formatFileSize(cvFile.size)}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={removeFile}
                        className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ) : (
                    <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:border-primary-400 dark:hover:border-primary-500 transition-colors bg-gray-50 dark:bg-gray-800/30">
                      <div className="flex flex-col items-center">
                        <Upload className="h-6 w-6 text-gray-400 mb-1" />
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          <span className="font-medium text-primary-600 dark:text-primary-400">
                            Cliquez pour choisir
                          </span>{' '}
                          ou glissez-deposez
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          PDF ou DOCX (max 10 Mo)
                        </p>
                      </div>
                      <input
                        type="file"
                        className="hidden"
                        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        onChange={handleFileChange}
                      />
                    </label>
                  )}
                  {cvError && (
                    <p className="mt-1 text-sm text-red-600 dark:text-red-400">{cvError}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Note / Commentaire
                  </label>
                  <textarea
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm min-h-[100px] focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Informations complementaires sur le candidat..."
                    {...register('candidate_note')}
                  />
                  {errors.candidate_note && (
                    <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                      {errors.candidate_note.message}
                    </p>
                  )}
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => navigate(`/opportunities/${id}`)}
                  >
                    Annuler
                  </Button>
                  <Button
                    type="submit"
                    isLoading={mutation.isPending}
                    disabled={opportunity.status !== 'published'}
                  >
                    Soumettre la cooptation
                  </Button>
                </div>
              </form>
            ) : (
              <div className="text-center py-6 text-gray-500 dark:text-gray-400">
                <CheckCircle className="h-10 w-10 text-emerald-500 mx-auto mb-3" />
                <p className="font-medium text-gray-900 dark:text-gray-100">
                  Cooptation soumise avec succes !
                </p>
                <p className="text-sm mt-1">
                  Vous pouvez proposer un autre candidat ou revenir a l'opportunite.
                </p>
              </div>
            )}
          </Card>

        </div>
      </div>
    </div>
  );
}
