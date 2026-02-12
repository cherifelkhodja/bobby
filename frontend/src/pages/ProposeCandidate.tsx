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
  User,
  Upload,
  X,
  FileText,
} from 'lucide-react';

import { getPublishedOpportunity } from '../api/publishedOpportunities';
import { cooptationsApi } from '../api/cooptations';
import { getErrorMessage } from '../api/client';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { PageSpinner } from '../components/ui/Spinner';

const cooptationSchema = z.object({
  candidate_first_name: z.string().min(1, 'Prenom requis'),
  candidate_last_name: z.string().min(1, 'Nom requis'),
  candidate_email: z.string().email('Email invalide'),
  candidate_civility: z.enum(['M', 'Mme']),
  candidate_phone: z.string().min(1, 'Telephone requis'),
  candidate_daily_rate: z.coerce.number().positive('TJM requis'),
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
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Back link */}
      <Link
        to={`/opportunities/${id}`}
        className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Retour a l'opportunite
      </Link>

      {/* Opportunity banner */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
              Opportunite
            </p>
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 truncate">
              {opportunity.title}
            </h2>
            <div className="flex items-center gap-4 mt-1.5 text-xs text-gray-500 dark:text-gray-400">
              <span className="flex items-center gap-1">
                <Briefcase className="h-3 w-3" />
                {formatDate(opportunity.created_at)}
              </span>
              {opportunity.end_date && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  Fin : {formatDate(opportunity.end_date)}
                </span>
              )}
            </div>
          </div>
          <span className={`flex-shrink-0 inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
            opportunity.status === 'published'
              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400'
              : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
          }`}>
            {opportunity.status === 'published' ? 'Active' : opportunity.status_display}
          </span>
        </div>
        {opportunity.skills.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            {opportunity.skills.map((skill) => (
              <span
                key={skill}
                className="px-2 py-0.5 bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded text-xs border border-gray-200 dark:border-gray-600"
              >
                {skill}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Form card */}
      {showForm ? (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
          <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <User className="h-5 w-5 text-primary-500" />
              Proposer un candidat
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              Remplissez les informations du profil que vous souhaitez recommander.
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-5">
            {/* Identity */}
            <div>
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                Identite
              </h3>
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
            </div>

            {/* Contact */}
            <div>
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                Contact & tarif
              </h3>
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
              <div className="mt-4">
                <Input
                  label="TJM souhaite (EUR/jour)"
                  type="number"
                  placeholder="500"
                  error={errors.candidate_daily_rate?.message}
                  {...register('candidate_daily_rate')}
                />
              </div>
            </div>

            {/* CV Upload */}
            <div>
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                CV <span className="text-red-500">*</span>
              </h3>
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
                <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:border-primary-400 dark:hover:border-primary-500 transition-colors bg-gray-50 dark:bg-gray-800/30">
                  <div className="flex flex-col items-center">
                    <Upload className="h-5 w-5 text-gray-400 mb-1" />
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

            {/* Note */}
            <div>
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                Commentaire
              </h3>
              <textarea
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm min-h-[80px] focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="Informations complementaires sur le candidat..."
                {...register('candidate_note')}
              />
              {errors.candidate_note && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.candidate_note.message}
                </p>
              )}
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2 border-t border-gray-100 dark:border-gray-700">
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
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm p-8 text-center">
          <CheckCircle className="h-12 w-12 text-emerald-500 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Cooptation soumise avec succes !
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Votre recommandation a bien ete enregistree.
          </p>
          <div className="flex justify-center gap-3 mt-6">
            <Button variant="secondary" onClick={() => setShowForm(true)}>
              Proposer un autre candidat
            </Button>
            <Button onClick={() => navigate(`/opportunities/${id}`)}>
              Retour a l'opportunite
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
