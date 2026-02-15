import { useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShieldCheck,
  Upload,
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Building2,
} from 'lucide-react';
import { toast } from 'sonner';

import { portalApi } from '../api/portal';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { PageSpinner } from '../components/ui/Spinner';

const DOCUMENT_STATUS_ICONS: Record<string, typeof CheckCircle> = {
  validated: CheckCircle,
  rejected: XCircle,
  received: Clock,
  requested: Upload,
  expiring_soon: AlertTriangle,
  expired: XCircle,
};

const DOCUMENT_STATUS_COLORS: Record<string, string> = {
  validated: 'text-green-500',
  rejected: 'text-red-500',
  received: 'text-blue-500',
  requested: 'text-gray-400',
  expiring_soon: 'text-orange-500',
  expired: 'text-red-400',
};

const DOCUMENT_STATUS_LABELS: Record<string, string> = {
  validated: 'Validé',
  rejected: 'Rejeté',
  received: 'En cours de vérification',
  requested: 'En attente',
  expiring_soon: 'Expire bientôt',
  expired: 'Expiré',
};

export default function Portal() {
  const { token } = useParams<{ token: string }>();
  const queryClient = useQueryClient();

  // Verify magic link
  const { data: portalInfo, isLoading, isError } = useQuery({
    queryKey: ['portal', token],
    queryFn: () => portalApi.verifyToken(token!),
    enabled: !!token,
    retry: false,
  });

  // Get documents
  const { data: docsData } = useQuery({
    queryKey: ['portal-documents', token],
    queryFn: () => portalApi.getDocuments(token!),
    enabled: !!token && !!portalInfo,
  });

  // Contract review (if purpose is contract_review)
  const { data: contractDraft } = useQuery({
    queryKey: ['portal-contract', token],
    queryFn: () => portalApi.getContractDraft(token!),
    enabled: !!token && portalInfo?.purpose === 'contract_review',
  });

  if (isLoading) return <PortalSpinner />;

  if (isError || !portalInfo) {
    return (
      <PortalLayout>
        <Card className="max-w-lg mx-auto text-center py-12">
          <XCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Lien invalide ou expiré
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Ce lien d'accès n'est plus valide. Veuillez contacter votre interlocuteur
            pour obtenir un nouveau lien.
          </p>
        </Card>
      </PortalLayout>
    );
  }

  const isDocumentUpload = portalInfo.purpose === 'document_upload';
  const isContractReview = portalInfo.purpose === 'contract_review';

  return (
    <PortalLayout>
      {/* Header */}
      <div className="max-w-3xl mx-auto mb-8">
        <div className="flex items-center gap-3 mb-4">
          <Building2 className="h-8 w-8 text-primary-600" />
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              Portail partenaire
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {portalInfo.third_party.company_name}
            </p>
          </div>
        </div>
      </div>

      {/* Document upload section */}
      {isDocumentUpload && docsData && (
        <div className="max-w-3xl mx-auto">
          <Card className="mb-6">
            <div className="flex items-center gap-3 mb-4">
              <ShieldCheck className="h-6 w-6 text-primary-600" />
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Documents de conformité
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Veuillez téléverser les documents demandés ci-dessous.
                </p>
              </div>
            </div>
          </Card>

          <div className="space-y-3">
            {docsData.documents.map((doc) => (
              <DocumentUploadCard
                key={doc.id}
                doc={doc}
                token={token!}
                onSuccess={() => {
                  queryClient.invalidateQueries({ queryKey: ['portal-documents', token] });
                }}
              />
            ))}

            {docsData.documents.length === 0 && (
              <Card className="text-center py-8">
                <CheckCircle className="h-10 w-10 text-green-500 mx-auto mb-3" />
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  Tous les documents ont été fournis. Merci !
                </p>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Contract review section */}
      {isContractReview && (
        <div className="max-w-3xl mx-auto">
          <ContractReviewSection token={token!} contractDraft={contractDraft} />
        </div>
      )}
    </PortalLayout>
  );
}

function PortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <FileText className="h-6 w-6 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900 dark:text-white">
            Bobby
          </span>
        </div>
      </header>
      <main className="px-6 py-8">{children}</main>
    </div>
  );
}

function PortalSpinner() {
  return (
    <PortalLayout>
      <PageSpinner />
    </PortalLayout>
  );
}

function DocumentUploadCard({
  doc,
  token,
  onSuccess,
}: {
  doc: { id: string; document_type: string; status: string; file_name: string | null; rejection_reason: string | null };
  token: string;
  onSuccess: () => void;
}) {
  const [dragOver, setDragOver] = useState(false);
  const Icon = DOCUMENT_STATUS_ICONS[doc.status] ?? FileText;
  const iconColor = DOCUMENT_STATUS_COLORS[doc.status] ?? 'text-gray-400';
  const statusLabel = DOCUMENT_STATUS_LABELS[doc.status] ?? doc.status;
  const needsUpload = doc.status === 'requested' || doc.status === 'rejected';

  const uploadMutation = useMutation({
    mutationFn: (file: File) => portalApi.uploadDocument(token, doc.id, file),
    onSuccess: () => {
      toast.success('Document téléversé avec succès.');
      onSuccess();
    },
    onError: () => {
      toast.error('Erreur lors du téléversement.');
    },
  });

  const handleFileSelect = useCallback(
    (file: File) => {
      if (file.size > 10 * 1024 * 1024) {
        toast.error('Le fichier dépasse 10 Mo.');
        return;
      }
      uploadMutation.mutate(file);
    },
    [uploadMutation],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFileSelect(file);
    },
    [handleFileSelect],
  );

  return (
    <Card>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <Icon className={`h-5 w-5 mt-0.5 ${iconColor}`} />
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {doc.document_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {statusLabel}
            </p>
            {doc.file_name && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Fichier : {doc.file_name}
              </p>
            )}
            {doc.rejection_reason && (
              <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                Motif du rejet : {doc.rejection_reason}
              </p>
            )}
          </div>
        </div>
      </div>

      {needsUpload && (
        <div
          className={`mt-3 border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
            dragOver
              ? 'border-primary-400 bg-primary-50 dark:bg-primary-900/20'
              : 'border-gray-300 dark:border-gray-600'
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          {uploadMutation.isPending ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">Envoi en cours...</p>
          ) : (
            <>
              <Upload className="h-6 w-6 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Glissez un fichier ici ou{' '}
                <label className="text-primary-600 hover:text-primary-700 cursor-pointer">
                  parcourir
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleFileSelect(file);
                    }}
                  />
                </label>
              </p>
              <p className="text-xs text-gray-400 mt-1">PDF, JPG, PNG — max 10 Mo</p>
            </>
          )}
        </div>
      )}
    </Card>
  );
}

function ContractReviewSection({
  token,
  contractDraft,
}: {
  token: string;
  contractDraft?: { contract_request_id: string; status: string; download_url: string | null } | null;
}) {
  const [decision, setDecision] = useState<'approved' | 'changes_requested' | null>(null);
  const [comments, setComments] = useState('');

  const reviewMutation = useMutation({
    mutationFn: () => portalApi.submitContractReview(token, decision!, comments || undefined),
    onSuccess: (data) => {
      toast.success(data.message);
      setDecision(null);
      setComments('');
    },
    onError: () => {
      toast.error('Erreur lors de la soumission.');
    },
  });

  return (
    <div>
      <Card className="mb-6">
        <div className="flex items-center gap-3 mb-4">
          <FileText className="h-6 w-6 text-primary-600" />
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Relecture du contrat
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Veuillez relire le contrat ci-dessous et donner votre décision.
            </p>
          </div>
        </div>

        {contractDraft?.download_url && (
          <a
            href={contractDraft.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-primary-600 hover:text-primary-700 mb-4"
          >
            <FileText className="h-4 w-4" />
            Télécharger le brouillon du contrat
          </a>
        )}
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
          Votre décision
        </h3>

        <div className="flex gap-3 mb-4">
          <button
            onClick={() => setDecision('approved')}
            className={`flex-1 p-4 rounded-lg border-2 text-center transition-colors ${
              decision === 'approved'
                ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                : 'border-gray-200 dark:border-gray-700 hover:border-green-300'
            }`}
          >
            <CheckCircle className={`h-6 w-6 mx-auto mb-2 ${decision === 'approved' ? 'text-green-500' : 'text-gray-400'}`} />
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              Approuver
            </p>
          </button>
          <button
            onClick={() => setDecision('changes_requested')}
            className={`flex-1 p-4 rounded-lg border-2 text-center transition-colors ${
              decision === 'changes_requested'
                ? 'border-orange-500 bg-orange-50 dark:bg-orange-900/20'
                : 'border-gray-200 dark:border-gray-700 hover:border-orange-300'
            }`}
          >
            <AlertTriangle className={`h-6 w-6 mx-auto mb-2 ${decision === 'changes_requested' ? 'text-orange-500' : 'text-gray-400'}`} />
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              Demander des modifications
            </p>
          </button>
        </div>

        {decision === 'changes_requested' && (
          <textarea
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            placeholder="Décrivez les modifications souhaitées..."
            className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 mb-4"
            rows={4}
          />
        )}

        {decision && (
          <Button
            onClick={() => reviewMutation.mutate()}
            disabled={reviewMutation.isPending || (decision === 'changes_requested' && !comments.trim())}
            className="w-full"
          >
            {reviewMutation.isPending ? 'Envoi...' : 'Confirmer ma décision'}
          </Button>
        )}
      </Card>
    </div>
  );
}
