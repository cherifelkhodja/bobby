/**
 * JobPostingDetails - Page to view and manage a job posting and its applications.
 */

import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  ChevronLeft,
  Loader2,
  AlertCircle,
  ExternalLink,
  Send,
  XCircle,
  X,
  Eye,
  EyeOff,
  Download,
  Building2,
  MapPin,
  Calendar,
  Users,
  FileText,
  Check,
  CheckCircle,
  Trash2,
  RefreshCw,
  Pencil,
  Info,
  Star,
  Briefcase,
  User,
  Phone,
} from 'lucide-react';
import { hrApi, type OpportunityDetailResponse } from '../api/hr';
import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_STATUS_COLORS,
  getMatchingScoreColor,
  getCvQualityScoreColor,
} from '../types';
import type { ApplicationStatus, JobApplication } from '../types';
import {
  JOB_POSTING_STATUS_BADGES,
  EMPLOYMENT_STATUS_OPTIONS,
  AVAILABILITY_FILTER_OPTIONS,
  SORT_OPTIONS,
  EXPERIENCE_LEVEL_LABELS,
  CLASSIFICATION_LABELS,
  DISPLAY_MODE_OPTIONS,
  type DisplayMode,
} from '../constants/hr';
import { ApplicationDetailContent } from '../components/hr/ApplicationDetailContent';

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
  const [displayMode, setDisplayMode] = useState<DisplayMode>('drawer');
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
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <p className="ml-2 text-gray-600 dark:text-gray-400">Chargement...</p>
      </div>
    );
  }

  if (postingError || !posting) {
    return (
      <div className="space-y-6">
        <Link
          to="/rh"
          className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline"
        >
          <ChevronLeft className="h-5 w-5" />
          Retour
        </Link>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400 flex-shrink-0" />
            <div>
              <h3 className="font-semibold text-red-800 dark:text-red-300">Erreur</h3>
              <p className="text-red-700 dark:text-red-400">
                Annonce non trouvée. Veuillez réessayer.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const statusBadge = JOB_POSTING_STATUS_BADGES[posting.status as keyof typeof JOB_POSTING_STATUS_BADGES];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          to="/rh"
          className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline mb-4"
        >
          <ChevronLeft className="h-5 w-5" />
          Retour aux opportunités
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{posting.title}</h1>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${statusBadge.color}`}>
                {statusBadge.label}
              </span>
            </div>
            <p className="text-gray-600 dark:text-gray-400">
              <button
                onClick={handleShowOpportunityDetail}
                className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
                title="Voir les détails de l'opportunité Boond"
              >
                {posting.opportunity_reference}
              </button>
              {' '}• Créée le{' '}
              {new Date(posting.created_at).toLocaleDateString('fr-FR')}
            </p>
          </div>
          <div className="flex gap-2">
            {/* Edit button - available for all statuses */}
            <Link
              to={`/rh/annonces/edit/${postingId}`}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
            >
              <Pencil className="h-4 w-4" />
              Modifier
            </Link>
            {posting.status === 'draft' && (
              <>
                <button
                  onClick={() => publishMutation.mutate()}
                  disabled={publishMutation.isPending}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-medium rounded-lg transition-colors"
                >
                  {publishMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                  Publier sur Turnover-IT
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 text-red-700 dark:text-red-400 font-medium rounded-lg transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                  Supprimer
                </button>
              </>
            )}
            {posting.status === 'published' && (
              <>
                <button
                  onClick={() => closeMutation.mutate()}
                  disabled={closeMutation.isPending}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-orange-400 text-white font-medium rounded-lg transition-colors"
                >
                  {closeMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <XCircle className="h-4 w-4" />
                  )}
                  Fermer l'annonce
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 text-red-700 dark:text-red-400 font-medium rounded-lg transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                  Supprimer
                </button>
              </>
            )}
            {posting.status === 'closed' && (
              <>
                <button
                  onClick={() => reactivateMutation.mutate()}
                  disabled={reactivateMutation.isPending}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-medium rounded-lg transition-colors"
                >
                  {reactivateMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                  Réactiver l'annonce
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 text-red-700 dark:text-red-400 font-medium rounded-lg transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                  Supprimer
                </button>
              </>
            )}
            {posting.turnoverit_public_url && (
              <a
                href={posting.turnoverit_public_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white font-medium rounded-lg transition-colors"
              >
                <ExternalLink className="h-4 w-4" />
                Voir sur Turnover-IT
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Error alerts */}
      {publishMutation.isError && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-200">
            Erreur lors de la publication. Veuillez réessayer.
          </p>
        </div>
      )}

      {/* Posting Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <Building2 className="h-5 w-5 text-gray-500 dark:text-gray-400" />
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Client</p>
              <p className="font-medium text-gray-900 dark:text-white">
                {posting.client_name || '-'}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <MapPin className="h-5 w-5 text-gray-500 dark:text-gray-400" />
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Localisation</p>
              <p className="font-medium text-gray-900 dark:text-white">
                {[posting.location_city, posting.location_country].filter(Boolean).join(', ') ||
                  posting.location_country}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <Eye className="h-5 w-5 text-gray-500 dark:text-gray-400" />
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Vues</p>
              <p className="font-medium text-gray-900 dark:text-white">
                {posting.view_count}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <Users className="h-5 w-5 text-gray-500 dark:text-gray-400" />
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Candidatures</p>
              <p className="font-medium text-gray-900 dark:text-white">
                {posting.applications_total}{' '}
                {posting.applications_new > 0 && (
                  <span className="text-blue-600 dark:text-blue-400">
                    (+{posting.applications_new} nouvelle{posting.applications_new > 1 ? 's' : ''})
                  </span>
                )}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <Calendar className="h-5 w-5 text-gray-500 dark:text-gray-400" />
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Date de début</p>
              <p className="font-medium text-gray-900 dark:text-white">
                {posting.start_date
                  ? new Date(posting.start_date).toLocaleDateString('fr-FR')
                  : '-'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Public application link */}
      {posting.application_url && posting.status === 'published' && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-blue-900 dark:text-blue-100">
                Lien de candidature public
              </p>
              <p className="text-sm text-blue-700 dark:text-blue-300 break-all">
                {posting.application_url}
              </p>
            </div>
            <button
              onClick={() => navigator.clipboard.writeText(posting.application_url!)}
              className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Copier
            </button>
          </div>
        </div>
      )}

      {/* Applications List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-visible">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 relative z-10">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Candidatures</h2>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {applicationsData?.total || 0} résultat{(applicationsData?.total || 0) > 1 ? 's' : ''}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 relative">
            {/* Status filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as ApplicationStatus | '')}
              className="filter-select"
            >
              <option value="">Tous statuts</option>
              {Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            {/* Employment status filter */}
            <select
              value={employmentStatusFilter}
              onChange={(e) => setEmploymentStatusFilter(e.target.value)}
              className="filter-select"
            >
              {EMPLOYMENT_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            {/* Availability filter */}
            <select
              value={availabilityFilter}
              onChange={(e) => setAvailabilityFilter(e.target.value)}
              className="filter-select"
            >
              {AVAILABILITY_FILTER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            {/* Separator */}
            <span className="text-gray-300 dark:text-gray-600">|</span>
            {/* Sort */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="filter-select"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  Tri: {opt.label}
                </option>
              ))}
            </select>
            <button
              onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
              className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-600"
              title={sortOrder === 'desc' ? 'Décroissant' : 'Croissant'}
            >
              {sortOrder === 'desc' ? '↓' : '↑'}
            </button>
            {/* Separator */}
            <span className="text-gray-300 dark:text-gray-600">|</span>
            {/* Display mode selector */}
            <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-700 rounded p-0.5">
              {DISPLAY_MODE_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                return (
                  <button
                    key={opt.value}
                    onClick={() => {
                      setDisplayMode(opt.value);
                      if (opt.value !== 'inline') setExpandedRowId(null);
                      if (opt.value === 'inline') setSelectedApplication(null);
                    }}
                    className={`p-1 rounded transition-colors ${
                      displayMode === opt.value
                        ? 'bg-white dark:bg-gray-600 shadow-sm text-blue-600 dark:text-blue-400'
                        : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                    }`}
                    title={opt.label}
                  >
                    <Icon className="h-3.5 w-3.5" />
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {loadingApplications ? (
          <div className="p-8 flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
          </div>
        ) : applicationsData?.items.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            Aucune candidature pour le moment
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px]">
                    Candidat
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px] w-[180px]">
                    Statut Pro
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px] w-[100px]">
                    TJM
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px] w-[140px]">
                    Salaire
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px] w-[120px]">
                    Disponibilité
                  </th>
                  <th className="text-center py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px] w-[90px]">
                    Matching
                  </th>
                  <th className="text-center py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px] w-[90px]">
                    Qualité CV
                  </th>
                  <th className="text-center py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px] w-[90px]">
                    Statut
                  </th>
                  <th className="text-center py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px] w-[140px]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {applicationsData?.items.map((application) => {
                  const isExpanded = displayMode === 'inline' && expandedRowId === application.id;
                  const isUnread = !application.is_read;
                  return (
                    <React.Fragment key={application.id}>
                      <tr
                        className={`transition-colors ${
                          isExpanded
                            ? 'bg-blue-50 dark:bg-blue-900/20'
                            : isUnread
                              ? 'bg-blue-50/50 dark:bg-blue-900/10 hover:bg-blue-100/50 dark:hover:bg-blue-900/20'
                              : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                        }`}
                      >
                        <td className="py-2 px-3">
                          <div>
                            <button
                              onClick={() => handleOpenApplication(application)}
                              className={`font-medium text-left ${isUnread ? 'text-blue-900 dark:text-blue-100' : 'text-gray-900 dark:text-white'}`}
                            >
                              {application.full_name}
                              {isUnread && (
                                <span className="ml-1.5 inline-flex items-center px-1 py-px rounded text-[7px] font-semibold bg-blue-500 text-white uppercase align-middle">
                                  new
                                </span>
                              )}
                            </button>
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                              {application.job_title}
                            </p>
                            <p className="text-[10px] text-gray-400 dark:text-gray-500">
                              {application.email}
                            </p>
                          </div>
                        </td>
                        <td className="py-2 px-3">
                          {application.employment_status_display ? (
                            <div className="flex flex-wrap gap-1">
                              {application.employment_status_display.toLowerCase().includes('salarié') && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300">
                                  Salarié
                                </span>
                              )}
                              {application.employment_status_display.toLowerCase().includes('freelance') && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-300">
                                  Freelance
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="py-2 px-3">
                          <span className="text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">{application.tjm_range || '-'}</span>
                        </td>
                        <td className="py-2 px-3">
                          <span className="text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">{application.salary_range || '-'}</span>
                        </td>
                        <td className="py-2 px-3">
                          <span className="text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">
                            {application.availability_display || application.availability || '-'}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-center">
                          {application.matching_score !== null ? (
                            <div className="relative group inline-block">
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium cursor-help ${getMatchingScoreColor(
                                  application.matching_score
                                )}`}
                              >
                                {application.matching_score}%
                                <Info className="h-3 w-3 opacity-60" />
                              </span>
                              {application.matching_details && (
                                <div className="absolute left-0 top-full mt-1 z-50 hidden group-hover:block w-72 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg text-xs">
                                  <p className="font-medium text-gray-900 dark:text-white mb-2">Analyse Matching</p>
                                  <p className="text-gray-600 dark:text-gray-400 mb-2">{application.matching_details.summary}</p>
                                  {application.matching_details.strengths.length > 0 && (
                                    <div className="mb-2">
                                      <p className="font-medium text-green-700 dark:text-green-400">Points forts :</p>
                                      <ul className="list-disc list-inside text-gray-600 dark:text-gray-400">
                                        {application.matching_details.strengths.slice(0, 3).map((s, i) => (
                                          <li key={i}>{s}</li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                  {application.matching_details.gaps.length > 0 && (
                                    <div>
                                      <p className="font-medium text-orange-700 dark:text-orange-400">Attention :</p>
                                      <ul className="list-disc list-inside text-gray-600 dark:text-gray-400">
                                        {application.matching_details.gaps.slice(0, 3).map((g, i) => (
                                          <li key={i}>{g}</li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          ) : (
                            <span className="text-gray-500 dark:text-gray-400">-</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-center">
                          {application.cv_quality_score !== null && application.cv_quality ? (
                            <div className="relative group inline-block">
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium cursor-help ${getCvQualityScoreColor(
                                  application.cv_quality_score
                                )}`}
                              >
                                {application.cv_quality_score}/20
                                <Info className="h-3 w-3 opacity-60" />
                              </span>
                              <div className="absolute left-0 top-full mt-1 z-50 hidden group-hover:block w-80 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg text-xs">
                                <p className="font-medium text-gray-900 dark:text-white mb-2">Analyse Qualité CV</p>
                                <div className="flex gap-2 mb-2">
                                  <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-gray-700 dark:text-gray-300">
                                    {EXPERIENCE_LEVEL_LABELS[application.cv_quality.niveau_experience] || application.cv_quality.niveau_experience}
                                  </span>
                                  <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-gray-700 dark:text-gray-300">
                                    {application.cv_quality.annees_experience} ans
                                  </span>
                                  <span className={`px-2 py-0.5 rounded ${
                                    application.cv_quality.classification === 'EXCELLENT' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' :
                                    application.cv_quality.classification === 'BON' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300' :
                                    application.cv_quality.classification === 'MOYEN' ? 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300' :
                                    'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                                  }`}>
                                    {CLASSIFICATION_LABELS[application.cv_quality.classification] || application.cv_quality.classification}
                                  </span>
                                </div>
                                {application.cv_quality.details_notes && (
                                  <div className="space-y-1 mb-2 border-t border-gray-200 dark:border-gray-700 pt-2">
                                    <p className="font-medium text-gray-700 dark:text-gray-300 mb-1">Détail des notes :</p>
                                    {application.cv_quality.details_notes.stabilite_missions && (
                                      <div className="flex justify-between">
                                        <span className="text-gray-600 dark:text-gray-400">Stabilité missions</span>
                                        <span className="font-medium">{application.cv_quality.details_notes.stabilite_missions.note}/{application.cv_quality.details_notes.stabilite_missions.max}</span>
                                      </div>
                                    )}
                                    {application.cv_quality.details_notes.qualite_comptes && (
                                      <div className="flex justify-between">
                                        <span className="text-gray-600 dark:text-gray-400">Qualité comptes</span>
                                        <span className="font-medium">{application.cv_quality.details_notes.qualite_comptes.note}/{application.cv_quality.details_notes.qualite_comptes.max}</span>
                                      </div>
                                    )}
                                    {application.cv_quality.details_notes.parcours_scolaire && (
                                      <div className="flex justify-between">
                                        <span className="text-gray-600 dark:text-gray-400">Parcours scolaire</span>
                                        <span className="font-medium">{application.cv_quality.details_notes.parcours_scolaire.note}/{application.cv_quality.details_notes.parcours_scolaire.max}</span>
                                      </div>
                                    )}
                                    {application.cv_quality.details_notes.continuite_parcours && (
                                      <div className="flex justify-between">
                                        <span className="text-gray-600 dark:text-gray-400">Continuité parcours</span>
                                        <span className="font-medium">{application.cv_quality.details_notes.continuite_parcours.note}/{application.cv_quality.details_notes.continuite_parcours.max}</span>
                                      </div>
                                    )}
                                    {application.cv_quality.details_notes.bonus_malus && application.cv_quality.details_notes.bonus_malus.valeur !== 0 && (
                                      <div className="flex justify-between">
                                        <span className="text-gray-600 dark:text-gray-400">Bonus/Malus</span>
                                        <span className={`font-medium ${application.cv_quality.details_notes.bonus_malus.valeur > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                          {application.cv_quality.details_notes.bonus_malus.valeur > 0 ? '+' : ''}{application.cv_quality.details_notes.bonus_malus.valeur}
                                        </span>
                                      </div>
                                    )}
                                  </div>
                                )}
                                <p className="text-gray-600 dark:text-gray-400 italic">{application.cv_quality.synthese}</p>
                              </div>
                            </div>
                          ) : (
                            <span className="text-gray-500 dark:text-gray-400">-</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-center">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${
                              APPLICATION_STATUS_COLORS[application.status as ApplicationStatus]
                            }`}
                          >
                            {APPLICATION_STATUS_LABELS[application.status as ApplicationStatus]}
                          </span>
                        </td>
                        <td className="py-2 px-3">
                          <div className="flex items-center justify-center gap-0.5">
                            {/* Voir */}
                            <button
                              onClick={() => handleOpenApplication(application)}
                              className={`p-1.5 rounded-lg transition-colors ${
                                isExpanded
                                  ? 'text-blue-700 bg-blue-100 dark:text-blue-300 dark:bg-blue-800/30'
                                  : 'text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20'
                              }`}
                              title="Voir détails"
                            >
                              <Eye className="h-4 w-4" />
                            </button>
                            {/* Marquer comme lu */}
                            <button
                              onClick={() => !application.is_read && handleMarkAsRead(application)}
                              disabled={application.is_read}
                              className={`p-1.5 rounded-lg transition-colors ${
                                application.is_read
                                  ? 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                                  : 'text-orange-600 dark:text-orange-400 hover:bg-orange-50 dark:hover:bg-orange-900/20'
                              }`}
                              title={application.is_read ? 'Déjà lu' : 'Marquer comme lu'}
                            >
                              <EyeOff className="h-4 w-4" />
                            </button>
                            {/* Valider */}
                            <button
                              onClick={() => application.status === 'en_cours' && handleQuickValidate(application)}
                              disabled={application.status !== 'en_cours'}
                              className={`p-1.5 rounded-lg transition-colors ${
                                application.status !== 'en_cours'
                                  ? 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                                  : 'text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20'
                              }`}
                              title={application.status === 'en_cours' ? 'Valider' : 'Non disponible'}
                            >
                              <Check className="h-4 w-4" />
                            </button>
                            {/* Refuser */}
                            <button
                              onClick={() => application.status === 'en_cours' && handleQuickReject(application)}
                              disabled={application.status !== 'en_cours'}
                              className={`p-1.5 rounded-lg transition-colors ${
                                application.status !== 'en_cours'
                                  ? 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                                  : 'text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20'
                              }`}
                              title={application.status === 'en_cours' ? 'Refuser' : 'Non disponible'}
                            >
                              <XCircle className="h-4 w-4" />
                            </button>
                            {/* Télécharger CV */}
                            <button
                              onClick={() => handleDownloadCv(application)}
                              className="p-1.5 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                              title="Télécharger CV"
                            >
                              <Download className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                      {/* Inline expansion row */}
                      {isExpanded && selectedApplication && selectedApplication.id === application.id && (
                        <tr className="bg-blue-50/50 dark:bg-blue-900/10">
                          <td colSpan={9} className="p-0">
                            <div className="border-l-4 border-blue-500">
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
                                updateStatusMutation={updateStatusMutation}
                                updateNoteMutation={updateNoteMutation}
                                reanalyzeMutation={reanalyzeMutation}
                                retryBoondMutation={retryBoondMutation}
                                compact
                              />
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Application Detail - Modal Mode */}
      {selectedApplication && displayMode === 'modal' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between sticky top-0 bg-white dark:bg-gray-800 z-10">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {selectedApplication.full_name}
              </h3>
              <button
                onClick={handleCloseDetail}
                className="p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
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
              updateStatusMutation={updateStatusMutation}
              updateNoteMutation={updateNoteMutation}
              reanalyzeMutation={reanalyzeMutation}
              retryBoondMutation={retryBoondMutation}
            />
          </div>
        </div>
      )}

      {/* Application Detail - Drawer Mode */}
      {selectedApplication && displayMode === 'drawer' && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/30 z-40"
            onClick={handleCloseDetail}
          />
          {/* Drawer */}
          <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-white dark:bg-gray-800 shadow-xl z-50 overflow-y-auto animate-slide-in-right">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between sticky top-0 bg-white dark:bg-gray-800 z-10">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {selectedApplication.full_name}
              </h3>
              <button
                onClick={handleCloseDetail}
                className="p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
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
              updateStatusMutation={updateStatusMutation}
              updateNoteMutation={updateNoteMutation}
              reanalyzeMutation={reanalyzeMutation}
              retryBoondMutation={retryBoondMutation}
            />
          </div>
        </>
      )}

      {/* Application Detail - Split View */}
      {selectedApplication && displayMode === 'split' && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow mt-4">
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              Détails : {selectedApplication.full_name}
            </h3>
            <button
              onClick={handleCloseDetail}
              className="p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            >
              <X className="h-4 w-4" />
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
            updateStatusMutation={updateStatusMutation}
            updateNoteMutation={updateNoteMutation}
            reanalyzeMutation={reanalyzeMutation}
            retryBoondMutation={retryBoondMutation}
            compact
          />
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

      {/* Opportunity Detail Drawer */}
      {showOpportunityDetail && (
        <div className="fixed inset-0 bg-black/50 flex justify-end z-50">
          <div
            className="w-full max-w-lg bg-white dark:bg-gray-800 shadow-xl animate-slide-in-right overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <Briefcase className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">Détails Opportunité Boond</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {opportunityDetail?.reference || posting?.opportunity_reference}
                  </p>
                </div>
              </div>
              <button
                onClick={handleCloseOpportunityDetail}
                className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              {loadingOpportunityDetail ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                </div>
              ) : opportunityDetail ? (
                <>
                  {/* Title */}
                  <div>
                    <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                      {opportunityDetail.title}
                    </h4>
                    {opportunityDetail.state_name && (
                      <span
                        className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium"
                        style={{
                          backgroundColor: opportunityDetail.state_color ? `${opportunityDetail.state_color}20` : '#e5e7eb',
                          color: opportunityDetail.state_color || '#6b7280',
                        }}
                      >
                        {opportunityDetail.state_name}
                      </span>
                    )}
                  </div>

                  {/* Client / Company */}
                  {opportunityDetail.company_name && (
                    <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <Building2 className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                      <div>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Client</p>
                        <p className="font-medium text-gray-900 dark:text-white">{opportunityDetail.company_name}</p>
                      </div>
                    </div>
                  )}

                  {/* Manager */}
                  {opportunityDetail.manager_name && (
                    <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <User className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                      <div>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Responsable commercial</p>
                        <p className="font-medium text-gray-900 dark:text-white">{opportunityDetail.manager_name}</p>
                      </div>
                    </div>
                  )}

                  {/* Contact */}
                  {opportunityDetail.contact_name && (
                    <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <Phone className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                      <div>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Contact client</p>
                        <p className="font-medium text-gray-900 dark:text-white">{opportunityDetail.contact_name}</p>
                      </div>
                    </div>
                  )}

                  {/* Location */}
                  {opportunityDetail.place && (
                    <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <MapPin className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                      <div>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Lieu</p>
                        <p className="font-medium text-gray-900 dark:text-white">{opportunityDetail.place}</p>
                      </div>
                    </div>
                  )}

                  {/* Dates */}
                  <div className="grid grid-cols-2 gap-3">
                    {opportunityDetail.start_date && (
                      <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                        <p className="text-xs text-gray-500 dark:text-gray-400">Date de début</p>
                        <p className="font-medium text-gray-900 dark:text-white">
                          {new Date(opportunityDetail.start_date).toLocaleDateString('fr-FR')}
                        </p>
                      </div>
                    )}
                    {opportunityDetail.end_date && (
                      <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                        <p className="text-xs text-gray-500 dark:text-gray-400">Date de fin</p>
                        <p className="font-medium text-gray-900 dark:text-white">
                          {new Date(opportunityDetail.end_date).toLocaleDateString('fr-FR')}
                        </p>
                      </div>
                    )}
                    {opportunityDetail.duration && (
                      <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                        <p className="text-xs text-gray-500 dark:text-gray-400">Durée</p>
                        <p className="font-medium text-gray-900 dark:text-white">{opportunityDetail.duration} jours</p>
                      </div>
                    )}
                  </div>

                  {/* Description */}
                  {opportunityDetail.description && (
                    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
                      <h5 className="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        Description
                      </h5>
                      <div
                        className="text-sm text-gray-700 dark:text-gray-300 prose prose-sm dark:prose-invert max-w-none"
                        dangerouslySetInnerHTML={{ __html: opportunityDetail.description }}
                      />
                    </div>
                  )}

                  {/* Criteria */}
                  {opportunityDetail.criteria && (
                    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
                      <h5 className="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                        <CheckCircle className="h-4 w-4" />
                        Critères
                      </h5>
                      <div
                        className="text-sm text-gray-700 dark:text-gray-300 prose prose-sm dark:prose-invert max-w-none"
                        dangerouslySetInnerHTML={{ __html: opportunityDetail.criteria }}
                      />
                    </div>
                  )}

                  {/* Expertise Area */}
                  {opportunityDetail.expertise_area && (
                    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
                      <h5 className="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                        <Star className="h-4 w-4" />
                        Domaine d'expertise
                      </h5>
                      <p className="text-sm text-gray-700 dark:text-gray-300">{opportunityDetail.expertise_area}</p>
                    </div>
                  )}

                  {/* Agency */}
                  {opportunityDetail.agency_name && (
                    <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <p className="text-xs text-gray-500 dark:text-gray-400">Agence</p>
                      <p className="font-medium text-gray-900 dark:text-white">{opportunityDetail.agency_name}</p>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <AlertCircle className="h-8 w-8 mx-auto mb-2" />
                  <p>Impossible de charger les détails</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-full">
                  <Trash2 className="h-6 w-6 text-red-600 dark:text-red-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Supprimer l'annonce
                </h3>
              </div>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Êtes-vous sûr de vouloir supprimer cette annonce ?
                {posting?.turnoverit_reference && ' Elle sera également supprimée de Turnover-IT.'}
                {' '}Cette action est irréversible.
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white font-medium rounded-lg transition-colors"
                >
                  Annuler
                </button>
                <button
                  onClick={() => deleteMutation.mutate()}
                  disabled={deleteMutation.isPending}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white font-medium rounded-lg transition-colors"
                >
                  {deleteMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                  Supprimer
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
