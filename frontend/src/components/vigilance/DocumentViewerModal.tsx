import { useQuery } from '@tanstack/react-query';
import { CheckCircle, Download, FileText, X, XCircle } from 'lucide-react';

import { vigilanceApi } from '../../api/vigilance';
import { Button } from '../ui/Button';
import { PageSpinner } from '../ui/Spinner';
import type { DocumentStatus, VigilanceDocument } from '../../types';
import { daysUntil, formatDate } from './dateUtils';

// ─── Helpers ──────────────────────────────────────────────────────────────────

export function ExpiryBadge({ expiresAt }: { expiresAt: string | null }) {
  const days = daysUntil(expiresAt);
  if (days === null) return null;

  if (days < 0)
    return (
      <span className="st st-red">
        <span className="dot" />
        Expiré il y a {Math.abs(days)} j
      </span>
    );
  if (days <= 30)
    return (
      <span className="st st-amb">
        <span className="dot" />
        Expire dans {days} j
      </span>
    );
  return (
    <span className="st st-grn">
      <span className="dot" />
      Valide encore {days} j
    </span>
  );
}

const DOC_CHIP: Record<DocumentStatus, { label: string; cls: string }> = {
  requested: { label: 'Demandé', cls: 'st-sla' },
  received: { label: 'Reçu', cls: 'st-blu' },
  validated: { label: 'Validé', cls: 'st-grn' },
  rejected: { label: 'Rejeté', cls: 'st-red' },
  expiring_soon: { label: 'Expire bientôt', cls: 'st-amb' },
  expired: { label: 'Expiré', cls: 'st-red' },
};

function docChip(doc: Pick<VigilanceDocument, 'status' | 'is_unavailable'>): {
  label: string;
  cls: string;
} {
  if (doc.status === 'validated' && doc.is_unavailable) {
    return { label: 'Validation temporaire', cls: 'st-amb' };
  }
  return DOC_CHIP[doc.status] ?? { label: doc.status, cls: 'st-sla' };
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
  const chip = docChip(doc);

  // Fallback: use values from auto_check_results if dedicated columns are null
  const acr = doc.auto_check_results ?? {};
  const docDate = doc.document_date ?? (acr.document_date as string | null | undefined) ?? null;
  const expiryDate = doc.expires_at ?? (acr.expiry_date as string | null | undefined) ?? null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-sur border border-lin rounded-2xl shadow-2xl w-full max-w-6xl h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between gap-3 px-5 py-3 border-b border-lin2 flex-shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="dico">
              <FileText className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="dn truncate">{doc.document_type_display}</p>
              {doc.file_name && <p className="ds truncate">{doc.file_name}</p>}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {urlData?.url && (
              <a
                href={urlData.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 h-[30px] px-3 rounded-[9px] border border-lin bg-sur text-xs font-medium text-ink hover:bg-srf2 transition-colors"
              >
                <Download className="h-3.5 w-3.5" /> Télécharger
              </a>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Fermer"
              className="p-1.5 rounded-lg text-mut2 hover:text-ink hover:bg-srf2 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="flex flex-1 min-h-0">
          {/* Viewer */}
          <div className="flex-1 bg-srf2 flex items-center justify-center overflow-hidden">
            {!doc.s3_key ? (
              <div className="text-center text-mut2">
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
              <p className="text-sm text-mut">Impossible de charger le document.</p>
            )}
          </div>

          {/* Metadata + Actions sidebar */}
          <div className="w-72 flex-shrink-0 border-l border-lin2 flex flex-col overflow-y-auto">
            {/* Status */}
            <div className="p-4 border-b border-lin2">
              <p className="ml !mb-2">Statut</p>
              <span className={`st ${chip.cls}`}>
                <span className="dot" />
                {chip.label}
              </span>
            </div>

            {/* Dates */}
            <div className="p-4 border-b border-lin2 space-y-3">
              <p className="ml">Dates</p>

              <div>
                <p className="ds !mt-0">Déposé le</p>
                <p className="mv">{formatDate(doc.uploaded_at)}</p>
              </div>

              {doc.validated_at && (
                <div>
                  <p className="ds !mt-0">Validé le</p>
                  <p className="mv">{formatDate(doc.validated_at)}</p>
                </div>
              )}

              {doc.rejected_at && (
                <div>
                  <p className="ds !mt-0">Rejeté le</p>
                  <p className="mv">{formatDate(doc.rejected_at)}</p>
                </div>
              )}

              {doc.document_type !== 'rib' && (
                <>
                  <div>
                    <p className="ds !mt-0">Date du document</p>
                    <p className="mv">{formatDate(docDate)}</p>
                    {doc.is_valid_at_upload === false && (
                      <div className="mt-1.5">
                        <span className="st st-red">
                          <span className="dot" />
                          Invalide à l'émission
                        </span>
                      </div>
                    )}
                  </div>

                  <div>
                    <p className="ds !mt-0">Valide jusqu'au</p>
                    <p className="mv">{formatDate(expiryDate)}</p>
                    {expiryDate && (
                      <div className="mt-1.5">
                        <ExpiryBadge expiresAt={expiryDate} />
                      </div>
                    )}
                  </div>
                </>
              )}

              {doc.file_size && (
                <div>
                  <p className="ds !mt-0">Taille</p>
                  <p className="mv">{(doc.file_size / 1024).toFixed(1)} Ko</p>
                </div>
              )}
            </div>

            {/* Rejection reason */}
            {doc.rejection_reason && (
              <div className="p-4 border-b border-lin2">
                <p className="ml !mb-2">Motif du rejet</p>
                <p className="text-[12.5px] leading-relaxed text-red-fg bg-red-bg rounded-lg px-2.5 py-2">
                  {doc.rejection_reason}
                </p>
              </div>
            )}

            {/* Unavailability reason */}
            {doc.is_unavailable && doc.unavailability_reason && (
              <div className="p-4 border-b border-lin2">
                <p className="ml !mb-2">Raison d'indisponibilité</p>
                <p className="text-[12.5px] leading-relaxed text-amb-fg bg-amb-bg rounded-lg px-2.5 py-2">
                  {doc.unavailability_reason}
                </p>
              </div>
            )}

            {/* Auto-check results */}
            {doc.auto_check_results && Object.keys(doc.auto_check_results).length > 0 && (
              <div className="p-4 border-b border-lin2">
                <p className="ml !mb-2.5">Vérifications auto</p>
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
                          <CheckCircle className="h-4 w-4 text-grn-fg flex-shrink-0 mt-0.5" />
                        ) : (
                          <XCircle className="h-4 w-4 text-redt flex-shrink-0 mt-0.5" />
                        )}
                        <div className="min-w-0">
                          <p className={`text-xs font-medium ${isPresent ? 'text-ink' : 'text-mut'}`}>
                            {label}
                          </p>
                          {displayValue && (
                            <p className="ds !mt-0.5 truncate">{displayValue}</p>
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
                <p className="ml !mb-2.5">Actions</p>
                <div className="flex flex-col gap-2">
                  <Button
                    onClick={onValidate}
                    disabled={isValidating}
                    className="w-full"
                    leftIcon={<CheckCircle className="h-4 w-4" />}
                  >
                    {isValidating ? 'Validation…' : 'Valider le document'}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={onRejectStart}
                    className="w-full !text-redt"
                    leftIcon={<XCircle className="h-4 w-4" />}
                  >
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
