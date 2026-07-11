/**
 * ApplicationDetailContent - Reusable detail panel for a job application (design v2).
 *
 * Renders the "expand" content of an application row: analyses IA (matching +
 * qualité CV) on the left, coordonnées + actions (statut, notes, CV) on the right.
 * In `compact` mode it returns two column fragments meant to be placed inside a
 * 2-column grid parent (`.expand` or equivalent); otherwise columns are stacked
 * (modal / drawer layouts).
 */

import { Download, FileText, RefreshCw, Star } from 'lucide-react';
import { APPLICATION_STATUS_LABELS } from '../../types';
import type { ApplicationStatus, JobApplication } from '../../types';
import {
  EXPERIENCE_LEVEL_LABELS,
  CLASSIFICATION_LABELS,
} from '../../constants/hr';
import { Button } from '../ui/Button';

/** Chip v2 pour le score de matching : ≥80 vert, 50-79 ambre, <50 rouge. */
export function matchingScoreChip(score: number): string {
  if (score >= 80) return 'st-grn';
  if (score >= 50) return 'st-amb';
  return 'st-red';
}

/** Chip v2 pour la note de qualité CV (/20). */
export function cvQualityScoreChip(score: number): string {
  if (score >= 16) return 'st-grn';
  if (score >= 12) return 'st-blu';
  if (score >= 8) return 'st-amb';
  return 'st-red';
}

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
  handleQuickValidate?: (application: JobApplication) => void;
  handleQuickReject?: (application: JobApplication) => void;
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
  handleQuickValidate,
  handleQuickReject,
  updateStatusMutation,
  updateNoteMutation,
  reanalyzeMutation,
  retryBoondMutation,
  compact = false,
}: ApplicationDetailContentProps) {
  const infoPairs: { label: string; value: string }[] = [
    { label: 'Email', value: application.email },
    { label: 'Téléphone', value: application.phone || '—' },
    { label: 'Poste', value: application.job_title || '—' },
    { label: 'Statut pro', value: application.employment_status_display || '—' },
    ...(application.tjm_range ? [{ label: 'TJM', value: application.tjm_range }] : []),
    ...(application.salary_range ? [{ label: 'Salaire', value: application.salary_range }] : []),
    {
      label: 'Disponibilité',
      value: application.availability_display || application.availability || '—',
    },
    {
      label: 'Candidature',
      value: new Date(application.created_at).toLocaleDateString('fr-FR'),
    },
    { label: 'CV', value: application.cv_filename || '—' },
  ];

  /* ── Colonne gauche : analyses IA ─────────────────────────────────── */
  const analysisColumn = (
    <div className="space-y-3 min-w-0">
      {application.matching_details ? (
        <div className="xcard">
          <div className="xh">
            <FileText className="h-3.5 w-3.5 text-mut2 shrink-0" />
            <h4 className="xt">Analyse Matching</h4>
            {application.matching_score !== null && (
              <span className={`st ${matchingScoreChip(application.matching_score)} ml-auto`}>
                {application.matching_score} %
              </span>
            )}
          </div>
          <p className="xp">{application.matching_details.summary}</p>
          {application.matching_details.strengths.length > 0 && (
            <>
              <p className="xl g">Points forts</p>
              <ul className="xul">
                {application.matching_details.strengths.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </>
          )}
          {application.matching_details.gaps.length > 0 && (
            <>
              <p className="xl o">Attention</p>
              <ul className="xul">
                {application.matching_details.gaps.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      ) : (
        <div className="xcard">
          <div className="xh">
            <FileText className="h-3.5 w-3.5 text-mut2 shrink-0" />
            <h4 className="xt">Analyse Matching</h4>
          </div>
          <p className="notec">
            Analyse IA non disponible pour cette candidature — utilisez « Re-analyser ».
          </p>
        </div>
      )}

      {application.cv_quality && (
        <div className="xcard">
          <div className="xh">
            <Star className="h-3.5 w-3.5 text-mut2 shrink-0" />
            <h4 className="xt">Analyse Qualité CV</h4>
            {application.cv_quality_score !== null && (
              <span className={`st ${cvQualityScoreChip(application.cv_quality_score)} ml-auto`}>
                {application.cv_quality_score}/20
              </span>
            )}
          </div>
          <p className="xp">{application.cv_quality.synthese}</p>
          <p className="notec">
            Niveau :{' '}
            {EXPERIENCE_LEVEL_LABELS[application.cv_quality.niveau_experience] ||
              application.cv_quality.niveau_experience}{' '}
            · Expérience : {application.cv_quality.annees_experience} ans · Classification :{' '}
            {CLASSIFICATION_LABELS[application.cv_quality.classification] ||
              application.cv_quality.classification}
          </p>
          {application.cv_quality.points_forts.length > 0 && (
            <>
              <p className="xl g">Points forts</p>
              <ul className="xul">
                {application.cv_quality.points_forts.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </>
          )}
          {application.cv_quality.points_faibles.length > 0 && (
            <>
              <p className="xl o">Points faibles</p>
              <ul className="xul">
                {application.cv_quality.points_faibles.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );

  /* ── Colonne droite : coordonnées + actions ───────────────────────── */
  const actionsColumn = (
    <div className="space-y-3 min-w-0">
      <div className="xcard">
        <div className="cfgrid !grid-cols-2 !mt-0">
          {infoPairs.map(({ label, value }) => (
            <div key={label} className="min-w-0">
              <p className="ml">{label}</p>
              <p className="mv !text-[12.5px] break-words">{value}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="xcard">
        <label className="f-lab" htmlFor={`app-status-${application.id}`}>
          Changer le statut
        </label>
        <div className="flex gap-2">
          <select
            id={`app-status-${application.id}`}
            value={newStatus}
            onChange={(e) => setNewStatus(e.target.value as ApplicationStatus)}
            className="f-in !px-2.5 flex-1 min-w-0"
          >
            {Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <Button
            type="button"
            onClick={handleStatusChange}
            disabled={newStatus === application.status}
            isLoading={updateStatusMutation.isPending}
            className="!h-[38px]"
          >
            OK
          </Button>
        </div>
        {application.status === 'en_cours' && handleQuickValidate && handleQuickReject && (
          <div className="flex gap-2 mt-2.5">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="flex-1 !text-grn-fg"
              onClick={() => handleQuickValidate(application)}
            >
              Valider
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="flex-1 !text-redt"
              onClick={() => handleQuickReject(application)}
            >
              Refuser
            </Button>
          </div>
        )}

        <label className="f-lab !mt-3.5" htmlFor={`app-notes-${application.id}`}>
          Notes
        </label>
        <textarea
          id={`app-notes-${application.id}`}
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          placeholder="Notes sur ce candidat…"
          rows={compact ? 2 : 3}
          className="f-ta !min-h-[54px]"
        />
        <Button
          type="button"
          variant="secondary"
          size="sm"
          className="mt-2"
          onClick={() => handleNoteUpdate(application)}
          disabled={noteText === (application.notes || '')}
          isLoading={updateNoteMutation.isPending}
        >
          Sauvegarder la note
        </Button>

        {application.status === 'valide' && (
          <div className="mt-3.5 pt-3 border-t border-lin2">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="ml !mb-0">BoondManager</span>
                {application.boond_sync_status === 'synced' && (
                  <span className="st st-grn">
                    <span className="dot" />
                    Synchronisé
                  </span>
                )}
                {application.boond_sync_status === 'error' && (
                  <span className="st st-red">
                    <span className="dot" />
                    Erreur
                  </span>
                )}
                {application.boond_sync_status === 'pending' && (
                  <span className="st st-amb">
                    <span className="dot" />
                    En attente
                  </span>
                )}
                {application.boond_candidate_id && (
                  <span className="ref !text-[11px]">ID {application.boond_candidate_id}</span>
                )}
              </div>
              {application.boond_sync_status === 'error' && (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  leftIcon={<RefreshCw className="h-3 w-3" />}
                  onClick={() => handleRetryBoondSync(application)}
                  isLoading={retryBoondMutation.isPending}
                >
                  Réessayer
                </Button>
              )}
            </div>
            {application.boond_sync_error && (
              <p
                className="text-[11.5px] text-redt mt-1.5 truncate"
                title={application.boond_sync_error}
              >
                {application.boond_sync_error}
              </p>
            )}
          </div>
        )}

        <div className="flex items-center justify-between gap-2 flex-wrap mt-3.5 pt-3 border-t border-lin2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            leftIcon={<Download className="h-3.5 w-3.5" />}
            onClick={() => handleDownloadCv(application)}
          >
            Télécharger CV
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
            onClick={() => handleReanalyze(application)}
            isLoading={reanalyzeMutation.isPending}
            title="Relancer l'analyse IA (matching + qualité CV)"
          >
            Re-analyser
          </Button>
        </div>
      </div>
    </div>
  );

  if (compact) {
    // Deux enfants directs : à placer dans un parent en grille 2 colonnes (`.expand`).
    return (
      <>
        {analysisColumn}
        {actionsColumn}
      </>
    );
  }

  return (
    <div className="p-5 space-y-3">
      {analysisColumn}
      {actionsColumn}
    </div>
  );
}
