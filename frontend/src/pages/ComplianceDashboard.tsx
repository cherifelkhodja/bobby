import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShieldCheck,
  ShieldAlert,
  Clock,
  AlertTriangle,
  FileCheck,
  FileX,
  Search,
  ChevronRight,
  Hourglass,
  Eye,
  Download,
  X,
  Calendar,
  CalendarCheck,
  CalendarX,
  Timer,
  CheckCircle,
  XCircle,
  FileText,
  Building2,
  Mail,
  Hash,
} from 'lucide-react';
import { toast } from 'sonner';

import { vigilanceApi } from '../api/vigilance';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { PageSpinner } from '../components/ui/Spinner';
import { getErrorMessage } from '../api/client';
import {
  COMPLIANCE_STATUS_CONFIG,
  DOCUMENT_STATUS_CONFIG,
} from '../types';
import type {
  ComplianceStatus,
  ThirdPartyWithDocuments,
  VigilanceDocument,
} from '../types';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function daysUntil(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const diff = new Date(iso).getTime() - Date.now();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function ExpiryBadge({ expiresAt }: { expiresAt: string | null }) {
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

// ─── Document Viewer Modal ────────────────────────────────────────────────────

function DocumentViewerModal({
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
                const cfg = DOCUMENT_STATUS_CONFIG[doc.status as keyof typeof DOCUMENT_STATUS_CONFIG];
                return (
                  <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${cfg?.color ?? 'bg-gray-100 text-gray-600'}`}>
                    {cfg?.label ?? doc.status}
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

              {doc.document_date && (
                <div className="flex items-start gap-2">
                  <FileText className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Date du document</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {formatDate(doc.document_date)}
                    </p>
                    {doc.is_valid_at_upload === false && (
                      <span className="inline-flex items-center gap-1 mt-1 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 px-2 py-0.5 text-xs font-medium">
                        <XCircle className="h-3 w-3" /> Document invalide à l'émission
                      </span>
                    )}
                  </div>
                </div>
              )}

              {doc.expires_at && (
                <div className="flex items-start gap-2">
                  <Timer className="h-4 w-4 text-orange-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Valide jusqu'au</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {formatDate(doc.expires_at)}
                    </p>
                    <div className="mt-1">
                      <ExpiryBadge expiresAt={doc.expires_at} />
                    </div>
                  </div>
                </div>
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

            {/* Auto-check results */}
            {doc.auto_check_results && Object.keys(doc.auto_check_results).length > 0 && (
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Vérifications auto</p>
                <div className="space-y-1">
                  {Object.entries(doc.auto_check_results).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between text-xs">
                      <span className="text-gray-600 dark:text-gray-400">{k}</span>
                      <span className={v ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                        {v ? '✓' : '✗'}
                      </span>
                    </div>
                  ))}
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

// ─── Document Card ─────────────────────────────────────────────────────────────

function DocumentCard({
  doc,
  onView,
  onValidate,
  onRejectStart,
  isRejectingThis,
  rejectReason,
  onRejectReasonChange,
  onRejectConfirm,
  onRejectCancel,
  isValidating,
  isRejecting,
}: {
  doc: VigilanceDocument;
  onView: () => void;
  onValidate: () => void;
  onRejectStart: () => void;
  isRejectingThis: boolean;
  rejectReason: string;
  onRejectReasonChange: (v: string) => void;
  onRejectConfirm: () => void;
  onRejectCancel: () => void;
  isValidating: boolean;
  isRejecting: boolean;
}) {
  const statusCfg = DOCUMENT_STATUS_CONFIG[doc.status as keyof typeof DOCUMENT_STATUS_CONFIG];
  const canValidate = doc.status === 'received';
  const hasFile = !!doc.s3_key;

  return (
    <Card className="overflow-hidden">
      {/* Top bar: type + status */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {doc.status === 'validated' ? (
            <FileCheck className="h-5 w-5 text-green-500 flex-shrink-0" />
          ) : doc.status === 'rejected' || doc.status === 'expired' ? (
            <FileX className="h-5 w-5 text-red-500 flex-shrink-0" />
          ) : doc.status === 'received' ? (
            <FileCheck className="h-5 w-5 text-blue-500 flex-shrink-0" />
          ) : (
            <FileText className="h-5 w-5 text-gray-400 flex-shrink-0" />
          )}
          <span className="text-sm font-semibold text-gray-900 dark:text-white">
            {doc.document_type_display}
          </span>
        </div>
        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusCfg?.color ?? 'bg-gray-100 text-gray-600'}`}>
          {statusCfg?.label ?? doc.status}
        </span>
      </div>

      {/* Metadata row */}
      <div className="grid grid-cols-4 gap-2 mb-3 text-xs">
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-2">
          <p className="text-gray-400 mb-0.5 flex items-center gap-1">
            <Calendar className="h-3 w-3" /> Déposé le
          </p>
          <p className="font-medium text-gray-900 dark:text-white">
            {formatDate(doc.uploaded_at)}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-2">
          <p className="text-gray-400 mb-0.5 flex items-center gap-1">
            <FileText className="h-3 w-3" /> Date document
          </p>
          <p className="font-medium text-gray-900 dark:text-white">
            {formatDate(doc.document_date)}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-2">
          <p className="text-gray-400 mb-0.5 flex items-center gap-1">
            <CalendarCheck className="h-3 w-3" /> Valide jusqu'au
          </p>
          <p className="font-medium text-gray-900 dark:text-white">
            {formatDate(doc.expires_at)}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-2">
          <p className="text-gray-400 mb-0.5 flex items-center gap-1">
            <Timer className="h-3 w-3" /> Délai
          </p>
          <div className="mt-0.5">
            {doc.expires_at ? (
              <ExpiryBadge expiresAt={doc.expires_at} />
            ) : doc.is_valid_at_upload === false ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 px-2 py-0.5 text-xs font-medium">
                <XCircle className="h-3 w-3" /> Invalide
              </span>
            ) : (
              <span className="font-medium text-gray-400">—</span>
            )}
          </div>
        </div>
      </div>

      {/* File info + actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          {doc.file_name ? (
            <span className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[180px]">
              {doc.file_name}
              {doc.file_size ? ` · ${(doc.file_size / 1024).toFixed(0)} Ko` : ''}
            </span>
          ) : (
            <span className="text-xs text-gray-400 italic">En attente de dépôt</span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {hasFile && (
            <button
              onClick={onView}
              className="inline-flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:underline"
            >
              <Eye className="h-3.5 w-3.5" /> Visualiser
            </button>
          )}
          {canValidate && !isRejectingThis && (
            <>
              <Button size="sm" onClick={onValidate} disabled={isValidating}>
                <CheckCircle className="h-3.5 w-3.5 mr-1" />
                {isValidating ? '...' : 'Valider'}
              </Button>
              <Button variant="secondary" size="sm" onClick={onRejectStart} className="text-red-600 dark:text-red-400">
                <XCircle className="h-3.5 w-3.5 mr-1" />
                Rejeter
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Rejection reason display */}
      {doc.rejection_reason && (
        <p className="mt-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg px-2 py-1">
          Motif : {doc.rejection_reason}
        </p>
      )}

      {/* Inline rejection form */}
      {isRejectingThis && (
        <div className="mt-3 border-t border-gray-200 dark:border-gray-700 pt-3">
          <textarea
            value={rejectReason}
            onChange={(e) => onRejectReasonChange(e.target.value)}
            placeholder="Motif du rejet (min. 5 caractères)..."
            className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 resize-none"
            rows={2}
            autoFocus
          />
          <div className="flex gap-2 mt-2">
            <Button
              size="sm"
              onClick={onRejectConfirm}
              disabled={rejectReason.length < 5 || isRejecting}
              className="bg-red-600 hover:bg-red-700"
            >
              Confirmer le rejet
            </Button>
            <Button variant="secondary" size="sm" onClick={onRejectCancel}>
              Annuler
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}

// ─── Third Party Documents Panel ─────────────────────────────────────────────

function ThirdPartyDocumentsPanel({
  tpDocs,
  onRequestDocs,
  onValidate,
  onRejectStart,
  rejectDocId,
  rejectReason,
  onRejectReasonChange,
  onRejectConfirm,
  onRejectCancel,
  isRequesting,
  isValidating,
  isRejecting,
}: {
  tpDocs: ThirdPartyWithDocuments;
  onRequestDocs: () => void;
  onValidate: (docId: string) => void;
  onRejectStart: (docId: string) => void;
  rejectDocId: string | null;
  rejectReason: string;
  onRejectReasonChange: (v: string) => void;
  onRejectConfirm: () => void;
  onRejectCancel: () => void;
  isRequesting: boolean;
  isValidating: boolean;
  isRejecting: boolean;
}) {
  const queryClient = useQueryClient();
  const [viewingDoc, setViewingDoc] = useState<VigilanceDocument | null>(null);
  const cs = COMPLIANCE_STATUS_CONFIG[tpDocs.compliance_status as ComplianceStatus];

  const handleValidateFromModal = (docId: string) => {
    onValidate(docId);
    setViewingDoc(null);
  };

  const handleRejectStartFromModal = (doc: VigilanceDocument) => {
    setViewingDoc(null);
    onRejectStart(doc.id);
  };

  const validateMutationForModal = useMutation({
    mutationFn: (docId: string) => vigilanceApi.validateDocument(docId),
    onSuccess: () => {
      toast.success('Document validé.');
      queryClient.invalidateQueries({ queryKey: ['vigilance-documents', tpDocs.id] });
      queryClient.invalidateQueries({ queryKey: ['compliance-dashboard'] });
      setViewingDoc(null);
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  // Count by status for summary
  const receivedCount = tpDocs.documents.filter((d) => d.status === 'received').length;
  const validatedCount = tpDocs.documents.filter((d) => d.status === 'validated').length;
  const pendingCount = tpDocs.documents.filter((d) => d.status === 'requested').length;

  return (
    <div>
      {/* Document viewer modal */}
      {viewingDoc && (
        <DocumentViewerModal
          doc={viewingDoc}
          onClose={() => setViewingDoc(null)}
          onValidate={() => validateMutationForModal.mutate(viewingDoc.id)}
          onRejectStart={() => handleRejectStartFromModal(viewingDoc)}
          isValidating={validateMutationForModal.isPending}
        />
      )}

      {/* Header card */}
      <Card className="mb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {tpDocs.company_name ?? (
                <span className="italic text-gray-400 dark:text-gray-500">Nom inconnu</span>
              )}
            </h2>
            <div className="flex flex-wrap items-center gap-3 mt-1">
              {tpDocs.siren && (
                <span className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                  <Hash className="h-3 w-3" /> SIREN {tpDocs.siren}
                </span>
              )}
              <span className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                <Mail className="h-3 w-3" /> {tpDocs.contact_email}
              </span>
              <span className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                <Building2 className="h-3 w-3" />
                {tpDocs.type === 'portage' ? 'Portage salarial' :
                 tpDocs.type === 'esn' ? 'ESN' :
                 tpDocs.type === 'freelance' ? 'Freelance' : tpDocs.type}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            {cs && (
              <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${cs.color}`}>
                {cs.label}
              </span>
            )}
            <Button
              variant="secondary"
              size="sm"
              onClick={onRequestDocs}
              disabled={isRequesting}
            >
              {isRequesting ? 'Envoi...' : 'Demander documents'}
            </Button>
          </div>
        </div>

        {/* Summary counters */}
        {tpDocs.documents.length > 0 && (
          <div className="flex gap-4 mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
            <div className="text-center">
              <p className="text-xl font-bold text-gray-900 dark:text-white">{tpDocs.documents.length}</p>
              <p className="text-xs text-gray-500">Total</p>
            </div>
            {receivedCount > 0 && (
              <div className="text-center">
                <p className="text-xl font-bold text-blue-600 dark:text-blue-400">{receivedCount}</p>
                <p className="text-xs text-gray-500">À valider</p>
              </div>
            )}
            {validatedCount > 0 && (
              <div className="text-center">
                <p className="text-xl font-bold text-green-600 dark:text-green-400">{validatedCount}</p>
                <p className="text-xs text-gray-500">Validés</p>
              </div>
            )}
            {pendingCount > 0 && (
              <div className="text-center">
                <p className="text-xl font-bold text-yellow-600 dark:text-yellow-400">{pendingCount}</p>
                <p className="text-xs text-gray-500">En attente</p>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Documents list */}
      <div className="space-y-3">
        {tpDocs.documents.map((doc) => (
          <DocumentCard
            key={doc.id}
            doc={doc}
            onView={() => setViewingDoc(doc)}
            onValidate={() => handleValidateFromModal(doc.id)}
            onRejectStart={() => onRejectStart(doc.id)}
            isRejectingThis={rejectDocId === doc.id}
            rejectReason={rejectDocId === doc.id ? rejectReason : ''}
            onRejectReasonChange={onRejectReasonChange}
            onRejectConfirm={onRejectConfirm}
            onRejectCancel={onRejectCancel}
            isValidating={isValidating}
            isRejecting={isRejecting}
          />
        ))}

        {tpDocs.documents.length === 0 && (
          <Card className="text-center py-10">
            <FileText className="h-10 w-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Aucun document pour ce tiers.
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              Cliquez sur "Demander documents" pour initier la collecte.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ComplianceDashboard() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [complianceFilter, setComplianceFilter] = useState<ComplianceStatus | ''>('');
  const [selectedThirdPartyId, setSelectedThirdPartyId] = useState<string | null>(null);
  const [rejectDocId, setRejectDocId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ['compliance-dashboard'],
    queryFn: () => vigilanceApi.getDashboard(),
  });

  const { data: thirdParties, isLoading: listLoading } = useQuery({
    queryKey: ['vigilance-third-parties', complianceFilter, search],
    queryFn: () =>
      vigilanceApi.listThirdParties({
        limit: 100,
        ...(complianceFilter ? { compliance_status: complianceFilter } : {}),
        ...(search ? { search } : {}),
      }),
  });

  const { data: tpDocs } = useQuery({
    queryKey: ['vigilance-documents', selectedThirdPartyId],
    queryFn: () => vigilanceApi.getThirdPartyDocuments(selectedThirdPartyId!),
    enabled: !!selectedThirdPartyId,
  });

  const requestDocsMutation = useMutation({
    mutationFn: (tpId: string) => vigilanceApi.requestDocuments(tpId),
    onSuccess: () => {
      toast.success('Documents demandés.');
      queryClient.invalidateQueries({ queryKey: ['vigilance-documents', selectedThirdPartyId] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const validateMutation = useMutation({
    mutationFn: (docId: string) => vigilanceApi.validateDocument(docId),
    onSuccess: () => {
      toast.success('Document validé.');
      queryClient.invalidateQueries({ queryKey: ['vigilance-documents', selectedThirdPartyId] });
      queryClient.invalidateQueries({ queryKey: ['compliance-dashboard'] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const rejectMutation = useMutation({
    mutationFn: () => vigilanceApi.rejectDocument(rejectDocId!, rejectReason),
    onSuccess: () => {
      toast.success('Document rejeté.');
      setRejectDocId(null);
      setRejectReason('');
      queryClient.invalidateQueries({ queryKey: ['vigilance-documents', selectedThirdPartyId] });
      queryClient.invalidateQueries({ queryKey: ['compliance-dashboard'] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  if (dashLoading) return <PageSpinner />;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Conformité documentaire
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Suivi de la vigilance documentaire des tiers
        </p>
      </div>

      {/* Stats cards */}
      {dashboard && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <Card>
            <div className="flex items-center gap-3">
              <ShieldCheck className="h-8 w-8 text-green-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{dashboard.compliant}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Conformes</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <ShieldAlert className="h-8 w-8 text-red-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{dashboard.non_compliant}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Non conformes</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <Hourglass className="h-8 w-8 text-blue-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{dashboard.under_review}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">En vérification</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <Clock className="h-8 w-8 text-orange-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{dashboard.documents_pending_review}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Docs à valider</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-8 w-8 text-yellow-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{dashboard.documents_expiring_soon}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Expirent bientôt</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Compliance rate */}
      {dashboard && (
        <Card className="mb-6">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Taux de conformité</span>
            <span className="text-lg font-bold text-gray-900 dark:text-white">{dashboard.compliance_rate}%</span>
          </div>
          <div className="mt-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className="bg-green-500 h-2 rounded-full transition-all"
              style={{ width: `${Math.min(dashboard.compliance_rate, 100)}%` }}
            />
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Third party list */}
        <div className="lg:col-span-1">
          <div className="flex gap-2 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Rechercher..."
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <select
              value={complianceFilter}
              onChange={(e) => setComplianceFilter(e.target.value as ComplianceStatus | '')}
              className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
            >
              <option value="">Tous</option>
              {Object.entries(COMPLIANCE_STATUS_CONFIG).map(([key, { label }]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </div>

          {listLoading ? (
            <PageSpinner />
          ) : (
            <div className="space-y-2">
              {thirdParties?.items.map((tp) => {
                const cs = COMPLIANCE_STATUS_CONFIG[tp.compliance_status as ComplianceStatus];
                const isPending = tp.compliance_status === 'pending';
                const isSelected = selectedThirdPartyId === tp.id;
                return (
                  <button
                    key={tp.id}
                    onClick={() => !isPending && setSelectedThirdPartyId(tp.id)}
                    disabled={isPending}
                    title={isPending ? 'En attente que le tiers complète son portail' : undefined}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      isPending
                        ? 'border-gray-200 dark:border-gray-700 opacity-60 cursor-not-allowed'
                        : isSelected
                          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {tp.company_name ?? (
                            <span className="italic text-gray-400 dark:text-gray-500">Nom inconnu</span>
                          )}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                          {tp.siren ? `SIREN ${tp.siren}` : tp.contact_email}
                        </p>
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        {cs && (
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${cs.color}`}>
                            {cs.label}
                          </span>
                        )}
                        {!isPending && <ChevronRight className="h-4 w-4 text-gray-400" />}
                      </div>
                    </div>
                    {isPending && (
                      <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                        En attente de complétion du portail
                      </p>
                    )}
                  </button>
                );
              })}
              {thirdParties?.items.length === 0 && (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                  Aucun tiers trouvé.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Right: Documents */}
        <div className="lg:col-span-2">
          {selectedThirdPartyId && tpDocs ? (
            <ThirdPartyDocumentsPanel
              tpDocs={tpDocs}
              onRequestDocs={() => requestDocsMutation.mutate(selectedThirdPartyId)}
              onValidate={(docId) => validateMutation.mutate(docId)}
              onRejectStart={(docId) => setRejectDocId(docId)}
              rejectDocId={rejectDocId}
              rejectReason={rejectReason}
              onRejectReasonChange={setRejectReason}
              onRejectConfirm={() => rejectMutation.mutate()}
              onRejectCancel={() => { setRejectDocId(null); setRejectReason(''); }}
              isRequesting={requestDocsMutation.isPending}
              isValidating={validateMutation.isPending}
              isRejecting={rejectMutation.isPending}
            />
          ) : (
            <Card className="flex items-center justify-center py-16">
              <div className="text-center">
                <ShieldCheck className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Sélectionnez un tiers pour voir ses documents.
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
