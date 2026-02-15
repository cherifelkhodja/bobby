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

export default function ComplianceDashboard() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [complianceFilter, setComplianceFilter] = useState<ComplianceStatus | ''>('');
  const [selectedThirdPartyId, setSelectedThirdPartyId] = useState<string | null>(null);
  const [rejectDocId, setRejectDocId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  // Dashboard stats
  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ['compliance-dashboard'],
    queryFn: () => vigilanceApi.getDashboard(),
  });

  // Third parties list
  const { data: thirdParties, isLoading: listLoading } = useQuery({
    queryKey: ['vigilance-third-parties', complianceFilter, search],
    queryFn: () =>
      vigilanceApi.listThirdParties({
        limit: 100,
        ...(complianceFilter ? { compliance_status: complianceFilter } : {}),
        ...(search ? { search } : {}),
      }),
  });

  // Selected third party documents
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
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <div className="flex items-center gap-3">
              <ShieldCheck className="h-8 w-8 text-green-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {dashboard.compliant}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Conformes</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <ShieldAlert className="h-8 w-8 text-red-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {dashboard.non_compliant}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Non conformes</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <Clock className="h-8 w-8 text-orange-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {dashboard.documents_pending_review}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">À valider</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-8 w-8 text-yellow-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {dashboard.documents_expiring_soon}
                </p>
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
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Taux de conformité
            </span>
            <span className="text-lg font-bold text-gray-900 dark:text-white">
              {dashboard.compliance_rate}%
            </span>
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
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {listLoading ? (
            <PageSpinner />
          ) : (
            <div className="space-y-2">
              {thirdParties?.items.map((tp) => {
                const cs = COMPLIANCE_STATUS_CONFIG[tp.compliance_status as ComplianceStatus];
                return (
                  <button
                    key={tp.id}
                    onClick={() => setSelectedThirdPartyId(tp.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      selectedThirdPartyId === tp.id
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {tp.company_name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {tp.siren}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {cs && (
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cs.color}`}>
                            {cs.label}
                          </span>
                        )}
                        <ChevronRight className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
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

        {/* Right: Documents detail */}
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
  const cs = COMPLIANCE_STATUS_CONFIG[tpDocs.compliance_status as ComplianceStatus];

  return (
    <div>
      <Card className="mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {tpDocs.company_name}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {tpDocs.siren} — {tpDocs.contact_email}
            </p>
          </div>
          <div className="flex items-center gap-3">
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
              {isRequesting ? 'Demande...' : 'Demander documents'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Document counts */}
      {Object.keys(tpDocs.document_counts).length > 0 && (
        <div className="flex gap-2 mb-4 flex-wrap">
          {Object.entries(tpDocs.document_counts).map(([status, count]) => {
            const cfg = DOCUMENT_STATUS_CONFIG[status as keyof typeof DOCUMENT_STATUS_CONFIG];
            return (
              <span
                key={status}
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg?.color ?? 'bg-gray-100 text-gray-600'}`}
              >
                {cfg?.label ?? status}: {count}
              </span>
            );
          })}
        </div>
      )}

      {/* Documents list */}
      <div className="space-y-2">
        {tpDocs.documents.map((doc) => (
          <DocumentRow
            key={doc.id}
            doc={doc}
            onValidate={() => onValidate(doc.id)}
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
          <Card className="text-center py-8">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Aucun document pour ce tiers.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}

function DocumentRow({
  doc,
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
  const statusCfg = DOCUMENT_STATUS_CONFIG[doc.status];
  const canValidate = doc.status === 'received';

  return (
    <Card>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {doc.status === 'validated' ? (
            <FileCheck className="h-5 w-5 text-green-500" />
          ) : doc.status === 'rejected' || doc.status === 'expired' ? (
            <FileX className="h-5 w-5 text-red-500" />
          ) : (
            <FileCheck className="h-5 w-5 text-gray-400" />
          )}
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {doc.document_type_display}
            </p>
            <div className="flex items-center gap-2 mt-0.5">
              <span
                className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusCfg?.color ?? 'bg-gray-100 text-gray-600'}`}
              >
                {statusCfg?.label ?? doc.status}
              </span>
              {doc.file_name && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {doc.file_name}
                </span>
              )}
              {doc.expires_at && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Expire le{' '}
                  {new Date(doc.expires_at).toLocaleDateString('fr-FR')}
                </span>
              )}
            </div>
            {doc.rejection_reason && (
              <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                Motif : {doc.rejection_reason}
              </p>
            )}
          </div>
        </div>

        {canValidate && !isRejectingThis && (
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={onValidate}
              disabled={isValidating}
            >
              Valider
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={onRejectStart}
            >
              Rejeter
            </Button>
          </div>
        )}
      </div>

      {isRejectingThis && (
        <div className="mt-3 border-t border-gray-200 dark:border-gray-700 pt-3">
          <textarea
            value={rejectReason}
            onChange={(e) => onRejectReasonChange(e.target.value)}
            placeholder="Motif du rejet (min. 5 caractères)..."
            className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
            rows={2}
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
