import { useQuery } from '@tanstack/react-query';
import {
  Calendar,
  CalendarCheck,
  CalendarX,
  CheckCircle,
  Download,
  FileText,
  Timer,
  X,
  XCircle,
} from 'lucide-react';

import { vigilanceApi } from '../../api/vigilance';
import { Button } from '../ui/Button';
import { PageSpinner } from '../ui/Spinner';
import { getDocumentBadgeConfig } from '../../types';
import type { VigilanceDocument } from '../../types';
import { daysUntil, formatDate } from './dateUtils';

// ─── Helpers ──────────────────────────────────────────────────────────────────

export function ExpiryBadge({ expiresAt }: { expiresAt: string | null }) {
  const days = daysUntil(expiresAt);
  if (days === null) return null;

  if (days < 0)
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 px-2 py-0.5 text-xs font-medium">
        <CalendarX className="h-3 w-3" /> Expiré il y a {Math.abs(days)}j
      </span>
    );
  if (days <= 30)
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300 px-2 py-0.5 text-xs font-medium">
        <Timer className="h-3 w-3" /> Expire dans {days}j
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 px-2 py-0.5 text-xs font-medium">
      <CalendarCheck className="h-3 w-3" /> Valide encore {days}j
    </span>
  );
}

// ─── Auto-check labels ────────────────────────────────────────────────────────

const AUTO_CHECK_CONFIG: Record<string, { label: string; isDate?: boolean; isText?: boolean }> = {
  document_date: { label: "Date d'émission détectée", isDate: true },
  expiry_date:   { label: "Date d'expiration détectée", isDate: true },
  is_valid:      { label: 'Document valide à la date d\'émission' },
  beneficiaire:  { label: 'Bénéficiaire identifié', isText: true },
  iban:          { label: 'IBAN détecté', isText: true },
  bic:           { label: 'BIC détecté', isText: true },
};

// ─── Document Viewer Modal ────────────────────────────────────────────────────

