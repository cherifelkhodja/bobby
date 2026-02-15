import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  FileSignature,
  Send,
  PenTool,
  Upload,
  CheckCircle,
  AlertTriangle,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';

import { contractsApi } from '../api/contracts';
import { useAuthStore } from '../stores/authStore';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';
import { getErrorMessage } from '../api/client';
import { CONTRACT_STATUS_CONFIG } from '../types';
import type { ContractRequestStatus } from '../types';

const THIRD_PARTY_TYPE_LABELS: Record<string, string> = {
  freelance: 'Freelance',
  sous_traitant: 'Sous-traitant',
  salarie: 'Salarié',
};

const ACTION_CONFIG: Partial<
  Record<ContractRequestStatus, { label: string; action: string; icon: typeof Send; variant: 'primary' | 'secondary' }>
> = {
  configuring_contract: {
    label: 'Générer le brouillon',
    action: 'generate-draft',
    icon: FileSignature,
    variant: 'primary',
  },
  draft_generated: {
    label: 'Envoyer au partenaire',
    action: 'send-draft-to-partner',
    icon: Send,
    variant: 'primary',
  },
  partner_approved: {
    label: 'Envoyer en signature',
    action: 'send-for-signature',
    icon: PenTool,
    variant: 'primary',
  },
  signed: {
    label: 'Pousser vers Boond',
    action: 'push-to-crm',
    icon: Upload,
    variant: 'primary',
  },
};

