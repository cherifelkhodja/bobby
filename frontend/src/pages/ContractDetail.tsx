import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  FileSignature,
  FileText,
  Mail,
  Send,
  PenTool,
  Upload,
  CheckCircle,
  AlertTriangle,
  Trash2,
  RefreshCw,
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

  const [docCollectionForm, setDocCollectionForm] = useState({
    siren: '',
    company_name: '',
    legal_form: '',
    siret: '',
    rcs_city: '',
    rcs_number: '',
    head_office_address: '',
    representative_name: '',
    representative_title: '',
    capital: '',
  });
  const [showResendForm, setShowResendForm] = useState(false);

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

  const syncMutation = useMutation({
    mutationFn: () => contractsApi.syncFromBoond(id!),
    onSuccess: () => {
      toast.success('Données Boond synchronisées.');
      setFormInitialized(false);
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
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

  const initiateDocCollectionMutation = useMutation({
    mutationFn: () =>
      contractsApi.initiateDocumentCollection(id!, {
        siren: docCollectionForm.siren,
        company_name: docCollectionForm.company_name,
        legal_form: docCollectionForm.legal_form,
        siret: docCollectionForm.siret,
        rcs_city: docCollectionForm.rcs_city,
        rcs_number: docCollectionForm.rcs_number,
        head_office_address: docCollectionForm.head_office_address,
        representative_name: docCollectionForm.representative_name,
        representative_title: docCollectionForm.representative_title,
        capital: docCollectionForm.capital || undefined,
      }),
    onSuccess: () => {
      toast.success('Email de collecte envoyé au tiers.');
      setShowResendForm(false);
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

  const isDocCollectionFormValid =
    /^\d{9}$/.test(docCollectionForm.siren) &&
    /^\d{14}$/.test(docCollectionForm.siret) &&
    docCollectionForm.company_name !== '' &&
    docCollectionForm.legal_form !== '' &&
    docCollectionForm.rcs_city !== '' &&
    docCollectionForm.rcs_number !== '' &&
    docCollectionForm.head_office_address !== '' &&
    docCollectionForm.representative_name !== '' &&
    docCollectionForm.representative_title !== '';

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
            <Button
              variant="secondary"
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
              {syncMutation.isPending ? 'Sync...' : 'Sync Boond'}
            </Button>
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

      {/* Document collection form (ADV) — initiation depuis commercial_validated */}
      {isAdv && cr.status === 'commercial_validated' && (
        <Card className="mb-6 border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="h-4 w-4 text-blue-500" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              Collecte des documents du tiers
            </h3>
          </div>
          {cr.contractualization_contact_email && (
            <div className="flex items-center gap-2 mb-4 px-3 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <Mail className="h-3.5 w-3.5 text-blue-500 flex-shrink-0" />
              <p className="text-xs text-blue-700 dark:text-blue-300">
                Le lien portail sera envoyé à{' '}
                <span className="font-medium">{cr.contractualization_contact_email}</span>
              </p>
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                SIREN *
              </label>
              <input
                type="text"
                maxLength={9}
                value={docCollectionForm.siren}
                onChange={(e) =>
                  setDocCollectionForm((f) => ({ ...f, siren: e.target.value.replace(/\D/g, '') }))
                }
                placeholder="9 chiffres"
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                SIRET *
              </label>
              <input
                type="text"
                maxLength={14}
                value={docCollectionForm.siret}
                onChange={(e) =>
                  setDocCollectionForm((f) => ({ ...f, siret: e.target.value.replace(/\D/g, '') }))
                }
                placeholder="14 chiffres"
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Raison sociale *
              </label>
              <input
                type="text"
                value={docCollectionForm.company_name}
                onChange={(e) =>
                  setDocCollectionForm((f) => ({ ...f, company_name: e.target.value }))
                }
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Forme juridique *
              </label>
              <input
                type="text"
                value={docCollectionForm.legal_form}
                onChange={(e) =>
                  setDocCollectionForm((f) => ({ ...f, legal_form: e.target.value }))
                }
                placeholder="SAS, SASU, EURL..."
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Ville RCS *
              </label>
              <input
                type="text"
                value={docCollectionForm.rcs_city}
                onChange={(e) =>
                  setDocCollectionForm((f) => ({ ...f, rcs_city: e.target.value }))
                }
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Numéro RCS *
              </label>
              <input
                type="text"
                value={docCollectionForm.rcs_number}
                onChange={(e) =>
                  setDocCollectionForm((f) => ({ ...f, rcs_number: e.target.value }))
                }
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Adresse du siège social *
              </label>
              <input
                type="text"
                value={docCollectionForm.head_office_address}
                onChange={(e) =>
                  setDocCollectionForm((f) => ({ ...f, head_office_address: e.target.value }))
                }
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Représentant légal *
              </label>
              <input
                type="text"
                value={docCollectionForm.representative_name}
                onChange={(e) =>
                  setDocCollectionForm((f) => ({ ...f, representative_name: e.target.value }))
                }
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Qualité du représentant *
              </label>
              <input
                type="text"
                value={docCollectionForm.representative_title}
                onChange={(e) =>
                  setDocCollectionForm((f) => ({ ...f, representative_title: e.target.value }))
                }
                placeholder="Président, Gérant..."
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Capital social
              </label>
              <input
                type="text"
                value={docCollectionForm.capital}
                onChange={(e) =>
                  setDocCollectionForm((f) => ({ ...f, capital: e.target.value }))
                }
                placeholder="Ex : 10 000 €"
                className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <Button
              onClick={() => initiateDocCollectionMutation.mutate()}
              disabled={!isDocCollectionFormValid || initiateDocCollectionMutation.isPending}
              isLoading={initiateDocCollectionMutation.isPending}
            >
              <FileText className="h-4 w-4 mr-2" />
              Lancer la collecte de documents
            </Button>
          </div>
        </Card>
      )}

      {/* Re-envoi lien collecte (ADV) — depuis collecting_documents */}
      {isAdv && cr.status === 'collecting_documents' && (
        <Card className="mb-6 border-indigo-200 dark:border-indigo-800">
          <div className="flex items-start gap-3">
            <FileText className="h-5 w-5 text-indigo-500 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-indigo-800 dark:text-indigo-300">
                Collecte de documents en cours
              </h3>
              {cr.contractualization_contact_email && (
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 flex items-center gap-1">
                  <Mail className="h-3 w-3 flex-shrink-0" />
                  Lien envoyé à{' '}
                  <span className="font-medium">{cr.contractualization_contact_email}</span>
                </p>
              )}
              {!showResendForm ? (
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-3"
                  onClick={() => setShowResendForm(true)}
                >
                  Renvoyer le lien de collecte
                </Button>
              ) : (
                <div className="mt-4 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">SIREN *</label>
                      <input type="text" maxLength={9} value={docCollectionForm.siren} onChange={(e) => setDocCollectionForm((f) => ({ ...f, siren: e.target.value.replace(/\D/g, '') }))} placeholder="9 chiffres" className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">SIRET *</label>
                      <input type="text" maxLength={14} value={docCollectionForm.siret} onChange={(e) => setDocCollectionForm((f) => ({ ...f, siret: e.target.value.replace(/\D/g, '') }))} placeholder="14 chiffres" className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Raison sociale *</label>
                      <input type="text" value={docCollectionForm.company_name} onChange={(e) => setDocCollectionForm((f) => ({ ...f, company_name: e.target.value }))} className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Forme juridique *</label>
                      <input type="text" value={docCollectionForm.legal_form} onChange={(e) => setDocCollectionForm((f) => ({ ...f, legal_form: e.target.value }))} placeholder="SAS, SASU, EURL..." className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Ville RCS *</label>
                      <input type="text" value={docCollectionForm.rcs_city} onChange={(e) => setDocCollectionForm((f) => ({ ...f, rcs_city: e.target.value }))} className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Numéro RCS *</label>
                      <input type="text" value={docCollectionForm.rcs_number} onChange={(e) => setDocCollectionForm((f) => ({ ...f, rcs_number: e.target.value }))} className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300" />
                    </div>
                    <div className="md:col-span-2">
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Adresse du siège social *</label>
                      <input type="text" value={docCollectionForm.head_office_address} onChange={(e) => setDocCollectionForm((f) => ({ ...f, head_office_address: e.target.value }))} className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Représentant légal *</label>
                      <input type="text" value={docCollectionForm.representative_name} onChange={(e) => setDocCollectionForm((f) => ({ ...f, representative_name: e.target.value }))} className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Qualité du représentant *</label>
                      <input type="text" value={docCollectionForm.representative_title} onChange={(e) => setDocCollectionForm((f) => ({ ...f, representative_title: e.target.value }))} placeholder="Président, Gérant..." className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Capital social</label>
                      <input type="text" value={docCollectionForm.capital} onChange={(e) => setDocCollectionForm((f) => ({ ...f, capital: e.target.value }))} placeholder="Ex : 10 000 €" className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300" />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => initiateDocCollectionMutation.mutate()}
                      disabled={!isDocCollectionFormValid || initiateDocCollectionMutation.isPending}
                      isLoading={initiateDocCollectionMutation.isPending}
                    >
                      Renvoyer
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setShowResendForm(false)}
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
