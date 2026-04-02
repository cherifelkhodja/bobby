import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  FileSignature,
  Send,
  PenTool,
  CheckCircle,
  AlertTriangle,
  Trash2,
  Mail,
  Copy,
  Check,
  Settings,
  Clock,
  Download,
  ChevronDown,
  ChevronUp,
  Pencil,
  RotateCcw,
  MessageSquare,
  Plus,
  GripVertical,
  User,
  X,
} from 'lucide-react';
import { toast } from 'sonner';

import { contractsApi, contractCompaniesApi, contractArticlesApi, contractAnnexesApi, contractConsultantsApi } from '../api/contracts';
import { vigilanceApi } from '../api/vigilance';
import { useAuthStore } from '../stores/authStore';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';
import { getErrorMessage } from '../api/client';
import { CONTRACT_STATUS_CONFIG, getDocumentBadgeConfig } from '../types';
import type { ContractRequestStatus, ContractRequest } from '../types';

// Progressive UI: status ordering for determining which sections to show
const STATUS_ORDER: Record<ContractRequestStatus, number> = {
  pending_commercial_validation: 0,
  commercial_validated: 1,
  collecting_documents: 2,
  reviewing_compliance: 3,
  compliance_blocked: 3,
  configuring_contract: 4, // Legacy
  draft_generated: 5,
  draft_sent_to_partner: 6,
  partner_approved: 7,
  partner_requested_changes: 5,
  sent_for_signature: 8,
  signed: 9,
  active: 10,
  archived: 11,
  redirected_payfit: -1,
  cancelled: -1,
};

/** Check if a CR has reached at least the given status level. */
function hasReachedStatus(current: ContractRequestStatus, target: ContractRequestStatus): boolean {
  return STATUS_ORDER[current] >= STATUS_ORDER[target];
}

const ACTION_CONFIG: Partial<
  Record<ContractRequestStatus, { label: string; action: string; icon: typeof Send; variant: 'primary' | 'secondary' }>