export default function ContractDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const isAdv = user?.role === 'adv' || user?.role === 'admin';

  const [overrideReason, setOverrideReason] = useState('');
  const [showOverride, setShowOverride] = useState(false);
  const [showCancelModal, setShowCancelModal] = useState(false);

  const { data: cr, isLoading } = useQuery({
    queryKey: ['contract-request', id],
    queryFn: () => contractsApi.get(id!),
    enabled: !!id,
  });

  const { data: contracts } = useQuery({
    queryKey: ['contracts', id],
    queryFn: () => contractsApi.listContracts(id!),
    enabled: !!id,
  });

  const actionMutation = useMutation({
    mutationFn: async (action: string) => {
      switch (action) {
        case 'generate-draft':
          return contractsApi.generateDraft(id!);
        case 'send-draft-to-partner':
          return contractsApi.sendDraftToPartner(id!);
        case 'send-for-signature':
          return contractsApi.sendForSignature(id!);
        case 'push-to-crm':
          return contractsApi.pushToCrm(id!);
        default:
          throw new Error(`Action inconnue: ${action}`);
      }
    },
    onSuccess: () => {
      toast.success('Action effectuée avec succès.');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['contracts', id] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const overrideMutation = useMutation({
    mutationFn: () => contractsApi.complianceOverride(id!, overrideReason),
    onSuccess: () => {
      toast.success('Conformité forcée.');
      setShowOverride(false);
      setOverrideReason('');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => contractsApi.cancel(id!),
    onSuccess: () => {
      toast.success('Demande de contrat annulée.');
      setShowCancelModal(false);
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const canCancel = cr && isAdv && cr.status !== 'cancelled' && cr.status !== 'signed' && cr.status !== 'archived' && cr.status !== 'redirected_payfit';

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });

  if (isLoading || !cr) {
    return <PageSpinner />;
  }

  const statusConfig = CONTRACT_STATUS_CONFIG[cr.status];
  const actionConfig = isAdv ? ACTION_CONFIG[cr.status] : undefined;

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/contracts')}
          className="flex items-center text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Retour aux contrats
        </button>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {cr.reference}
            </h1>
            <div className="flex items-center gap-3 mt-2">
              <span
                className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${statusConfig?.color ?? 'bg-gray-100 text-gray-600'}`}
              >
                {statusConfig?.label ?? cr.status_display}
              </span>
              {cr.client_name && (
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {cr.client_name}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {actionConfig && (
              <Button
                onClick={() => actionMutation.mutate(actionConfig.action)}
                disabled={actionMutation.isPending}
              >
                <actionConfig.icon className="h-4 w-4 mr-2" />
                {actionMutation.isPending ? 'En cours...' : actionConfig.label}
              </Button>
            )}
            {canCancel && (
              <Button
                variant="secondary"
                onClick={() => setShowCancelModal(true)}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Annuler
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Info cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <p className="text-xs text-gray-500 dark:text-gray-400">Type tiers</p>
          <p className="text-sm font-medium text-gray-900 dark:text-white mt-1">
            {cr.third_party_type
              ? THIRD_PARTY_TYPE_LABELS[cr.third_party_type] ?? cr.third_party_type
              : '-'}
          </p>
        </Card>
        <Card>
          <p className="text-xs text-gray-500 dark:text-gray-400">TJM</p>
          <p className="text-sm font-medium text-gray-900 dark:text-white mt-1">
            {cr.daily_rate ? `${cr.daily_rate} €/j` : '-'}
          </p>
        </Card>
        <Card>
          <p className="text-xs text-gray-500 dark:text-gray-400">Date de début</p>
          <p className="text-sm font-medium text-gray-900 dark:text-white mt-1">
            {cr.start_date ? formatDate(cr.start_date) : '-'}
          </p>
        </Card>
        <Card>
          <p className="text-xs text-gray-500 dark:text-gray-400">Commercial</p>
          <p className="text-sm font-medium text-gray-900 dark:text-white mt-1">
            {cr.commercial_email}
          </p>
        </Card>
      </div>

      {/* Mission description */}
      {cr.mission_description && (
        <Card className="mb-6">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
            Description de la mission
          </h3>
          <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
            {cr.mission_description}
          </p>
        </Card>
      )}

      {/* Compliance override (for blocked status) */}
      {isAdv && cr.status === 'compliance_blocked' && (
        <Card className="mb-6 border-orange-200 dark:border-orange-800">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-orange-500 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-orange-800 dark:text-orange-300">
                Conformité bloquée
              </h3>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                Les documents de conformité du tiers ne sont pas complets.
              </p>
              {!showOverride ? (
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-3"
                  onClick={() => setShowOverride(true)}
                >
                  Forcer la conformité
                </Button>
              ) : (
                <div className="mt-3 space-y-2">
                  <textarea
                    value={overrideReason}
                    onChange={(e) => setOverrideReason(e.target.value)}
                    placeholder="Raison du forçage (min. 10 caractères)..."
                    className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                    rows={2}
                  />
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => overrideMutation.mutate()}
                      disabled={overrideReason.length < 10 || overrideMutation.isPending}
                    >
                      Confirmer
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setShowOverride(false);
                        setOverrideReason('');
                      }}
                    >
                      Annuler
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Contracts list */}
      {contracts && contracts.length > 0 && (
        <Card className="mb-6">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            Documents contractuels
          </h3>
          <div className="space-y-2">
            {contracts.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <FileSignature className="h-4 w-4 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {c.reference} - v{c.version}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {formatDate(c.created_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {c.signed_at && (
                    <span className="flex items-center text-xs text-green-600 dark:text-green-400">
                      <CheckCircle className="h-3.5 w-3.5 mr-1" />
                      Signé le {formatDate(c.signed_at)}
                    </span>
                  )}
                  {c.yousign_status && !c.signed_at && (
                    <span className="text-xs text-violet-600 dark:text-violet-400">
                      YouSign: {c.yousign_status}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Metadata */}
      <Card>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
          Informations
        </h3>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-gray-500 dark:text-gray-400">Positionnement Boond</dt>
          <dd className="text-gray-900 dark:text-white">#{cr.boond_positioning_id}</dd>
          <dt className="text-gray-500 dark:text-gray-400">Conformité forcée</dt>
          <dd className="text-gray-900 dark:text-white">
            {cr.compliance_override ? 'Oui' : 'Non'}
          </dd>
          <dt className="text-gray-500 dark:text-gray-400">Créé le</dt>
          <dd className="text-gray-900 dark:text-white">{formatDate(cr.created_at)}</dd>
          <dt className="text-gray-500 dark:text-gray-400">Mis à jour le</dt>
          <dd className="text-gray-900 dark:text-white">{formatDate(cr.updated_at)}</dd>
        </dl>
      </Card>

      {/* Cancel confirmation modal */}
      <Modal
        isOpen={showCancelModal}
        onClose={() => setShowCancelModal(false)}
        title="Annuler la demande de contrat"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Voulez-vous vraiment annuler la demande <span className="font-semibold">{cr.reference}</span> ?
          </p>
          <p className="text-sm text-red-600 dark:text-red-400">
            Cette action est irréversible.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="secondary"
              onClick={() => setShowCancelModal(false)}
              disabled={cancelMutation.isPending}
            >
              Non, garder
            </Button>
            <Button
              variant="primary"
              onClick={() => cancelMutation.mutate()}
              isLoading={cancelMutation.isPending}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Oui, annuler
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
