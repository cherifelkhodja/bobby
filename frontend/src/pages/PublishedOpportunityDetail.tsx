/**
 * PublishedOpportunityDetail - Page to view a published opportunity and its cooptations.
 * Accessible by admin and commercial users.
 */

import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  ChevronLeft,
  Loader2,
  AlertCircle,
  Calendar,
  Users,
  FileText,
  Hash,
  Sparkles,
  XCircle,
  RefreshCw,
  User,
  Mail,
  Phone,
} from 'lucide-react';
import {
  getPublishedOpportunity,
  closeOpportunity,
  reopenOpportunity,
} from '../api/publishedOpportunities';
import { cooptationsApi } from '../api/cooptations';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import type { PublishedOpportunityStatus } from '../types';

const STATUS_BADGES: Record<PublishedOpportunityStatus, { label: string; bgClass: string; textClass: string }> = {
  draft: {
    label: 'Brouillon',
    bgClass: 'bg-gray-100 dark:bg-gray-700',
    textClass: 'text-gray-800 dark:text-gray-300',
  },
  published: {
    label: 'Publiée',
    bgClass: 'bg-green-100 dark:bg-green-900/30',
    textClass: 'text-green-800 dark:text-green-300',
  },
  closed: {
    label: 'Clôturée',
    bgClass: 'bg-red-100 dark:bg-red-900/30',
    textClass: 'text-red-800 dark:text-red-300',
  },
};

const COOPTATION_STATUS_BADGES: Record<string, { label: string; bgClass: string; textClass: string }> = {
  pending: {
    label: 'En attente',
    bgClass: 'bg-yellow-100 dark:bg-yellow-900/30',
    textClass: 'text-yellow-800 dark:text-yellow-300',
  },
  in_review: {
    label: 'En cours d\'examen',
    bgClass: 'bg-blue-100 dark:bg-blue-900/30',
    textClass: 'text-blue-800 dark:text-blue-300',
  },
  interview: {
    label: 'En entretien',
    bgClass: 'bg-purple-100 dark:bg-purple-900/30',
    textClass: 'text-purple-800 dark:text-purple-300',
  },
  accepted: {
    label: 'Accepté',
    bgClass: 'bg-green-100 dark:bg-green-900/30',
    textClass: 'text-green-800 dark:text-green-300',
  },
  rejected: {
    label: 'Refusé',
    bgClass: 'bg-red-100 dark:bg-red-900/30',
    textClass: 'text-red-800 dark:text-red-300',
  },
};

