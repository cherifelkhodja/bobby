/**
 * ApplicationDetailContent - Reusable detail panel for a job application.
 *
 * Extracted from JobPostingDetails. Renders candidate info, matching analysis,
 * CV quality analysis, status change, notes, and action buttons.
 * Displayed inside modal, drawer, split, or inline expansion layouts.
 */

import {
  Loader2,
  AlertCircle,
  Download,
  FileText,
  Edit2,
  CheckCircle,
  RefreshCw,
  Info,
  Star,
} from 'lucide-react';
import {
  APPLICATION_STATUS_LABELS,
  getMatchingScoreColor,
  getCvQualityScoreColor,
} from '../../types';
import type { ApplicationStatus, JobApplication } from '../../types';
import {
  EXPERIENCE_LEVEL_LABELS,
  CLASSIFICATION_LABELS,
} from '../../constants/hr';

export interface ApplicationDetailContentProps {
  application: JobApplication;
  newStatus: ApplicationStatus | '';
  setNewStatus: (status: ApplicationStatus | '') => void;
  noteText: string;
  setNoteText: (text: string) => void;
  handleStatusChange: () => void;
  handleNoteUpdate: (application: JobApplication) => void;
  handleDownloadCv: (application: JobApplication) => void;
  handleReanalyze: (application: JobApplication) => void;
  handleRetryBoondSync: (application: JobApplication) => void;
  updateStatusMutation: { isPending: boolean };
  updateNoteMutation: { isPending: boolean };
  reanalyzeMutation: { isPending: boolean };
  retryBoondMutation: { isPending: boolean };
  compact?: boolean;
}

