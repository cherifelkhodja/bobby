import { Fragment, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronRight, FileCheck, FileText, FileX } from 'lucide-react';
import { toast } from 'sonner';

import { vigilanceApi } from '../api/vigilance';
import { Button } from '../components/ui/Button';
import { PageSpinner, Spinner } from '../components/ui/Spinner';
import { InlineSearchInput } from '../components/ui/SearchInput';
import {
  DocumentViewerModal,
  ExpiryBadge,
} from '../components/vigilance/DocumentViewerModal';
import { formatDate } from '../components/vigilance/dateUtils';
import { getErrorMessage } from '../api/client';
import { COMPLIANCE_STATUS_CONFIG } from '../types';
import type {
  ComplianceStatus,
  DocumentStatus,
  ThirdPartyWithDocuments,
  VigilanceDocument,
} from '../types';

// ─── v2 chips ──────────────────────────────────────────────────────────────────

const COMPLIANCE_CHIP: Record<ComplianceStatus, { label: string; cls: string }> = {
  pending: { label: 'Dossier en cours', cls: 'st-sla' },
  under_review: { label: 'En vérification', cls: 'st-sla' },
  compliant: { label: 'Conforme', cls: 'st-grn' },
  expiring_soon: { label: 'Expire bientôt', cls: 'st-amb' },
  non_compliant: { label: 'Non conforme', cls: 'st-red' },
};

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

const TYPE_LABELS: Record<string, string> = {
  freelance: 'Freelance',
  sous_traitant: 'Sous-traitant',
  portage_salarial: 'Portage salarial',
  portage_commercial: 'Portage commercial',
  portage: 'Portage salarial',
  salarie: 'Salarié',
  esn: 'ESN',
};

// ─── Document Card ─────────────────────────────────────────────────────────────

