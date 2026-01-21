/**
 * JobPostingDetails - Page to view and manage a job posting and its applications.
 */

import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ChevronLeft,
  Loader2,
  AlertCircle,
  ExternalLink,
  Send,
  XCircle,
  Eye,
  Download,
  Building2,
  MapPin,
  Calendar,
  Users,
  FileText,
  Edit2,
  CheckCircle,
  Trash2,
} from 'lucide-react';
import { hrApi } from '../api/hr';
import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_STATUS_COLORS,
  getMatchingScoreColor,
} from '../types';
import type { ApplicationStatus, JobApplication } from '../types';

const JOB_POSTING_STATUS_BADGES = {
  draft: {
    label: 'Brouillon',
    color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
  },
  published: {
    label: 'Publiée',
    color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  },
  closed: {
    label: 'Fermée',
    color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  },
};

export default function JobPostingDetails() {
  const { postingId } = useParams<{ postingId: string }>();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | ''>('');
  const [selectedApplication, setSelectedApplication] = useState<JobApplication | null>(null);
  const [noteText, setNoteText] = useState('');
  const [newStatus, setNewStatus] = useState<ApplicationStatus | ''>('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

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
    queryKey: ['hr-job-applications', postingId, statusFilter],
    queryFn: () =>
      hrApi.getApplications(postingId!, {
        status: statusFilter || undefined,
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
              {posting.opportunity_reference} • Créée le{' '}
              {new Date(posting.created_at).toLocaleDateString('fr-FR')}
            </p>
          </div>
          <div className="flex gap-2">
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
              <button
                onClick={() => closeMutation.mutate()}
                disabled={closeMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white font-medium rounded-lg transition-colors"
              >
                {closeMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <XCircle className="h-4 w-4" />
                )}
                Fermer l'annonce
              </button>
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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Candidatures</h2>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as ApplicationStatus | '')}
            className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">Tous les statuts</option>
            {Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
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
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Candidat
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    TJM
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Disponibilité
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Matching
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Statut
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {applicationsData?.items.map((application) => (
                  <tr
                    key={application.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">
                          {application.full_name}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {application.job_title}
                        </p>
                        <p className="text-xs text-gray-400 dark:text-gray-500">
                          {application.email}
                        </p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-gray-900 dark:text-white">{application.tjm_range}</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-gray-900 dark:text-white">
                        {new Date(application.availability_date).toLocaleDateString('fr-FR')}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      {application.matching_score !== null ? (
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium ${getMatchingScoreColor(
                            application.matching_score
                          )}`}
                        >
                          {application.matching_score}%
                        </span>
                      ) : (
                        <span className="text-gray-500 dark:text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          APPLICATION_STATUS_COLORS[application.status as ApplicationStatus]
                        }`}
                      >
                        {APPLICATION_STATUS_LABELS[application.status as ApplicationStatus]}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleDownloadCv(application)}
                          className="p-1.5 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                          title="Télécharger CV"
                        >
                          <Download className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => {
                            setSelectedApplication(application);
                            setNewStatus(application.status as ApplicationStatus);
                            setNoteText(application.notes || '');
                          }}
                          className="p-1.5 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                          title="Voir détails"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Application Detail Modal */}
      {selectedApplication && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {selectedApplication.full_name}
              </h3>
              <button
                onClick={() => setSelectedApplication(null)}
                className="p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              >
                <XCircle className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Contact Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Email</p>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {selectedApplication.email}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Téléphone</p>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {selectedApplication.phone}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Poste</p>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {selectedApplication.job_title}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">TJM</p>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {selectedApplication.tjm_range}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Disponibilité</p>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {new Date(selectedApplication.availability_date).toLocaleDateString('fr-FR')}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Candidature reçue</p>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {new Date(selectedApplication.created_at).toLocaleDateString('fr-FR')}
                  </p>
                </div>
              </div>

              {/* Matching Details */}
              {selectedApplication.matching_details && (
                <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <FileText className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                    <h4 className="font-medium text-gray-900 dark:text-white">Analyse du profil</h4>
                    <span
                      className={`ml-auto px-2.5 py-0.5 rounded-full text-sm font-medium ${getMatchingScoreColor(
                        selectedApplication.matching_score ?? 0
                      )}`}
                    >
                      {selectedApplication.matching_score}%
                    </span>
                  </div>
                  <p className="text-gray-700 dark:text-gray-300 mb-3">
                    {selectedApplication.matching_details.summary}
                  </p>
                  {selectedApplication.matching_details.strengths.length > 0 && (
                    <div className="mb-2">
                      <p className="text-sm font-medium text-green-700 dark:text-green-400 mb-1">
                        Points forts
                      </p>
                      <ul className="list-disc list-inside text-sm text-gray-600 dark:text-gray-400">
                        {selectedApplication.matching_details.strengths.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {selectedApplication.matching_details.gaps.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-orange-700 dark:text-orange-400 mb-1">
                        Points d'attention
                      </p>
                      <ul className="list-disc list-inside text-sm text-gray-600 dark:text-gray-400">
                        {selectedApplication.matching_details.gaps.map((g, i) => (
                          <li key={i}>{g}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Status Change */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Changer le statut
                </label>
                <div className="flex gap-2">
                  <select
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value as ApplicationStatus)}
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    {Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={handleStatusChange}
                    disabled={
                      updateStatusMutation.isPending ||
                      newStatus === selectedApplication.status
                    }
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors inline-flex items-center gap-2"
                  >
                    {updateStatusMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <CheckCircle className="h-4 w-4" />
                    )}
                    Appliquer
                  </button>
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Notes internes
                </label>
                <textarea
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  placeholder="Ajouter des notes sur ce candidat..."
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
                <button
                  onClick={() => handleNoteUpdate(selectedApplication)}
                  disabled={updateNoteMutation.isPending || noteText === (selectedApplication.notes || '')}
                  className="mt-2 px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-gray-900 dark:text-white font-medium rounded-lg transition-colors inline-flex items-center gap-2"
                >
                  {updateNoteMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Edit2 className="h-4 w-4" />
                  )}
                  Sauvegarder
                </button>
              </div>

              {/* CV Download */}
              <div className="flex justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => handleDownloadCv(selectedApplication)}
                  className="inline-flex items-center gap-2 px-4 py-2 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 font-medium rounded-lg transition-colors"
                >
                  <Download className="h-4 w-4" />
                  Télécharger le CV
                </button>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {selectedApplication.cv_filename}
                </p>
              </div>
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
                  Supprimer le brouillon
                </h3>
              </div>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Êtes-vous sûr de vouloir supprimer ce brouillon d'annonce ? Cette action est irréversible.
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