export function ApplicationDetailContent({
  application,
  newStatus,
  setNewStatus,
  noteText,
  setNoteText,
  handleStatusChange,
  handleNoteUpdate,
  handleDownloadCv,
  handleReanalyze,
  handleRetryBoondSync,
  updateStatusMutation,
  updateNoteMutation,
  reanalyzeMutation,
  retryBoondMutation,
  compact = false,
}: ApplicationDetailContentProps) {
  return (
    <div className={`${compact ? 'p-3' : 'p-6'} space-y-4`}>
      {/* Candidate Info */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-gray-500 dark:text-gray-400">Email</p>
          <p className="font-medium text-gray-900 dark:text-white">{application.email}</p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400">Téléphone</p>
          <p className="font-medium text-gray-900 dark:text-white">{application.phone}</p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400">Poste</p>
          <p className="font-medium text-gray-900 dark:text-white">{application.job_title}</p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400">TJM</p>
          <p className="font-medium text-gray-900 dark:text-white">{application.tjm_range || '-'}</p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400">Disponibilité</p>
          <p className="font-medium text-gray-900 dark:text-white">
            {application.availability_display || application.availability || '-'}
          </p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400">Date candidature</p>
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            {new Date(application.created_at).toLocaleDateString('fr-FR')}
          </p>
        </div>
      </div>

      {/* Matching Analysis */}
      {application.matching_details && (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            <h4 className="text-sm font-medium text-gray-900 dark:text-white">Analyse Matching</h4>
            <div className="ml-auto relative group">
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium cursor-help ${getMatchingScoreColor(
                  application.matching_score ?? 0
                )}`}
              >
                {application.matching_score}%
                <Info className="h-3 w-3" />
              </span>
              <div className="absolute right-0 top-full mt-1 z-50 hidden group-hover:block w-64 p-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg text-xs">
                <p className="font-medium text-gray-900 dark:text-white mb-1">Score de matching</p>
                <p className="text-gray-600 dark:text-gray-400">
                  Évalue l'adéquation entre le CV du candidat et les exigences du poste (compétences, expérience, technologies).
                </p>
              </div>
            </div>
          </div>
          <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">
            {application.matching_details.summary}
          </p>
          {application.matching_details.strengths.length > 0 && (
            <div className="mb-2">
              <p className="text-xs font-medium text-green-700 dark:text-green-400 mb-1">Points forts</p>
              <ul className="list-disc list-inside text-xs text-gray-600 dark:text-gray-400">
                {application.matching_details.strengths.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {application.matching_details.gaps.length > 0 && (
            <div>
              <p className="text-xs font-medium text-orange-700 dark:text-orange-400 mb-1">Attention</p>
              <ul className="list-disc list-inside text-xs text-gray-600 dark:text-gray-400">
                {application.matching_details.gaps.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* CV Quality Analysis */}
      {application.cv_quality && (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <Star className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            <h4 className="text-sm font-medium text-gray-900 dark:text-white">Analyse Qualité CV</h4>
            <div className="ml-auto relative group">
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium cursor-help ${getCvQualityScoreColor(
                  application.cv_quality_score ?? 0
                )}`}
              >
                {application.cv_quality_score}/20
                <Info className="h-3 w-3" />
              </span>
              <div className="absolute right-0 top-full mt-1 z-50 hidden group-hover:block w-72 p-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg text-xs">
                <p className="font-medium text-gray-900 dark:text-white mb-1">Note de qualité CV</p>
                <p className="text-gray-600 dark:text-gray-400 mb-2">
                  Évalue la qualité intrinsèque du profil : stabilité des missions, qualité des comptes, parcours scolaire, continuité.
                </p>
                <div className="space-y-1 text-gray-600 dark:text-gray-400">
                  <p><span className="font-medium">Niveau :</span> {EXPERIENCE_LEVEL_LABELS[application.cv_quality.niveau_experience] || application.cv_quality.niveau_experience}</p>
                  <p><span className="font-medium">Expérience :</span> {application.cv_quality.annees_experience} ans</p>
                  <p><span className="font-medium">Classification :</span> {CLASSIFICATION_LABELS[application.cv_quality.classification] || application.cv_quality.classification}</p>
                </div>
              </div>
            </div>
          </div>
          <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">
            {application.cv_quality.synthese}
          </p>
          {application.cv_quality.points_forts.length > 0 && (
            <div className="mb-2">
              <p className="text-xs font-medium text-green-700 dark:text-green-400 mb-1">Points forts</p>
              <ul className="list-disc list-inside text-xs text-gray-600 dark:text-gray-400">
                {application.cv_quality.points_forts.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {application.cv_quality.points_faibles.length > 0 && (
            <div>
              <p className="text-xs font-medium text-orange-700 dark:text-orange-400 mb-1">Points faibles</p>
              <ul className="list-disc list-inside text-xs text-gray-600 dark:text-gray-400">
                {application.cv_quality.points_faibles.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Status Change */}
      <div>
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
          Changer le statut
        </label>
        <div className="flex gap-2">
          <select
            value={newStatus}
            onChange={(e) => setNewStatus(e.target.value as ApplicationStatus)}
            className="flex-1 px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            {Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <button
            onClick={handleStatusChange}
            disabled={updateStatusMutation.isPending || newStatus === application.status}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors inline-flex items-center gap-1"
          >
            {updateStatusMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <CheckCircle className="h-3.5 w-3.5" />
            )}
            OK
          </button>
        </div>
      </div>

      {/* Notes */}
      <div>
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
          Notes
        </label>
        <textarea
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          placeholder="Notes sur ce candidat..."
          rows={compact ? 2 : 3}
          className="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        />
        <button
          onClick={() => handleNoteUpdate(application)}
          disabled={updateNoteMutation.isPending || noteText === (application.notes || '')}
          className="mt-1 px-3 py-1.5 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-gray-900 dark:text-white text-sm font-medium rounded-lg transition-colors inline-flex items-center gap-1"
        >
          {updateNoteMutation.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Edit2 className="h-3.5 w-3.5" />
          )}
          Sauvegarder
        </button>
      </div>

      {/* Boond Sync Status */}
      {application.status === 'valide' && (
        <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 dark:text-gray-400">BoondManager :</span>
              {application.boond_sync_status === 'synced' && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">
                  <CheckCircle className="h-3 w-3" />
                  Synchronisé
                </span>
              )}
              {application.boond_sync_status === 'error' && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">
                  <AlertCircle className="h-3 w-3" />
                  Erreur
                </span>
              )}
              {application.boond_sync_status === 'pending' && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300">
                  <Loader2 className="h-3 w-3" />
                  En attente
                </span>
              )}
              {application.boond_candidate_id && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  ID: {application.boond_candidate_id}
                </span>
              )}
            </div>
            {application.boond_sync_status === 'error' && (
              <button
                onClick={() => handleRetryBoondSync(application)}
                disabled={retryBoondMutation.isPending}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors disabled:opacity-50"
              >
                {retryBoondMutation.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <RefreshCw className="h-3 w-3" />
                )}
                Réessayer
              </button>
            )}
          </div>
          {application.boond_sync_error && (
            <p className="text-xs text-red-600 dark:text-red-400 mt-1 truncate" title={application.boond_sync_error}>
              {application.boond_sync_error}
            </p>
          )}
        </div>
      )}

      {/* CV Download & Re-analyze */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={() => handleDownloadCv(application)}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 font-medium rounded-lg transition-colors"
        >
          <Download className="h-3.5 w-3.5" />
          Télécharger CV
        </button>
        <button
          onClick={() => handleReanalyze(application)}
          disabled={reanalyzeMutation.isPending}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 font-medium rounded-lg transition-colors disabled:opacity-50"
          title="Relancer l'analyse IA (matching + qualité CV)"
        >
          {reanalyzeMutation.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          Re-analyser
        </button>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[150px]">
          {application.cv_filename}
        </p>
      </div>
    </div>
  );
}
