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
  Loader2,
  AlertCircle,
  Calendar,
  Users,
  FileText,
  Hash,
  XCircle,
  RefreshCw,
  User,
  Mail,
  Phone,
  Download,
  X,
  Euro,
  Clock,
  ChevronRight,
  Pencil,
  CheckCircle,
  Ban,
  ArrowRight,
  Trash2,
} from 'lucide-react';
import {
  getPublishedOpportunity,
  closeOpportunity,
  reopenOpportunity,
  updatePublishedOpportunity,
  deletePublishedOpportunity,
} from '../api/publishedOpportunities';
import { useAuthStore } from '../stores/authStore';
import { cooptationsApi } from '../api/cooptations';
import { getErrorMessage } from '../api/client';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { PageSpinner } from '../components/ui/Spinner';
import type { Cooptation, CooptationStatus, PublishedOpportunity, PublishedOpportunityStatus } from '../types';

const STATUS_BADGES: Record<PublishedOpportunityStatus, { label: string; chip: string }> = {
  draft: { label: 'Brouillon', chip: 'st-sla' },
  published: { label: 'Active', chip: 'st-grn' },
  closed: { label: 'Fermée', chip: 'st-red' },
};

const COOPTATION_STATUS_CHIPS: Record<string, { label: string; chip: string }> = {
  pending: { label: 'En attente', chip: 'st-amb' },
  in_review: { label: "En cours d'examen", chip: 'st-blu' },
  interview: { label: 'En entretien', chip: 'st-ind' },
  accepted: { label: 'Accepté', chip: 'st-grn' },
  rejected: { label: 'Refusé', chip: 'st-red' },
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
  pending: { label: 'Remettre en attente', icon: RefreshCw, colorClass: 'text-amb-fg hover:bg-amb-bg' },
  in_review: { label: "En cours d'examen", icon: ArrowRight, colorClass: 'text-blu-fg hover:bg-blu-bg' },
  interview: { label: 'Entretien', icon: ArrowRight, colorClass: 'text-ind-fg hover:bg-ind-bg' },
  accepted: { label: 'Accepter', icon: CheckCircle, colorClass: 'text-grn-fg hover:bg-grn-bg' },
  rejected: { label: 'Refuser', icon: Ban, colorClass: 'text-redt hover:bg-red-bg' },
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
      toast.success('Statut mis à jour');
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

  const statusChip = COOPTATION_STATUS_CHIPS[cooptation.status] || COOPTATION_STATUS_CHIPS.pending;
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
                  <div className="flex h-full flex-col bg-sur border-l border-lin shadow-xl">
                    {/* Header */}
                    <div className="px-5 py-4 border-b border-lin">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-pris rounded-full flex items-center justify-center shrink-0">
                            <User className="h-5 w-5 text-prit" />
                          </div>
                          <div>
                            <Dialog.Title className="text-[15px] font-bold text-ink">
                              {cooptation.candidate_name}
                            </Dialog.Title>
                            <span className={`st ${statusChip.chip} mt-1`}>
                              <span className="dot" />
                              {statusChip.label}
                            </span>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={onClose}
                          className="text-mut2 hover:text-ink transition-colors"
                          aria-label="Fermer"
                        >
                          <X className="h-5 w-5" />
                        </button>
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
                      {/* Status actions */}
                      {nextStatuses.length > 0 && (
                        <div>
                          <p className="ml mb-2">Actions</p>
                          {!statusAction ? (
                            <div className="flex flex-wrap gap-2">
                              {nextStatuses.map((nextStatus) => {
                                const config = STATUS_ACTION_CONFIG[nextStatus];
                                const Icon = config.icon;
                                return (
                                  <button
                                    key={nextStatus}
                                    type="button"
                                    onClick={() => handleStatusChange(nextStatus)}
                                    className={`inline-flex items-center gap-1.5 h-[30px] px-3 text-xs font-medium border border-lin rounded-[9px] transition-colors ${config.colorClass}`}
                                  >
                                    <Icon className="h-3.5 w-3.5" />
                                    {config.label}
                                  </button>
                                );
                              })}
                            </div>
                          ) : (
                            <div className="space-y-3 p-3.5 bg-srf2 rounded-xl border border-lin">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-[13px] text-mut">
                                  Changer le statut vers :
                                </span>
                                <span className={`st ${COOPTATION_STATUS_CHIPS[statusAction]?.chip}`}>
                                  <span className="dot" />
                                  {COOPTATION_STATUS_CHIPS[statusAction]?.label}
                                </span>
                              </div>
                              <div>
                                <label htmlFor="status-comment" className="f-lab">
                                  Commentaire {statusAction === 'rejected' ? <span className="text-redt">*</span> : '(optionnel)'}
                                </label>
                                <textarea
                                  id="status-comment"
                                  value={statusComment}
                                  onChange={(e) => {
                                    setStatusComment(e.target.value);
                                    if (statusError) setStatusError(null);
                                  }}
                                  placeholder={statusAction === 'rejected' ? 'Motif du rejet…' : 'Commentaire…'}
                                  className="f-ta !min-h-[60px]"
                                />
                                {statusError && (
                                  <p className="f-hint !text-redt">{statusError}</p>
                                )}
                              </div>
                              <div className="flex justify-end gap-2">
                                <Button variant="ghost" size="sm" onClick={handleCancelStatus}>
                                  Annuler
                                </Button>
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
                        <p className="ml mb-2">Contact</p>
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-[13px]">
                            <Mail className="h-4 w-4 text-mut2 shrink-0" />
                            <a
                              href={`mailto:${cooptation.candidate_email}`}
                              className="text-prit hover:underline"
                            >
                              {cooptation.candidate_email}
                            </a>
                          </div>
                          {cooptation.candidate_phone && (
                            <div className="flex items-center gap-2 text-[13px]">
                              <Phone className="h-4 w-4 text-mut2 shrink-0" />
                              <a
                                href={`tel:${cooptation.candidate_phone}`}
                                className="text-ink hover:underline"
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
                          <p className="ml mb-2">TJM souhaité</p>
                          <div className="flex items-center gap-2">
                            <Euro className="h-4 w-4 text-mut2 shrink-0" />
                            <span className="tjm">{cooptation.candidate_daily_rate} € / jour</span>
                          </div>
                        </div>
                      )}

                      {/* CV */}
                      {cooptation.candidate_cv_filename && (
                        <div>
                          <p className="ml mb-2">CV</p>
                          <button
                            type="button"
                            onClick={handleDownloadCv}
                            disabled={isDownloading}
                            className="filecard w-full text-left hover:border-pri transition-colors disabled:opacity-60"
                          >
                            <div className="dico">
                              <FileText className="h-4 w-4" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="dn truncate">{cooptation.candidate_cv_filename}</p>
                              <p className="ds">Cliquez pour télécharger</p>
                            </div>
                            {isDownloading ? (
                              <Loader2 className="h-4 w-4 text-mut2 animate-spin shrink-0" />
                            ) : (
                              <Download className="h-4 w-4 text-mut2 shrink-0" />
                            )}
                          </button>
                        </div>
                      )}

                      {/* Note */}
                      {cooptation.candidate_note && (
                        <div>
                          <p className="ml mb-2">Note</p>
                          <p className="quote !mt-0 whitespace-pre-line">
                            {cooptation.candidate_note}
                          </p>
                        </div>
                      )}

                      {/* Submitter */}
                      <div>
                        <p className="ml mb-2">Soumis par</p>
                        <div className="flex items-center gap-2 text-[13px] text-ink">
                          <User className="h-4 w-4 text-mut2 shrink-0" />
                          <span>{cooptation.submitter_name || '—'}</span>
                        </div>
                        <div className="flex items-center gap-2 text-[12.5px] text-mut mt-1.5">
                          <Clock className="h-4 w-4 text-mut2 shrink-0" />
                          <span>
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
                          <p className="ml mb-2.5">Historique</p>
                          <div>
                            {cooptation.status_history.map((change, i) => {
                              const chip = COOPTATION_STATUS_CHIPS[change.to_status] || COOPTATION_STATUS_CHIPS.pending;
                              const isLast = i === cooptation.status_history.length - 1;
                              return (
                                <div key={i} className="ev">
                                  <span className="evd" />
                                  {!isLast && <span className="evl" />}
                                  <p className="evt">
                                    {chip.label} · {new Date(change.changed_at).toLocaleDateString('fr-FR')}
                                  </p>
                                  {change.comment && <p className="evs">{change.comment}</p>}
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
        end_date: endDate,
      }),
    onSuccess: () => {
      toast.success('Opportunité mise à jour');
      onSaved();
      onClose();
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Modifier l'opportunité" size="lg">
      <div className="space-y-4">
        <Input
          label="Titre"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <div>
          <label htmlFor="edit-opp-description" className="f-lab">
            Description
          </label>
          <textarea
            id="edit-opp-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="f-ta !min-h-[200px]"
          />
        </div>
        <div>
          <Input
            label="Compétences (séparées par des virgules)"
            value={skillsText}
            onChange={(e) => setSkillsText(e.target.value)}
            placeholder="React, TypeScript, Node.js"
          />
        </div>
        <Input
          label="Date de fin *"
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          required
        />
        <div className="flex justify-end gap-2 pt-3 border-t border-lin2">
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button
            onClick={() => updateMutation.mutate()}
            isLoading={updateMutation.isPending}
            disabled={!title.trim() || !description.trim() || !endDate}
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
  const user = useAuthStore((state) => state.user);
  const isAdmin = user?.role === 'admin';
  const [selectedCooptation, setSelectedCooptation] = useState<Cooptation | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteCooptationId, setDeleteCooptationId] = useState<string | null>(null);

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

  // Delete opportunity mutation (admin only)
  const deleteOpportunityMutation = useMutation({
    mutationFn: () => deletePublishedOpportunity(publishedId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-boond-opportunities'] });
      queryClient.invalidateQueries({ queryKey: ['published-opportunities'] });
      toast.success('Opportunité supprimée');
      navigate(-1);
    },
    onError: () => {
      toast.error('Erreur lors de la suppression');
    },
  });

  // Delete cooptation mutation (admin only)
  const deleteCooptationMutation = useMutation({
    mutationFn: (id: string) => cooptationsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cooptations-by-opportunity', publishedId] });
      toast.success('Cooptation supprimée');
      setDeleteCooptationId(null);
      setSelectedCooptation(null);
    },
    onError: () => {
      toast.error('Erreur lors de la suppression');
      setDeleteCooptationId(null);
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
    return <PageSpinner />;
  }

  if (error || !opportunity) {
    return (
      <div className="text-center py-16">
        <AlertCircle className="h-10 w-10 text-redt mx-auto mb-4" />
        <h2 className="text-[15px] font-bold text-ink mb-2">Opportunité non trouvée</h2>
        <p className="notec mb-6">Cette opportunité n'existe pas ou a été supprimée.</p>
        <Button variant="secondary" onClick={() => navigate('/my-boond-opportunities')}>
          Retour aux opportunités
        </Button>
      </div>
    );
  }

  const statusBadge = STATUS_BADGES[opportunity.status as PublishedOpportunityStatus] || STATUS_BADGES.draft;
  const cooptations = cooptationsData?.items || [];

  const gridCols = 'grid-cols-[1.7fr_100px_80px_170px_1fr_95px_60px]';

  return (
    <div>
      {/* Breadcrumb / back */}
      <Link
        to="/my-boond-opportunities"
        className="bc block cursor-pointer !text-mut2 hover:!text-mut"
      >
        ← Commercial / Gestion opportunités
      </Link>

      {/* Header */}
      <div className="hdcard !mt-2">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <span className={`st ${statusBadge.chip}`}>
              <span className="dot" />
              {statusBadge.label}
            </span>
            <h1 className="h1 !text-[26px] mt-2.5">{opportunity.title}</h1>
            <div className="om !mt-3.5 !mb-0">
              <span className="omi">
                <Hash className="h-3.5 w-3.5" />
                Réf. Boond : {opportunity.boond_opportunity_id}
              </span>
              <span className="omi">
                <Calendar className="h-3.5 w-3.5" />
                Publiée le {new Date(opportunity.created_at).toLocaleDateString('fr-FR')}
              </span>
              {opportunity.end_date && (
                <span className="omi">
                  <Calendar className="h-3.5 w-3.5" />
                  Fin prévue : {new Date(opportunity.end_date).toLocaleDateString('fr-FR')}
                </span>
              )}
              <span className="omi">
                <Users className="h-3.5 w-3.5" />
                {cooptations.length} cooptation{cooptations.length > 1 ? 's' : ''}
              </span>
            </div>
          </div>
          <div className="flex gap-2 shrink-0 flex-wrap">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setShowEditModal(true)}
              leftIcon={<Pencil className="h-3.5 w-3.5" />}
            >
              Modifier
            </Button>
            {opportunity.status === 'published' && (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => closeMutation.mutate()}
                disabled={closeMutation.isPending}
                leftIcon={<XCircle className="h-3.5 w-3.5" />}
                className="!text-redt"
              >
                {closeMutation.isPending ? 'Fermeture…' : 'Clôturer'}
              </Button>
            )}
            {opportunity.status === 'closed' && (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => reopenMutation.mutate()}
                disabled={reopenMutation.isPending}
                leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
              >
                {reopenMutation.isPending ? 'Réactivation…' : 'Réactiver'}
              </Button>
            )}
            {isAdmin && (
              <Button
                size="sm"
                variant="danger"
                onClick={() => setShowDeleteConfirm(true)}
                leftIcon={<Trash2 className="h-3.5 w-3.5" />}
              >
                Supprimer
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Description */}
      <div className="card mt-4">
        <h3 className="ct">Description anonymisée</h3>
        <p className="odesc !max-w-none mt-2.5 whitespace-pre-line">{opportunity.description}</p>
      </div>

      {/* Skills */}
      {opportunity.skills.length > 0 && (
        <div className="card mt-4">
          <h3 className="ct mb-3">Compétences extraites</h3>
          <div className="flex flex-wrap gap-2">
            {opportunity.skills.map((skill, index) => (
              <span key={index} className="sk">
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Cooptations */}
      <div className="flex items-center justify-between gap-4 mt-7 mb-2.5">
        <h3 className="ct">Cooptations reçues</h3>
        {cooptations.length > 0 && (
          <span className="cs !mt-0">
            {cooptations.length} candidat{cooptations.length > 1 ? 's' : ''} proposé{cooptations.length > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {isLoadingCooptations ? (
        <div className="card flex items-center justify-center gap-2 py-10">
          <Loader2 className="h-5 w-5 text-prit animate-spin" />
          <span className="text-[13px] text-mut">Chargement…</span>
        </div>
      ) : cooptations.length === 0 ? (
        <div className="card text-center py-10">
          <Users className="h-8 w-8 text-mut2 mx-auto mb-3" />
          <p className="dn">Aucune cooptation pour cette opportunité</p>
          <p className="ds mt-1.5">
            Les candidats proposés par les consultants apparaîtront ici.
          </p>
        </div>
      ) : (
        <div className="tbl">
          <div className={`thead ${gridCols}`}>
            <span>Candidat</span>
            <span>TJM</span>
            <span>CV</span>
            <span>Statut</span>
            <span>Soumis par</span>
            <span>Date</span>
            <span></span>
          </div>
          {cooptations.map((cooptation) => {
            const coopChip = COOPTATION_STATUS_CHIPS[cooptation.status] || COOPTATION_STATUS_CHIPS.pending;
            return (
              <div
                key={cooptation.id}
                onClick={() => setSelectedCooptation(cooptation)}
                className={`row click ${gridCols} group`}
              >
                <div className="min-w-0">
                  <p className="nm truncate">{cooptation.candidate_name}</p>
                  <p className="ns truncate">
                    {cooptation.candidate_email}
                    {cooptation.candidate_phone && ` · ${cooptation.candidate_phone}`}
                  </p>
                </div>
                <span className="tjm">
                  {cooptation.candidate_daily_rate
                    ? `${cooptation.candidate_daily_rate} €`
                    : '—'}
                </span>
                <div>
                  {cooptation.candidate_cv_filename ? (
                    <span className="omi text-xs font-medium text-prit">
                      <FileText className="h-3.5 w-3.5" />
                      CV
                    </span>
                  ) : (
                    <span className="cell text-mut2">—</span>
                  )}
                </div>
                <div>
                  <span className={`st ${coopChip.chip}`}>
                    <span className="dot" />
                    {coopChip.label}
                  </span>
                </div>
                <span className="cell truncate">{cooptation.submitter_name || '—'}</span>
                <span className="cell">
                  {new Date(cooptation.submitted_at).toLocaleDateString('fr-FR')}
                </span>
                <div className="flex items-center justify-end gap-1">
                  {isAdmin && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteCooptationId(cooptation.id);
                      }}
                      className="p-1 rounded-md text-mut2 opacity-0 group-hover:opacity-100 hover:text-redt hover:bg-red-bg transition-all"
                      title="Supprimer"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                  <ChevronRight className="h-4 w-4 chev shrink-0" />
                </div>
              </div>
            );
          })}
          <div className="tfoot">
            <span>
              {cooptations.length} cooptation{cooptations.length > 1 ? 's' : ''} · cliquez sur une
              ligne pour gérer le candidat
            </span>
          </div>
        </div>
      )}

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


      {/* Delete opportunity confirmation modal (admin only) */}
      <Modal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        title="Supprimer l'opportunité"
      >
        <div className="space-y-4">
          <p className="notec">
            Êtes-vous sûr de vouloir supprimer définitivement cette opportunité ?
          </p>
          <p className="text-[12.5px] text-redt">Cette action est irréversible.</p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setShowDeleteConfirm(false)}>
              Annuler
            </Button>
            <Button
              variant="danger"
              onClick={() => deleteOpportunityMutation.mutate()}
              isLoading={deleteOpportunityMutation.isPending}
            >
              Supprimer
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete cooptation confirmation modal (admin only) */}
      <Modal
        isOpen={!!deleteCooptationId}
        onClose={() => setDeleteCooptationId(null)}
        title="Supprimer la cooptation"
      >
        <div className="space-y-4">
          <p className="notec">
            Êtes-vous sûr de vouloir supprimer définitivement cette cooptation ?
          </p>
          <p className="text-[12.5px] text-redt">Cette action est irréversible.</p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setDeleteCooptationId(null)}>
              Annuler
            </Button>
            <Button
              variant="danger"
              onClick={() => deleteCooptationId && deleteCooptationMutation.mutate(deleteCooptationId)}
              isLoading={deleteCooptationMutation.isPending}
            >
              Supprimer
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
