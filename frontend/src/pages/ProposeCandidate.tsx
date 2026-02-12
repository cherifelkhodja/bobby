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
  Users,
  User,
  Mail,
  Phone,
} from 'lucide-react';

import { getPublishedOpportunity } from '../api/publishedOpportunities';
import { cooptationsApi } from '../api/cooptations';
import { getErrorMessage } from '../api/client';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { PageSpinner } from '../components/ui/Spinner';
import type { CooptationStatus } from '../types';

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

export default function ProposeCandidate() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(true);

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

  // Fetch existing cooptations for this opportunity
  const { data: cooptationsData, isLoading: loadingCooptations } = useQuery({
    queryKey: ['cooptations-by-opportunity', id],
    queryFn: () => cooptationsApi.listByOpportunity(id!, { page: 1, page_size: 50 }),
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
      queryClient.invalidateQueries({ queryKey: ['cooptations-by-opportunity', id] });
      queryClient.invalidateQueries({ queryKey: ['my-cooptations'] });
      queryClient.invalidateQueries({ queryKey: ['my-stats'] });
      toast.success('Cooptation soumise avec succes !');
      reset();
      setShowForm(false);
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const onSubmit = (data: CooptationFormData) => {
    if (!id) return;
    mutation.mutate({
      opportunity_id: id,
      ...data,
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

  const cooptations = cooptationsData?.items || [];
  const totalCooptations = cooptationsData?.total || 0;

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

          {/* Submitted cooptations list */}
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
              <Users className="h-5 w-5 text-primary-500" />
              Candidats proposes
              {totalCooptations > 0 && (
                <span className="ml-2 px-2.5 py-0.5 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full text-sm font-medium">
                  {totalCooptations}
                </span>
              )}
            </h2>

            {loadingCooptations ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-500" />
              </div>
            ) : cooptations.length === 0 ? (
              <div className="text-center py-8">
                <Users className="h-10 w-10 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Aucun candidat propose pour le moment.
                </p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  Soyez le premier a proposer un profil !
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100 dark:divide-gray-700">
                {cooptations.map((cooptation) => (
                  <div
                    key={cooptation.id}
                    className="py-3 first:pt-0 last:pb-0 flex items-center justify-between gap-4"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="flex-shrink-0 w-9 h-9 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center">
                        <User className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {cooptation.candidate_name}
                        </p>
                        <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                          <span className="flex items-center gap-1 truncate">
                            <Mail className="h-3 w-3" />
                            {cooptation.candidate_email}
                          </span>
                          {cooptation.candidate_phone && (
                            <span className="flex items-center gap-1">
                              <Phone className="h-3 w-3" />
                              {cooptation.candidate_phone}
                            </span>
                          )}
                        </div>
                        {cooptation.submitter_name && (
                          <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                            Propose par {cooptation.submitter_name} le {formatDate(cooptation.submitted_at)}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {cooptation.candidate_daily_rate && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {cooptation.candidate_daily_rate} EUR/j
                        </span>
                      )}
                      <Badge status={cooptation.status as CooptationStatus} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
