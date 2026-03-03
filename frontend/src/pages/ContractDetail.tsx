import { useState, useEffect } from 'react';
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
  Mail,
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
  const isCommercialOrAdmin =
    user?.role === 'commercial' || user?.role === 'admin' || user?.role === 'adv';

  const [overrideReason, setOverrideReason] = useState('');
  const [showOverride, setShowOverride] = useState(false);
  const [showCancelModal, setShowCancelModal] = useState(false);

  // Commercial validation form state — pre-filled from Boond data
  const [validationForm, setValidationForm] = useState({
    third_party_type: '',
    daily_rate: '',
    start_date: '',
    end_date: '',
    contact_email: '',
    client_name: '',
    mission_title: '',
    mission_description: '',
    consultant_civility: '',
    consultant_first_name: '',
    consultant_last_name: '',
    mission_site_name: '',
    mission_address: '',
    mission_postal_code: '',
    mission_city: '',
  });
  const [formInitialized, setFormInitialized] = useState(false);

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

  // Pre-fill validation form with Boond data when CR loads
  useEffect(() => {
    if (cr && !formInitialized) {
      setValidationForm((f) => ({
        ...f,
        daily_rate: cr.daily_rate ? String(cr.daily_rate) : '',
        start_date: cr.start_date ?? '',
        end_date: cr.end_date ?? '',
        client_name: cr.client_name ?? '',
        mission_title: cr.mission_title ?? '',
        mission_description: cr.mission_description ?? '',
        consultant_civility: cr.consultant_civility ?? '',
        consultant_first_name: cr.consultant_first_name ?? '',
        consultant_last_name: cr.consultant_last_name ?? '',
        mission_site_name: cr.mission_site_name ?? '',
        mission_address: cr.mission_address ?? '',
        mission_postal_code: cr.mission_postal_code ?? '',
        mission_city: cr.mission_city ?? '',
      }));
      setFormInitialized(true);
    }
  }, [cr, formInitialized]);

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

  const resendCollectionEmailMutation = useMutation({
    mutationFn: () => contractsApi.resendCollectionEmail(id!),
    onSuccess: () => {
      toast.success('Email de collecte renvoyé.');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const validateCommercialMutation = useMutation({
    mutationFn: () =>
      contractsApi.validateCommercial(id!, {
        third_party_type: validationForm.third_party_type,
        daily_rate: parseFloat(validationForm.daily_rate),
        start_date: validationForm.start_date,
        end_date: validationForm.end_date || undefined,
        contact_email: validationForm.contact_email,
        client_name: validationForm.client_name || undefined,
        mission_title: validationForm.mission_title || undefined,
        mission_description: validationForm.mission_description || undefined,
        consultant_civility: validationForm.consultant_civility || undefined,
        consultant_first_name: validationForm.consultant_first_name || undefined,
        consultant_last_name: validationForm.consultant_last_name || undefined,
        mission_site_name: validationForm.mission_site_name || undefined,
        mission_address: validationForm.mission_address || undefined,
        mission_postal_code: validationForm.mission_postal_code || undefined,
        mission_city: validationForm.mission_city || undefined,
      }),
    onSuccess: () => {
      toast.success('Validation commerciale effectuée.');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const isValidationFormValid =
    validationForm.third_party_type !== '' &&
    validationForm.daily_rate !== '' &&
    parseFloat(validationForm.daily_rate) > 0 &&
    validationForm.start_date !== '' &&
    validationForm.contact_email !== '';

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

      {/* Commercial validation form */}
      {isCommercialOrAdmin && cr.status === 'pending_commercial_validation' && (
        <Card className="mb-6 border-yellow-200 dark:border-yellow-800">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
            Validation commerciale
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Type de tiers *
              </label>
              <select
                value={validationForm.third_party_type}
                onChange={(e) =>
                  setValidationForm((f) => ({ ...f, third_party_type: e.target.value }))
                }
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              >
                <option value="">Sélectionner...</option>
                <option value="freelance">Freelance</option>
                <option value="sous_traitant">Sous-traitant</option>
                <option value="salarie">Salarié</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                TJM (€/j) *
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={validationForm.daily_rate}
                onChange={(e) =>
                  setValidationForm((f) => ({ ...f, daily_rate: e.target.value }))
                }
                placeholder={cr.daily_rate ? String(cr.daily_rate) : ''}
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Date de début *
              </label>
              <input
                type="date"
                value={validationForm.start_date}
                onChange={(e) =>
                  setValidationForm((f) => ({ ...f, start_date: e.target.value }))
                }
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Date de fin
              </label>
              <input
                type="date"
                value={validationForm.end_date}
                onChange={(e) =>
                  setValidationForm((f) => ({ ...f, end_date: e.target.value }))
                }
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Email contact contractualisation *
              </label>
              <input
                type="email"
                value={validationForm.contact_email}
                onChange={(e) =>
                  setValidationForm((f) => ({ ...f, contact_email: e.target.value }))
                }
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Client
              </label>
              <input
                type="text"
                value={validationForm.client_name}
                onChange={(e) =>
                  setValidationForm((f) => ({ ...f, client_name: e.target.value }))
                }
                placeholder={cr.client_name ?? ''}
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Intitulé de la mission
              </label>
              <input
                type="text"
                value={validationForm.mission_title}
                onChange={(e) =>
                  setValidationForm((f) => ({ ...f, mission_title: e.target.value }))
                }
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>

            {/* Consultant */}
            <div className="md:col-span-2 border-t border-gray-200 dark:border-gray-700 pt-4 mt-2">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wide">Consultant</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Civilité
                  </label>
                  <select
                    value={validationForm.consultant_civility}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, consultant_civility: e.target.value }))
                    }
                    className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                  >
                    <option value="">-</option>
                    <option value="M.">M.</option>
                    <option value="Mme">Mme</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Prénom
                  </label>
                  <input
                    type="text"
                    value={validationForm.consultant_first_name}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, consultant_first_name: e.target.value }))
                    }
                    className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Nom
                  </label>
                  <input
                    type="text"
                    value={validationForm.consultant_last_name}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, consultant_last_name: e.target.value }))
                    }
                    className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                  />
                </div>
              </div>
            </div>

            {/* Adresse de la mission */}
            <div className="md:col-span-2 border-t border-gray-200 dark:border-gray-700 pt-4 mt-2">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wide">Adresse de la mission</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Nom du site
                  </label>
                  <input
                    type="text"
                    value={validationForm.mission_site_name}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, mission_site_name: e.target.value }))
                    }
                    className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Adresse
                  </label>
                  <input
                    type="text"
                    value={validationForm.mission_address}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, mission_address: e.target.value }))
                    }
                    className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Code postal
                  </label>
                  <input
                    type="text"
                    value={validationForm.mission_postal_code}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, mission_postal_code: e.target.value }))
                    }
                    className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Ville
                  </label>
                  <input
                    type="text"
                    value={validationForm.mission_city}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, mission_city: e.target.value }))
                    }
                    className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                  />
                </div>
              </div>
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <Button
              onClick={() => validateCommercialMutation.mutate()}
              disabled={!isValidationFormValid || validateCommercialMutation.isPending}
              isLoading={validateCommercialMutation.isPending}
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Valider
            </Button>
          </div>
        </Card>
      )}

      {/* Validated commercial data (read-only, shown after validation) */}
      {cr.status !== 'pending_commercial_validation' && cr.third_party_type && (
        <Card className="mb-6">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-4">
            Informations validées par le commercial
          </h3>
          <div className="space-y-4">
            {/* Ligne 1 — données contrat */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {cr.third_party_type && (
                <div>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">Type de tiers</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                    {cr.third_party_type === 'freelance' ? 'Freelance / EI' : cr.third_party_type === 'sous_traitant' ? 'Sous-traitant' : 'Salarié'}
                  </p>
                </div>
              )}
              {cr.daily_rate && (
                <div>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">TJM</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {cr.daily_rate.toLocaleString('fr-FR')} €/j
                  </p>
                </div>
              )}
              {cr.start_date && (
                <div>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">Début</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{formatDate(cr.start_date)}</p>
                </div>
              )}
              {cr.end_date && (
                <div>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">Fin</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{formatDate(cr.end_date)}</p>
                </div>
              )}
            </div>

            {/* Ligne 2 — mission + consultant + email */}
            {(cr.mission_title || cr.consultant_first_name || cr.contractualization_contact_email) && (
              <div className="pt-3 border-t border-gray-100 dark:border-gray-700 grid grid-cols-1 md:grid-cols-3 gap-4">
                {cr.mission_title && (
                  <div>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">Intitulé mission</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{cr.mission_title}</p>
                  </div>
                )}
                {(cr.consultant_first_name || cr.consultant_last_name) && (
                  <div>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">Consultant</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {[cr.consultant_civility, cr.consultant_first_name, cr.consultant_last_name].filter(Boolean).join(' ')}
                    </p>
                  </div>
                )}
                {cr.contractualization_contact_email && (
                  <div>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">Email contact tiers</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{cr.contractualization_contact_email}</p>
                  </div>
                )}
              </div>
            )}

            {/* Ligne 3 — adresse (pleine largeur si présente) */}
            {(cr.mission_address || cr.mission_city) && (
              <div className="pt-3 border-t border-gray-100 dark:border-gray-700">
                <p className="text-xs text-gray-400 dark:text-gray-500 mb-0.5">Adresse de mission</p>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {[cr.mission_site_name, cr.mission_address, cr.mission_postal_code, cr.mission_city].filter(Boolean).join(' · ')}
                </p>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Collecting documents — info banner + resend button */}
      {isAdv && (cr.status === 'collecting_documents' || cr.status === 'compliance_blocked') && (
        <Card className="mb-6 border-indigo-200 dark:border-indigo-800">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <Mail className="h-5 w-5 text-indigo-500 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="text-sm font-semibold text-indigo-800 dark:text-indigo-300">
                  Collecte de documents en cours
                </h3>
                {cr.contractualization_contact_email && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    Lien envoyé à{' '}
                    <span className="font-medium">{cr.contractualization_contact_email}</span>
                  </p>
                )}
              </div>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => resendCollectionEmailMutation.mutate()}
              disabled={resendCollectionEmailMutation.isPending}
              isLoading={resendCollectionEmailMutation.isPending}
            >
              <Mail className="h-4 w-4 mr-2" />
              Renvoyer le lien
            </Button>
          </div>
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
