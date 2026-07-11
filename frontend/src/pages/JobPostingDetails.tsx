/**
 * JobPostingDetails - Page to view and manage a job posting and its applications.
 */

import { Fragment, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  AlertCircle,
  Briefcase,
  Building2,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Copy,
  ExternalLink,
  FileText,
  Loader2,
  MapPin,
  Pencil,
  Phone,
  RefreshCw,
  Send,
  Star,
  Trash2,
  User,
  X,
  XCircle,
} from 'lucide-react';
import { hrApi, type OpportunityDetailResponse } from '../api/hr';
import { APPLICATION_STATUS_LABELS } from '../types';
import type { ApplicationStatus, JobApplication } from '../types';
import {
  JOB_POSTING_STATUS_BADGES,
  EMPLOYMENT_STATUS_OPTIONS,
  AVAILABILITY_FILTER_OPTIONS,
  SORT_OPTIONS,
  CONTRACT_TYPE_LABELS,
  DISPLAY_MODE_OPTIONS,
  type DisplayMode,
} from '../constants/hr';
import {
  ApplicationDetailContent,
  matchingScoreChip,
  cvQualityScoreChip,
} from '../components/hr/ApplicationDetailContent';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';

// Chips v2 par statut d'annonce
const POSTING_STATUS_CHIPS: Record<string, string> = {
  draft: 'st-sla',
  published: 'st-grn',
  closed: 'st-red',
};

// Chips v2 par statut de candidature
const APPLICATION_STATUS_CHIPS: Record<ApplicationStatus, string> = {
  en_cours: 'st-amb',
  valide: 'st-grn',
  refuse: 'st-red',
};

// Colonnes de la table candidatures (ahead + arow doivent partager la même grille)
const APP_GRID = 'grid-cols-[1.4fr_120px_110px_100px_100px_130px_24px]';

