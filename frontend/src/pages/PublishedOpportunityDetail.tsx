/**
 * PublishedOpportunityDetail - Page to view a published opportunity and its cooptations.
 * Accessible by admin and commercial users.
 */

import { Fragment, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Dialog, Transition } from '@headlessui/react';
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
  Download,
  X,
  Euro,
  MessageSquare,
  Clock,
  ChevronRight,
  Pencil,
  CheckCircle,
  Ban,
  ArrowRight,
} from 'lucide-react';
import {
  getPublishedOpportunity,
  closeOpportunity,
  reopenOpportunity,
  updatePublishedOpportunity,
} from '../api/publishedOpportunities';
import { cooptationsApi } from '../api/cooptations';
import { getErrorMessage } from '../api/client';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import type { Cooptation, CooptationStatus, PublishedOpportunity, PublishedOpportunityStatus } from '../types';

const STATUS_BADGES: Record<PublishedOpportunityStatus, { label: string; bgClass: string; textClass: string }> = {
  draft: {
    label: 'Brouillon',
    bgClass: 'bg-gray-100 dark:bg-gray-700',
    textClass: 'text-gray-800 dark:text-gray-300',
  },
  published: {
    label: 'Publiee',
    bgClass: 'bg-green-100 dark:bg-green-900/30',
    textClass: 'text-green-800 dark:text-green-300',
  },
  closed: {
    label: 'Cloturee',
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
    label: 'Accepte',
    bgClass: 'bg-green-100 dark:bg-green-900/30',
    textClass: 'text-green-800 dark:text-green-300',
  },
  rejected: {
    label: 'Refuse',
    bgClass: 'bg-red-100 dark:bg-red-900/30',
    textClass: 'text-red-800 dark:text-red-300',
  },
};

// Valid status transitions
const VALID_TRANSITIONS: Record<CooptationStatus, CooptationStatus[]> = {
  pending: ['in_review', 'rejected'],
  in_review: ['interview', 'accepted', 'rejected'],
  interview: ['accepted', 'rejected'],
  accepted: [],
  rejected: ['pending'],
};

const STATUS_ACTION_CONFIG: Record<CooptationStatus, { label: string; icon: typeof CheckCircle; colorClass: string }> = {
  pending: { label: 'Remettre en attente', icon: RefreshCw, colorClass: 'text-yellow-600 border-yellow-300 hover:bg-yellow-50 dark:text-yellow-400 dark:border-yellow-700 dark:hover:bg-yellow-900/20' },
  in_review: { label: 'En cours d\'examen', icon: ArrowRight, colorClass: 'text-blue-600 border-blue-300 hover:bg-blue-50 dark:text-blue-400 dark:border-blue-700 dark:hover:bg-blue-900/20' },
  interview: { label: 'Entretien', icon: ArrowRight, colorClass: 'text-purple-600 border-purple-300 hover:bg-purple-50 dark:text-purple-400 dark:border-purple-700 dark:hover:bg-purple-900/20' },
  accepted: { label: 'Accepter', icon: CheckCircle, colorClass: 'text-green-600 border-green-300 hover:bg-green-50 dark:text-green-400 dark:border-green-700 dark:hover:bg-green-900/20' },
  rejected: { label: 'Refuser', icon: Ban, colorClass: 'text-red-600 border-red-300 hover:bg-red-50 dark:text-red-400 dark:border-red-700 dark:hover:bg-red-900/20' },
};