export default function PublishedOpportunityDetail() {
  const { publishedId } = useParams<{ publishedId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Fetch published opportunity
  const {
    data: opportunity,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['published-opportunity', publishedId],
    queryFn: () => getPublishedOpportunity(publishedId!),
    enabled: !!publishedId,
  });

  // Fetch cooptations for this opportunity
  const { data: cooptationsData, isLoading: isLoadingCooptations } = useQuery({
    queryKey: ['cooptations-by-opportunity', publishedId],
    queryFn: () => cooptationsApi.listByOpportunity(publishedId!, { page_size: 100 }),
    enabled: !!publishedId,
  });

  // Close mutation
  const closeMutation = useMutation({
    mutationFn: () => closeOpportunity(publishedId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['published-opportunity', publishedId] });
      queryClient.invalidateQueries({ queryKey: ['my-boond-opportunities'] });
      toast.success('Opportunité clôturée');
    },
    onError: () => {
      toast.error('Erreur lors de la clôture');
    },
  });

  // Reopen mutation
  const reopenMutation = useMutation({
    mutationFn: () => reopenOpportunity(publishedId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['published-opportunity', publishedId] });
      queryClient.invalidateQueries({ queryKey: ['my-boond-opportunities'] });
      toast.success('Opportunité réactivée');
    },
    onError: () => {
      toast.error('Erreur lors de la réactivation');
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  if (error || !opportunity) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Opportunité non trouvée
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          Cette opportunité n'existe pas ou a été supprimée.
        </p>
        <Button variant="outline" onClick={() => navigate('/my-boond-opportunities')}>
          Retour aux opportunités
        </Button>
      </div>
    );
  }

  const statusBadge = STATUS_BADGES[opportunity.status as PublishedOpportunityStatus] || STATUS_BADGES.draft;
  const cooptations = cooptationsData?.items || [];

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        to="/my-boond-opportunities"
        className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
      >
        <ChevronLeft className="h-4 w-4" />
        Retour aux opportunités
      </Link>

      {/* Header */}
      <Card className="!p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100 truncate">
                {opportunity.title}
              </h1>
              <span className={`px-2.5 py-0.5 text-xs font-medium rounded-full flex-shrink-0 ${statusBadge.bgClass} ${statusBadge.textClass}`}>
                {statusBadge.label}
              </span>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Réf Boond: {opportunity.boond_opportunity_id}
              {' · '}
              Publiée le {new Date(opportunity.created_at).toLocaleDateString('fr-FR')}
            </p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            {opportunity.status === 'published' && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => closeMutation.mutate()}
                disabled={closeMutation.isPending}
                leftIcon={<XCircle className="h-4 w-4" />}
                className="text-red-600 border-red-300 hover:bg-red-50 dark:text-red-400 dark:border-red-700 dark:hover:bg-red-900/20"
              >
                {closeMutation.isPending ? 'Fermeture...' : 'Clôturer'}
              </Button>
            )}
            {opportunity.status === 'closed' && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => reopenMutation.mutate()}
                disabled={reopenMutation.isPending}
                leftIcon={<RefreshCw className="h-4 w-4" />}
              >
                {reopenMutation.isPending ? 'Réactivation...' : 'Réactiver'}
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="!p-3 text-center">
          <div className="flex items-center justify-center mb-1">
            <Hash className="h-4 w-4 text-gray-400" />
          </div>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {opportunity.boond_opportunity_id}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Réf Boond</p>
        </Card>
        <Card className="!p-3 text-center">
          <div className="flex items-center justify-center mb-1">
            <Sparkles className="h-4 w-4 text-gray-400" />
          </div>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {opportunity.skills.length}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Compétences</p>
        </Card>
        <Card className="!p-3 text-center">
          <div className="flex items-center justify-center mb-1">
            <Users className="h-4 w-4 text-gray-400" />
          </div>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {cooptations.length}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Cooptations</p>
        </Card>
        <Card className="!p-3 text-center">
          <div className="flex items-center justify-center mb-1">
            <Calendar className="h-4 w-4 text-gray-400" />
          </div>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {opportunity.end_date
              ? new Date(opportunity.end_date).toLocaleDateString('fr-FR')
              : '-'}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Date de fin</p>
        </Card>
      </div>

      {/* Skills */}
      {opportunity.skills.length > 0 && (
        <Card>
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Compétences extraites
            </h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {opportunity.skills.map((skill, index) => (
              <span
                key={index}
                className="px-2.5 py-1 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 rounded-md text-sm font-medium"
              >
                {skill}
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Description */}
      <Card>
        <div className="flex items-center gap-2 mb-3">
          <FileText className="h-4 w-4 text-gray-500 dark:text-gray-400" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Description anonymisée
          </h2>
        </div>
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <p className="text-gray-700 dark:text-gray-300 whitespace-pre-line text-sm leading-relaxed">
            {opportunity.description}
          </p>
        </div>
      </Card>

      {/* Cooptations table */}
      <Card className="!p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Cooptations ({cooptations.length})
            </h2>
          </div>
        </div>

        {isLoadingCooptations ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 text-primary-500 animate-spin" />
            <span className="ml-2 text-sm text-gray-500">Chargement...</span>
          </div>
        ) : cooptations.length === 0 ? (
          <div className="text-center py-8">
            <Users className="h-8 w-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Aucune cooptation pour cette opportunité
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800/50">
                <tr>
                  <th className="text-left py-2 px-4 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-xs">
                    Candidat
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-xs">
                    Contact
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-xs">
                    TJM
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-xs">
                    Statut
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-xs">
                    Soumis par
                  </th>
                  <th className="text-left py-2 px-4 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-xs">
                    Date
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {cooptations.map((cooptation) => {
                  const statusBadge = COOPTATION_STATUS_BADGES[cooptation.status] || COOPTATION_STATUS_BADGES.pending;
                  return (
                    <tr
                      key={cooptation.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-800/30"
                    >
                      <td className="py-2.5 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center flex-shrink-0">
                            <User className="h-3.5 w-3.5 text-primary-600 dark:text-primary-400" />
                          </div>
                          <span className="font-medium text-gray-900 dark:text-gray-100">
                            {cooptation.candidate_name}
                          </span>
                        </div>
                      </td>
                      <td className="py-2.5 px-4">
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400 text-xs">
                            <Mail className="h-3 w-3" />
                            {cooptation.candidate_email}
                          </div>
                          {cooptation.candidate_phone && (
                            <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400 text-xs">
                              <Phone className="h-3 w-3" />
                              {cooptation.candidate_phone}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 px-4 text-gray-600 dark:text-gray-400">
                        {cooptation.candidate_daily_rate
                          ? `${cooptation.candidate_daily_rate} €/j`
                          : '-'}
                      </td>
                      <td className="py-2.5 px-4">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusBadge.bgClass} ${statusBadge.textClass}`}>
                          {statusBadge.label}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-gray-600 dark:text-gray-400 text-xs">
                        {cooptation.submitter_name || '-'}
                      </td>
                      <td className="py-2.5 px-4 text-gray-600 dark:text-gray-400 text-xs">
                        {new Date(cooptation.submitted_at).toLocaleDateString('fr-FR')}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