export default function JobPostingDetails() {
  const { postingId } = useParams<{ postingId: string }>();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Filter state
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | ''>('');
  const [employmentStatusFilter, setEmploymentStatusFilter] = useState('');
  const [availabilityFilter, setAvailabilityFilter] = useState('');
  // Sort state
  const [sortBy, setSortBy] = useState('score');
  const [sortOrder, setSortOrder] = useState('desc');
  // Display mode state
  const [displayMode, setDisplayMode] = useState<DisplayMode>('inline');
  // Detail view state
  const [selectedApplication, setSelectedApplication] = useState<JobApplication | null>(null);
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null);
  const [noteText, setNoteText] = useState('');
  const [newStatus, setNewStatus] = useState<ApplicationStatus | ''>('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  // Opportunity detail state
  const [showOpportunityDetail, setShowOpportunityDetail] = useState(false);
  const [opportunityDetail, setOpportunityDetail] = useState<OpportunityDetailResponse | null>(null);
  const [loadingOpportunityDetail, setLoadingOpportunityDetail] = useState(false);

  // Fetch job posting
  const {
    data: posting,
    isLoading: loadingPosting,
    error: postingError,
  } = useQuery({
    queryKey: ['hr-job-posting', postingId],
    queryFn: () => hrApi.getJobPosting(postingId!),
    enabled: !!postingId,
  });

  // Fetch applications
  const {
    data: applicationsData,
    isLoading: loadingApplications,
    refetch: refetchApplications,
  } = useQuery({
    queryKey: ['hr-job-applications', postingId, statusFilter, employmentStatusFilter, availabilityFilter, sortBy, sortOrder],
    queryFn: () =>
      hrApi.getApplications(postingId!, {
        status: statusFilter || undefined,
        employment_status: employmentStatusFilter || undefined,
        availability: availabilityFilter || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page_size: 100,
      }),
    enabled: !!postingId,
  });

  // Publish mutation
  const publishMutation = useMutation({
    mutationFn: () => hrApi.publishJobPosting(postingId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-job-posting', postingId] });
      queryClient.invalidateQueries({ queryKey: ['hr-opportunities'] });
    },
  });

  // Close mutation
  const closeMutation = useMutation({
    mutationFn: () => hrApi.closeJobPosting(postingId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-job-posting', postingId] });
      queryClient.invalidateQueries({ queryKey: ['hr-opportunities'] });
    },
  });

  // Reactivate mutation
  const reactivateMutation = useMutation({
    mutationFn: () => hrApi.reactivateJobPosting(postingId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-job-posting', postingId] });
      queryClient.invalidateQueries({ queryKey: ['hr-opportunities'] });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => hrApi.deleteJobPosting(postingId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr-opportunities'] });
      queryClient.invalidateQueries({ queryKey: ['hr-job-postings'] });
      navigate('/rh');
    },
  });

  // Update status mutation
  const updateStatusMutation = useMutation({
    mutationFn: ({ applicationId, status }: { applicationId: string; status: ApplicationStatus }) =>
      hrApi.updateApplicationStatus(applicationId, status),
    onSuccess: () => {
      refetchApplications();
      setSelectedApplication(null);
    },
  });

  // Update note mutation
  const updateNoteMutation = useMutation({
    mutationFn: ({ applicationId, note }: { applicationId: string; note: string }) =>
      hrApi.updateApplicationNote(applicationId, note),
    onSuccess: () => {
      refetchApplications();
    },
  });

  // Reanalyze application (matching + CV quality)
  const reanalyzeMutation = useMutation({
    mutationFn: (applicationId: string) => hrApi.reanalyzeApplication(applicationId),
    onSuccess: (updatedApplication) => {
      refetchApplications();
      setSelectedApplication(updatedApplication);
    },
  });

  // Handle reanalyze
  const handleReanalyze = (application: JobApplication) => {
    reanalyzeMutation.mutate(application.id);
  };

  // Retry Boond sync
  const retryBoondMutation = useMutation({
    mutationFn: (applicationId: string) => hrApi.retryBoondSync(applicationId),
    onSuccess: (updatedApplication) => {
      toast.success('Candidat créé dans BoondManager');
      refetchApplications();
      setSelectedApplication(updatedApplication);
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast.error(axiosError.response?.data?.detail || 'Échec de la synchronisation BoondManager');
    },
  });

  const handleRetryBoondSync = (application: JobApplication) => {
    retryBoondMutation.mutate(application.id);
  };

  // Download CV
  const handleDownloadCv = async (application: JobApplication) => {
    try {
      const response = await hrApi.getCvDownloadUrl(application.id);
      window.open(response.url, '_blank');
    } catch (error) {
      console.error('Error downloading CV:', error);
    }
  };

  const handleStatusChange = () => {
    if (selectedApplication && newStatus) {
      updateStatusMutation.mutate({
        applicationId: selectedApplication.id,
        status: newStatus,
      });
    }
  };

  const handleNoteUpdate = (application: JobApplication) => {
    updateNoteMutation.mutate({
      applicationId: application.id,
      note: noteText,
    });
  };

  // Open application detail and mark as viewed
  const handleOpenApplication = async (application: JobApplication) => {
    try {
      // Call API with markViewed=true to auto-transition from NOUVEAU to EN_COURS
      const updatedApplication = await hrApi.getApplication(application.id, true);

      // Handle inline expansion mode differently
      if (displayMode === 'inline') {
        setExpandedRowId(expandedRowId === application.id ? null : application.id);
      }

      setSelectedApplication(updatedApplication);
      setNewStatus(updatedApplication.status as ApplicationStatus);
      setNoteText(updatedApplication.notes || '');
      // Refetch to update counts
      refetchApplications();
    } catch {
      // Fallback to local data if API fails
      if (displayMode === 'inline') {
        setExpandedRowId(expandedRowId === application.id ? null : application.id);
      }
      setSelectedApplication(application);
      setNewStatus(application.status as ApplicationStatus);
      setNoteText(application.notes || '');
    }
  };

  // Close detail view
  const handleCloseDetail = () => {
    setSelectedApplication(null);
    setExpandedRowId(null);
  };

  // Mark as read without opening modal (for bulk action)
  const handleMarkAsRead = async (application: JobApplication) => {
    if (application.is_read) return;
    try {
      await hrApi.getApplication(application.id, true);
      refetchApplications();
      toast.success('Candidature marquée comme lue');
    } catch (error) {
      console.error('Error marking as read:', error);
      toast.error('Erreur lors du marquage comme lu');
    }
  };

  // Quick validate action
  const handleQuickValidate = async (application: JobApplication) => {
    if (application.status !== 'en_cours') return;
    try {
      await hrApi.updateApplicationStatus(application.id, 'valide');
      refetchApplications();
      toast.success(`Candidature de ${application.full_name} validée`);
    } catch (error) {
      console.error('Error validating application:', error);
      toast.error('Erreur lors de la validation');
    }
  };

  // Quick reject action
  const handleQuickReject = async (application: JobApplication) => {
    if (application.status !== 'en_cours') return;
    try {
      await hrApi.updateApplicationStatus(application.id, 'refuse');
      refetchApplications();
      toast.success(`Candidature de ${application.full_name} refusée`);
    } catch (error) {
      console.error('Error rejecting application:', error);
      toast.error('Erreur lors du refus');
    }
  };

  // Fetch and show opportunity details from Boond
  const handleShowOpportunityDetail = async () => {
    if (!posting) return;
    // Extract Boond ID from reference (format: "BOOND-1234")
    const boondId = posting.boond_opportunity_id || posting.opportunity_reference?.replace('BOOND-', '');
    if (!boondId) return;

    setLoadingOpportunityDetail(true);
    setShowOpportunityDetail(true);
    try {
      const detail = await hrApi.getOpportunityDetail(boondId);
      setOpportunityDetail(detail);
    } catch (error) {
      console.error('Error fetching opportunity detail:', error);
    } finally {
      setLoadingOpportunityDetail(false);
    }
  };

  // Close opportunity detail panel
  const handleCloseOpportunityDetail = () => {
    setShowOpportunityDetail(false);
    setOpportunityDetail(null);
  };

  if (loadingPosting) {
    return <PageSpinner />;
  }

  if (postingError || !posting) {
    return (
      <div>
        <p className="bc">
          <button type="button" className="hover:text-ink" onClick={() => navigate('/rh')}>
            ← RH / Gestion des annonces
          </button>
        </p>
        <div className="alert red">
          <AlertCircle className="h-[18px] w-[18px] shrink-0" />
          <span>Annonce non trouvée. Veuillez réessayer.</span>
        </div>
      </div>
    );
  }

  const statusBadge = JOB_POSTING_STATUS_BADGES[posting.status as keyof typeof JOB_POSTING_STATUS_BADGES];

  const applications = applicationsData?.items ?? [];
  const scoredApplications = applications.filter((a) => a.matching_score !== null);
  const averageMatchingScore =
    scoredApplications.length > 0
      ? Math.round(
          scoredApplications.reduce((sum, a) => sum + (a.matching_score ?? 0), 0) /
            scoredApplications.length
        )
      : null;

  const contractTypesLabel = posting.contract_types
    .map((t) => CONTRACT_TYPE_LABELS[t] || t)
    .join(' ou ');
  const subParts = [
    posting.client_name,
    contractTypesLabel || null,
    posting.published_at
      ? `publiée le ${new Date(posting.published_at).toLocaleDateString('fr-FR')}`
      : `créée le ${new Date(posting.created_at).toLocaleDateString('fr-FR')}`,
    posting.status === 'published' && posting.application_token
      ? `/postuler/${posting.application_token.slice(0, 8)}…`
      : null,
  ].filter(Boolean);

  return (
    <div>
      {/* Fil d'ariane */}
      <p className="bc">
        <button type="button" className="hover:text-ink" onClick={() => navigate('/rh')}>
          ← RH / Gestion des annonces
        </button>
        {' / '}
        <button
          type="button"
          className="font-mono hover:text-ink"
          onClick={handleShowOpportunityDetail}
          title="Voir les détails de l'opportunité Boond"
        >
          {posting.opportunity_reference}
        </button>
      </p>

      {/* Entête */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap min-w-0">
          <h1 className="h1">{posting.title}</h1>
          <span className={`st ${POSTING_STATUS_CHIPS[posting.status] ?? 'st-sla'}`}>
            <span className="dot" />
            {statusBadge.label}
          </span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {posting.status === 'published' && posting.application_url && (
            <Button
              type="button"
              variant="secondary"
              leftIcon={<Copy className="h-3.5 w-3.5" />}
              onClick={() => navigator.clipboard.writeText(posting.application_url!)}
            >
              Copier le lien public
            </Button>
          )}
          {posting.turnoverit_public_url && (
            <a
              href={posting.turnoverit_public_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn2 !text-ink"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Page publique
            </a>
          )}
          <Link to={`/rh/annonces/edit/${postingId}`} className="btn2 !text-ink">
            <Pencil className="h-3.5 w-3.5" />
            Modifier
          </Link>
          {posting.status === 'draft' && (
            <Button
              type="button"
              leftIcon={<Send className="h-3.5 w-3.5" />}
              onClick={() => publishMutation.mutate()}
              isLoading={publishMutation.isPending}
            >
              Publier sur Turnover-IT
            </Button>
          )}
          {posting.status === 'published' && (
            <Button
              type="button"
              variant="secondary"
              className="!text-redt"
              leftIcon={<XCircle className="h-3.5 w-3.5" />}
              onClick={() => closeMutation.mutate()}
              isLoading={closeMutation.isPending}
            >
              Fermer
            </Button>
          )}
          {posting.status === 'closed' && (
            <Button
              type="button"
              variant="secondary"
              leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
              onClick={() => reactivateMutation.mutate()}
              isLoading={reactivateMutation.isPending}
            >
              Réactiver
            </Button>
          )}
          <Button
            type="button"
            variant="ghost"
            className="!text-redt"
            leftIcon={<Trash2 className="h-3.5 w-3.5" />}
            onClick={() => setShowDeleteConfirm(true)}
          >
            Supprimer
          </Button>
        </div>
      </div>
      <p className="sub">{subParts.join(' · ')}</p>

      {/* Erreur de publication */}
      {publishMutation.isError && (
        <div className="alert red">
          <AlertCircle className="h-[18px] w-[18px] shrink-0" />
          <span>Erreur lors de la publication. Veuillez réessayer.</span>
        </div>
      )}

      {/* KPIs */}
      <div className="kpis !grid-cols-3 max-w-[760px]">
        <div className="kpi">
          <p className="kl">Candidatures</p>
          <p className="kv">{posting.applications_total}</p>
          <p className="ks">
            {posting.view_count} vue{posting.view_count > 1 ? 's' : ''} de l'annonce
          </p>
        </div>
        <div className="kpi">
          <p className="kl">Nouvelles à traiter</p>
          <p className="kv text-blu-fg">{posting.applications_new}</p>
          <p className="ks">candidatures non lues</p>
        </div>
        <div className="kpi">
          <p className="kl">Score matching moyen</p>
          <p className="kv">{averageMatchingScore !== null ? `${averageMatchingScore} %` : '—'}</p>
          <p className="ks">
            {scoredApplications.length > 0
              ? `sur ${scoredApplications.length} candidature${scoredApplications.length > 1 ? 's' : ''} analysée${scoredApplications.length > 1 ? 's' : ''}`
              : 'aucune candidature analysée'}
          </p>
        </div>
      </div>

      {/* Filtres & tri */}
      <div className="flex items-center gap-2 flex-wrap mb-3.5">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as ApplicationStatus | '')}
          className="filter-select"
          aria-label="Filtrer par statut"
        >
          <option value="">Tous statuts</option>
          {Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={employmentStatusFilter}
          onChange={(e) => setEmploymentStatusFilter(e.target.value)}
          className="filter-select"
          aria-label="Filtrer par statut professionnel"
        >
          {EMPLOYMENT_STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select
          value={availabilityFilter}
          onChange={(e) => setAvailabilityFilter(e.target.value)}
          className="filter-select"
          aria-label="Filtrer par disponibilité"
        >
          {AVAILABILITY_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="filter-select"
          aria-label="Trier par"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              Trier : {opt.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
          className="selbox !px-3"
          title={sortOrder === 'desc' ? 'Tri décroissant' : 'Tri croissant'}
        >
          {sortOrder === 'desc' ? '↓' : '↑'}
        </button>
        <div className="seg2 ml-auto">
          {DISPLAY_MODE_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  setDisplayMode(opt.value);
                  if (opt.value !== 'inline') setExpandedRowId(null);
                  if (opt.value === 'inline') setSelectedApplication(null);
                }}
                className={`seg2b ${displayMode === opt.value ? 'on' : ''}`}
                title={opt.label}
              >
                <Icon className="h-3.5 w-3.5" />
              </button>
            );
          })}
        </div>
      </div>

      {/* Table des candidatures */}
      <div className="tbl">
        <div className={`ahead ${APP_GRID}`}>
          <span>Candidat</span>
          <span>Statut pro</span>
          <span>TJM / Salaire</span>
          <span>Dispo</span>
          <span>Matching</span>
          <span>Statut</span>
          <span></span>
        </div>
        {loadingApplications ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-mut2" />
          </div>
        ) : applications.length === 0 ? (
          <div className="py-10 px-5 text-center">
            <p className="dn">Aucune candidature pour le moment</p>
            <p className="ds mt-1.5">
              Les candidatures reçues via le lien public apparaîtront ici.
            </p>
          </div>
        ) : (
          applications.map((application) => {
            const isExpanded = displayMode === 'inline' && expandedRowId === application.id;
            const isUnread = !application.is_read;
            return (
              <Fragment key={application.id}>
                <div
                  className={`arow ${APP_GRID} ${
                    isExpanded || selectedApplication?.id === application.id ? '!bg-srf2' : ''
                  }`}
                  onClick={() => handleOpenApplication(application)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && e.target === e.currentTarget) {
                      handleOpenApplication(application);
                    }
                  }}
                >
                  <div className="min-w-0">
                    <p className="nm truncate">{application.full_name}</p>
                    <p className="ns truncate">{application.email}</p>
                  </div>
                  <span className="cell truncate">
                    {application.employment_status_display || '—'}
                  </span>
                  <span className="cell whitespace-nowrap">
                    {application.tjm_range || application.salary_range || '—'}
                  </span>
                  <span className="cell truncate">
                    {application.availability_display || application.availability || '—'}
                  </span>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {application.matching_score !== null ? (
                      <span className={`st ${matchingScoreChip(application.matching_score)}`}>
                        {application.matching_score} %
                      </span>
                    ) : (
                      <span className="cell text-mut2">—</span>
                    )}
                    {application.cv_quality_score !== null && (
                      <span className={`st ${cvQualityScoreChip(application.cv_quality_score)}`}>
                        {application.cv_quality_score}/20
                      </span>
                    )}
                  </div>
                  <div>
                    {isUnread ? (
                      <button
                        type="button"
                        className="st st-blu"
                        title="Marquer comme lue sans ouvrir"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleMarkAsRead(application);
                        }}
                      >
                        <span className="dot" />
                        Nouvelle
                      </button>
                    ) : (
                      <span
                        className={`st ${APPLICATION_STATUS_CHIPS[application.status as ApplicationStatus] ?? 'st-sla'}`}
                      >
                        <span className="dot" />
                        {APPLICATION_STATUS_LABELS[application.status as ApplicationStatus] ??
                          application.status_display}
                      </span>
                    )}
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4 chev justify-self-end" />
                  ) : (
                    <ChevronDown className="h-4 w-4 chev justify-self-end" />
                  )}
                </div>
                {/* Ligne dépliée (mode expansion) */}
                {isExpanded && selectedApplication && selectedApplication.id === application.id && (
                  <div className="expand items-start">
                    <ApplicationDetailContent
                      application={selectedApplication}
                      newStatus={newStatus}
                      setNewStatus={setNewStatus}
                      noteText={noteText}
                      setNoteText={setNoteText}
                      handleStatusChange={handleStatusChange}
                      handleNoteUpdate={handleNoteUpdate}
                      handleDownloadCv={handleDownloadCv}
                      handleReanalyze={handleReanalyze}
                      handleRetryBoondSync={handleRetryBoondSync}
                      handleQuickValidate={handleQuickValidate}
                      handleQuickReject={handleQuickReject}
                      updateStatusMutation={updateStatusMutation}
                      updateNoteMutation={updateNoteMutation}
                      reanalyzeMutation={reanalyzeMutation}
                      retryBoondMutation={retryBoondMutation}
                      compact
                    />
                  </div>
                )}
              </Fragment>
            );
          })
        )}
        <div className="tfoot">
          <span>
            {applicationsData?.total ?? 0} candidature{(applicationsData?.total ?? 0) > 1 ? 's' : ''}
            {posting.applications_new > 0 &&
              ` · ${posting.applications_new} nouvelle${posting.applications_new > 1 ? 's' : ''}`}
          </span>
        </div>
      </div>

      {/* Détail candidature — mode pop-up */}
      {selectedApplication && displayMode === 'modal' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-sur border border-lin rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-5 py-4 border-b border-lin flex items-center justify-between sticky top-0 bg-sur z-10">
              <h3 className="ct">{selectedApplication.full_name}</h3>
              <button
                type="button"
                onClick={handleCloseDetail}
                className="p-1 text-mut2 hover:text-ink"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <ApplicationDetailContent
              application={selectedApplication}
              newStatus={newStatus}
              setNewStatus={setNewStatus}
              noteText={noteText}
              setNoteText={setNoteText}
              handleStatusChange={handleStatusChange}
              handleNoteUpdate={handleNoteUpdate}
              handleDownloadCv={handleDownloadCv}
              handleReanalyze={handleReanalyze}
              handleRetryBoondSync={handleRetryBoondSync}
              handleQuickValidate={handleQuickValidate}
              handleQuickReject={handleQuickReject}
              updateStatusMutation={updateStatusMutation}
              updateNoteMutation={updateNoteMutation}
              reanalyzeMutation={reanalyzeMutation}
              retryBoondMutation={retryBoondMutation}
            />
          </div>
        </div>
      )}

      {/* Détail candidature — mode panneau latéral */}
      {selectedApplication && displayMode === 'drawer' && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 bg-black/30 z-40" onClick={handleCloseDetail} />
          {/* Drawer */}
          <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-sur border-l border-lin shadow-xl z-50 overflow-y-auto animate-slide-in-right">
            <div className="px-5 py-4 border-b border-lin flex items-center justify-between sticky top-0 bg-sur z-10">
              <h3 className="ct">{selectedApplication.full_name}</h3>
              <button
                type="button"
                onClick={handleCloseDetail}
                className="p-1 text-mut2 hover:text-ink"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <ApplicationDetailContent
              application={selectedApplication}
              newStatus={newStatus}
              setNewStatus={setNewStatus}
              noteText={noteText}
              setNoteText={setNoteText}
              handleStatusChange={handleStatusChange}
              handleNoteUpdate={handleNoteUpdate}
              handleDownloadCv={handleDownloadCv}
              handleReanalyze={handleReanalyze}
              handleRetryBoondSync={handleRetryBoondSync}
              handleQuickValidate={handleQuickValidate}
              handleQuickReject={handleQuickReject}
              updateStatusMutation={updateStatusMutation}
              updateNoteMutation={updateNoteMutation}
              reanalyzeMutation={reanalyzeMutation}
              retryBoondMutation={retryBoondMutation}
            />
          </div>
        </>
      )}

      {/* Détail candidature — vue split */}
      {selectedApplication && displayMode === 'split' && (
        <div className="card !p-0 mt-4 overflow-hidden">
          <div className="px-5 py-3.5 border-b border-lin flex items-center justify-between">
            <h3 className="ct">Détails : {selectedApplication.full_name}</h3>
            <button
              type="button"
              onClick={handleCloseDetail}
              className="p-1 text-mut2 hover:text-ink"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="p-4 bg-srf2 grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-3.5 items-start">
            <ApplicationDetailContent
              application={selectedApplication}
              newStatus={newStatus}
              setNewStatus={setNewStatus}
              noteText={noteText}
              setNoteText={setNoteText}
              handleStatusChange={handleStatusChange}
              handleNoteUpdate={handleNoteUpdate}
              handleDownloadCv={handleDownloadCv}
              handleReanalyze={handleReanalyze}
              handleRetryBoondSync={handleRetryBoondSync}
              handleQuickValidate={handleQuickValidate}
              handleQuickReject={handleQuickReject}
              updateStatusMutation={updateStatusMutation}
              updateNoteMutation={updateNoteMutation}
              reanalyzeMutation={reanalyzeMutation}
              retryBoondMutation={retryBoondMutation}
              compact
            />
          </div>
        </div>
      )}

      {/* CSS for drawer animation */}
      <style>{`
        @keyframes slide-in-right {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
        .animate-slide-in-right {
          animation: slide-in-right 0.2s ease-out;
        }
      `}</style>

      {/* Panneau détail opportunité Boond */}
      {showOpportunityDetail && (
        <div className="fixed inset-0 bg-black/50 flex justify-end z-50">
          <div
            className="w-full max-w-lg bg-sur border-l border-lin shadow-xl animate-slide-in-right overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="sticky top-0 bg-sur border-b border-lin p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="dico">
                  <Briefcase className="h-4 w-4" />
                </span>
                <div>
                  <h3 className="ct">Détails Opportunité Boond</h3>
                  <p className="ref !text-[11px]">
                    {opportunityDetail?.reference || posting?.opportunity_reference}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleCloseOpportunityDetail}
                className="p-2 text-mut2 hover:text-ink hover:bg-srf2 rounded-lg transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              {loadingOpportunityDetail ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-mut2" />
                </div>
              ) : opportunityDetail ? (
                <>
                  {/* Title */}
                  <div>
                    <h4 className="text-[15px] font-bold text-ink mb-2">
                      {opportunityDetail.title}
                    </h4>
                    {opportunityDetail.state_name && (
                      <span
                        className="inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold"
                        style={{
                          backgroundColor: opportunityDetail.state_color
                            ? `${opportunityDetail.state_color}20`
                            : 'var(--sla-bg)',
                          color: opportunityDetail.state_color || 'var(--sla-fg)',
                        }}
                      >
                        {opportunityDetail.state_name}
                      </span>
                    )}
                  </div>

                  {/* Client / Company */}
                  {opportunityDetail.company_name && (
                    <div className="flex items-center gap-3 p-3 bg-srf2 rounded-[10px]">
                      <Building2 className="h-4 w-4 text-mut2 shrink-0" />
                      <div className="min-w-0">
                        <p className="ml">Client</p>
                        <p className="mv !text-[13px]">{opportunityDetail.company_name}</p>
                      </div>
                    </div>
                  )}

                  {/* Manager */}
                  {opportunityDetail.manager_name && (
                    <div className="flex items-center gap-3 p-3 bg-srf2 rounded-[10px]">
                      <User className="h-4 w-4 text-mut2 shrink-0" />
                      <div className="min-w-0">
                        <p className="ml">Responsable commercial</p>
                        <p className="mv !text-[13px]">{opportunityDetail.manager_name}</p>
                      </div>
                    </div>
                  )}

                  {/* Contact */}
                  {opportunityDetail.contact_name && (
                    <div className="flex items-center gap-3 p-3 bg-srf2 rounded-[10px]">
                      <Phone className="h-4 w-4 text-mut2 shrink-0" />
                      <div className="min-w-0">
                        <p className="ml">Contact client</p>
                        <p className="mv !text-[13px]">{opportunityDetail.contact_name}</p>
                      </div>
                    </div>
                  )}

                  {/* Location */}
                  {opportunityDetail.place && (
                    <div className="flex items-center gap-3 p-3 bg-srf2 rounded-[10px]">
                      <MapPin className="h-4 w-4 text-mut2 shrink-0" />
                      <div className="min-w-0">
                        <p className="ml">Lieu</p>
                        <p className="mv !text-[13px]">{opportunityDetail.place}</p>
                      </div>
                    </div>
                  )}

                  {/* Dates */}
                  <div className="grid grid-cols-2 gap-3">
                    {opportunityDetail.start_date && (
                      <div className="p-3 bg-srf2 rounded-[10px]">
                        <p className="ml">Date de début</p>
                        <p className="mv !text-[13px]">
                          {new Date(opportunityDetail.start_date).toLocaleDateString('fr-FR')}
                        </p>
                      </div>
                    )}
                    {opportunityDetail.end_date && (
                      <div className="p-3 bg-srf2 rounded-[10px]">
                        <p className="ml">Date de fin</p>
                        <p className="mv !text-[13px]">
                          {new Date(opportunityDetail.end_date).toLocaleDateString('fr-FR')}
                        </p>
                      </div>
                    )}
                    {opportunityDetail.duration && (
                      <div className="p-3 bg-srf2 rounded-[10px]">
                        <p className="ml">Durée</p>
                        <p className="mv !text-[13px]">{opportunityDetail.duration} jours</p>
                      </div>
                    )}
                  </div>

                  {/* Description */}
                  {opportunityDetail.description && (
                    <div className="border border-lin rounded-[10px] p-3.5">
                      <h5 className="xt flex items-center gap-2 mb-2">
                        <FileText className="h-3.5 w-3.5 text-mut2" />
                        Description
                      </h5>
                      <div
                        className="text-[13px] text-mut leading-relaxed max-w-none"
                        dangerouslySetInnerHTML={{ __html: opportunityDetail.description }}
                      />
                    </div>
                  )}

                  {/* Criteria */}
                  {opportunityDetail.criteria && (
                    <div className="border border-lin rounded-[10px] p-3.5">
                      <h5 className="xt flex items-center gap-2 mb-2">
                        <CheckCircle className="h-3.5 w-3.5 text-mut2" />
                        Critères
                      </h5>
                      <div
                        className="text-[13px] text-mut leading-relaxed max-w-none"
                        dangerouslySetInnerHTML={{ __html: opportunityDetail.criteria }}
                      />
                    </div>
                  )}

                  {/* Expertise Area */}
                  {opportunityDetail.expertise_area && (
                    <div className="border border-lin rounded-[10px] p-3.5">
                      <h5 className="xt flex items-center gap-2 mb-2">
                        <Star className="h-3.5 w-3.5 text-mut2" />
                        Domaine d'expertise
                      </h5>
                      <p className="text-[13px] text-mut">{opportunityDetail.expertise_area}</p>
                    </div>
                  )}

                  {/* Agency */}
                  {opportunityDetail.agency_name && (
                    <div className="p-3 bg-srf2 rounded-[10px]">
                      <p className="ml">Agence</p>
                      <p className="mv !text-[13px]">{opportunityDetail.agency_name}</p>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-8 text-mut">
                  <AlertCircle className="h-8 w-8 mx-auto mb-2 text-mut2" />
                  <p className="text-[13px]">Impossible de charger les détails</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Confirmation de suppression */}
      <Modal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        title="Supprimer l'annonce"
      >
        <div className="space-y-4">
          <p className="notec">
            Êtes-vous sûr de vouloir supprimer cette annonce ?
            {posting.turnoverit_reference && ' Elle sera également supprimée de Turnover-IT.'}{' '}
            Cette action est irréversible.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowDeleteConfirm(false)}
              disabled={deleteMutation.isPending}
            >
              Annuler
            </Button>
            <Button
              type="button"
              variant="danger"
              leftIcon={<Trash2 className="h-3.5 w-3.5" />}
              onClick={() => deleteMutation.mutate()}
              isLoading={deleteMutation.isPending}
            >
              Supprimer
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