function DocumentCard({
  doc,
  onView,
  onValidate,
  onTempValidate,
  onRejectStart,
  isRejectingThis,
  rejectReason,
  onRejectReasonChange,
  onRejectConfirm,
  onRejectCancel,
  isValidating,
  isTempValidating,
  isRejecting,
}: {
  doc: VigilanceDocument;
  onView: () => void;
  onValidate: () => void;
  onTempValidate: () => void;
  onRejectStart: () => void;
  isRejectingThis: boolean;
  rejectReason: string;
  onRejectReasonChange: (v: string) => void;
  onRejectConfirm: () => void;
  onRejectCancel: () => void;
  isValidating: boolean;
  isTempValidating: boolean;
  isRejecting: boolean;
}) {
  const [confirmTempValidate, setConfirmTempValidate] = useState(false);
  const chip = docChip(doc);
  const isTempValidated = doc.status === 'validated' && doc.is_unavailable;
  const canValidate = doc.status === 'received';
  const canTempValidate = doc.status === 'requested';
  const hasFile = !!doc.s3_key;

  const metaParts: string[] = [];
  if (doc.uploaded_at) metaParts.push(`Déposé le ${formatDate(doc.uploaded_at)}`);
  if (doc.document_type !== 'rib') {
    if (doc.document_date) metaParts.push(`Document du ${formatDate(doc.document_date)}`);
    if (doc.expires_at) metaParts.push(`Valide jusqu'au ${formatDate(doc.expires_at)}`);
  }
  if (doc.file_name) {
    metaParts.push(
      doc.file_size
        ? `${doc.file_name} · ${(doc.file_size / 1024).toFixed(0)} Ko`
        : doc.file_name,
    );
  }

  return (
    <div>
      <div className="qrow">
        <div className="dico">
          {isTempValidated ? (
            <FileCheck className="h-4 w-4 text-amb-fg" />
          ) : doc.status === 'validated' ? (
            <FileCheck className="h-4 w-4 text-grn-fg" />
          ) : doc.status === 'rejected' || doc.status === 'expired' ? (
            <FileX className="h-4 w-4 text-redt" />
          ) : doc.status === 'received' ? (
            <FileCheck className="h-4 w-4 text-blu-fg" />
          ) : (
            <FileText className="h-4 w-4" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="dn">{doc.document_type_display}</p>
          <p className="ds">{metaParts.length > 0 ? metaParts.join(' · ') : 'En attente de dépôt'}</p>
          {doc.rejection_reason && (
            <p className="ds !text-redt">Motif de rejet : {doc.rejection_reason}</p>
          )}
          {doc.is_unavailable && doc.unavailability_reason && (
            <p className="ds !text-amb-fg">
              Raison d'indisponibilité : {doc.unavailability_reason}
            </p>
          )}
        </div>
        <div className="flex items-center justify-end gap-2 flex-wrap shrink-0">
          {doc.document_type !== 'rib' &&
            (doc.expires_at ? (
              <ExpiryBadge expiresAt={doc.expires_at} />
            ) : doc.is_valid_at_upload === false ? (
              <span className="st st-red">
                <span className="dot" />
                Invalide
              </span>
            ) : null)}
          <span className={`st ${chip.cls}`}>
            <span className="dot" />
            {chip.label}
          </span>
          {hasFile && (
            <Button variant="secondary" size="sm" onClick={onView}>
              Visualiser
            </Button>
          )}
          {canValidate && !isRejectingThis && (
            <>
              <Button size="sm" onClick={onValidate} disabled={isValidating}>
                {isValidating ? '…' : 'Valider'}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={onRejectStart}
                className="!text-redt"
              >
                Rejeter
              </Button>
            </>
          )}
          {canTempValidate &&
            !isRejectingThis &&
            (!confirmTempValidate ? (
              <button
                type="button"
                onClick={() => setConfirmTempValidate(true)}
                className="text-xs font-semibold text-prit hover:underline whitespace-nowrap"
              >
                Valider temporairement
              </button>
            ) : (
              <span className="flex items-center gap-2 text-xs text-mut whitespace-nowrap">
                Confirmer ?
                <button
                  type="button"
                  onClick={() => {
                    onTempValidate();
                    setConfirmTempValidate(false);
                  }}
                  disabled={isTempValidating}
                  className="font-semibold text-grn-fg hover:underline disabled:opacity-50"
                >
                  {isTempValidating ? '…' : 'Oui'}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmTempValidate(false)}
                  className="text-mut2 hover:underline"
                >
                  Annuler
                </button>
              </span>
            ))}
        </div>
      </div>

      {/* Inline rejection form */}
      {isRejectingThis && (
        <div className="pb-3.5 pl-[46px]">
          <textarea
            value={rejectReason}
            onChange={(e) => onRejectReasonChange(e.target.value)}
            placeholder="Motif du rejet (min. 5 caractères)…"
            className="f-ta"
            rows={2}
            autoFocus
          />
          <div className="flex gap-2 mt-2">
            <Button
              variant="danger"
              size="sm"
              onClick={onRejectConfirm}
              disabled={rejectReason.length < 5 || isRejecting}
            >
              Confirmer le rejet
            </Button>
            <Button variant="secondary" size="sm" onClick={onRejectCancel}>
              Annuler
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Third Party Documents Panel ─────────────────────────────────────────────

function ThirdPartyDocumentsPanel({
  tpDocs,
  onRequestDocs,
  onValidate,
  onTempValidate,
  onRejectStart,
  rejectDocId,
  rejectReason,
  onRejectReasonChange,
  onRejectConfirm,
  onRejectCancel,
  isRequesting,
  isValidating,
  isTempValidating,
  isRejecting,
}: {
  tpDocs: ThirdPartyWithDocuments;
  onRequestDocs: () => void;
  onValidate: (docId: string) => void;
  onTempValidate: (docId: string) => void;
  onRejectStart: (docId: string) => void;
  rejectDocId: string | null;
  rejectReason: string;
  onRejectReasonChange: (v: string) => void;
  onRejectConfirm: () => void;
  onRejectCancel: () => void;
  isRequesting: boolean;
  isValidating: boolean;
  isTempValidating: boolean;
  isRejecting: boolean;
}) {
  const queryClient = useQueryClient();
  const [viewingDoc, setViewingDoc] = useState<VigilanceDocument | null>(null);
  const cs = COMPLIANCE_CHIP[tpDocs.compliance_status as ComplianceStatus];

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

  const summaryParts: string[] = [];
  if (receivedCount > 0) summaryParts.push(`${receivedCount} à valider`);
  if (validatedCount > 0)
    summaryParts.push(`${validatedCount} validé${validatedCount > 1 ? 's' : ''}`);
  if (pendingCount > 0) summaryParts.push(`${pendingCount} en attente de dépôt`);

  return (
    <div className="min-w-0">
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

      {/* Panel header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          <h3 className="ct">Dossier documentaire</h3>
          {cs && (
            <span className={`st ${cs.cls}`}>
              <span className="dot" />
              {cs.label}
            </span>
          )}
          {tpDocs.documents.length > 0 && (
            <span className="ds !mt-0">
              {tpDocs.documents.length} document{tpDocs.documents.length > 1 ? 's' : ''}
              {summaryParts.length > 0 ? ` · ${summaryParts.join(' · ')}` : ''}
            </span>
          )}
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={onRequestDocs}
          disabled={isRequesting}
        >
          {isRequesting ? 'Envoi…' : 'Demander documents'}
        </Button>
      </div>

      {/* Documents list */}
      <div className="mt-1">
        {tpDocs.documents.map((doc) => (
          <DocumentCard
            key={doc.id}
            doc={doc}
            onView={() => setViewingDoc(doc)}
            onValidate={() => handleValidateFromModal(doc.id)}
            onTempValidate={() => onTempValidate(doc.id)}
            onRejectStart={() => onRejectStart(doc.id)}
            isRejectingThis={rejectDocId === doc.id}
            rejectReason={rejectDocId === doc.id ? rejectReason : ''}
            onRejectReasonChange={onRejectReasonChange}
            onRejectConfirm={onRejectConfirm}
            onRejectCancel={onRejectCancel}
            isValidating={isValidating}
            isTempValidating={isTempValidating}
            isRejecting={isRejecting}
          />
        ))}
      </div>

      {tpDocs.documents.length === 0 && (
        <div className="text-center py-8">
          <FileText className="h-8 w-8 text-mut2 mx-auto mb-2" />
          <p className="dn">Aucun document pour ce tiers</p>
          <p className="ds mt-1.5">
            Cliquez sur « Demander documents » pour initier la collecte.
          </p>
        </div>
      )}
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
    mutationFn: (tpId: string) => {
      const category = tpDocs?.entity_category as 'ei' | 'societe' | null;
      if (!category) {
        return Promise.reject(new Error('Catégorie d\'entité inconnue. Le tiers doit compléter ses informations sur le portail.'));
      }
      return vigilanceApi.requestDocuments(tpId, category);
    },
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

  const tempValidateMutation = useMutation({
    mutationFn: (docId: string) => vigilanceApi.tempValidateDocument(docId),
    onSuccess: () => {
      toast.success('Document validé temporairement (15 jours).');
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

  const items = thirdParties?.items ?? [];
  const gridCols = 'grid-cols-[1.3fr_110px_130px_1fr_150px_24px]';

  return (
    <div>
      <p className="bc">Contrats / Tiers & conformité</p>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="h1">Tiers & conformité</h1>
          <p className="sub">
            {dashboard
              ? `${dashboard.total_third_parties} tiers · vigilance documentaire pilotée par Bobby`
              : 'Suivi de la vigilance documentaire des tiers'}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <InlineSearchInput
            value={search}
            onChange={setSearch}
            placeholder="Rechercher un tiers…"
            className="w-56"
          />
          <select
            value={complianceFilter}
            onChange={(e) => setComplianceFilter(e.target.value as ComplianceStatus | '')}
            className="filter-select"
          >
            <option value="">Tous les statuts</option>
            {Object.entries(COMPLIANCE_STATUS_CONFIG).map(([key, { label }]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* KPIs */}
      {dashboard && (
        <div className="kpis">
          <div className="kpi">
            <p className="kl">Tiers actifs</p>
            <p className="kv">{dashboard.total_third_parties}</p>
            <p className="ks">
              {dashboard.pending} en constitution · {dashboard.under_review} en vérification
            </p>
          </div>
          <div className="kpi">
            <p className="kl">Conformes</p>
            <p className="kv text-grn-fg">{dashboard.compliant}</p>
            <p className="ks">{dashboard.compliance_rate} % du parc</p>
          </div>
          <div className="kpi">
            <p className="kl">Expirent sous 30 j</p>
            <p className="kv text-amb-fg">{dashboard.expiring_soon}</p>
            <p className="ks">
              {dashboard.documents_expiring_soon} document
              {dashboard.documents_expiring_soon > 1 ? 's' : ''} concerné
              {dashboard.documents_expiring_soon > 1 ? 's' : ''}
            </p>
          </div>
          <div className="kpi">
            <p className="kl">Non conformes</p>
            <p className={`kv ${dashboard.non_compliant > 0 ? 'red' : ''}`}>
              {dashboard.non_compliant}
            </p>
            <p className="ks">Contractualisation bloquée</p>
          </div>
        </div>
      )}

      {/* Third parties table */}
      <div className="tbl">
        <div className={`thead ${gridCols}`}>
          <span>Tiers</span>
          <span>Type</span>
          <span>SIREN</span>
          <span>Représentant</span>
          <span>Conformité</span>
          <span></span>
        </div>

        {listLoading ? (
          <div className="flex justify-center py-10">
            <Spinner />
          </div>
        ) : (
          <>
            {items.map((tp) => {
              const isPending = tp.compliance_status === 'pending';
              const isSelected = selectedThirdPartyId === tp.id;
              const cs = COMPLIANCE_CHIP[tp.compliance_status as ComplianceStatus];
              return (
                <Fragment key={tp.id}>
                  <div
                    className={`row ${gridCols} ${isPending ? 'opacity-60' : 'click'}`}
                    onClick={() => {
                      if (!isPending) setSelectedThirdPartyId(isSelected ? null : tp.id);
                    }}
                    title={isPending ? 'En attente que le tiers complète son portail' : undefined}
                  >
                    <div className="min-w-0">
                      <p className="nm truncate">
                        {tp.company_name || <span className="italic text-mut2">Nom inconnu</span>}
                      </p>
                      <p className="ns truncate">{tp.contact_email}</p>
                    </div>
                    <span className="cell truncate">{TYPE_LABELS[tp.type] ?? tp.type}</span>
                    <span className="ref">{tp.siren || '—'}</span>
                    <span className="cell truncate">
                      {tp.representative_name ||
                        (isPending ? (
                          <span className="text-mut2">Portail à compléter</span>
                        ) : (
                          '—'
                        ))}
                    </span>
                    <span>
                      {cs && (
                        <span className={`st ${cs.cls}`}>
                          <span className="dot" />
                          {cs.label}
                        </span>
                      )}
                    </span>
                    <ChevronRight
                      className={`h-4 w-4 chev justify-self-end transition-transform ${
                        isSelected ? 'rotate-90' : ''
                      } ${isPending ? 'invisible' : ''}`}
                    />
                  </div>

                  {/* Expanded documents panel */}
                  {isSelected && !isPending && (
                    <div className="expand !grid-cols-1">
                      {tpDocs ? (
                        <ThirdPartyDocumentsPanel
                          tpDocs={tpDocs}
                          onRequestDocs={() => requestDocsMutation.mutate(tp.id)}
                          onValidate={(docId) => validateMutation.mutate(docId)}
                          onTempValidate={(docId) => tempValidateMutation.mutate(docId)}
                          onRejectStart={(docId) => setRejectDocId(docId)}
                          rejectDocId={rejectDocId}
                          rejectReason={rejectReason}
                          onRejectReasonChange={setRejectReason}
                          onRejectConfirm={() => rejectMutation.mutate()}
                          onRejectCancel={() => {
                            setRejectDocId(null);
                            setRejectReason('');
                          }}
                          isRequesting={requestDocsMutation.isPending}
                          isValidating={validateMutation.isPending}
                          isTempValidating={tempValidateMutation.isPending}
                          isRejecting={rejectMutation.isPending}
                        />
                      ) : (
                        <div className="flex justify-center py-6">
                          <Spinner />
                        </div>
                      )}
                    </div>
                  )}
                </Fragment>
              );
            })}

            {items.length === 0 && (
              <div className="text-center py-10">
                <p className="dn">Aucun tiers trouvé</p>
                <p className="ds mt-1.5">
                  {search || complianceFilter
                    ? 'Modifiez votre recherche ou le filtre de conformité.'
                    : 'Les tiers apparaissent automatiquement lors des demandes de contrat.'}
                </p>
              </div>
            )}

            <div className="tfoot">
              <span>
                {items.length} tiers
                {complianceFilter &&
                  ` · filtre : ${COMPLIANCE_STATUS_CONFIG[complianceFilter]?.label ?? complianceFilter}`}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