export function DocumentViewerModal({
  doc,
  onClose,
  onValidate,
  onRejectStart,
  isValidating,
}: {
  doc: VigilanceDocument;
  onClose: () => void;
  onValidate: () => void;
  onRejectStart: () => void;
  isValidating: boolean;
}) {
  const { data: urlData, isLoading } = useQuery({
    queryKey: ['vigilance-doc-url', doc.id],
    queryFn: () => vigilanceApi.getDocumentDownloadUrl(doc.id),
    enabled: !!doc.s3_key,
    staleTime: 20 * 60 * 1000,
  });

  const isPdf =
    doc.file_name?.toLowerCase().endsWith('.pdf') ||
    urlData?.url?.includes('.pdf');
  const canValidate = doc.status === 'received';

  // Fallback: use values from auto_check_results if dedicated columns are null
  const acr = doc.auto_check_results ?? {};
  const docDate = doc.document_date ?? (acr.document_date as string | null | undefined) ?? null;
  const expiryDate = doc.expires_at ?? (acr.expiry_date as string | null | undefined) ?? null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-6xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-3">
            <FileText className="h-5 w-5 text-primary-500" />
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                {doc.document_type_display}
              </h3>
              {doc.file_name && (
                <p className="text-xs text-gray-500 dark:text-gray-400">{doc.file_name}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {urlData?.url && (
              <a
                href={urlData.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white border border-gray-300 dark:border-gray-600 rounded-lg px-2.5 py-1.5 transition-colors"
              >
                <Download className="h-3.5 w-3.5" /> Télécharger
              </a>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="flex flex-1 min-h-0">
          {/* Viewer */}
          <div className="flex-1 bg-gray-100 dark:bg-gray-800 flex items-center justify-center overflow-hidden rounded-bl-xl">
            {!doc.s3_key ? (
              <div className="text-center text-gray-400">
                <FileText className="h-12 w-12 mx-auto mb-2 opacity-40" />
                <p className="text-sm">Aucun fichier disponible</p>
              </div>
            ) : isLoading ? (
              <PageSpinner />
            ) : urlData?.url ? (
              isPdf ? (
                <iframe
                  src={`${urlData.url}#toolbar=1&navpanes=0`}
                  className="w-full h-full"
                  title={doc.document_type_display}
                />
              ) : (
                <img
                  src={urlData.url}
                  alt={doc.document_type_display}
                  className="max-w-full max-h-full object-contain p-4"
                />
              )
            ) : (
              <p className="text-sm text-gray-500">Impossible de charger le document.</p>
            )}
          </div>

          {/* Metadata + Actions sidebar */}
          <div className="w-72 flex-shrink-0 border-l border-gray-200 dark:border-gray-700 flex flex-col overflow-y-auto">
            {/* Status */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Statut</p>
              {(() => {
                const cfg = getDocumentBadgeConfig(doc);
                return (
                  <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${cfg.color}`}>
                    {cfg.label}
                  </span>
                );
              })()}
            </div>

            {/* Dates */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 space-y-3">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Dates</p>

              <div className="flex items-start gap-2">
                <Calendar className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Déposé le</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatDate(doc.uploaded_at)}
                  </p>
                </div>
              </div>

              {doc.validated_at && (
                <div className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Validé le</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {formatDate(doc.validated_at)}
                    </p>
                  </div>
                </div>
              )}

              {doc.rejected_at && (
                <div className="flex items-start gap-2">
                  <XCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Rejeté le</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {formatDate(doc.rejected_at)}
                    </p>
                  </div>
                </div>
              )}

              {doc.document_type !== 'rib' && (
                <>
                  <div className="flex items-start gap-2">
                    <FileText className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Date du document</p>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {formatDate(docDate)}
                      </p>
                      {doc.is_valid_at_upload === false && (
                        <span className="inline-flex items-center gap-1 mt-1 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 px-2 py-0.5 text-xs font-medium">
                          <XCircle className="h-3 w-3" /> Document invalide à l'émission
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-start gap-2">
                    <Timer className="h-4 w-4 text-orange-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Valide jusqu'au</p>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {formatDate(expiryDate)}
                      </p>
                      {expiryDate && (
                        <div className="mt-1">
                          <ExpiryBadge expiresAt={expiryDate} />
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}

              {doc.file_size && (
                <div className="flex items-start gap-2">
                  <FileText className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Taille</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {(doc.file_size / 1024).toFixed(1)} Ko
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Rejection reason */}
            {doc.rejection_reason && (
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Motif du rejet</p>
                <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg p-2">
                  {doc.rejection_reason}
                </p>
              </div>
            )}

            {/* Unavailability reason */}
            {doc.is_unavailable && doc.unavailability_reason && (
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Raison d'indisponibilité</p>
                <p className="text-sm text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 rounded-lg p-2">
                  {doc.unavailability_reason}
                </p>
              </div>
            )}

            {/* Auto-check results */}
            {doc.auto_check_results && Object.keys(doc.auto_check_results).length > 0 && (
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Vérifications auto</p>
                <div className="space-y-2">
                  {Object.entries(doc.auto_check_results).map(([k, v]) => {
                    const cfg = AUTO_CHECK_CONFIG[k];
                    const label = cfg?.label ?? k;
                    const isPresent = v !== null && v !== undefined && v !== false && v !== '';
                    const displayValue = cfg?.isDate && typeof v === 'string'
                      ? formatDate(v)
                      : cfg?.isText && typeof v === 'string'
                      ? v
                      : null;
                    return (
                      <div key={k} className="flex items-start gap-2">
                        {isPresent ? (
                          <CheckCircle className="h-4 w-4 text-green-500 dark:text-green-400 flex-shrink-0 mt-0.5" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500 dark:text-red-400 flex-shrink-0 mt-0.5" />
                        )}
                        <div className="min-w-0">
                          <p className={`text-xs font-medium ${isPresent ? 'text-gray-700 dark:text-gray-200' : 'text-gray-500 dark:text-gray-400'}`}>
                            {label}
                          </p>
                          {displayValue && (
                            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{displayValue}</p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Validation actions */}
            {canValidate && (
              <div className="p-4 mt-auto">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Actions</p>
                <div className="flex flex-col gap-2">
                  <Button
                    onClick={onValidate}
                    disabled={isValidating}
                    className="w-full justify-center"
                  >
                    <CheckCircle className="h-4 w-4 mr-1.5" />
                    {isValidating ? 'Validation...' : 'Valider le document'}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={onRejectStart}
                    className="w-full justify-center text-red-600 dark:text-red-400 border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    <XCircle className="h-4 w-4 mr-1.5" />
                    Rejeter
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