function CandidateDrawer({
  cooptation,
  isOpen,
  onClose,
  onStatusUpdated,
}: {
  cooptation: Cooptation | null;
  isOpen: boolean;
  onClose: () => void;
  onStatusUpdated: () => void;
}) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [statusAction, setStatusAction] = useState<CooptationStatus | null>(null);
  const [statusComment, setStatusComment] = useState('');
  const [statusError, setStatusError] = useState<string | null>(null);

  const statusMutation = useMutation({
    mutationFn: ({ id, status, comment }: { id: string; status: string; comment?: string }) =>
      cooptationsApi.updateStatus(id, status, comment || undefined),
    onSuccess: () => {
      toast.success('Statut mis a jour');
      setStatusAction(null);
      setStatusComment('');
      setStatusError(null);
      onStatusUpdated();
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const handleDownloadCv = async () => {
    if (!cooptation) return;
    setIsDownloading(true);
    try {
      const { url } = await cooptationsApi.getCvDownloadUrl(cooptation.id);
      window.open(url, '_blank');
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsDownloading(false);
    }
  };

  const handleStatusChange = (newStatus: CooptationStatus) => {
    if (newStatus === 'rejected') {
      setStatusAction(newStatus);
      setStatusComment('');
      setStatusError(null);
    } else {
      setStatusAction(newStatus);
      setStatusComment('');
      setStatusError(null);
    }
  };

  const handleConfirmStatus = () => {
    if (!cooptation || !statusAction) return;

    if (statusAction === 'rejected' && !statusComment.trim()) {
      setStatusError('Le commentaire est obligatoire pour un rejet');
      return;
    }

    statusMutation.mutate({
      id: cooptation.id,
      status: statusAction,
      comment: statusComment.trim() || undefined,
    });
  };

  const handleCancelStatus = () => {
    setStatusAction(null);
    setStatusComment('');
    setStatusError(null);
  };

  if (!cooptation) return null;

  const statusBadge = COOPTATION_STATUS_BADGES[cooptation.status] || COOPTATION_STATUS_BADGES.pending;
  const nextStatuses = VALID_TRANSITIONS[cooptation.status] || [];

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 overflow-hidden">
            <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
              <Transition.Child
                as={Fragment}
                enter="transform transition ease-in-out duration-300"
                enterFrom="translate-x-full"
                enterTo="translate-x-0"
                leave="transform transition ease-in-out duration-200"
                leaveFrom="translate-x-0"
                leaveTo="translate-x-full"
              >
                <Dialog.Panel className="pointer-events-auto w-screen max-w-md">
                  <div className="flex h-full flex-col bg-white dark:bg-gray-900 shadow-xl">
                    {/* Header */}
                    <div className="px-4 py-4 border-b border-gray-200 dark:border-gray-700">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center">
                            <User className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                          </div>
                          <div>
                            <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                              {cooptation.candidate_name}
                            </Dialog.Title>
                            <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${statusBadge.bgClass} ${statusBadge.textClass}`}>
                              {statusBadge.label}
                            </span>
                          </div>
                        </div>
                        <button
                          onClick={onClose}
                          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                        >
                          <X className="h-5 w-5" />
                        </button>
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
                      {/* Status actions */}
                      {nextStatuses.length > 0 && (
                        <div>
                          <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                            Actions
                          </h3>
                          {!statusAction ? (
                            <div className="flex flex-wrap gap-2">
                              {nextStatuses.map((nextStatus) => {
                                const config = STATUS_ACTION_CONFIG[nextStatus];
                                const Icon = config.icon;
                                return (
                                  <button
                                    key={nextStatus}
                                    onClick={() => handleStatusChange(nextStatus)}
                                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium border rounded-lg transition-colors ${config.colorClass}`}
                                  >
                                    <Icon className="h-3.5 w-3.5" />
                                    {config.label}
                                  </button>
                                );
                              })}
                            </div>
                          ) : (
                            <div className="space-y-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                              <div className="flex items-center gap-2">
                                <span className="text-sm text-gray-700 dark:text-gray-300">
                                  Changer le statut vers :
                                </span>
                                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${COOPTATION_STATUS_BADGES[statusAction]?.bgClass} ${COOPTATION_STATUS_BADGES[statusAction]?.textClass}`}>
                                  {COOPTATION_STATUS_BADGES[statusAction]?.label}
                                </span>
                              </div>
                              <div>
                                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                                  Commentaire {statusAction === 'rejected' ? <span className="text-red-500">*</span> : '(optionnel)'}
                                </label>
                                <textarea
                                  value={statusComment}
                                  onChange={(e) => {
                                    setStatusComment(e.target.value);
                                    if (statusError) setStatusError(null);
                                  }}
                                  placeholder={statusAction === 'rejected' ? 'Motif du rejet...' : 'Commentaire...'}
                                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm min-h-[60px] focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                                />
                                {statusError && (
                                  <p className="mt-1 text-xs text-red-600 dark:text-red-400">{statusError}</p>
                                )}
                              </div>
                              <div className="flex gap-2">
                                <button
                                  onClick={handleCancelStatus}
                                  className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
                                >
                                  Annuler
                                </button>
                                <Button
                                  size="sm"
                                  onClick={handleConfirmStatus}
                                  isLoading={statusMutation.isPending}
                                >
                                  Confirmer
                                </Button>
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Contact */}
                      <div>
                        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                          Contact
                        </h3>
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-sm">
                            <Mail className="h-4 w-4 text-gray-400 flex-shrink-0" />
                            <a
                              href={`mailto:${cooptation.candidate_email}`}
                              className="text-primary-600 dark:text-primary-400 hover:underline"
                            >
                              {cooptation.candidate_email}
                            </a>
                          </div>
                          {cooptation.candidate_phone && (
                            <div className="flex items-center gap-2 text-sm">
                              <Phone className="h-4 w-4 text-gray-400 flex-shrink-0" />
                              <a
                                href={`tel:${cooptation.candidate_phone}`}
                                className="text-gray-700 dark:text-gray-300 hover:underline"
                              >
                                {cooptation.candidate_phone}
                              </a>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* TJM */}
                      {cooptation.candidate_daily_rate && (
                        <div>
                          <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                            TJM souhaite
                          </h3>
                          <div className="flex items-center gap-2 text-sm">
                            <Euro className="h-4 w-4 text-gray-400 flex-shrink-0" />
                            <span className="text-gray-900 dark:text-gray-100 font-medium">
                              {cooptation.candidate_daily_rate} EUR/jour
                            </span>
                          </div>
                        </div>
                      )}

                      {/* CV */}
                      {cooptation.candidate_cv_filename && (
                        <div>
                          <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                            CV
                          </h3>
                          <button
                            onClick={handleDownloadCv}
                            disabled={isDownloading}
                            className="w-full flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-left"
                          >
                            <FileText className="h-5 w-5 text-primary-600 dark:text-primary-400 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                                {cooptation.candidate_cv_filename}
                              </p>
                              <p className="text-xs text-gray-500 dark:text-gray-400">
                                Cliquez pour telecharger
                              </p>
                            </div>
                            {isDownloading ? (
                              <Loader2 className="h-4 w-4 text-gray-400 animate-spin flex-shrink-0" />
                            ) : (
                              <Download className="h-4 w-4 text-gray-400 flex-shrink-0" />
                            )}
                          </button>
                        </div>
                      )}

                      {/* Note */}
                      {cooptation.candidate_note && (
                        <div>
                          <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                            Note
                          </h3>
                          <div className="flex gap-2 text-sm">
                            <MessageSquare className="h-4 w-4 text-gray-400 flex-shrink-0 mt-0.5" />
                            <p className="text-gray-700 dark:text-gray-300 whitespace-pre-line">
                              {cooptation.candidate_note}
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Submitter */}
                      <div>
                        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                          Soumis par
                        </h3>
                        <div className="flex items-center gap-2 text-sm">
                          <User className="h-4 w-4 text-gray-400 flex-shrink-0" />
                          <span className="text-gray-700 dark:text-gray-300">
                            {cooptation.submitter_name || '-'}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-sm mt-1">
                          <Clock className="h-4 w-4 text-gray-400 flex-shrink-0" />
                          <span className="text-gray-500 dark:text-gray-400">
                            {new Date(cooptation.submitted_at).toLocaleDateString('fr-FR', {
                              day: 'numeric',
                              month: 'long',
                              year: 'numeric',
                            })}
                          </span>
                        </div>
                      </div>

                      {/* Status history */}
                      {cooptation.status_history.length > 0 && (
                        <div>
                          <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                            Historique
                          </h3>
                          <div className="space-y-2">
                            {cooptation.status_history.map((change, i) => {
                              const toBadge = COOPTATION_STATUS_BADGES[change.to_status] || COOPTATION_STATUS_BADGES.pending;
                              return (
                                <div key={i} className="flex items-start gap-2 text-xs text-gray-500 dark:text-gray-400">
                                  <ChevronRight className="h-3 w-3 flex-shrink-0 mt-0.5" />
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <span className={`px-1.5 py-0.5 rounded-full ${toBadge.bgClass} ${toBadge.textClass}`}>
                                        {toBadge.label}
                                      </span>
                                      <span>
                                        {new Date(change.changed_at).toLocaleDateString('fr-FR')}
                                      </span>
                                    </div>
                                    {change.comment && (
                                      <p className="text-gray-600 dark:text-gray-400 italic mt-0.5">
                                        {change.comment}
                                      </p>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

function EditOpportunityModal({
  opportunity,
  isOpen,
  onClose,
  onSaved,
}: {
  opportunity: PublishedOpportunity;
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(opportunity.title);
  const [description, setDescription] = useState(opportunity.description);
  const [skillsText, setSkillsText] = useState(opportunity.skills.join(', '));
  const [endDate, setEndDate] = useState(opportunity.end_date || '');

  const updateMutation = useMutation({
    mutationFn: () =>
      updatePublishedOpportunity(opportunity.id, {
        title,
        description,
        skills: skillsText
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        end_date: endDate || null,
      }),
    onSuccess: () => {
      toast.success('Opportunite mise a jour');
      onSaved();
      onClose();
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Modifier l'opportunite" size="lg">
      <div className="space-y-4">
        <Input
          label="Titre"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm min-h-[200px] focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Competences (separees par des virgules)
          </label>
          <Input
            value={skillsText}
            onChange={(e) => setSkillsText(e.target.value)}
            placeholder="React, TypeScript, Node.js"
          />
        </div>
        <Input
          label="Date de fin"
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
        />
        <div className="flex justify-end gap-3 pt-2 border-t border-gray-100 dark:border-gray-700">
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button
            onClick={() => updateMutation.mutate()}
            isLoading={updateMutation.isPending}
            disabled={!title.trim() || !description.trim()}
          >
            Enregistrer
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default function PublishedOpportunityDetail() {
  const { publishedId } = useParams<{ publishedId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedCooptation, setSelectedCooptation] = useState<Cooptation | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);

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
      toast.success('Opportunite cloturee');
    },
    onError: () => {
      toast.error('Erreur lors de la cloture');
    },
  });

  // Reopen mutation
  const reopenMutation = useMutation({
    mutationFn: () => reopenOpportunity(publishedId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['published-opportunity', publishedId] });
      queryClient.invalidateQueries({ queryKey: ['my-boond-opportunities'] });
      toast.success('Opportunite reactivee');
    },
    onError: () => {
      toast.error('Erreur lors de la reactivation');
    },
  });

  const handleStatusUpdated = () => {
    queryClient.invalidateQueries({ queryKey: ['cooptations-by-opportunity', publishedId] });
    setSelectedCooptation(null);
  };

  const handleOpportunitySaved = () => {
    queryClient.invalidateQueries({ queryKey: ['published-opportunity', publishedId] });
    queryClient.invalidateQueries({ queryKey: ['my-boond-opportunities'] });
    queryClient.invalidateQueries({ queryKey: ['published-opportunities'] });
  };

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
          Opportunite non trouvee
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          Cette opportunite n'existe pas ou a ete supprimee.
        </p>
        <Button variant="outline" onClick={() => navigate('/my-boond-opportunities')}>
          Retour aux opportunites
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
        Retour aux opportunites
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
              Ref Boond: {opportunity.boond_opportunity_id}
              {' · '}
              Publiee le {new Date(opportunity.created_at).toLocaleDateString('fr-FR')}
            </p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowEditModal(true)}
              leftIcon={<Pencil className="h-4 w-4" />}
            >
              Modifier
            </Button>
            {opportunity.status === 'published' && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => closeMutation.mutate()}
                disabled={closeMutation.isPending}
                leftIcon={<XCircle className="h-4 w-4" />}
                className="text-red-600 border-red-300 hover:bg-red-50 dark:text-red-400 dark:border-red-700 dark:hover:bg-red-900/20"
              >
                {closeMutation.isPending ? 'Fermeture...' : 'Cloturer'}
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
                {reopenMutation.isPending ? 'Reactivation...' : 'Reactiver'}
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
          <p className="text-xs text-gray-500 dark:text-gray-400">Ref Boond</p>
        </Card>
        <Card className="!p-3 text-center">
          <div className="flex items-center justify-center mb-1">
            <Sparkles className="h-4 w-4 text-gray-400" />
          </div>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {opportunity.skills.length}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Competences</p>
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
              Competences extraites
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
            Description anonymisee
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
              Aucune cooptation pour cette opportunite
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
                    CV
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
                  const coopStatusBadge = COOPTATION_STATUS_BADGES[cooptation.status] || COOPTATION_STATUS_BADGES.pending;
                  return (
                    <tr
                      key={cooptation.id}
                      onClick={() => setSelectedCooptation(cooptation)}
                      className="hover:bg-gray-50 dark:hover:bg-gray-800/30 cursor-pointer"
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
                          ? `${cooptation.candidate_daily_rate} EUR/j`
                          : '-'}
                      </td>
                      <td className="py-2.5 px-4">
                        {cooptation.candidate_cv_filename ? (
                          <span className="inline-flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400">
                            <FileText className="h-3 w-3" />
                            CV
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">-</span>
                        )}
                      </td>
                      <td className="py-2.5 px-4">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${coopStatusBadge.bgClass} ${coopStatusBadge.textClass}`}>
                          {coopStatusBadge.label}
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

      {/* Candidate detail drawer */}
      <CandidateDrawer
        cooptation={selectedCooptation}
        isOpen={!!selectedCooptation}
        onClose={() => setSelectedCooptation(null)}
        onStatusUpdated={handleStatusUpdated}
      />

      {/* Edit opportunity modal */}
      {showEditModal && opportunity && (
        <EditOpportunityModal
          opportunity={opportunity}
          isOpen={showEditModal}
          onClose={() => setShowEditModal(false)}
          onSaved={handleOpportunitySaved}
        />
      )}
    </div>
  );
}