> = {
  reviewing_compliance: {
    label: 'Générer le brouillon',
    action: 'generate-draft',
    icon: FileSignature,
    variant: 'primary',
  },
  compliance_blocked: {
    label: 'Générer le brouillon',
    action: 'generate-draft',
    icon: FileSignature,
    variant: 'primary',
  },
  partner_requested_changes: {
    label: 'Générer la nouvelle version',
    action: 'generate-draft',
    icon: RotateCcw,
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
};


const INPUT_CLS =
  'w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300';

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
  const [linkCopied, setLinkCopied] = useState(false);

  const [tempValidatingDocId, setTempValidatingDocId] = useState<string | null>(null);

  // Commercial validation form state — simplified for contrat cadre
  const [validationForm, setValidationForm] = useState({
    third_party_type: '',
    contact_email: '',
    consultant_civility: '',
    consultant_first_name: '',
    consultant_last_name: '',
    consultant_email: '',
    consultant_phone: '',
    company_id: '',
  });
  const [formInitialized, setFormInitialized] = useState(false);

  // Contract configuration form state
  const [configForm, setConfigForm] = useState({
    company_id: '' as string,
    payment_terms: 'net_30',
    invoice_submission_method: 'email',
    estimated_days: '',
    tacit_renewal_months: '',
    excluded_optional_article_keys: [] as string[],
    special_conditions: '',
  });
  const [configFormInitialized, setConfigFormInitialized] = useState(false);

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

  const { data: companies = [] } = useQuery({
    queryKey: ['contract-companies-active'],
    queryFn: contractCompaniesApi.listActive,
    enabled: isCommercialOrAdmin,
  });

  const { data: allArticles = [] } = useQuery({
    queryKey: ['contract-articles'],
    queryFn: contractArticlesApi.list,
    enabled: isAdv,
  });
  const optionalArticles = allArticles.filter((a) => a.is_optional && a.is_active);
  const activeArticles = allArticles.filter((a) => a.is_active);

  const { data: allAnnexes = [] } = useQuery({
    queryKey: ['contract-annexes'],
    queryFn: contractAnnexesApi.list,
    enabled: isAdv,
  });
  const activeAnnexes = allAnnexes.filter((a) => a.is_active);

  const { data: complianceDocs } = useQuery({
    queryKey: ['compliance-docs', cr?.third_party_id],
    queryFn: () => vigilanceApi.getThirdPartyDocuments(cr!.third_party_id!),
    enabled: !!cr?.third_party_id && isCommercialOrAdmin,
  });


  // Pre-fill validation form with Boond data when CR loads
  useEffect(() => {
    if (cr && !formInitialized) {
      setValidationForm((f) => ({
        ...f,
        consultant_civility: cr.consultant_civility ?? '',
        consultant_first_name: cr.consultant_first_name ?? '',
        consultant_last_name: cr.consultant_last_name ?? '',
        consultant_email: cr.consultant_email ?? '',
        consultant_phone: cr.consultant_phone ?? '',
        company_id: cr.company_id ?? '',
      }));
      setFormInitialized(true);
    }
  }, [cr, formInitialized]);

  // Pre-fill config form from existing contract_config (or auto-assigned company_id)
  useEffect(() => {
    if (cr && !configFormInitialized) {
      const cfg = (cr.contract_config as Record<string, unknown>) ?? {};
      setConfigForm({
        company_id: (cfg.company_id as string) || cr.company_id || '',
        payment_terms: (cfg.payment_terms as string) ?? 'net_30',
        invoice_submission_method: (cfg.invoice_submission_method as string) ?? 'email',
        estimated_days: cfg.estimated_days != null ? String(cfg.estimated_days) : '',
        tacit_renewal_months: cfg.tacit_renewal_months != null ? String(cfg.tacit_renewal_months) : '',
        excluded_optional_article_keys: (cfg.excluded_optional_article_keys as string[]) ?? [],
        special_conditions: (cfg.special_conditions as string) ?? '',
      });
      setConfigFormInitialized(true);
    }
  }, [cr, configFormInitialized]);

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

  const retryBoondSyncMutation = useMutation({
    mutationFn: () => contractsApi.retryBoondSync(id!),
    onSuccess: () => {
      toast.success('Synchronisation Boond relancée.');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['contracts', id] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const boondConvertMutation = useMutation({
    mutationFn: () => contractsApi.boondConvertCandidate(id!),
    onSuccess: (data) => {
      if (data.already_resource) {
        toast.info(`Candidat #${data.boond_candidate_id} est déjà une ressource.`);
      } else {
        toast.success(`Candidat converti en ressource #${data.new_resource_id}.`);
      }
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const boondCompanyMutation = useMutation({
    mutationFn: () => contractsApi.boondCreateCompany(id!),
    onSuccess: (data) => {
      const msg = data.created_company
        ? `Société créée (ID ${data.boond_provider_id}), ${data.contacts_created.length} contact(s).`
        : `Société déjà existante (ID ${data.boond_provider_id}), ${data.contacts_created.length} contact(s) ajouté(s).`;
      toast.success(msg);
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
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

  const tempValidateMutation = useMutation({
    mutationFn: (docId: string) => vigilanceApi.validateDocument(docId),
    onSuccess: () => {
      toast.success('Document validé temporairement.');
      setTempValidatingDocId(null);
      queryClient.invalidateQueries({ queryKey: ['compliance-docs', cr?.third_party_id] });
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const validateDocMutation = useMutation({
    mutationFn: (docId: string) => vigilanceApi.validateDocument(docId),
    onSuccess: () => {
      toast.success('Document validé.');
      queryClient.invalidateQueries({ queryKey: ['compliance-docs', cr?.third_party_id] });
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const [rejectingDocId, setRejectingDocId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const rejectDocMutation = useMutation({
    mutationFn: ({ docId, reason }: { docId: string; reason: string }) =>
      vigilanceApi.rejectDocument(docId, reason),
    onSuccess: () => {
      toast.success('Document rejeté.');
      setRejectingDocId(null);
      setRejectReason('');
      queryClient.invalidateQueries({ queryKey: ['compliance-docs', cr?.third_party_id] });
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
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

  const rollbackMutation = useMutation({
    mutationFn: () => contractsApi.rollbackStatus(id!),
    onSuccess: () => {
      toast.success('Retour à l\'état précédent effectué.');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const [editingAutoCheck, setEditingAutoCheck] = useState<{ docId: string; data: Record<string, string> } | null>(null);
  const updateAutoCheckMutation = useMutation({
    mutationFn: ({ docId, data }: { docId: string; data: Record<string, string> }) =>
      vigilanceApi.updateAutoCheck(docId, data),
    onSuccess: () => {
      toast.success('Donnees mises a jour.');
      setEditingAutoCheck(null);
      queryClient.invalidateQueries({ queryKey: ['compliance-docs', cr?.third_party_id] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const reExtractMutation = useMutation({
    mutationFn: (docId: string) => vigilanceApi.reExtract(docId),
    onSuccess: () => {
      toast.success('Re-analyse terminee.');
      queryClient.invalidateQueries({ queryKey: ['compliance-docs', cr?.third_party_id] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
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

  const { data: signatureChecklist, refetch: refetchChecklist } = useQuery({
    queryKey: ['signature-checklist', id],
    queryFn: () => contractsApi.getSignatureChecklist(id!),
    enabled: !!id && cr?.status === 'sent_for_signature',
  });

  const uploadSignatureDocMutation = useMutation({
    mutationFn: ({ itemId, file }: { itemId: string; file: File }) =>
      contractsApi.uploadSignatureDocument(id!, itemId, file),
    onSuccess: () => {
      toast.success('Document uploade.');
      refetchChecklist();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const markAsSignedMutation = useMutation({
    mutationFn: () => contractsApi.markAsSigned(id!),
    onSuccess: () => {
      toast.success('Contrat marqué comme signé.');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['contracts', id] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const configureMutation = useMutation({
    mutationFn: async () => {
      // Auto-save config before generating draft
      await contractsApi.configure(id!, {
        company_id: configForm.company_id || null,
        payment_terms: configForm.payment_terms,
        invoice_submission_method: configForm.invoice_submission_method,
        estimated_days: configForm.estimated_days ? parseInt(configForm.estimated_days, 10) : undefined,
        tacit_renewal_months: configForm.tacit_renewal_months ? parseInt(configForm.tacit_renewal_months, 10) : undefined,
        excluded_optional_article_keys: configForm.excluded_optional_article_keys,
        special_conditions: configForm.special_conditions || undefined,
      });
      // Then generate the draft
      await contractsApi.generateDraft(id!);
    },
    onSuccess: () => {
      toast.success('Brouillon généré avec succès.');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['contracts', id] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const validateCommercialMutation = useMutation({
    mutationFn: () =>
      contractsApi.validateCommercial(id!, {
        third_party_type: validationForm.third_party_type,
        contact_email: validationForm.contact_email,
        company_id: validationForm.company_id || undefined,
        consultant_civility: validationForm.consultant_civility || undefined,
        consultant_first_name: validationForm.consultant_first_name || undefined,
        consultant_last_name: validationForm.consultant_last_name || undefined,
        consultant_email: validationForm.consultant_email || undefined,
        consultant_phone: validationForm.consultant_phone || undefined,
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
    validationForm.contact_email !== '';

  const canCancel = cr && isAdv && cr.status !== 'cancelled' && cr.status !== 'signed' && cr.status !== 'archived' && cr.status !== 'redirected_payfit';
  const canRollback = cr && isAdv && cr.status !== 'pending_commercial_validation' && cr.status !== 'cancelled' && cr.status !== 'archived';

  const prePartnerStatuses = new Set([
    'reviewing_compliance',
    'compliance_blocked',
    'draft_generated',
    'partner_requested_changes',
  ]);
  const showConfigForm = isAdv && !!cr?.status && prePartnerStatuses.has(cr.status);

  // Articles are now managed globally from Admin > Contrat AT tab

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

  // Latest contract (for partner_comments)
  const latestContract = contracts && contracts.length > 0
    ? contracts[contracts.length - 1]
    : null;

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

        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {cr.display_reference}
              </h1>
              <span
                className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${statusConfig?.color ?? 'bg-gray-100 text-gray-600'}`}
              >
                {statusConfig?.label ?? cr.status_display}
              </span>
              {(() => {
                const company = companies.find((c) => c.id === (cr.contract_config as Record<string, unknown> | null)?.company_id || c.id === cr.company_id)
                  ?? companies.find((c) => c.is_default);
                return company ? (
                  <span
                    className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold border"
                    style={{ color: company.color_code, borderColor: company.color_code, backgroundColor: `${company.color_code}15` }}
                  >
                    {company.name}
                  </span>
                ) : null;
              })()}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Download signed contract button */}
            {latestContract?.signed_at && latestContract?.s3_key_signed && (
              <Button
                variant="secondary"
                onClick={async () => {
                  try {
                    const url = await contractsApi.getContractDownloadUrl(cr.id, latestContract.id, 'signed');
                    window.open(url, '_blank');
                  } catch {
                    toast.error('Impossible de telecharger le contrat signe.');
                  }
                }}
              >
                <Download className="h-4 w-4 mr-2" />
                Contrat signe
              </Button>
            )}
            {actionConfig && (
              <Button
                onClick={() => actionMutation.mutate(actionConfig.action)}
                disabled={actionMutation.isPending}
              >
                <actionConfig.icon className="h-4 w-4 mr-2" />
                {actionMutation.isPending ? 'En cours...' : actionConfig.label}
              </Button>
            )}
            {canRollback && (
              <Button
                variant="secondary"
                onClick={() => rollbackMutation.mutate()}
                disabled={rollbackMutation.isPending}
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                {rollbackMutation.isPending ? 'Retour...' : 'État précédent'}
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
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Société émettrice
              </label>
              <select
                value={validationForm.company_id}
                onChange={(e) =>
                  setValidationForm((f) => ({ ...f, company_id: e.target.value }))
                }
                className={INPUT_CLS}
              >
                <option value="">Sélectionner...</option>
                {companies.filter((c) => c.is_active).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.code})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Type de tiers *
              </label>
              <select
                value={validationForm.third_party_type}
                onChange={(e) =>
                  setValidationForm((f) => ({ ...f, third_party_type: e.target.value }))
                }
                className={INPUT_CLS}
              >
                <option value="">Sélectionner...</option>
                <option value="freelance">Freelance</option>
                <option value="sous_traitant">Sous-traitant</option>
                <option value="portage_salarial">Portage salarial</option>
                <option value="salarie">Salarié</option>
              </select>
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
                className={INPUT_CLS}
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
                    className={INPUT_CLS}
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
                    className={INPUT_CLS}
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
                    className={INPUT_CLS}
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Email professionnel
                  </label>
                  <input
                    type="email"
                    value={validationForm.consultant_email}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, consultant_email: e.target.value }))
                    }
                    placeholder="prenom.nom@societe.fr"
                    className={INPUT_CLS}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Téléphone
                  </label>
                  <input
                    type="tel"
                    value={validationForm.consultant_phone}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, consultant_phone: e.target.value }))
                    }
                    placeholder="+33 6 00 00 00 00"
                    className={INPUT_CLS}
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

      {/* Partner requested changes — banner */}
      {isAdv && cr.status === 'partner_requested_changes' && (
        <Card className="mb-4 border-orange-200 dark:border-orange-800">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-orange-500 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-sm font-semibold text-orange-800 dark:text-orange-300">
                Le partenaire demande des modifications
              </h3>
              {latestContract?.partner_comments ? (
                <p className="mt-1 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                  {latestContract.partner_comments}
                </p>
              ) : (
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Aucun commentaire fourni.
                </p>
              )}
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Modifiez les articles/annexes ci-dessous ou la configuration, puis re-générez le brouillon.
              </p>
            </div>
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
            <div className="flex items-center gap-2 flex-shrink-0">
              {cr.portal_url && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(cr.portal_url!);
                    setLinkCopied(true);
                    setTimeout(() => setLinkCopied(false), 2000);
                  }}
                >
                  {linkCopied ? (
                    <Check className="h-4 w-4 mr-2 text-green-500" />
                  ) : (
                    <Copy className="h-4 w-4 mr-2" />
                  )}
                  {linkCopied ? 'Copié !' : 'Copier le lien'}
                </Button>
              )}
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
          </div>
        </Card>
      )}


      {/* Draft sent to partner — waiting banner */}
      {cr.status === 'draft_sent_to_partner' && (
        <Card className="mb-6 border-sky-200 dark:border-sky-800">
          <div className="flex items-start gap-3">
            <Clock className="h-5 w-5 text-sky-500 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-sm font-semibold text-sky-800 dark:text-sky-300">
                Brouillon envoyé au partenaire
              </h3>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                En attente de la réponse du partenaire (approbation ou demande de modifications).
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Sent for signature — checklist */}
      {cr.status === 'sent_for_signature' && (
        <Card className="mb-6 border-violet-200 dark:border-violet-800">
          <div className="flex items-start gap-3">
            <PenTool className="h-5 w-5 text-violet-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-violet-800 dark:text-violet-300">
                Documents a signer
              </h3>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                Uploadez chaque document signe pour valider la signature.
              </p>

              {isAdv && signatureChecklist && (
                <div className="mt-4 space-y-2">
                  {/* Partner documents */}
                  {signatureChecklist.filter(i => i.signer_role === 'partner').length > 0 && (
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400 mb-1.5">
                        Partenaire
                      </p>
                      <div className="space-y-1.5">
                        {signatureChecklist.filter(i => i.signer_role === 'partner').map(item => (
                          <div key={item.id} className="flex items-center justify-between p-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
                            <div className="flex items-center gap-2 min-w-0">
                              {item.uploaded ? (
                                <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
                              ) : (
                                <div className="h-4 w-4 rounded-full border-2 border-gray-300 dark:border-gray-600 shrink-0" />
                              )}
                              <div className="min-w-0">
                                <p className="text-xs font-medium text-gray-900 dark:text-white truncate">{item.label}</p>
                                {item.file_name && (
                                  <p className="text-[10px] text-gray-500 truncate">{item.file_name}</p>
                                )}
                              </div>
                            </div>
                            <label className="text-xs text-primary hover:underline cursor-pointer shrink-0 ml-2">
                              {item.uploaded ? 'Remplacer' : 'Uploader'}
                              <input
                                type="file"
                                accept=".pdf"
                                className="hidden"
                                onChange={(e) => {
                                  const f = e.target.files?.[0];
                                  if (f) uploadSignatureDocMutation.mutate({ itemId: item.id, file: f });
                                  e.target.value = '';
                                }}
                              />
                            </label>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Consultant documents */}
                  {signatureChecklist.filter(i => i.signer_role === 'consultant').length > 0 && (
                    <div className="mt-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-purple-600 dark:text-purple-400 mb-1.5">
                        Collaborateur
                      </p>
                      <div className="space-y-1.5">
                        {signatureChecklist.filter(i => i.signer_role === 'consultant').map(item => (
                          <div key={item.id} className="flex items-center justify-between p-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
                            <div className="flex items-center gap-2 min-w-0">
                              {item.uploaded ? (
                                <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
                              ) : (
                                <div className="h-4 w-4 rounded-full border-2 border-gray-300 dark:border-gray-600 shrink-0" />
                              )}
                              <div className="min-w-0">
                                <p className="text-xs font-medium text-gray-900 dark:text-white truncate">{item.label}</p>
                                {item.file_name && (
                                  <p className="text-[10px] text-gray-500 truncate">{item.file_name}</p>
                                )}
                              </div>
                            </div>
                            <label className="text-xs text-primary hover:underline cursor-pointer shrink-0 ml-2">
                              {item.uploaded ? 'Remplacer' : 'Uploader'}
                              <input
                                type="file"
                                accept=".pdf"
                                className="hidden"
                                onChange={(e) => {
                                  const f = e.target.files?.[0];
                                  if (f) uploadSignatureDocMutation.mutate({ itemId: item.id, file: f });
                                  e.target.value = '';
                                }}
                              />
                            </label>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Validate button */}
                  <div className="pt-3">
                    <Button
                      variant="primary"
                      size="sm"
                      disabled={!signatureChecklist.every(i => i.uploaded) || markAsSignedMutation.isPending}
                      onClick={() => markAsSignedMutation.mutate()}
                      isLoading={markAsSignedMutation.isPending}
                    >
                      <CheckCircle className="h-4 w-4 mr-1" />
                      Valider la signature ({signatureChecklist.filter(i => i.uploaded).length}/{signatureChecklist.length})
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Boond sync actions — visible when signed, active or archived */}
      {isAdv && (cr.status === 'signed' || cr.status === 'active' || cr.status === 'archived') && (
        <Card className="mb-6 border-emerald-200 dark:border-emerald-800">
          <div className="flex items-start gap-3 mb-4">
            <RotateCcw className="h-5 w-5 text-emerald-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">
                Actions BoondManager
              </h3>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                Synchronisation fournisseur et consultant vers Boond.
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {/* Action 1 — société + contacts */}
            <div className="flex flex-col gap-1 p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                1 · Societe fournisseur + Contacts
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Cree la societe fournisseur et les contacts (signataire, ADV, commercial).
              </span>
              <Button
                variant="outline"
                size="sm"
                className="mt-1 self-start"
                disabled={boondCompanyMutation.isPending}
                onClick={() => boondCompanyMutation.mutate()}
              >
                <RotateCcw className={`h-3.5 w-3.5 mr-1 ${boondCompanyMutation.isPending ? 'animate-spin' : ''}`} />
                {boondCompanyMutation.isPending ? 'En cours...' : 'Executer'}
              </Button>
            </div>

            {/* Action 2 — candidat → ressource */}
            {(cr.boond_candidate_id || cr.boond_resource_id) && (
              <div className="flex flex-col gap-1 p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  2 · Candidat → Ressource
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Convertit le candidat en ressource Boond et lie le fournisseur.
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-1 self-start"
                  disabled={boondConvertMutation.isPending}
                  onClick={() => boondConvertMutation.mutate()}
                >
                  <RotateCcw className={`h-3.5 w-3.5 mr-1 ${boondConvertMutation.isPending ? 'animate-spin' : ''}`} />
                  {boondConvertMutation.isPending ? 'En cours...' : 'Executer'}
                </Button>
              </div>
            )}
          </div>

          {/* Tout relancer */}
          <div className="mt-3 pt-3 border-t border-emerald-100 dark:border-emerald-900 flex justify-end">
            <Button
              variant="outline"
              size="sm"
              disabled={retryBoondSyncMutation.isPending}
              onClick={() => retryBoondSyncMutation.mutate()}
            >
              <RotateCcw className={`h-4 w-4 mr-1 ${retryBoondSyncMutation.isPending ? 'animate-spin' : ''}`} />
              {retryBoondSyncMutation.isPending ? 'En cours...' : 'Relancer la sync fournisseur'}
            </Button>
          </div>
        </Card>
      )}

      {/* Consultants section — visible after signing */}
      {isAdv && hasReachedStatus(cr.status, 'signed') && (
        <ConsultantsSection contractRequestId={cr.id} cr={cr} />
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
                    className={INPUT_CLS}
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

      {/* Contract configuration form */}
      {showConfigForm && (
        <Card className="mb-6 border-purple-200 dark:border-purple-800">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-5 flex items-center gap-2">
            <Settings className="h-4 w-4 text-purple-500" />
            Preparation du contrat
          </h3>

          {/* Section 0 — Société émettrice */}
          <div className="mb-5">
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wide">
              Société émettrice du contrat
            </p>
            <select
              value={configForm.company_id}
              onChange={(e) => setConfigForm((f) => ({ ...f, company_id: e.target.value }))}
              className={INPUT_CLS}
            >
              <option value="">— Utiliser la société par défaut —</option>
              {companies
                .filter((c) => c.is_active)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.legal_form} {c.name}{c.is_default ? ' (par défaut)' : ''}
                  </option>
                ))}
            </select>
            {companies.length === 0 && (
              <p className="text-xs text-gray-400 mt-1">
                Aucune société configurée — rendez-vous dans{' '}
                <strong>Administration &gt; Sociétés</strong> pour en ajouter.
              </p>
            )}
          </div>

          {/* Section 1 — Conditions financières */}
          <div className="mb-5 border-t border-gray-200 dark:border-gray-700 pt-4">
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wide">
              Conditions financières
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Délai de paiement
                </label>
                <select
                  value={configForm.payment_terms}
                  onChange={(e) => setConfigForm((f) => ({ ...f, payment_terms: e.target.value }))}
                  className={INPUT_CLS}
                >
                  <option value="immediate">Comptant</option>
                  <option value="net_30">30 jours</option>
                  <option value="net_45_eom">45 jours fin de mois</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Dépôt des factures
                </label>
                <select
                  value={configForm.invoice_submission_method}
                  onChange={(e) => setConfigForm((f) => ({ ...f, invoice_submission_method: e.target.value }))}
                  className={INPUT_CLS}
                >
                  {(() => {
                    const selectedCompany = companies.find((c) => c.id === configForm.company_id)
                      ?? companies.find((c) => c.is_default);
                    const mail = selectedCompany?.invoices_company_mail;
                    return (
                      <>
                        <option value="email">
                          Email{mail ? ` — ${mail}` : ' — (email non configuré)'}
                        </option>
                        <option value="boondmanager">BoondManager</option>
                      </>
                    );
                  })()}
                </select>
              </div>
            </div>
          </div>

          {/* Section 2 — Articles optionnels */}
          {optionalArticles.length > 0 && (
            <div className="mb-5 border-t border-gray-200 dark:border-gray-700 pt-4">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
                Articles optionnels
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-500 mb-3">
                Cochez les articles à inclure dans ce contrat. Les articles non cochés seront exclus du PDF.
              </p>
              <div className="space-y-2">
                {optionalArticles.map((article) => {
                  const isIncluded = !configForm.excluded_optional_article_keys.includes(article.article_key);
                  return (
                    <label
                      key={article.article_key}
                      className="flex items-center gap-3 cursor-pointer group"
                    >
                      <input
                        type="checkbox"
                        checked={isIncluded}
                        onChange={(e) => {
                          setConfigForm((f) => {
                            const excluded = f.excluded_optional_article_keys;
                            if (e.target.checked) {
                              return {
                                ...f,
                                excluded_optional_article_keys: excluded.filter(
                                  (k) => k !== article.article_key,
                                ),
                              };
                            } else {
                              return {
                                ...f,
                                excluded_optional_article_keys: [...excluded, article.article_key],
                              };
                            }
                          });
                        }}
                        className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white transition-colors">
                        {article.title}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          {/* Section 3 — Conditions particulières */}
          <div className="mb-5 border-t border-gray-200 dark:border-gray-700 pt-4">
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
              Conditions particulières
            </p>
            <textarea
              value={configForm.special_conditions}
              onChange={(e) => setConfigForm((f) => ({ ...f, special_conditions: e.target.value }))}
              placeholder="Clauses libres, conditions spécifiques à cette mission..."
              className={INPUT_CLS}
              rows={3}
            />
          </div>

          {/* Section 4 — Article/annex editor (inline) */}
          {activeArticles.length > 0 && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mb-5">
              <ArticleAnnexEditor
                contractRequestId={id!}
                articles={activeArticles}
                annexes={activeAnnexes}
                existingOverrides={(cr.contract_config as Record<string, unknown> | null) ?? {}}
                onSaved={() => queryClient.invalidateQueries({ queryKey: ['contract-request', id] })}
                onRegenerateDraft={undefined}
                isRegenerating={false}
                inline
              />
            </div>
          )}

          <div className="flex justify-end">
            <Button
              onClick={() => configureMutation.mutate()}
              disabled={configureMutation.isPending}
              isLoading={configureMutation.isPending}
            >
              <FileSignature className="h-4 w-4 mr-2" />
              {latestContract ? 'Régénérer le brouillon' : 'Générer le brouillon'}
            </Button>
          </div>
        </Card>
      )}

      {/* Third-party company info — visible after document collection starts */}
      {isCommercialOrAdmin && complianceDocs && hasReachedStatus(cr.status, 'collecting_documents') && (
        <Card className="mb-6">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
            Informations société
          </h3>
          <div className="grid grid-cols-2 gap-x-8 gap-y-4 text-sm">
            {cr.third_party_type && (
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">Type de tiers</p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {cr.third_party_type === 'freelance' ? 'Freelance / EI' : cr.third_party_type === 'sous_traitant' ? 'Sous-traitant' : cr.third_party_type === 'portage_salarial' ? 'Portage salarial' : 'Salarié'}
                </p>
              </div>
            )}
            {complianceDocs.company_name && (
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">Raison sociale</p>
                <p className="font-medium text-gray-900 dark:text-white">{complianceDocs.company_name}</p>
              </div>
            )}
            {complianceDocs.legal_form && (
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">Forme juridique</p>
                <p className="font-medium text-gray-900 dark:text-white">{complianceDocs.legal_form}</p>
              </div>
            )}
            {complianceDocs.capital && (
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">Capital</p>
                <p className="font-medium text-gray-900 dark:text-white">{complianceDocs.capital} €</p>
              </div>
            )}
            {complianceDocs.siren && (
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">SIREN</p>
                <p className="font-medium text-gray-900 dark:text-white">{complianceDocs.siren}</p>
              </div>
            )}
            {complianceDocs.siret && (
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">SIRET</p>
                <p className="font-medium text-gray-900 dark:text-white">{complianceDocs.siret}</p>
              </div>
            )}
            {(complianceDocs.rcs_city || complianceDocs.rcs_number) && (
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">RCS</p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {[complianceDocs.rcs_city, complianceDocs.rcs_number].filter(Boolean).join(' ')}
                </p>
              </div>
            )}
            {complianceDocs.head_office_address && (
              <div className="col-span-2">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">Siège social</p>
                <p className="font-medium text-gray-900 dark:text-white">{complianceDocs.head_office_address}</p>
              </div>
            )}
          </div>

          {(() => {
            const hasRepresentative = complianceDocs.representative_first_name || complianceDocs.representative_last_name || complianceDocs.representative_name;
            const hasSignatory = complianceDocs.signatory_first_name || complianceDocs.signatory_last_name;
            const hasAdv = complianceDocs.adv_contact_first_name || complianceDocs.adv_contact_last_name || complianceDocs.adv_contact_email;
            const hasBilling = complianceDocs.billing_contact_first_name || complianceDocs.billing_contact_last_name || complianceDocs.billing_contact_email;
            const hasContractContact = cr.contractualization_contact_email || complianceDocs.contact_email;
            if (!hasRepresentative && !hasSignatory && !hasAdv && !hasBilling && !hasContractContact) return null;

            const formatName = (civility: string | null, firstName: string | null, lastName: string | null) =>
              [civility, firstName, lastName].filter(Boolean).join(' ') || null;

            const ContactCard = ({ title, name, email, phone }: { title: string; name: string | null; email: string | null; phone: string | null }) => (
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 text-sm">
                <p className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">{title}</p>
                {name && <p className="font-medium text-gray-900 dark:text-white mb-1">{name}</p>}
                {email && <p className="text-gray-600 dark:text-gray-400 text-xs">{email}</p>}
                {phone && <p className="text-gray-500 dark:text-gray-500 text-xs">{phone}</p>}
                {!name && !email && !phone && <p className="text-gray-400 dark:text-gray-600 text-xs italic">Non renseigné</p>}
              </div>
            );

            return (
              <div className="border-t border-gray-100 dark:border-gray-700 mt-4 pt-4">
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">Contacts</p>
                <div className="grid grid-cols-2 gap-3">
                  {hasRepresentative && (
                    <ContactCard
                      title="Représentant légal"
                      name={
                        formatName(complianceDocs.representative_civility, complianceDocs.representative_first_name, complianceDocs.representative_last_name)
                        || (complianceDocs.representative_title ? `${complianceDocs.representative_title} ${complianceDocs.representative_name ?? ''}`.trim() : complianceDocs.representative_name)
                      }
                      email={complianceDocs.representative_email}
                      phone={complianceDocs.representative_phone}
                    />
                  )}
                  {hasSignatory && (
                    <ContactCard
                      title="Signataire"
                      name={formatName(complianceDocs.signatory_civility, complianceDocs.signatory_first_name, complianceDocs.signatory_last_name)}
                      email={complianceDocs.signatory_email}
                      phone={complianceDocs.signatory_phone}
                    />
                  )}
                  {hasAdv && (
                    <ContactCard
                      title="Contact ADV"
                      name={formatName(complianceDocs.adv_contact_civility, complianceDocs.adv_contact_first_name, complianceDocs.adv_contact_last_name)}
                      email={complianceDocs.adv_contact_email}
                      phone={complianceDocs.adv_contact_phone}
                    />
                  )}
                  {hasBilling && (
                    <ContactCard
                      title="Contact facturation"
                      name={formatName(complianceDocs.billing_contact_civility, complianceDocs.billing_contact_first_name, complianceDocs.billing_contact_last_name)}
                      email={complianceDocs.billing_contact_email}
                      phone={complianceDocs.billing_contact_phone}
                    />
                  )}
                  {hasContractContact && (
                    <ContactCard
                      title="Contact contractualisation"
                      name={null}
                      email={cr.contractualization_contact_email ?? complianceDocs.contact_email}
                      phone={null}
                    />
                  )}
                </div>
              </div>
            );
          })()}

          {/* Consultant sub-section */}
          {(cr.consultant_first_name || cr.consultant_last_name) && (
            <div className="border-t border-gray-100 dark:border-gray-700 mt-4 pt-4">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">Consultant</p>
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 text-sm inline-block min-w-[250px]">
                <p className="font-medium text-gray-900 dark:text-white mb-1">
                  {[cr.consultant_civility, cr.consultant_first_name, cr.consultant_last_name].filter(Boolean).join(' ')}
                </p>
                {cr.consultant_email && (
                  <p className="text-gray-600 dark:text-gray-400 text-xs">{cr.consultant_email}</p>
                )}
                {cr.consultant_phone && (
                  <p className="text-gray-500 dark:text-gray-500 text-xs">{cr.consultant_phone}</p>
                )}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Compliance documents — visible to ADV + commercial after document collection starts */}
      {isCommercialOrAdmin && complianceDocs && complianceDocs.documents.length > 0 && hasReachedStatus(cr.status, 'collecting_documents') && (
        <Card className="mb-6">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-gray-400" />
            Documents de conformité
          </h3>
          <div className="space-y-2">
            {complianceDocs.documents.map((doc) => {
              const docBadge = getDocumentBadgeConfig(doc);
              const canValidate = isAdv && doc.status === 'received';
              const canTempValidate = isAdv && doc.status === 'requested' && doc.is_unavailable;
              const isTempValidating = tempValidatingDocId === doc.id;
              const isRejecting = rejectingDocId === doc.id;
              return (
                <div
                  key={doc.id}
                  className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                >
                  <div className="flex items-center justify-between">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {doc.document_type_display}
                      </p>
                      {doc.file_name && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{doc.file_name}</p>
                      )}
                      {doc.expires_at && (
                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                          Expire le {new Date(doc.expires_at).toLocaleDateString('fr-FR')}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 ml-3 shrink-0">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${docBadge.color}`}>
                        {docBadge.label}
                      </span>
                      {canValidate && (
                        <>
                          <button
                            onClick={() => validateDocMutation.mutate(doc.id)}
                            disabled={validateDocMutation.isPending}
                            className="text-xs font-medium text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 px-2 py-1 rounded transition-colors disabled:opacity-50"
                          >
                            Valider
                          </button>
                          <button
                            onClick={() => setRejectingDocId(doc.id)}
                            className="text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 px-2 py-1 rounded transition-colors"
                          >
                            Rejeter
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                  {doc.is_unavailable && doc.unavailability_reason && (
                    <p className="mt-1.5 text-xs text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 rounded px-2 py-1">
                      Indisponible : {doc.unavailability_reason}
                    </p>
                  )}
                  {doc.rejection_reason && (
                    <p className="mt-1.5 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded px-2 py-1">
                      Motif de rejet : {doc.rejection_reason}
                    </p>
                  )}
                  {isRejecting && (
                    <div className="mt-2 flex items-center gap-2">
                      <input
                        type="text"
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="Motif du rejet..."
                        className="flex-1 text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                        autoFocus
                      />
                      <button
                        onClick={() => rejectDocMutation.mutate({ docId: doc.id, reason: rejectReason })}
                        disabled={!rejectReason.trim() || rejectDocMutation.isPending}
                        className="text-xs font-medium text-red-600 dark:text-red-400 hover:underline disabled:opacity-50"
                      >
                        Confirmer
                      </button>
                      <button
                        onClick={() => { setRejectingDocId(null); setRejectReason(''); }}
                        className="text-xs text-gray-400 hover:underline"
                      >
                        Annuler
                      </button>
                    </div>
                  )}
                  {canTempValidate && !isRejecting && (
                    <div className="mt-2">
                      {!isTempValidating ? (
                        <button
                          onClick={() => setTempValidatingDocId(doc.id)}
                          className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
                        >
                          Valider temporairement
                        </button>
                      ) : (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500 dark:text-gray-400">Confirmer ?</span>
                          <button
                            onClick={() => tempValidateMutation.mutate(doc.id)}
                            disabled={tempValidateMutation.isPending}
                            className="text-xs font-medium text-green-600 dark:text-green-400 hover:underline disabled:opacity-50"
                          >
                            Oui
                          </button>
                          <button
                            onClick={() => setTempValidatingDocId(null)}
                            className="text-xs text-gray-400 hover:underline"
                          >
                            Non
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                  {/* Auto-check results + edit/re-extract */}
                  {doc.auto_check_results && Object.keys(doc.auto_check_results).length > 0 && (
                    <div className="mt-2 p-2 bg-gray-100 dark:bg-gray-700/50 rounded text-xs">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide" style={{ fontSize: '10px' }}>Verifications auto</span>
                        <div className="flex gap-1">
                          {isAdv && (
                            <>
                              <button
                                onClick={() => setEditingAutoCheck({ docId: doc.id, data: { ...doc.auto_check_results } as Record<string, string> })}
                                className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                              >
                                Modifier
                              </button>
                              <button
                                onClick={() => reExtractMutation.mutate(doc.id)}
                                disabled={reExtractMutation.isPending}
                                className="text-xs text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50"
                              >
                                {reExtractMutation.isPending ? 'Analyse...' : 'Re-analyser'}
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                      {Object.entries(doc.auto_check_results).filter(([k]) => !['is_valid', 'document_date', 'expiry_date'].includes(k)).map(([key, val]) => (
                        <div key={key} className="flex gap-2 text-gray-600 dark:text-gray-300">
                          <span className="text-gray-400 dark:text-gray-500 capitalize">{key.replace(/_/g, ' ')} :</span>
                          <span className="font-medium">{String(val || '—')}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {/* Inline edit form */}
                  {editingAutoCheck?.docId === doc.id && (
                    <div className="mt-2 p-2 bg-indigo-50 dark:bg-indigo-900/20 rounded space-y-2">
                      {Object.entries(editingAutoCheck.data).filter(([k]) => !['is_valid', 'document_date', 'expiry_date'].includes(k)).map(([key, val]) => (
                        <div key={key} className="flex items-center gap-2">
                          <label className="text-xs text-gray-500 dark:text-gray-400 w-24 capitalize">{key.replace(/_/g, ' ')}</label>
                          <input
                            type="text"
                            value={val ?? ''}
                            onChange={(e) => setEditingAutoCheck((prev) => prev ? { ...prev, data: { ...prev.data, [key]: e.target.value } } : null)}
                            className="flex-1 text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                          />
                        </div>
                      ))}
                      <div className="flex gap-2 justify-end">
                        <button onClick={() => setEditingAutoCheck(null)} className="text-xs text-gray-400 hover:underline">Annuler</button>
                        <button
                          onClick={() => updateAutoCheckMutation.mutate({ docId: doc.id, data: editingAutoCheck.data })}
                          disabled={updateAutoCheckMutation.isPending}
                          className="text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:underline disabled:opacity-50"
                        >
                          {updateAutoCheckMutation.isPending ? 'Sauvegarde...' : 'Sauvegarder'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
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
            {[...contracts].sort((a, b) => {
              // Signed first, then final (non-PROV), then provisional (PROV) by version desc
              const aSigned = !!(a.signed_at && a.s3_key_signed);
              const bSigned = !!(b.signed_at && b.s3_key_signed);
              if (aSigned !== bSigned) return aSigned ? -1 : 1;
              const aProv = a.reference.startsWith('PROV-');
              const bProv = b.reference.startsWith('PROV-');
              if (aProv !== bProv) return aProv ? 1 : -1;
              return b.version - a.version;
            }).map((c) => {
              const isSigned = !!(c.signed_at && c.s3_key_signed);
              const isProvisional = c.reference.startsWith('PROV-');
              const isFinal = !isProvisional;

              return (
                <div
                  key={c.id}
                  className={`flex items-center justify-between p-3 rounded-lg ${
                    isSigned
                      ? 'bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800'
                      : isFinal
                        ? 'bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800'
                        : 'bg-gray-50 dark:bg-gray-800'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <FileSignature className={`h-4 w-4 ${isSigned ? 'text-green-500' : isFinal ? 'text-blue-400' : 'text-gray-300'}`} />
                    <div>
                      <div className="flex items-center gap-2">
                        <p className={`text-sm font-medium ${isProvisional ? 'text-gray-400 dark:text-gray-500' : 'text-gray-900 dark:text-white'}`}>
                          {isSigned
                            ? `${c.reference} (Signed)`
                            : isFinal
                              ? c.reference
                              : `${c.reference} v${c.version}`
                          }
                        </p>
                        {isSigned && (
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Signe
                          </span>
                        )}
                        {!isSigned && isFinal && (
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                            Definitif
                          </span>
                        )}
                        {isProvisional && (
                          <span className="text-xs text-gray-400 dark:text-gray-500">
                            Brouillon
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                        {formatDate(c.created_at)}{isSigned ? ` — signe le ${formatDate(c.signed_at!)}` : ''}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {isSigned ? (
                      <button
                        onClick={async () => {
                          try {
                            const url = await contractsApi.getContractDownloadUrl(cr.id, c.id, 'signed');
                            window.open(url, '_blank');
                          } catch {
                            toast.error('Impossible de telecharger.');
                          }
                        }}
                        className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400 hover:text-green-800 font-medium transition-colors"
                      >
                        <Download className="h-3.5 w-3.5" />
                        {c.reference} (Signed).pdf
                      </button>
                    ) : (
                      <button
                        onClick={async () => {
                          try {
                            const url = await contractsApi.getContractDownloadUrl(cr.id, c.id, 'draft');
                            window.open(url, '_blank');
                          } catch {
                            toast.error('Impossible de telecharger.');
                          }
                        }}
                        className={`flex items-center gap-1 text-xs transition-colors ${isProvisional ? 'text-gray-400 hover:text-gray-600' : 'text-indigo-600 dark:text-indigo-400 hover:text-indigo-800'}`}
                      >
                        <Download className="h-3.5 w-3.5" />
                        {isProvisional ? `${c.reference} v${c.version}.pdf` : `${c.reference}.pdf`}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Metadata */}
      <Card>
        <HistoryTimeline statusHistory={cr.status_history} />
      </Card>

      {/* Cancel confirmation modal */}
      <Modal
        isOpen={showCancelModal}
        onClose={() => setShowCancelModal(false)}
        title="Annuler la demande de contrat"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Voulez-vous vraiment annuler la demande <span className="font-semibold">{cr.display_reference}</span> ?
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

// ─── Article / Annex per-contract editor ─────────────────────────────────────

import type { ArticleTemplate, AnnexTemplate, CustomArticleItem, CustomAnnexItem } from '../api/contracts';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// ─── Sortable row used inside ArticleAnnexEditor ─────────────────────────────

function SortableEditorRow({
  itemKey,
  title,
  label,
  isCustom,
  isExpanded,
  isDeleted,
  isDirty,
  hasOverride,
  value,
  isPending,
  onToggleExpand,
  onToggleDelete,
  onChange,
  onReset,
  onSave,
}: {
  itemKey: string;
  title: string;
  label: string;
  isCustom: boolean;
  isExpanded: boolean;
  isDeleted: boolean;
  isDirty: boolean;
  hasOverride: boolean;
  value: string;
  isPending: boolean;
  onToggleExpand: () => void;
  onToggleDelete: (e: React.MouseEvent) => void;
  onChange: (v: string) => void;
  onReset: () => void;
  onSave: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: itemKey,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`border rounded-lg overflow-hidden ${isDragging ? 'shadow-lg z-10 relative' : ''} ${isDeleted ? 'border-red-200 dark:border-red-800 opacity-60' : 'border-gray-200 dark:border-gray-700'}`}
    >
      <div className="flex items-center">
        {/* Drag handle */}
        <button
          type="button"
          {...attributes}
          {...listeners}
          className="flex-shrink-0 px-2 py-3 text-gray-300 dark:text-gray-600 hover:text-gray-500 dark:hover:text-gray-400 cursor-grab active:cursor-grabbing touch-none bg-gray-50 dark:bg-gray-800/60"
          title="Glisser pour réordonner"
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <button
          type="button"
          className={`flex-1 flex items-center justify-between px-4 py-3 text-left transition-colors ${isDeleted ? 'bg-red-50 dark:bg-red-900/20' : 'bg-gray-50 dark:bg-gray-800/60 hover:bg-gray-100 dark:hover:bg-gray-800'}`}
          onClick={() => !isDeleted && onToggleExpand()}
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide flex-shrink-0">
              {label}
            </span>
            <span className={`text-sm font-medium truncate ${isDeleted ? 'line-through text-gray-400 dark:text-gray-500' : 'text-gray-800 dark:text-gray-200'}`}>
              {title}
            </span>
            {isCustom && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300 border border-green-200 dark:border-green-700 flex-shrink-0">
                ajouté
              </span>
            )}
            {isDeleted && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300 border border-red-200 dark:border-red-700 flex-shrink-0">
                supprimé
              </span>
            )}
            {!isDeleted && !isCustom && hasOverride && !isDirty && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 border border-amber-200 dark:border-amber-700 flex-shrink-0">
                <Pencil className="h-3 w-3 mr-1" />modifié
              </span>
            )}
            {!isDeleted && isDirty && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border border-blue-200 dark:border-blue-700 flex-shrink-0">
                non sauvegardé
              </span>
            )}
          </div>
          {!isDeleted && (isExpanded ? <ChevronUp className="h-4 w-4 text-gray-400 flex-shrink-0" /> : <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />)}
        </button>
        <button
          type="button"
          title={isDeleted ? 'Restaurer' : 'Supprimer du PDF'}
          onClick={onToggleDelete}
          disabled={isPending}
          className={`px-3 py-3 flex-shrink-0 transition-colors ${isDeleted ? 'text-green-500 hover:text-green-700 dark:hover:text-green-400 bg-red-50 dark:bg-red-900/20' : 'text-gray-300 hover:text-red-500 dark:hover:text-red-400 bg-gray-50 dark:bg-gray-800/60'}`}
        >
          {isDeleted ? <RotateCcw className="h-4 w-4" /> : <Trash2 className="h-4 w-4" />}
        </button>
      </div>

      {isExpanded && !isDeleted && (
        <div className="p-4 bg-white dark:bg-gray-900">
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full text-sm font-mono border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-y"
            rows={10}
          />
          <div className="flex items-center justify-between mt-2">
            {!isCustom ? (
              <button
                type="button"
                onClick={onReset}
                className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                disabled={isPending}
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Restaurer le modèle
              </button>
            ) : <span />}
            {isDirty && (
              <Button
                size="sm"
                onClick={onSave}
                disabled={isPending}
                isLoading={isPending}
              >
                Enregistrer
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main editor ─────────────────────────────────────────────────────────────

function ArticleAnnexEditor({
  contractRequestId,
  articles,
  annexes,
  existingOverrides,
  onSaved,
  onRegenerateDraft,
  isRegenerating,
  inline,
}: {
  contractRequestId: string;
  articles: ArticleTemplate[];
  annexes: AnnexTemplate[];
  existingOverrides: Record<string, unknown>;
  onSaved: () => void;
  onRegenerateDraft?: () => void;
  isRegenerating?: boolean;
  inline?: boolean;
}) {
  const articleOverrides = (existingOverrides.article_overrides ?? {}) as Record<string, string>;
  const annexOverrides = (existingOverrides.annex_overrides ?? {}) as Record<string, string>;
  const serverDeletedArticles = ((existingOverrides.deleted_article_keys ?? []) as string[]);
  const serverDeletedAnnexes = ((existingOverrides.deleted_annex_keys ?? []) as string[]);
  const serverCustomArticles = ((existingOverrides.custom_articles ?? []) as CustomArticleItem[]);
  const serverCustomAnnexes = ((existingOverrides.custom_annexes ?? []) as CustomAnnexItem[]);
  const serverArticleOrder = ((existingOverrides.article_order ?? []) as string[]);
  const serverAnnexOrder = ((existingOverrides.annex_order ?? []) as string[]);

  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [editing, setEditing] = useState<Record<string, string>>({});
  const [dirty, setDirty] = useState<Record<string, boolean>>({});
  const [deletedArticles, setDeletedArticles] = useState<string[]>(serverDeletedArticles);
  const [deletedAnnexes, setDeletedAnnexes] = useState<string[]>(serverDeletedAnnexes);
  const [customArticles, setCustomArticles] = useState<CustomArticleItem[]>(serverCustomArticles);
  const [customAnnexes, setCustomAnnexes] = useState<CustomAnnexItem[]>(serverCustomAnnexes);
  const [showAddArticle, setShowAddArticle] = useState(false);
  const [showAddAnnex, setShowAddAnnex] = useState(false);
  const [newTitle, setNewTitle] = useState('');

  // dnd-kit sensors
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  // Build ordered lists of keys for articles and annexes
  const buildArticleKeys = () => {
    const templateKeys = articles.map((a) => a.article_key);
    const customKeys = customArticles.map((c) => c.key);
    const allKeys = [...templateKeys, ...customKeys];
    if (serverArticleOrder.length > 0) {
      const ordered = [...serverArticleOrder];
      for (const k of allKeys) {
        if (!ordered.includes(k)) ordered.push(k);
      }
      return ordered.filter((k) => allKeys.includes(k));
    }
    return allKeys;
  };

  const buildAnnexKeys = () => {
    const templateKeys = annexes.map((a) => a.annexe_key);
    const customKeys = customAnnexes.map((c) => c.key);
    const allKeys = [...templateKeys, ...customKeys];
    if (serverAnnexOrder.length > 0) {
      const ordered = [...serverAnnexOrder];
      for (const k of allKeys) {
        if (!ordered.includes(k)) ordered.push(k);
      }
      return ordered.filter((k) => allKeys.includes(k));
    }
    return allKeys;
  };

  const [articleKeys, setArticleKeys] = useState<string[]>(buildArticleKeys);
  const [annexKeys, setAnnexKeys] = useState<string[]>(buildAnnexKeys);

  // Rebuild keys when custom items change
  useEffect(() => {
    setArticleKeys(buildArticleKeys());
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customArticles.length]);

  useEffect(() => {
    setAnnexKeys(buildAnnexKeys());
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customAnnexes.length]);

  // Lookup maps
  const articleMap = new Map(articles.map((a) => [a.article_key, a]));
  const annexMap = new Map(annexes.map((a) => [a.annexe_key, a]));
  const customArticleMap = new Map(customArticles.map((c) => [c.key, c]));
  const customAnnexMap = new Map(customAnnexes.map((c) => [c.key, c]));

  const saveMutation = useMutation({
    mutationFn: (data: Parameters<typeof contractsApi.saveArticleOverrides>[1]) =>
      contractsApi.saveArticleOverrides(contractRequestId, data),
    onSuccess: () => {
      toast.success('Modifications enregistrées.');
      setDirty({});
      onSaved();
    },
    onError: () => toast.error('Erreur lors de la sauvegarde.'),
  });

  const getValue = (key: string, defaultContent: string, isAnnex = false) => {
    if (key in editing) return editing[key];
    const overrides = isAnnex ? annexOverrides : articleOverrides;
    return overrides[key] ?? defaultContent;
  };

  const handleChange = (key: string, value: string) => {
    setEditing((e) => ({ ...e, [key]: value }));
    setDirty((d) => ({ ...d, [key]: true }));
  };

  const handleReset = (key: string, defaultContent: string, isAnnex = false) => {
    const overrides = isAnnex ? annexOverrides : articleOverrides;
    const hasOverride = !!overrides[key];
    if (hasOverride) {
      const payload = isAnnex
        ? { annex_overrides: { [key]: '' } }
        : { article_overrides: { [key]: '' } };
      saveMutation.mutate(payload);
    }
    setEditing((e) => ({ ...e, [key]: defaultContent }));
    setDirty((d) => ({ ...d, [key]: false }));
  };

  const handleSave = (key: string, isAnnex = false) => {
    const value = editing[key] ?? '';
    if (isAnnex && customAnnexMap.has(key)) {
      const updated = customAnnexes.map((c) =>
        c.key === key ? { ...c, content: value } : c,
      );
      setCustomAnnexes(updated);
      saveMutation.mutate({ custom_annexes: updated });
      return;
    }
    if (!isAnnex && customArticleMap.has(key)) {
      const updated = customArticles.map((c) =>
        c.key === key ? { ...c, content: value } : c,
      );
      setCustomArticles(updated);
      saveMutation.mutate({ custom_articles: updated });
      return;
    }
    const payload = isAnnex
      ? { annex_overrides: { [key]: value } }
      : { article_overrides: { [key]: value } };
    saveMutation.mutate(payload);
  };

  const handleToggleDelete = (key: string, isAnnex: boolean, e: React.MouseEvent) => {
    e.stopPropagation();
    if (isAnnex) {
      const next = deletedAnnexes.includes(key)
        ? deletedAnnexes.filter((k) => k !== key)
        : [...deletedAnnexes, key];
      setDeletedAnnexes(next);
      if (customAnnexMap.has(key) && !deletedAnnexes.includes(key)) {
        const updated = customAnnexes.filter((c) => c.key !== key);
        setCustomAnnexes(updated);
        setAnnexKeys((prev) => prev.filter((k) => k !== key));
        saveMutation.mutate({ custom_annexes: updated, deleted_annex_keys: next.filter((k) => k !== key) });
      } else {
        saveMutation.mutate({ deleted_annex_keys: next });
      }
    } else {
      const next = deletedArticles.includes(key)
        ? deletedArticles.filter((k) => k !== key)
        : [...deletedArticles, key];
      setDeletedArticles(next);
      if (customArticleMap.has(key) && !deletedArticles.includes(key)) {
        const updated = customArticles.filter((c) => c.key !== key);
        setCustomArticles(updated);
        setArticleKeys((prev) => prev.filter((k) => k !== key));
        saveMutation.mutate({ custom_articles: updated, deleted_article_keys: next.filter((k) => k !== key) });
      } else {
        saveMutation.mutate({ deleted_article_keys: next });
      }
    }
  };

  const handleDragEnd = (isAnnex: boolean) => (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const keys = isAnnex ? annexKeys : articleKeys;
    const setKeys = isAnnex ? setAnnexKeys : setArticleKeys;
    const oldIndex = keys.indexOf(active.id as string);
    const newIndex = keys.indexOf(over.id as string);
    const newOrder = arrayMove(keys, oldIndex, newIndex);

    setKeys(newOrder);
    const payload = isAnnex
      ? { annex_order: newOrder }
      : { article_order: newOrder };
    saveMutation.mutate(payload);
  };

  const handleAddCustom = (isAnnex: boolean) => {
    if (!newTitle.trim()) return;
    const slug = newTitle
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_|_$/g, '');
    const key = `custom_${slug}_${Date.now()}`;

    if (isAnnex) {
      const item: CustomAnnexItem = { key, title: newTitle.trim(), content: '' };
      const updated = [...customAnnexes, item];
      setCustomAnnexes(updated);
      saveMutation.mutate({ custom_annexes: updated });
    } else {
      const item: CustomArticleItem = { key, title: newTitle.trim(), content: '' };
      const updated = [...customArticles, item];
      setCustomArticles(updated);
      saveMutation.mutate({ custom_articles: updated });
    }
    setNewTitle('');
    setShowAddArticle(false);
    setShowAddAnnex(false);
  };

  const renderAddForm = (isAnnex: boolean, show: boolean, setShow: (v: boolean) => void) => (
    show ? (
      <div className="flex items-center gap-2 mt-2">
        <input
          type="text"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder={isAnnex ? 'Titre de la nouvelle annexe...' : 'Titre du nouvel article...'}
          className="flex-1 text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
          onKeyDown={(e) => e.key === 'Enter' && handleAddCustom(isAnnex)}
          autoFocus
        />
        <Button size="sm" onClick={() => handleAddCustom(isAnnex)} disabled={!newTitle.trim() || saveMutation.isPending}>
          Ajouter
        </Button>
        <button
          type="button"
          onClick={() => { setShow(false); setNewTitle(''); }}
          className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          Annuler
        </button>
      </div>
    ) : (
      <button
        type="button"
        onClick={() => { setShow(true); setNewTitle(''); }}
        className="inline-flex items-center gap-1.5 mt-2 text-xs text-primary-600 dark:text-primary-400 hover:text-primary-800 dark:hover:text-primary-200"
      >
        <Plus className="h-3.5 w-3.5" />
        {isAnnex ? 'Ajouter une annexe' : 'Ajouter un article'}
      </button>
    )
  );

  const content = (
    <>
      <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
        Edition des articles et annexes
      </p>
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
        Glissez pour reordonner, modifiez le contenu ou ajoutez des articles/annexes pour ce contrat uniquement.
      </p>

      {/* Articles */}
      <div className="mb-4">
        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Articles</h4>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd(false)}>
          <SortableContext items={articleKeys} strategy={verticalListSortingStrategy}>
            <div className="space-y-2">
              {articleKeys.map((key) => {
                const tpl = articleMap.get(key);
                const custom = customArticleMap.get(key);
                if (!tpl && !custom) return null;
                const title = tpl?.title ?? custom?.title ?? '';
                const content = tpl?.content ?? custom?.content ?? '';
                const isCustom = !!custom;
                const isDeleted = deletedArticles.includes(key);
                return (
                  <SortableEditorRow
                    key={key}
                    itemKey={key}
                    title={title}
                    label="Art."
                    isCustom={isCustom}
                    isExpanded={!!expanded[key]}
                    isDeleted={isDeleted}
                    isDirty={!!dirty[key]}
                    hasOverride={!!articleOverrides[key]}
                    value={getValue(key, content, false)}
                    isPending={saveMutation.isPending}
                    onToggleExpand={() => setExpanded((e) => ({ ...e, [key]: !e[key] }))}
                    onToggleDelete={(e) => handleToggleDelete(key, false, e)}
                    onChange={(v) => handleChange(key, v)}
                    onReset={() => handleReset(key, content, false)}
                    onSave={() => handleSave(key, false)}
                  />
                );
              })}
            </div>
          </SortableContext>
        </DndContext>
        {renderAddForm(false, showAddArticle, setShowAddArticle)}
      </div>

      {/* Annexes */}
      <div>
        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Annexes</h4>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd(true)}>
          <SortableContext items={annexKeys} strategy={verticalListSortingStrategy}>
            <div className="space-y-2">
              {annexKeys.map((key) => {
                const tpl = annexMap.get(key);
                const custom = customAnnexMap.get(key);
                if (!tpl && !custom) return null;
                const title = tpl?.title ?? custom?.title ?? '';
                const content = tpl?.content ?? custom?.content ?? '';
                const isCustom = !!custom;
                const isDeleted = deletedAnnexes.includes(key);
                return (
                  <SortableEditorRow
                    key={key}
                    itemKey={key}
                    title={title}
                    label="Annexe"
                    isCustom={isCustom}
                    isExpanded={!!expanded[key]}
                    isDeleted={isDeleted}
                    isDirty={!!dirty[key]}
                    hasOverride={!!annexOverrides[key]}
                    value={getValue(key, content, true)}
                    isPending={saveMutation.isPending}
                    onToggleExpand={() => setExpanded((e) => ({ ...e, [key]: !e[key] }))}
                    onToggleDelete={(e) => handleToggleDelete(key, true, e)}
                    onChange={(v) => handleChange(key, v)}
                    onReset={() => handleReset(key, content, true)}
                    onSave={() => handleSave(key, true)}
                  />
                );
              })}
            </div>
          </SortableContext>
        </DndContext>
        {renderAddForm(true, showAddAnnex, setShowAddAnnex)}
      </div>

      {onRegenerateDraft && (
        <div className="flex justify-end mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <Button
            onClick={onRegenerateDraft}
            disabled={isRegenerating}
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            {isRegenerating ? 'Régénération...' : 'Régénérer le brouillon'}
          </Button>
        </div>
      )}
    </>
  );

  if (inline) return content;
  return <Card className="mb-6">{content}</Card>;
}

// ─── History Timeline ────────────────────────────────────────────────────────

const NOISE_STATUSES = new Set(['configuring_contract', 'draft_generated', 'commercial_validated']);

function HistoryTimeline({
  statusHistory,
}: {
  statusHistory: Array<{ status: ContractRequestStatus; entered_at: string; comment?: string }>;
}) {
  const [showFull, setShowFull] = useState(false);
  const [expandedComments, setExpandedComments] = useState<Set<number>>(new Set());

  const toggleComment = (idx: number) => {
    setExpandedComments((prev) => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  };

  const hiddenCount = statusHistory.filter((e) => NOISE_STATUSES.has(e.status)).length;
  const visibleEntries = showFull
    ? statusHistory.map((e, i) => ({ ...e, originalIndex: i }))
    : statusHistory
        .map((e, i) => ({ ...e, originalIndex: i }))
        .filter((e) => !NOISE_STATUSES.has(e.status));

  return (
    <>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          Historique du contrat
        </h3>
        {hiddenCount > 0 && (
          <button
            onClick={() => setShowFull((v) => !v)}
            className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            {showFull ? 'Vue résumée' : `Voir tout (${statusHistory.length} étapes)`}
          </button>
        )}
      </div>

      {visibleEntries.length > 0 ? (
        <ol className="relative border-l border-gray-200 dark:border-gray-700 space-y-3 ml-2">
          {visibleEntries.map((entry) => {
            const cfg = CONTRACT_STATUS_CONFIG[entry.status as ContractRequestStatus];
            const label =
              entry.status === 'commercial_validated' ? 'Création' : (cfg?.label ?? entry.status);
            const isChanges = entry.status === 'partner_requested_changes';
            const isExpanded = expandedComments.has(entry.originalIndex);

            return (
              <li key={entry.originalIndex} className="ml-4">
                <span className="absolute -left-1.5 mt-1 h-3 w-3 rounded-full border-2 border-white dark:border-gray-800 bg-gray-400 dark:bg-gray-500" />
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cfg?.color ?? 'bg-gray-100 text-gray-700'}`}
                  >
                    {label}
                  </span>
                  <time className="text-xs text-gray-400 dark:text-gray-500">
                    {new Date(entry.entered_at).toLocaleString('fr-FR', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </time>
                  {isChanges && entry.comment && (
                    <button
                      onClick={() => toggleComment(entry.originalIndex)}
                      title="Voir le commentaire du partenaire"
                      className="inline-flex items-center gap-1 text-xs text-orange-600 dark:text-orange-400 hover:text-orange-800 dark:hover:text-orange-200"
                    >
                      <MessageSquare className="h-3.5 w-3.5" />
                      {isExpanded ? 'Masquer' : 'Commentaire'}
                    </button>
                  )}
                </div>
                {isChanges && entry.comment && isExpanded && (
                  <div className="mt-1.5 ml-1 border-l-2 border-orange-300 dark:border-orange-700 pl-3 text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                    {entry.comment}
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="text-sm text-gray-400 dark:text-gray-500">Aucun historique disponible.</p>
      )}
    </>
  );
}


// ── Consultants Section ─────────────────────────────────────────────────────

function ConsultantsSection({ contractRequestId, cr }: { contractRequestId: string; cr: ContractRequest }) {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({ first_name: '', last_name: '', email: '', phone: '' });

  const { data: consultants = [] } = useQuery({
    queryKey: ['contract-consultants', contractRequestId],
    queryFn: () => contractConsultantsApi.list(contractRequestId),
  });

  const addMutation = useMutation({
    mutationFn: () => contractConsultantsApi.add(contractRequestId, addForm),
    onSuccess: () => {
      toast.success('Consultant ajoute.');
      setShowAdd(false);
      setAddForm({ first_name: '', last_name: '', email: '', phone: '' });
      queryClient.invalidateQueries({ queryKey: ['contract-consultants', contractRequestId] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => contractConsultantsApi.remove(contractRequestId, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-consultants', contractRequestId] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const sendChartersMutation = useMutation({
    mutationFn: (consultantId: string) => contractConsultantsApi.sendCharters(contractRequestId, consultantId),
    onSuccess: () => {
      toast.success('Documents chartes generes et envoyes.');
      queryClient.invalidateQueries({ queryKey: ['contract-consultants', contractRequestId] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const STATUS_BADGES: Record<string, { label: string; color: string }> = {
    pending: { label: 'En attente', color: 'bg-gray-100 text-gray-600' },
    sent: { label: 'Envoye', color: 'bg-blue-100 text-blue-700' },
    signed: { label: 'Signe', color: 'bg-green-100 text-green-700' },
  };

  return (
    <Card className="mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <User className="h-4 w-4 text-gray-400" />
          Consultants
        </h3>
        <Button variant="secondary" size="sm" onClick={() => setShowAdd(true)}>
          <Plus className="h-3.5 w-3.5 mr-1" />
          Ajouter
        </Button>
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <input
              type="text"
              placeholder="Prenom *"
              value={addForm.first_name}
              onChange={(e) => setAddForm((f) => ({ ...f, first_name: e.target.value }))}
              className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
            />
            <input
              type="text"
              placeholder="Nom *"
              value={addForm.last_name}
              onChange={(e) => setAddForm((f) => ({ ...f, last_name: e.target.value }))}
              className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
            />
            <input
              type="email"
              placeholder="Email *"
              value={addForm.email}
              onChange={(e) => setAddForm((f) => ({ ...f, email: e.target.value }))}
              className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
            />
            <input
              type="tel"
              placeholder="Telephone"
              value={addForm.phone}
              onChange={(e) => setAddForm((f) => ({ ...f, phone: e.target.value }))}
              className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowAdd(false)} className="text-xs text-gray-400 hover:underline">Annuler</button>
            <Button
              size="sm"
              onClick={() => addMutation.mutate()}
              disabled={!addForm.first_name || !addForm.last_name || !addForm.email || addMutation.isPending}
              isLoading={addMutation.isPending}
            >
              Ajouter
            </Button>
          </div>
        </div>
      )}

      {/* Pre-fill first consultant from CR data */}
      {consultants.length === 0 && !showAdd && cr.consultant_first_name && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          Le consultant principal ({cr.consultant_first_name} {cr.consultant_last_name}) sera ajoute automatiquement.
          <button
            onClick={() => {
              setAddForm({
                first_name: cr.consultant_first_name || '',
                last_name: cr.consultant_last_name || '',
                email: cr.consultant_email || '',
                phone: cr.consultant_phone || '',
              });
              setShowAdd(true);
            }}
            className="ml-2 text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            Ajouter maintenant
          </button>
        </p>
      )}

      {/* Consultants list */}
      {consultants.length > 0 && (
        <div className="space-y-2">
          {consultants.map((c) => {
            const badge = STATUS_BADGES[c.charter_status] || STATUS_BADGES.pending;
            return (
              <div
                key={c.id}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {c.first_name} {c.last_name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {c.email}{c.phone ? ` · ${c.phone}` : ''}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${badge.color}`}>
                    {badge.label}
                  </span>
                  {c.charter_status === 'pending' && (
                    <button
                      onClick={() => sendChartersMutation.mutate(c.id)}
                      disabled={sendChartersMutation.isPending}
                      className="text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 px-2 py-1 rounded transition-colors disabled:opacity-50"
                    >
                      {sendChartersMutation.isPending ? 'Envoi...' : 'Envoyer les chartes'}
                    </button>
                  )}
                  <button
                    onClick={() => removeMutation.mutate(c.id)}
                    className="p-1 rounded text-gray-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                    title="Supprimer"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {consultants.length === 0 && !showAdd && !cr.consultant_first_name && (
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
          Aucun consultant. Ajoutez un consultant pour envoyer les chartes.
        </p>
      )}
    </Card>
  );
}
