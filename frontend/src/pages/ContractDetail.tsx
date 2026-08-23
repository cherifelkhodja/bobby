import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileSignature,
  FileText,
  Send,
  PenTool,
  CheckCircle,
  AlertTriangle,
  Trash2,
  Mail,
  Copy,
  Check,
  Lock,
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
  Eye,
  Upload,
  SkipForward,
} from 'lucide-react';
import { toast } from 'sonner';

import { contractsApi, contractCompaniesApi, contractArticlesApi, contractAnnexesApi, contractConsultantsApi } from '../api/contracts';
import { vigilanceApi } from '../api/vigilance';
import { purchaseOrdersApi } from '../api/purchaseOrders';
import { useAuthStore } from '../stores/authStore';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';
import { DocumentViewerModal } from '../components/vigilance/DocumentViewerModal';
import { ThirdPartyInfoForm } from '../components/contracts/ThirdPartyInfoForm';
import { getErrorMessage } from '../api/client';
import {
  CONTRACT_STATUS_CONFIG,
  PURCHASE_ORDER_STATUS_CONFIG,
  getDocumentBadgeConfig,
} from '../types';
import type { ContractRequestStatus, ContractRequest, VigilanceDocument } from '../types';

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
  // Legacy status: same affordance as reviewing_compliance so a legacy CR isn't stuck.
  configuring_contract: {
    label: 'Générer le brouillon',
    action: 'generate-draft',
    icon: FileSignature,
    variant: 'primary',
  },
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
  // partner_approved: handled separately with signature preview panel
};

// Stepper v2 — 6 étapes pilotées par CONTRACT_STATUS_CONFIG[status].stage
const STEP_LABELS = ['Validation', 'Documents', 'Configuration', 'Review', 'Signature', 'Signé'];

// Chips v2 des documents de vigilance
const DOC_CHIP_CLASS: Record<string, string> = {
  requested: 'st-sla',
  received: 'st-blu',
  validated: 'st-grn',
  rejected: 'st-red',
  expiring_soon: 'st-amb',
  expired: 'st-red',
};

function docChipClass(doc: Pick<VigilanceDocument, 'status' | 'is_unavailable'>): string {
  if (doc.status === 'validated' && doc.is_unavailable) return 'st st-amb';
  return `st ${DOC_CHIP_CLASS[doc.status] ?? 'st-sla'}`;
}

// Cartes sélectionnables « type de tiers » (validation commerciale)
const THIRD_PARTY_TYPE_CARDS = [
  {
    value: 'freelance',
    label: 'Freelance',
    desc: 'Contrat de sous-traitance individuel · Kbis, URSSAF, RC Pro…',
  },
  {
    value: 'sous_traitant',
    label: 'Sous-traitant',
    desc: 'Société avec salariés intervenant sur la mission',
  },
  {
    value: 'portage_salarial',
    label: 'Portage salarial',
    desc: 'Contrat conclu avec la société de portage',
  },
  {
    value: 'salarie',
    label: 'Salarié',
    desc: 'Embauche directe · redirigée vers le process Payfit',
  },
];

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
  const [deleteContractTarget, setDeleteContractTarget] = useState<{ id: string; reference: string } | null>(null);
  const [deleteContractConfirmText, setDeleteContractConfirmText] = useState('');
  const [linkCopied, setLinkCopied] = useState(false);

  const [tempValidatingDocId, setTempValidatingDocId] = useState<string | null>(null);
  const [uploadingDocId, setUploadingDocId] = useState<string | null>(null);
  const [viewingDoc, setViewingDoc] = useState<VigilanceDocument | null>(null);
  const [showSignaturePreview, setShowSignaturePreview] = useState(false);
  const [excludedCharterIds, setExcludedCharterIds] = useState<Set<string>>(new Set());

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
  // Manual entry: ADV enters the tiers info themselves without soliciting the fournisseur.
  const [manualEntry, setManualEntry] = useState(false);
  // Sub-option of manual entry: no vigilance document is collected at all.
  const [skipDocuments, setSkipDocuments] = useState(false);
  const [showSkipDocs, setShowSkipDocs] = useState(false);
  const [skipDocsReason, setSkipDocsReason] = useState('');
  const [showTpForm, setShowTpForm] = useState(false);

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
    // GET /vigilance/.../documents is ADV/admin only — restrict to avoid a silent 403 for commercials.
    enabled: !!cr?.third_party_id && isAdv,
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
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  // ADV approves the draft on the partner's behalf (fully manual flow).
  const approveDraftInternalMutation = useMutation({
    mutationFn: () => contractsApi.approveDraftInternal(id!),
    onSuccess: () => {
      toast.success('Brouillon validé (à la place du partenaire).');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['contracts', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const deleteContractMutation = useMutation({
    mutationFn: ({ contractId }: { contractId: string }) =>
      contractsApi.deleteContract(id!, contractId),
    onSuccess: (data) => {
      toast.success(data.message);
      setDeleteContractTarget(null);
      setDeleteContractConfirmText('');
      queryClient.invalidateQueries({ queryKey: ['contracts', id] });
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
    mutationFn: (docId: string) => vigilanceApi.tempValidateDocument(docId),
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

  const resendDraftEmailMutation = useMutation({
    mutationFn: () => contractsApi.resendDraftEmail(id!),
    onSuccess: () => {
      toast.success('Email de relecture renvoyé.');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const { data: signatureChecklist, refetch: refetchChecklist } = useQuery({
    queryKey: ['signature-checklist', id],
    queryFn: () => contractsApi.getSignatureChecklist(id!),
    // ADV/admin-only endpoint — gate to avoid a 403 for commercials.
    enabled: !!id && isAdv && cr?.status === 'sent_for_signature',
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

  const { data: signaturePreview } = useQuery({
    queryKey: ['signature-preview', id],
    queryFn: () => contractsApi.getSignaturePreview(id!),
    // ADV/admin-only endpoint — gate to avoid a 403 for commercials.
    enabled: !!id && isAdv && cr?.status === 'partner_approved',
  });

  const sendForSignatureMutation = useMutation({
    mutationFn: () => contractsApi.sendForSignature(id!, Array.from(excludedCharterIds)),
    onSuccess: () => {
      toast.success('Contrat envoye en signature.');
      setShowSignaturePreview(false);
      setExcludedCharterIds(new Set());
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const markAsSignedMutation = useMutation({
    mutationFn: () => contractsApi.markAsSigned(id!),
    onSuccess: () => {
      toast.success('Contrat marqué comme signé.');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['contracts', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const configureMutation = useMutation({
    mutationFn: async () => {
      // Defense-in-depth: re-persist the current article/annex editor state (stored
      // in contract_config) BEFORE configure, so a config write can't drop these keys
      // and the regenerated PDF reflects the edits.
      const cfg = (cr?.contract_config as Record<string, unknown>) ?? {};
      await contractsApi.saveArticleOverrides(id!, {
        article_overrides: cfg.article_overrides as Record<string, string> | undefined,
        annex_overrides: cfg.annex_overrides as Record<string, string> | undefined,
        deleted_article_keys: cfg.deleted_article_keys as string[] | undefined,
        deleted_annex_keys: cfg.deleted_annex_keys as string[] | undefined,
        custom_articles: cfg.custom_articles as CustomArticleItem[] | undefined,
        custom_annexes: cfg.custom_annexes as CustomAnnexItem[] | undefined,
        article_order: cfg.article_order as string[] | undefined,
        annex_order: cfg.annex_order as string[] | undefined,
      });
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
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  // Recovery UI: a CR stays "signed" (not "active") when the BoondManager sync failed.
  const retryBoondSyncMutation = useMutation({
    mutationFn: () => contractsApi.retryBoondSync(id!),
    onSuccess: () => {
      toast.success('Synchronisation BoondManager relancée.');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['contracts', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
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
        // When the ADV opts for manual entry, do not email the fournisseur.
        notify_third_party: !manualEntry,
        // Sub-option: skip the vigilance document deposit entirely.
        skip_documents: manualEntry && skipDocuments,
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

  // ADV uploads a compliance document on behalf of the tiers (manual entry).
  const uploadDocMutation = useMutation({
    mutationFn: ({ docId, file }: { docId: string; file: File }) =>
      vigilanceApi.uploadDocument(docId, file),
    onSuccess: () => {
      toast.success('Document déposé.');
      queryClient.invalidateQueries({ queryKey: ['compliance-docs', cr?.third_party_id] });
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
    onSettled: () => setUploadingDocId(null),
  });

  // Saisie « en personne » : ignorer le dépôt des documents de vigilance.
  const skipDocumentsMutation = useMutation({
    mutationFn: () => contractsApi.skipDocuments(id!, skipDocsReason.trim() || undefined),
    onSuccess: () => {
      toast.success('Dépôt des documents ignoré.');
      setShowSkipDocs(false);
      setSkipDocsReason('');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['compliance-docs', cr?.third_party_id] });
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const restoreDocumentsMutation = useMutation({
    mutationFn: () => contractsApi.restoreDocuments(id!),
    onSuccess: () => {
      toast.success('Collecte des documents rétablie.');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['compliance-docs', cr?.third_party_id] });
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  // Advance collecting_documents → reviewing_compliance (manual/ADV path).
  const startComplianceReviewMutation = useMutation({
    mutationFn: () => contractsApi.startComplianceReview(id!),
    onSuccess: () => {
      toast.success('Revue de conformité démarrée.');
      queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const isValidationFormValid =
    validationForm.third_party_type !== '' &&
    validationForm.contact_email !== '';

  const canCancel = cr && isAdv && cr.status !== 'cancelled' && cr.status !== 'signed' && cr.status !== 'active' && cr.status !== 'archived' && cr.status !== 'redirected_payfit';
  const canRollback = cr && isAdv && cr.status !== 'pending_commercial_validation' && cr.status !== 'cancelled' && cr.status !== 'archived' && cr.status !== 'active';

  const prePartnerStatuses = new Set([
    'reviewing_compliance',
    'compliance_blocked',
    'configuring_contract', // Legacy status — allow a legacy CR to reach the config/draft form.
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

  const consultantName = [cr.consultant_first_name, cr.consultant_last_name]
    .filter(Boolean)
    .join(' ');
  const statusChipClass = `st ${statusConfig?.color ?? 'bg-sla-bg text-sla-fg'}`;
  const issuingCompany =
    companies.find(
      (c) =>
        c.id === (cr.contract_config as Record<string, unknown> | null)?.company_id ||
        c.id === cr.company_id,
    ) ?? companies.find((c) => c.is_default);

  // Stepper v2 — stage 0 (annulée / Payfit) : aucune progression.
  const stage = statusConfig?.stage ?? 0;
  const stageBlocked = statusConfig?.group === 'blocked';
  const stepFillPct = stage === 0 ? 0 : Math.round(((stage === 6 ? 5 : stage - 1) / 5) * 84);
  const stepNodeClass = (step: number): string => {
    if (stage === 0) return 'nd';
    if (stage === 6 || step < stage) return 'nd d';
    if (step === stage) return stageBlocked ? 'nd bl' : 'nd cur';
    return 'nd';
  };

  const isPendingValidation = isCommercialOrAdmin && cr.status === 'pending_commercial_validation';

  // Documents de vigilance
  const vigDocs = complianceDocs?.documents ?? [];
  const validatedDocsCount = vigDocs.filter((d) => d.status === 'validated').length;
  const docsBarRed =
    cr.status === 'compliance_blocked' ||
    vigDocs.some((d) => d.status === 'rejected' || d.status === 'expired');

  // Saisie « en personne » : le dépôt des documents a été volontairement ignoré.
  const documentsSkipped = cr.documents_skipped;
  const showVigilanceCard =
    isAdv &&
    !documentsSkipped &&
    vigDocs.length > 0 &&
    hasReachedStatus(cr.status, 'collecting_documents');
  const showSkippedDocsCard =
    isAdv && documentsSkipped && hasReachedStatus(cr.status, 'collecting_documents');
  // Le rétablissement n'a de sens que tant que la conformité est encore en jeu.
  const canRestoreDocuments =
    cr.status === 'collecting_documents' ||
    cr.status === 'reviewing_compliance' ||
    cr.status === 'compliance_blocked';
  const showTpInfoCard =
    isAdv && !!complianceDocs && hasReachedStatus(cr.status, 'collecting_documents');
  const showConfigLocked = isAdv && cr.status === 'collecting_documents';
  const showConsultantsSection = isAdv && hasReachedStatus(cr.status, 'signed');
  const showLinkActions =
    isAdv &&
    !!cr.portal_url &&
    (cr.status === 'collecting_documents' ||
      cr.status === 'compliance_blocked' ||
      cr.status === 'draft_sent_to_partner');

  const hasLeftColumn =
    showVigilanceCard ||
    showSkippedDocsCard ||
    showConfigForm ||
    showConfigLocked ||
    showTpInfoCard ||
    showConsultantsSection ||
    cr.status === 'sent_for_signature';

  const copyPortalLink = () => {
    navigator.clipboard.writeText(cr.portal_url!);
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2000);
  };

  return (
    <div>
      {/* Fil d'ariane */}
      <button
        type="button"
        onClick={() => navigate('/contracts')}
        className="bc block cursor-pointer !text-mut2 hover:!text-mut"
      >
        ← Contrats / Demandes / {cr.display_reference}
      </button>

      {/* Entête */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="h1">
              {cr.display_reference}
              {consultantName && ` · ${consultantName}`}
            </h1>
            <span className={statusChipClass}>
              <span className="dot" />
              {statusConfig?.label ?? cr.status_display}
            </span>
            {issuingCompany && (
              <span
                className="st"
                style={{
                  color: issuingCompany.color_code,
                  backgroundColor: `${issuingCompany.color_code}15`,
                }}
              >
                <span className="dot" />
                {issuingCompany.name}
              </span>
            )}
          </div>
          {(cr.mission_title || cr.boond_positioning_id) && (
            <p className="sub">
              {[
                cr.mission_title,
                cr.boond_positioning_id ? `positionnement Boond #${cr.boond_positioning_id}` : null,
              ]
                .filter(Boolean)
                .join(' · ')}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {showLinkActions && (
            <Button
              variant="secondary"
              onClick={copyPortalLink}
              leftIcon={
                linkCopied ? (
                  <Check className="h-3.5 w-3.5 text-grn-fg" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )
              }
            >
              {linkCopied ? 'Copié !' : 'Copier le lien magique'}
            </Button>
          )}
          {isAdv &&
            !documentsSkipped &&
            (cr.status === 'collecting_documents' || cr.status === 'compliance_blocked') && (
              <Button
                variant="secondary"
                onClick={() => resendCollectionEmailMutation.mutate()}
                disabled={resendCollectionEmailMutation.isPending}
                isLoading={resendCollectionEmailMutation.isPending}
                leftIcon={<Mail className="h-3.5 w-3.5" />}
              >
                Relancer le tiers
              </Button>
            )}
          {isAdv && cr.status === 'draft_sent_to_partner' && (
            <Button
              variant="secondary"
              onClick={() => resendDraftEmailMutation.mutate()}
              disabled={resendDraftEmailMutation.isPending}
              isLoading={resendDraftEmailMutation.isPending}
              leftIcon={<Mail className="h-3.5 w-3.5" />}
            >
              Relancer le tiers
            </Button>
          )}
          {isAdv && cr.status === 'collecting_documents' && !documentsSkipped && (
            <>
              <Button
                variant="secondary"
                onClick={() => setShowSkipDocs(true)}
                leftIcon={<SkipForward className="h-3.5 w-3.5" />}
              >
                Passer le dépôt
              </Button>
              <Button
                onClick={() => startComplianceReviewMutation.mutate()}
                disabled={startComplianceReviewMutation.isPending}
                isLoading={startComplianceReviewMutation.isPending}
                leftIcon={<CheckCircle className="h-3.5 w-3.5" />}
              >
                Démarrer la revue
              </Button>
            </>
          )}
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
              leftIcon={<Download className="h-3.5 w-3.5" />}
            >
              Contrat signé
            </Button>
          )}
          {actionConfig && (
            <Button
              onClick={() => actionMutation.mutate(actionConfig.action)}
              disabled={actionMutation.isPending}
              leftIcon={<actionConfig.icon className="h-3.5 w-3.5" />}
            >
              {actionMutation.isPending ? 'En cours…' : actionConfig.label}
            </Button>
          )}
          {isAdv && (cr.status === 'draft_generated' || cr.status === 'draft_sent_to_partner') && (
            <Button
              variant="secondary"
              onClick={() => approveDraftInternalMutation.mutate()}
              disabled={approveDraftInternalMutation.isPending}
              title="Valider le brouillon sans passer par le fournisseur"
              leftIcon={<CheckCircle className="h-3.5 w-3.5" />}
            >
              {approveDraftInternalMutation.isPending ? 'Validation…' : 'Valider à la place du partenaire'}
            </Button>
          )}
          {cr.status === 'partner_approved' && isAdv && (
            <Button
              onClick={() => setShowSignaturePreview(true)}
              disabled={showSignaturePreview}
              leftIcon={<PenTool className="h-3.5 w-3.5" />}
            >
              Envoyer en signature
            </Button>
          )}
          {canRollback && (
            <Button
              variant="secondary"
              onClick={() => rollbackMutation.mutate()}
              disabled={rollbackMutation.isPending}
              leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
            >
              {rollbackMutation.isPending ? 'Retour…' : 'État précédent'}
            </Button>
          )}
          {canCancel && (
            <Button
              variant="secondary"
              onClick={() => setShowCancelModal(true)}
              leftIcon={<Trash2 className="h-3.5 w-3.5" />}
            >
              Annuler
            </Button>
          )}
        </div>
      </div>

      {/* Passer le dépôt des documents — confirmation + justification tracée */}
      {isAdv && showSkipDocs && (
        <div className="card mt-3">
          <h3 className="ct">Passer le dépôt des documents</h3>
          <p className="cs">
            Les documents de vigilance ne seront ni demandés ni attendus, et les emplacements
            encore vides seront retirés du dossier. La demande passe en revue de conformité avec
            une dérogation tracée dans l'activité.
          </p>
          <label className="f-lab mt-3.5" htmlFor="skip-docs-reason">
            Justification (optionnelle)
          </label>
          <textarea
            id="skip-docs-reason"
            value={skipDocsReason}
            onChange={(e) => setSkipDocsReason(e.target.value)}
            placeholder="Ex. : documents reçus et vérifiés hors Bobby…"
            className="f-ta"
            rows={2}
          />
          <div className="flex gap-2 mt-3">
            <Button
              size="sm"
              onClick={() => skipDocumentsMutation.mutate()}
              disabled={skipDocumentsMutation.isPending}
              isLoading={skipDocumentsMutation.isPending}
            >
              Confirmer
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setShowSkipDocs(false);
                setSkipDocsReason('');
              }}
            >
              Annuler
            </Button>
          </div>
        </div>
      )}

      {/* Conformité bloquée — alerte + dérogation tracée */}
      {isAdv && cr.status === 'compliance_blocked' && (
        <>
          <div className="alert red">
            <AlertTriangle className="h-[18px] w-[18px] shrink-0" />
            <span>
              Génération de contrat bloquée — les documents de vigilance ne sont pas tous validés.
              Validez-les dans la carte « Documents de vigilance », ou forcez la conformité avec une
              justification tracée.
            </span>
            {!showOverride && (
              <button type="button" className="alink" onClick={() => setShowOverride(true)}>
                Forcer la conformité →
              </button>
            )}
          </div>
          {showOverride && (
            <div className="card mt-3">
              <label className="f-lab" htmlFor="override-reason">
                Justification de la dérogation *
              </label>
              <textarea
                id="override-reason"
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="Raison du forçage (min. 10 caractères)…"
                className="f-ta"
                rows={2}
              />
              <div className="flex gap-2 mt-3">
                <Button
                  size="sm"
                  onClick={() => overrideMutation.mutate()}
                  disabled={overrideReason.length < 10 || overrideMutation.isPending}
                  isLoading={overrideMutation.isPending}
                >
                  Confirmer la dérogation
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
        </>
      )}

      {/* Signé mais synchronisation BoondManager en attente */}
      {isAdv && cr.status === 'signed' && (
        <div className="alert">
          <AlertTriangle className="h-[18px] w-[18px] shrink-0" />
          <span>
            Le contrat est signé mais n'a pas encore été synchronisé dans BoondManager. Relancez la
            synchronisation pour finaliser la mise en actif.
          </span>
          <button
            type="button"
            className="alink"
            onClick={() => retryBoondSyncMutation.mutate()}
            disabled={retryBoondSyncMutation.isPending}
          >
            {retryBoondSyncMutation.isPending ? 'Synchronisation…' : 'Relancer la synchronisation →'}
          </button>
        </div>
      )}

      {/* Carte d'entête : meta + stepper 6 étapes */}
      <div className="hdcard">
        <div className="meta">
          <div>
            <p className="ml">Partenaire</p>
            <p className="mv">{cr.third_party_name ?? complianceDocs?.company_name ?? '—'}</p>
          </div>
          {complianceDocs?.siren && (
            <div>
              <p className="ml">SIREN</p>
              <p className="mv font-mono">{complianceDocs.siren}</p>
            </div>
          )}
          <div>
            <p className="ml">Client final</p>
            <p className="mv">{cr.client_name ?? '—'}</p>
          </div>
          <div>
            <p className="ml">TJM achat</p>
            <p className="mv">{cr.daily_rate != null ? `${cr.daily_rate} €` : '—'}</p>
          </div>
          <div>
            <p className="ml">Démarrage</p>
            <p className="mv">{cr.start_date ? formatDate(cr.start_date) : '—'}</p>
          </div>
          <div>
            <p className="ml">Commercial</p>
            <p className="mv">{cr.commercial_name ?? '—'}</p>
          </div>
          <div>
            <p className="ml">Contact contrat</p>
            <p className="mv">{cr.contractualization_contact_email ?? '—'}</p>
          </div>
        </div>
        <div className="steps">
          <div className="track" />
          <div className="tfill" style={{ width: `${stepFillPct}%` }} />
          <div className="nodes">
            {STEP_LABELS.map((label, i) => (
              <div key={label} className="stw">
                <span className={stepNodeClass(i + 1)} />
                <p className="lb">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {isPendingValidation ? (
        /* ── Validation commerciale (screen « Formulaire commercial ») ─────── */
        <div className="cols">
          <div>
            <div className="card">
              <h3 className="ct">Type de tiers</h3>
              <p className="cs mb-3.5">
                Détermine les documents de vigilance et le modèle de contrat
              </p>
              <div className="tcards !grid-cols-2">
                {THIRD_PARTY_TYPE_CARDS.map((t) => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() =>
                      setValidationForm((f) => ({ ...f, third_party_type: t.value }))
                    }
                    className={`tcard text-left ${validationForm.third_party_type === t.value ? 'on' : ''}`}
                  >
                    <span className="tt block">{t.label}</span>
                    <span className="td2 block">{t.desc}</span>
                  </button>
                ))}
              </div>

              {validationForm.third_party_type === 'salarie' && (
                <div className="alert !mt-0 mb-4">
                  <AlertTriangle className="h-[18px] w-[18px] shrink-0" />
                  <span>
                    Cette demande sera redirigée vers le process Payfit — Bobby ne génère pas de
                    contrat de travail.
                  </span>
                </div>
              )}

              <div className="f-grid">
                <div className="col-span-2">
                  <label className="f-lab" htmlFor="cv-company">
                    Société émettrice
                  </label>
                  <select
                    id="cv-company"
                    value={validationForm.company_id}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, company_id: e.target.value }))
                    }
                    className="f-in !px-2.5"
                  >
                    <option value="">Sélectionner...</option>
                    {companies.filter((c) => c.is_active).map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.code})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="f-lab" htmlFor="cv-contact-email">
                    Email du contact contractualisation *
                  </label>
                  <input
                    id="cv-contact-email"
                    type="email"
                    value={validationForm.contact_email}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, contact_email: e.target.value }))
                    }
                    className="f-in"
                  />
                  <p className="f-hint">Recevra le lien magique de collecte documentaire</p>
                </div>
              </div>

              <p className="ml mt-5 mb-3">Consultant</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="f-lab" htmlFor="cv-civility">
                    Civilité
                  </label>
                  <select
                    id="cv-civility"
                    value={validationForm.consultant_civility}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, consultant_civility: e.target.value }))
                    }
                    className="f-in !px-2.5"
                  >
                    <option value="">-</option>
                    <option value="M.">M.</option>
                    <option value="Mme">Mme</option>
                  </select>
                </div>
                <div>
                  <label className="f-lab" htmlFor="cv-first-name">
                    Prénom
                  </label>
                  <input
                    id="cv-first-name"
                    type="text"
                    value={validationForm.consultant_first_name}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, consultant_first_name: e.target.value }))
                    }
                    className="f-in"
                  />
                </div>
                <div>
                  <label className="f-lab" htmlFor="cv-last-name">
                    Nom
                  </label>
                  <input
                    id="cv-last-name"
                    type="text"
                    value={validationForm.consultant_last_name}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, consultant_last_name: e.target.value }))
                    }
                    className="f-in"
                  />
                </div>
              </div>
              <div className="f-grid mt-4">
                <div>
                  <label className="f-lab" htmlFor="cv-email">
                    Email professionnel
                  </label>
                  <input
                    id="cv-email"
                    type="email"
                    value={validationForm.consultant_email}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, consultant_email: e.target.value }))
                    }
                    placeholder="prenom.nom@societe.fr"
                    className="f-in"
                  />
                </div>
                <div>
                  <label className="f-lab" htmlFor="cv-phone">
                    Téléphone
                  </label>
                  <input
                    id="cv-phone"
                    type="tel"
                    value={validationForm.consultant_phone}
                    onChange={(e) =>
                      setValidationForm((f) => ({ ...f, consultant_phone: e.target.value }))
                    }
                    placeholder="+33 6 00 00 00 00"
                    className="f-in"
                  />
                </div>
              </div>

              {/* Saisie manuelle : l'ADV renseigne tout sans solliciter le fournisseur */}
              <label className="flex items-start gap-2.5 mt-5 p-3 rounded-[10px] bg-srf2 border border-lin2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={manualEntry}
                  onChange={(e) => {
                    setManualEntry(e.target.checked);
                    if (!e.target.checked) setSkipDocuments(false);
                  }}
                  className="mt-0.5 rounded border-lin text-pri focus:ring-pri"
                />
                <span className="text-[12.5px] text-mut leading-relaxed">
                  <span className="font-semibold text-ink block">
                    Je saisis les informations moi-même
                  </span>
                  Aucun email ne sera envoyé au fournisseur. Vous renseignerez ensuite l'identité,
                  les contacts et les documents du tiers depuis cette page.
                </span>
              </label>

              {/* Sous-option : saisie en personne sans aucune collecte documentaire */}
              {manualEntry && (
                <label className="flex items-start gap-2.5 mt-2 ml-6 p-3 rounded-[10px] bg-srf2 border border-lin2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={skipDocuments}
                    onChange={(e) => setSkipDocuments(e.target.checked)}
                    className="mt-0.5 rounded border-lin text-pri focus:ring-pri"
                  />
                  <span className="text-[12.5px] text-mut leading-relaxed">
                    <span className="font-semibold text-ink block">
                      Sans dépôt des documents de vigilance
                    </span>
                    Aucun document ne sera demandé ni attendu. La demande passe directement en
                    revue de conformité avec une dérogation tracée dans l'activité.
                  </span>
                </label>
              )}

              <div className="flex items-center justify-between gap-2 mt-5">
                <span className="cs !mt-0">* champs requis</span>
                <Button
                  onClick={() => validateCommercialMutation.mutate()}
                  disabled={!isValidationFormValid || validateCommercialMutation.isPending}
                  isLoading={validateCommercialMutation.isPending}
                  leftIcon={<CheckCircle className="h-3.5 w-3.5" />}
                >
                  {manualEntry
                    ? skipDocuments
                      ? 'Valider sans collecte documentaire'
                      : 'Valider et saisir les informations'
                    : 'Valider'}
                </Button>
              </div>
            </div>
          </div>

          <div>
            <div className="card">
              <h3 className="ct mb-3.5">Ce qui se passe ensuite</h3>
              <div className="ev">
                <span className="evd" />
                <span className="evl" />
                <p className="evt">Recherche du tiers par SIREN</p>
                <p className="evs">Dossier existant réutilisé si le tiers est déjà connu</p>
              </div>
              <div className="ev">
                <span className="evd" />
                <span className="evl" />
                <p className="evt">Vérification de conformité</p>
                <p className="evs">Si conforme → configuration directe du contrat</p>
              </div>
              <div className="ev">
                <span className="evd" />
                <span className="evl" />
                <p className="evt">Collecte documentaire</p>
                <p className="evs">Lien magique envoyé au contact · relances J+3, J+7, J+14</p>
              </div>
              <div className="ev !pb-0">
                <span className="evd" />
                <p className="evt">Configuration puis signature</p>
                <p className="evs">Draft DOCX → review partenaire → YouSign → push Boond</p>
              </div>
            </div>
            <div className="card mt-4">
              <HistoryTimeline statusHistory={cr.status_history} />
            </div>
          </div>
        </div>
      ) : (
        /* ── Corps standard : colonne gauche (dossier) / colonne droite (activité) ── */
        <div className={hasLeftColumn ? 'cols' : 'mt-4'}>
          {hasLeftColumn && (
            <div className="space-y-4">
              {/* Dépôt des documents ignoré (saisie en personne) */}
              {showSkippedDocsCard && (
                <div className="card">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="ct">Documents de vigilance</h3>
                      <p className="cs">Dépôt ignoré — saisie en personne</p>
                    </div>
                    <span className="st st-amb shrink-0">
                      <span className="dot" />
                      Non collectés
                    </span>
                  </div>
                  <div className="lock mt-3">
                    <SkipForward className="h-4 w-4 shrink-0 mt-px" />
                    <span>
                      Aucun document n'est demandé au tiers pour cette demande. La conformité est
                      levée par dérogation — la justification est tracée dans l'activité.
                    </span>
                  </div>
                  {cr.compliance_override_reason && (
                    <div className="quote mt-3 whitespace-pre-wrap">
                      {cr.compliance_override_reason}
                    </div>
                  )}
                  {complianceDocs && !complianceDocs.company_info_submitted && (
                    <div className="alert !mt-3 !py-2.5 !text-[12.5px]">
                      <AlertTriangle className="h-4 w-4 shrink-0" />
                      <span>
                        L'identité du tiers n'est pas encore renseignée — complétez « Informations
                        société » avant de générer le brouillon, sinon le contrat sortira sans les
                        mentions légales du tiers.
                      </span>
                    </div>
                  )}
                  {canRestoreDocuments && (
                    <div className="flex gap-2 mt-3.5">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => restoreDocumentsMutation.mutate()}
                        disabled={restoreDocumentsMutation.isPending}
                        isLoading={restoreDocumentsMutation.isPending}
                        leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
                      >
                        Rétablir le dépôt
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {/* Documents de vigilance */}
              {showVigilanceCard && (
                <div className="card">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="ct">Documents de vigilance</h3>
                      <p className="cs">Collecte et validation des documents du tiers</p>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="docs">
                        {validatedDocsCount}/{vigDocs.length}
                      </span>
                      <div className="dbar ml-auto">
                        <div
                          className={`dfill ${docsBarRed ? 'r' : ''}`}
                          style={{
                            width: `${vigDocs.length ? Math.round((validatedDocsCount / vigDocs.length) * 100) : 0}%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                  <div className="mt-3">
                    {vigDocs.map((doc) => {
                      const docBadge = getDocumentBadgeConfig(doc);
                      const canValidate = isAdv && doc.status === 'received';
                      const canTempValidate = isAdv && doc.status === 'requested' && doc.is_unavailable;
                      // Champs d'auto-analyse éditables (les dates/validité sont gérées à part) :
                      // sans champ éditable, le bouton « Modifier » ouvrirait un formulaire vide.
                      const editableAutoCheckEntries = Object.entries(doc.auto_check_results ?? {})
                        .filter(([k]) => !['is_valid', 'document_date', 'expiry_date'].includes(k));
                      const isTempValidating = tempValidatingDocId === doc.id;
                      const isRejecting = rejectingDocId === doc.id;
                      return (
                        <div key={doc.id} className="border-t border-lin2 py-3 first:border-t-0 first:pt-0">
                          <div className="flex items-center gap-3">
                            <div className="dico">
                              <FileText className="h-4 w-4" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="dn truncate">{doc.document_type_display}</p>
                              <p className="ds truncate">
                                {doc.file_name ?? 'En attente de dépôt'}
                                {doc.expires_at &&
                                  ` · expire le ${new Date(doc.expires_at).toLocaleDateString('fr-FR')}`}
                              </p>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              {doc.s3_key && (
                                <button
                                  type="button"
                                  onClick={() => setViewingDoc(doc)}
                                  className="inline-flex items-center gap-1 text-[12px] font-semibold text-prit hover:bg-pris px-2 py-1 rounded-md transition-colors"
                                >
                                  <Eye className="h-3.5 w-3.5" /> Visualiser
                                </button>
                              )}
                              {(doc.status === 'requested' || doc.status === 'rejected' || doc.status === 'expired') && (
                                <label className="inline-flex items-center gap-1 text-[12px] font-semibold text-prit hover:bg-pris px-2 py-1 rounded-md transition-colors cursor-pointer">
                                  <Upload className="h-3.5 w-3.5" />
                                  {uploadingDocId === doc.id ? 'Dépôt…' : 'Déposer'}
                                  <input
                                    type="file"
                                    accept=".pdf,.jpg,.jpeg,.png"
                                    className="hidden"
                                    disabled={uploadingDocId === doc.id}
                                    onChange={(e) => {
                                      const file = e.target.files?.[0];
                                      if (file) {
                                        setUploadingDocId(doc.id);
                                        uploadDocMutation.mutate({ docId: doc.id, file });
                                      }
                                      e.target.value = '';
                                    }}
                                  />
                                </label>
                              )}
                              {canValidate ? (
                                <>
                                  <Button
                                    size="sm"
                                    onClick={() => validateDocMutation.mutate(doc.id)}
                                    disabled={validateDocMutation.isPending}
                                  >
                                    Valider
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => setRejectingDocId(doc.id)}
                                  >
                                    Rejeter
                                  </Button>
                                </>
                              ) : (
                                <span className={docChipClass(doc)}>
                                  <span className="dot" />
                                  {docBadge.label}
                                </span>
                              )}
                            </div>
                          </div>
                          {doc.is_unavailable && doc.unavailability_reason && (
                            <p className="mt-2 ml-[46px] text-[12px] text-amb-fg bg-amb-bg rounded-md px-2.5 py-1.5">
                              Indisponible : {doc.unavailability_reason}
                            </p>
                          )}
                          {doc.rejection_reason && (
                            <p className="mt-2 ml-[46px] text-[12px] text-red-fg bg-red-bg rounded-md px-2.5 py-1.5">
                              Motif de rejet : {doc.rejection_reason}
                            </p>
                          )}
                          {isRejecting && (
                            <div className="mt-2 ml-[46px] flex items-center gap-2">
                              <input
                                type="text"
                                value={rejectReason}
                                onChange={(e) => setRejectReason(e.target.value)}
                                placeholder="Motif du rejet…"
                                className="f-in !h-[30px] !text-[12px] flex-1"
                                autoFocus
                              />
                              <Button
                                size="sm"
                                variant="danger"
                                onClick={() => rejectDocMutation.mutate({ docId: doc.id, reason: rejectReason })}
                                disabled={!rejectReason.trim() || rejectDocMutation.isPending}
                              >
                                Confirmer
                              </Button>
                              <button
                                type="button"
                                onClick={() => { setRejectingDocId(null); setRejectReason(''); }}
                                className="text-[12px] text-mut2 hover:text-mut"
                              >
                                Annuler
                              </button>
                            </div>
                          )}
                          {canTempValidate && !isRejecting && (
                            <div className="mt-2 ml-[46px]">
                              {!isTempValidating ? (
                                <button
                                  type="button"
                                  onClick={() => setTempValidatingDocId(doc.id)}
                                  className="text-[12px] font-semibold text-prit hover:underline"
                                >
                                  Valider temporairement
                                </button>
                              ) : (
                                <div className="flex items-center gap-2 text-[12px]">
                                  <span className="text-mut">Confirmer ?</span>
                                  <button
                                    type="button"
                                    onClick={() => tempValidateMutation.mutate(doc.id)}
                                    disabled={tempValidateMutation.isPending}
                                    className="font-semibold text-grn-fg hover:underline disabled:opacity-50"
                                  >
                                    Oui
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setTempValidatingDocId(null)}
                                    className="text-mut2 hover:underline"
                                  >
                                    Non
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                          {/* Auto-check results + edit/re-extract */}
                          {doc.auto_check_results && Object.keys(doc.auto_check_results).length > 0 && (
                            <div className="mt-2 ml-[46px] rounded-[10px] bg-srf2 border border-lin2 px-3 py-2.5 text-[12px]">
                              <div className="flex items-center justify-between mb-1">
                                <span className="ml !mb-0">Vérifications auto</span>
                                <div className="flex gap-2">
                                  {isAdv && (
                                    <>
                                      {editableAutoCheckEntries.length > 0 && (
                                        <button
                                          type="button"
                                          onClick={() => setEditingAutoCheck({ docId: doc.id, data: { ...doc.auto_check_results } as Record<string, string> })}
                                          className="text-[12px] font-medium text-prit hover:underline"
                                        >
                                          Modifier
                                        </button>
                                      )}
                                      <button
                                        type="button"
                                        onClick={() => reExtractMutation.mutate(doc.id)}
                                        disabled={reExtractMutation.isPending}
                                        className="text-[12px] font-medium text-prit hover:underline disabled:opacity-50"
                                      >
                                        {reExtractMutation.isPending ? 'Analyse…' : 'Re-analyser'}
                                      </button>
                                    </>
                                  )}
                                </div>
                              </div>
                              {Object.entries(doc.auto_check_results).filter(([k]) => !['is_valid', 'document_date', 'expiry_date'].includes(k)).map(([key, val]) => (
                                <div key={key} className="flex gap-2 text-mut">
                                  <span className="text-mut2 capitalize">{key.replace(/_/g, ' ')} :</span>
                                  <span className="font-medium text-ink">{String(val || '—')}</span>
                                </div>
                              ))}
                            </div>
                          )}
                          {/* Inline edit form */}
                          {editingAutoCheck?.docId === doc.id && (
                            <div className="mt-2 ml-[46px] rounded-[10px] bg-pris border border-[color-mix(in_oklab,var(--pri)_25%,transparent)] px-3 py-2.5 space-y-2">
                              {Object.entries(editingAutoCheck.data).filter(([k]) => !['is_valid', 'document_date', 'expiry_date'].includes(k)).map(([key, val]) => (
                                <div key={key} className="flex items-center gap-2">
                                  <label className="text-[12px] text-mut w-28 capitalize shrink-0">{key.replace(/_/g, ' ')}</label>
                                  <input
                                    type="text"
                                    value={val ?? ''}
                                    onChange={(e) => setEditingAutoCheck((prev) => prev ? { ...prev, data: { ...prev.data, [key]: e.target.value } } : null)}
                                    className="f-in !h-[30px] !text-[12px]"
                                  />
                                </div>
                              ))}
                              <div className="flex gap-2 justify-end">
                                <button
                                  type="button"
                                  onClick={() => setEditingAutoCheck(null)}
                                  className="text-[12px] text-mut2 hover:text-mut"
                                >
                                  Annuler
                                </button>
                                <button
                                  type="button"
                                  onClick={() => updateAutoCheckMutation.mutate({ docId: doc.id, data: editingAutoCheck.data })}
                                  disabled={updateAutoCheckMutation.isPending}
                                  className="text-[12px] font-semibold text-prit hover:underline disabled:opacity-50"
                                >
                                  {updateAutoCheckMutation.isPending ? 'Sauvegarde…' : 'Sauvegarder'}
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Commentaire du partenaire (review) */}
              {isAdv && cr.status === 'partner_requested_changes' && (
                <div className="card">
                  <div className="flex items-center gap-2.5">
                    <AlertTriangle className="h-4 w-4 text-amb-fg shrink-0" />
                    <h3 className="ct">Le partenaire demande des modifications</h3>
                  </div>
                  {latestContract?.partner_comments ? (
                    <div className="quote whitespace-pre-wrap">{latestContract.partner_comments}</div>
                  ) : (
                    <p className="notec mt-2">Aucun commentaire fourni.</p>
                  )}
                  <p className="cs mt-2.5">
                    Modifiez les articles/annexes ci-dessous ou la configuration, puis re-générez le
                    brouillon.
                  </p>
                </div>
              )}

              {/* Configuration du contrat — verrouillée pendant la collecte */}
              {showConfigLocked && (
                <div className="card">
                  <h3 className="ct">Configuration du contrat</h3>
                  <div className="lock">
                    <Lock className="h-4 w-4 shrink-0 mt-px" />
                    <span>
                      Conditions de paiement, articles optionnels et annexes se débloquent quand les
                      documents requis sont validés. Validez les documents puis démarrez la revue de
                      conformité.
                    </span>
                  </div>
                  <div className="flex gap-2 mt-3.5">
                    <Button disabled>Générer le brouillon</Button>
                  </div>
                </div>
              )}

              {/* Configuration du contrat — formulaire complet */}
              {showConfigForm && (
                <div className="card">
                  <h3 className="ct">Configuration du contrat</h3>
                  <p className="cs">Conditions, articles et annexes repris dans le brouillon DOCX</p>

                  {cr.compliance_override && (
                    <div className="alert red !mt-3 !py-2.5 !text-[12.5px]">
                      <span>
                        Conformité débloquée par dérogation — justification tracée dans l'activité.
                      </span>
                    </div>
                  )}

                  <div className="f-grid mt-4">
                    <div className="col-span-2">
                      <label className="f-lab" htmlFor="cfg-company">
                        Société émettrice du contrat
                      </label>
                      <select
                        id="cfg-company"
                        value={configForm.company_id}
                        onChange={(e) => setConfigForm((f) => ({ ...f, company_id: e.target.value }))}
                        className="f-in !px-2.5"
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
                        <p className="f-hint">
                          Aucune société configurée — rendez-vous dans{' '}
                          <strong>Administration &gt; Sociétés</strong> pour en ajouter.
                        </p>
                      )}
                    </div>
                    <div>
                      <label className="f-lab" htmlFor="cfg-payment">
                        Délai de paiement
                      </label>
                      <select
                        id="cfg-payment"
                        value={configForm.payment_terms}
                        onChange={(e) => setConfigForm((f) => ({ ...f, payment_terms: e.target.value }))}
                        className="f-in !px-2.5"
                      >
                        <option value="immediate">Comptant</option>
                        <option value="net_30">30 jours</option>
                        <option value="net_45_eom">45 jours fin de mois</option>
                      </select>
                    </div>
                    <div>
                      <label className="f-lab" htmlFor="cfg-invoice">
                        Dépôt des factures
                      </label>
                      <select
                        id="cfg-invoice"
                        value={configForm.invoice_submission_method}
                        onChange={(e) => setConfigForm((f) => ({ ...f, invoice_submission_method: e.target.value }))}
                        className="f-in !px-2.5"
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

                  {/* Articles optionnels */}
                  {optionalArticles.length > 0 && (
                    <div className="mt-5 pt-4 border-t border-lin2">
                      <p className="ml mb-1">Articles optionnels</p>
                      <p className="f-hint !mt-0 mb-3">
                        Cochez les articles à inclure dans ce contrat. Les articles non cochés seront
                        exclus du PDF.
                      </p>
                      <div className="space-y-2">
                        {optionalArticles.map((article) => {
                          const isIncluded = !configForm.excluded_optional_article_keys.includes(article.article_key);
                          return (
                            <label
                              key={article.article_key}
                              className="flex items-center gap-2.5 cursor-pointer group"
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
                                className="h-4 w-4 rounded border-lin text-pri focus:ring-pri"
                              />
                              <span className="text-[12.5px] text-mut group-hover:text-ink transition-colors">
                                {article.title}
                              </span>
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Conditions particulières */}
                  <div className="mt-5 pt-4 border-t border-lin2">
                    <label className="f-lab" htmlFor="cfg-special">
                      Conditions particulières
                    </label>
                    <textarea
                      id="cfg-special"
                      value={configForm.special_conditions}
                      onChange={(e) => setConfigForm((f) => ({ ...f, special_conditions: e.target.value }))}
                      placeholder="Clauses libres, conditions spécifiques à cette mission…"
                      className="f-ta"
                      rows={3}
                    />
                  </div>

                  {/* Éditeur d'articles / annexes (inline) */}
                  {activeArticles.length > 0 && (
                    <div className="mt-5 pt-4 border-t border-lin2">
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

                  <div className="flex justify-end mt-5">
                    <Button
                      onClick={() => configureMutation.mutate()}
                      disabled={configureMutation.isPending}
                      isLoading={configureMutation.isPending}
                      leftIcon={<FileSignature className="h-3.5 w-3.5" />}
                    >
                      {latestContract ? 'Régénérer le brouillon' : 'Générer le brouillon'}
                    </Button>
                  </div>
                </div>
              )}

              {/* Signature en cours — checklist des documents signés */}
              {cr.status === 'sent_for_signature' && (
                <div className="card">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="ct">Documents à signer</h3>
                      <p className="cs">Uploadez chaque document signé pour valider la signature.</p>
                    </div>
                    <span className="st st-ind shrink-0">
                      <span className="dot" />
                      Signature
                    </span>
                  </div>

                  {isAdv && signatureChecklist && (
                    <div className="mt-2">
                      {/* Partner documents */}
                      {signatureChecklist.filter(i => i.signer_role === 'partner').length > 0 && (
                        <>
                          <p className="ml mt-3 mb-1">Partenaire</p>
                          {signatureChecklist.filter(i => i.signer_role === 'partner').map(item => (
                            <div key={item.id} className="doc">
                              <div className="dico">
                                {item.uploaded ? (
                                  <CheckCircle className="h-4 w-4 text-grn-fg" />
                                ) : (
                                  <span className="h-4 w-4 rounded-full border-2 border-lin block" />
                                )}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="dn truncate">{item.label}</p>
                                {item.file_name && <p className="ds truncate">{item.file_name}</p>}
                              </div>
                              <label className="text-[12px] font-semibold text-prit hover:underline cursor-pointer shrink-0">
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
                        </>
                      )}

                      {/* Consultant documents */}
                      {signatureChecklist.filter(i => i.signer_role === 'consultant').length > 0 && (
                        <>
                          <p className="ml mt-3 mb-1">Collaborateur</p>
                          {signatureChecklist.filter(i => i.signer_role === 'consultant').map(item => (
                            <div key={item.id} className="doc">
                              <div className="dico">
                                {item.uploaded ? (
                                  <CheckCircle className="h-4 w-4 text-grn-fg" />
                                ) : (
                                  <span className="h-4 w-4 rounded-full border-2 border-lin block" />
                                )}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="dn truncate">{item.label}</p>
                                {item.file_name && <p className="ds truncate">{item.file_name}</p>}
                              </div>
                              <label className="text-[12px] font-semibold text-prit hover:underline cursor-pointer shrink-0">
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
                        </>
                      )}

                      {/* Validate button */}
                      <div className="pt-4">
                        <Button
                          size="sm"
                          disabled={!signatureChecklist.every(i => i.uploaded) || markAsSignedMutation.isPending}
                          onClick={() => markAsSignedMutation.mutate()}
                          isLoading={markAsSignedMutation.isPending}
                          leftIcon={<CheckCircle className="h-3.5 w-3.5" />}
                        >
                          Valider la signature ({signatureChecklist.filter(i => i.uploaded).length}/{signatureChecklist.length})
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Informations société du tiers */}
              {showTpInfoCard && complianceDocs && (
                <div className="card">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 className="ct">Informations société</h3>
                      <p className="cs">Identité et contacts du tiers</p>
                    </div>
                    {!showTpForm && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setShowTpForm(true)}
                        leftIcon={<Pencil className="h-3.5 w-3.5" />}
                      >
                        {complianceDocs.company_info_submitted ? 'Modifier' : 'Saisir les informations'}
                      </Button>
                    )}
                  </div>

                  {showTpForm && (
                    <div className="mt-4">
                      <ThirdPartyInfoForm
                        contractRequestId={cr.id}
                        initial={complianceDocs}
                        onSaved={() => {
                          setShowTpForm(false);
                          queryClient.invalidateQueries({ queryKey: ['compliance-docs', cr.third_party_id] });
                          queryClient.invalidateQueries({ queryKey: ['contract-request', id] });
                        }}
                        onCancel={() => setShowTpForm(false)}
                      />
                    </div>
                  )}

                  {!showTpForm && (
                  <>
                  <div className="cfgrid">
                    {cr.third_party_type && (
                      <div>
                        <p className="ml">Type de tiers</p>
                        <p className="mv">
                          {cr.third_party_type === 'freelance' ? 'Freelance / EI' : cr.third_party_type === 'sous_traitant' ? 'Sous-traitant' : cr.third_party_type === 'portage_salarial' ? 'Portage salarial' : 'Salarié'}
                        </p>
                      </div>
                    )}
                    {complianceDocs.company_name && (
                      <div>
                        <p className="ml">Raison sociale</p>
                        <p className="mv">{complianceDocs.company_name}</p>
                      </div>
                    )}
                    {complianceDocs.legal_form && (
                      <div>
                        <p className="ml">Forme juridique</p>
                        <p className="mv">{complianceDocs.legal_form}</p>
                      </div>
                    )}
                    {complianceDocs.capital && (
                      <div>
                        <p className="ml">Capital</p>
                        <p className="mv">{complianceDocs.capital} €</p>
                      </div>
                    )}
                    {complianceDocs.siren && (
                      <div>
                        <p className="ml">SIREN</p>
                        <p className="mv font-mono">{complianceDocs.siren}</p>
                      </div>
                    )}
                    {complianceDocs.siret && (
                      <div>
                        <p className="ml">SIRET</p>
                        <p className="mv font-mono">{complianceDocs.siret}</p>
                      </div>
                    )}
                    {(complianceDocs.rcs_city || complianceDocs.rcs_number) && (
                      <div>
                        <p className="ml">RCS</p>
                        <p className="mv">
                          {[complianceDocs.rcs_city, complianceDocs.rcs_number].filter(Boolean).join(' ')}
                        </p>
                      </div>
                    )}
                    {complianceDocs.head_office_address && (
                      <div className="col-span-3">
                        <p className="ml">Siège social</p>
                        <p className="mv">{complianceDocs.head_office_address}</p>
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
                      <div className="bg-srf2 border border-lin2 rounded-[10px] p-3">
                        <p className="ml mb-1.5">{title}</p>
                        {name && <p className="mv !text-[13px]">{name}</p>}
                        {email && <p className="ds !mt-1">{email}</p>}
                        {phone && <p className="ds !mt-0.5">{phone}</p>}
                        {!name && !email && !phone && <p className="ds !mt-0 italic">Non renseigné</p>}
                      </div>
                    );

                    return (
                      <div className="border-t border-lin2 mt-4 pt-4">
                        <p className="ml mb-2.5">Contacts</p>
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
                    <div className="border-t border-lin2 mt-4 pt-4">
                      <p className="ml mb-2.5">Consultant</p>
                      <div className="bg-srf2 border border-lin2 rounded-[10px] p-3 inline-block min-w-[250px]">
                        <p className="mv !text-[13px]">
                          {[cr.consultant_civility, cr.consultant_first_name, cr.consultant_last_name].filter(Boolean).join(' ')}
                        </p>
                        {cr.consultant_email && <p className="ds !mt-1">{cr.consultant_email}</p>}
                        {cr.consultant_phone && <p className="ds !mt-0.5">{cr.consultant_phone}</p>}
                      </div>
                    </div>
                  )}
                  </>
                  )}
                </div>
              )}

              {/* Consultants (chartes) — visible après signature */}
              {showConsultantsSection && (
                <ConsultantsSection contractRequestId={cr.id} cr={cr} />
              )}

              {/* Missions rattachées à ce contrat cadre */}
              <PurchaseOrdersSection contractRequestId={cr.id} />
            </div>
          )}

          {/* Colonne droite : activité + documents contractuels */}
          <div className="space-y-4">
            <div className="card">
              <HistoryTimeline statusHistory={cr.status_history} />
            </div>

            {contracts && contracts.length > 0 && (
              <div className="card">
                <h3 className="ct mb-1">Documents contractuels</h3>
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
                    <div key={c.id} className="doc">
                      <div className="dico">
                        <FileSignature className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`dn truncate ${isProvisional ? '!text-mut' : ''}`}>
                          {isSigned
                            ? `${c.reference} (Signed)`
                            : isFinal
                              ? c.reference
                              : `${c.reference} v${c.version}`
                          }
                        </p>
                        <p className="ds truncate">
                          {formatDate(c.created_at)}{isSigned ? ` — signé le ${formatDate(c.signed_at!)}` : ''}
                        </p>
                      </div>
                      <span className={`st shrink-0 ${isSigned ? 'st-grn' : isFinal ? 'st-blu' : 'st-sla'}`}>
                        <span className="dot" />
                        {isSigned ? 'Signé' : isFinal ? 'Définitif' : 'Brouillon'}
                      </span>
                      <button
                        type="button"
                        onClick={async () => {
                          try {
                            const url = await contractsApi.getContractDownloadUrl(cr.id, c.id, isSigned ? 'signed' : 'draft');
                            window.open(url, '_blank');
                          } catch {
                            toast.error('Impossible de telecharger.');
                          }
                        }}
                        className="p-1.5 rounded-md text-mut2 hover:text-prit hover:bg-pris transition-colors shrink-0"
                        title={`Télécharger ${c.reference}.pdf`}
                      >
                        <Download className="h-4 w-4" />
                      </button>
                      {user?.role === 'admin' && (
                        <button
                          type="button"
                          onClick={() => setDeleteContractTarget({ id: c.id, reference: c.reference })}
                          className="p-1.5 rounded-md text-mut2 hover:text-redt hover:bg-red-bg transition-colors shrink-0"
                          title="Supprimer"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Document viewer modal (vigilance documents) */}
      {viewingDoc && (
        <DocumentViewerModal
          doc={viewingDoc}
          onClose={() => setViewingDoc(null)}
          onValidate={() => {
            validateDocMutation.mutate(viewingDoc.id);
            setViewingDoc(null);
          }}
          onRejectStart={() => {
            setRejectingDocId(viewingDoc.id);
            setViewingDoc(null);
          }}
          isValidating={validateDocMutation.isPending}
        />
      )}

      {/* Partner approved — signature documents selection modal */}
      <Modal
        isOpen={showSignaturePreview && cr.status === 'partner_approved'}
        onClose={() => setShowSignaturePreview(false)}
        title="Documents inclus dans la signature"
      >
        <div className="space-y-3">
          <p className="notec">
            Le contrat cadre est toujours inclus. Sélectionnez les documents supplémentaires à faire
            signer.
          </p>

          {/* Contract (always included, not toggleable) */}
          <div className="flex items-center gap-2.5 p-2.5 rounded-[10px] bg-srf2 border border-lin2">
            <input type="checkbox" checked disabled className="rounded border-lin" />
            <span className="text-[12.5px] font-semibold text-ink">Contrat cadre</span>
            <span className="text-[11px] text-mut2">(obligatoire)</span>
          </div>

          {!signaturePreview && (
            <p className="notec py-2 text-center">Chargement…</p>
          )}

          {signaturePreview && signaturePreview.length === 0 && (
            <p className="notec py-2 text-center">Aucun document supplémentaire configuré pour cette société.</p>
          )}

          {/* Partner documents */}
          {signaturePreview && signaturePreview.filter(i => i.signer_role === 'partner').length > 0 && (
            <div>
              <p className="ml !text-blu-fg mb-1">Partenaire</p>
              {signaturePreview.filter(i => i.signer_role === 'partner').map(item => (
                <label key={item.charter_template_id} className="flex items-center gap-2.5 p-2 rounded-[10px] hover:bg-srf2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!excludedCharterIds.has(item.charter_template_id)}
                    onChange={(e) => {
                      const next = new Set(excludedCharterIds);
                      if (e.target.checked) {
                        next.delete(item.charter_template_id);
                      } else {
                        next.add(item.charter_template_id);
                      }
                      setExcludedCharterIds(next);
                    }}
                    className="rounded border-lin text-pri focus:ring-pri"
                  />
                  <span className="text-[12.5px] text-ink flex-1">{item.label}</span>
                  <span className="text-[11px] text-mut2">{item.document_kind === 'charter_engagement' ? 'Signature' : 'AR'}</span>
                </label>
              ))}
            </div>
          )}

          {/* Consultant documents */}
          {signaturePreview && signaturePreview.filter(i => i.signer_role === 'consultant').length > 0 && (
            <div>
              <p className="ml !text-ind-fg mb-1">Collaborateur</p>
              {signaturePreview.filter(i => i.signer_role === 'consultant').map(item => (
                <label key={item.charter_template_id} className="flex items-center gap-2.5 p-2 rounded-[10px] hover:bg-srf2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!excludedCharterIds.has(item.charter_template_id)}
                    onChange={(e) => {
                      const next = new Set(excludedCharterIds);
                      if (e.target.checked) {
                        next.delete(item.charter_template_id);
                      } else {
                        next.add(item.charter_template_id);
                      }
                      setExcludedCharterIds(next);
                    }}
                    className="rounded border-lin text-pri focus:ring-pri"
                  />
                  <span className="text-[12.5px] text-ink flex-1">{item.label}</span>
                  <span className="text-[11px] text-mut2">{item.document_kind === 'charter_engagement' ? 'Signature' : 'AR'}</span>
                </label>
              ))}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-3 border-t border-lin2">
            <Button variant="secondary" size="sm" onClick={() => setShowSignaturePreview(false)}>
              Annuler
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => sendForSignatureMutation.mutate()}
              disabled={sendForSignatureMutation.isPending}
              isLoading={sendForSignatureMutation.isPending}
              leftIcon={<PenTool className="h-3.5 w-3.5" />}
            >
              Confirmer
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete contract confirmation modal (double verification) */}
      <Modal
        isOpen={!!deleteContractTarget}
        onClose={() => { setDeleteContractTarget(null); setDeleteContractConfirmText(''); }}
        title="Supprimer le contrat"
      >
        {deleteContractTarget && (
          <div className="space-y-4">
            <p className="notec">
              Supprimer définitivement le contrat{' '}
              <span className="font-semibold text-ink">{deleteContractTarget.reference}</span> ?
            </p>
            <p className="text-[12.5px] text-redt">
              Cette action est irréversible. Les fichiers PDF associés seront aussi supprimés.
            </p>
            <div>
              <label className="f-lab" htmlFor="delete-contract-confirm">
                Tapez{' '}
                <code className="px-1 py-0.5 bg-srf2 border border-lin2 rounded text-redt font-mono">
                  {deleteContractTarget.reference}
                </code>{' '}
                pour confirmer
              </label>
              <input
                id="delete-contract-confirm"
                type="text"
                value={deleteContractConfirmText}
                onChange={(e) => setDeleteContractConfirmText(e.target.value)}
                placeholder={deleteContractTarget.reference}
                className="f-in font-mono"
                autoFocus
              />
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-lin2">
              <Button variant="secondary" size="sm" onClick={() => { setDeleteContractTarget(null); setDeleteContractConfirmText(''); }}>
                Annuler
              </Button>
              <Button
                variant="danger"
                size="sm"
                disabled={deleteContractConfirmText !== deleteContractTarget.reference || deleteContractMutation.isPending}
                isLoading={deleteContractMutation.isPending}
                onClick={() => deleteContractMutation.mutate({ contractId: deleteContractTarget.id })}
                leftIcon={<Trash2 className="h-3.5 w-3.5" />}
              >
                Supprimer
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Cancel confirmation modal */}
      <Modal
        isOpen={showCancelModal}
        onClose={() => setShowCancelModal(false)}
        title="Annuler la demande de contrat"
      >
        <div className="space-y-4">
          <p className="notec">
            Voulez-vous vraiment annuler la demande{' '}
            <span className="font-semibold text-ink">{cr.display_reference}</span> ?
          </p>
          <p className="text-[12.5px] text-redt">Cette action est irréversible.</p>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="secondary"
              onClick={() => setShowCancelModal(false)}
              disabled={cancelMutation.isPending}
            >
              Non, garder
            </Button>
            <Button
              variant="danger"
              onClick={() => cancelMutation.mutate()}
              isLoading={cancelMutation.isPending}
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
      className={`border rounded-[10px] overflow-hidden bg-sur ${isDragging ? 'shadow-lg z-10 relative' : ''} ${isDeleted ? 'border-[color-mix(in_oklab,var(--red-fg)_35%,transparent)] opacity-60' : 'border-lin'}`}
    >
      <div className="flex items-center">
        {/* Drag handle */}
        <button
          type="button"
          {...attributes}
          {...listeners}
          className="flex-shrink-0 px-2 py-3 text-mut2 hover:text-mut cursor-grab active:cursor-grabbing touch-none bg-srf2"
          title="Glisser pour réordonner"
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <button
          type="button"
          className={`flex-1 flex items-center justify-between px-4 py-3 text-left transition-colors ${isDeleted ? 'bg-red-bg' : 'bg-srf2 hover:bg-lin2'}`}
          onClick={() => !isDeleted && onToggleExpand()}
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="ml !mb-0 flex-shrink-0">{label}</span>
            <span className={`text-[13px] font-semibold truncate ${isDeleted ? 'line-through text-mut2' : 'text-ink'}`}>
              {title}
            </span>
            {isCustom && (
              <span className="st st-grn !text-[10.5px] !px-2 !py-0.5 flex-shrink-0">ajouté</span>
            )}
            {isDeleted && (
              <span className="st st-red !text-[10.5px] !px-2 !py-0.5 flex-shrink-0">supprimé</span>
            )}
            {!isDeleted && !isCustom && hasOverride && !isDirty && (
              <span className="st st-amb !text-[10.5px] !px-2 !py-0.5 flex-shrink-0">
                <Pencil className="h-3 w-3" />
                modifié
              </span>
            )}
            {!isDeleted && isDirty && (
              <span className="st st-blu !text-[10.5px] !px-2 !py-0.5 flex-shrink-0">non sauvegardé</span>
            )}
          </div>
          {!isDeleted && (isExpanded ? <ChevronUp className="h-4 w-4 text-mut2 flex-shrink-0" /> : <ChevronDown className="h-4 w-4 text-mut2 flex-shrink-0" />)}
        </button>
        <button
          type="button"
          title={isDeleted ? 'Restaurer' : 'Supprimer du PDF'}
          onClick={onToggleDelete}
          disabled={isPending}
          className={`px-3 py-3 flex-shrink-0 transition-colors ${isDeleted ? 'text-grn-fg bg-red-bg' : 'text-mut2 hover:text-redt bg-srf2'}`}
        >
          {isDeleted ? <RotateCcw className="h-4 w-4" /> : <Trash2 className="h-4 w-4" />}
        </button>
      </div>

      {isExpanded && !isDeleted && (
        <div className="p-4 bg-sur border-t border-lin2">
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="f-ta font-mono !text-[12.5px]"
            rows={10}
          />
          <div className="flex items-center justify-between mt-2">
            {!isCustom ? (
              <button
                type="button"
                onClick={onReset}
                className="inline-flex items-center gap-1.5 text-[12px] text-mut2 hover:text-mut"
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
          placeholder={isAnnex ? 'Titre de la nouvelle annexe…' : 'Titre du nouvel article…'}
          className="f-in flex-1"
          onKeyDown={(e) => e.key === 'Enter' && handleAddCustom(isAnnex)}
          autoFocus
        />
        <Button size="sm" onClick={() => handleAddCustom(isAnnex)} disabled={!newTitle.trim() || saveMutation.isPending}>
          Ajouter
        </Button>
        <button
          type="button"
          onClick={() => { setShow(false); setNewTitle(''); }}
          className="text-[12px] text-mut2 hover:text-mut"
        >
          Annuler
        </button>
      </div>
    ) : (
      <button
        type="button"
        onClick={() => { setShow(true); setNewTitle(''); }}
        className="inline-flex items-center gap-1.5 mt-2 text-[12px] font-semibold text-prit hover:underline"
      >
        <Plus className="h-3.5 w-3.5" />
        {isAnnex ? 'Ajouter une annexe' : 'Ajouter un article'}
      </button>
    )
  );

  const content = (
    <>
      <p className="ml mb-1">Édition des articles et annexes</p>
      <p className="f-hint !mt-0 mb-4">
        Glissez pour réordonner, modifiez le contenu ou ajoutez des articles/annexes pour ce contrat
        uniquement.
      </p>

      {/* Articles */}
      <div className="mb-4">
        <h4 className="ml mb-2">Articles</h4>
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
        <h4 className="ml mb-2">Annexes</h4>
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
        <div className="flex justify-end mt-4 pt-4 border-t border-lin2">
          <Button
            onClick={onRegenerateDraft}
            disabled={isRegenerating}
            leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
          >
            {isRegenerating ? 'Régénération…' : 'Régénérer le brouillon'}
          </Button>
        </div>
      )}
    </>
  );

  if (inline) return content;
  return <div className="card mb-4">{content}</div>;
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
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
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
      <div className="flex items-center justify-between mb-3.5">
        <h3 className="ct">Activité</h3>
        {hiddenCount > 0 && (
          <button
            type="button"
            onClick={() => setShowFull((v) => !v)}
            className="text-[12px] font-medium text-prit hover:underline"
          >
            {showFull ? 'Vue résumée' : `Voir tout (${statusHistory.length} étapes)`}
          </button>
        )}
      </div>

      {visibleEntries.length > 0 ? (
        <div>
          {visibleEntries.map((entry, idx) => {
            const cfg = CONTRACT_STATUS_CONFIG[entry.status as ContractRequestStatus];
            const label =
              entry.status === 'commercial_validated' ? 'Création' : (cfg?.label ?? entry.status);
            const isChanges = entry.status === 'partner_requested_changes';
            const isExpanded = expandedComments.has(entry.originalIndex);
            const isLast = idx === visibleEntries.length - 1;

            return (
              <div key={entry.originalIndex} className={`ev ${isLast ? '!pb-0' : ''}`}>
                <span className="evd" />
                {!isLast && <span className="evl" />}
                <p className="evt">{label}</p>
                <p className="evs">
                  {new Date(entry.entered_at).toLocaleString('fr-FR', {
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                  {isChanges && entry.comment && (
                    <button
                      type="button"
                      onClick={() => toggleComment(entry.originalIndex)}
                      title="Voir le commentaire du partenaire"
                      className="inline-flex items-center gap-1 ml-2 font-semibold text-amb-fg hover:underline"
                    >
                      <MessageSquare className="h-3 w-3" />
                      {isExpanded ? 'Masquer' : 'Commentaire'}
                    </button>
                  )}
                </p>
                {isChanges && entry.comment && isExpanded && (
                  <div className="quote whitespace-pre-wrap !mt-1.5">{entry.comment}</div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <p className="notec">Aucun historique disponible.</p>
      )}
    </>
  );
}


// ── Consultants Section ─────────────────────────────────────────────────────

const CONSULTANT_CHARTER_CHIPS: Record<string, { label: string; cls: string }> = {
  pending: { label: 'En attente', cls: 'st-sla' },
  sent: { label: 'Envoyé', cls: 'st-blu' },
  signed: { label: 'Signé', cls: 'st-grn' },
};

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

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="ct">Consultants</h3>
          <p className="cs">Chartes à faire signer aux intervenants</p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setShowAdd(true)}
          leftIcon={<Plus className="h-3.5 w-3.5" />}
        >
          Ajouter
        </Button>
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="mt-4 p-3.5 rounded-[10px] bg-srf2 border border-lin2">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <input
              type="text"
              placeholder="Prénom *"
              value={addForm.first_name}
              onChange={(e) => setAddForm((f) => ({ ...f, first_name: e.target.value }))}
              className="f-in !h-[34px] !text-[12.5px]"
            />
            <input
              type="text"
              placeholder="Nom *"
              value={addForm.last_name}
              onChange={(e) => setAddForm((f) => ({ ...f, last_name: e.target.value }))}
              className="f-in !h-[34px] !text-[12.5px]"
            />
            <input
              type="email"
              placeholder="Email *"
              value={addForm.email}
              onChange={(e) => setAddForm((f) => ({ ...f, email: e.target.value }))}
              className="f-in !h-[34px] !text-[12.5px]"
            />
            <input
              type="tel"
              placeholder="Téléphone"
              value={addForm.phone}
              onChange={(e) => setAddForm((f) => ({ ...f, phone: e.target.value }))}
              className="f-in !h-[34px] !text-[12.5px]"
            />
          </div>
          <div className="flex justify-end items-center gap-3">
            <button
              type="button"
              onClick={() => setShowAdd(false)}
              className="text-[12px] text-mut2 hover:text-mut"
            >
              Annuler
            </button>
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
        <p className="notec mt-3">
          Le consultant principal ({cr.consultant_first_name} {cr.consultant_last_name}) sera ajouté automatiquement.
          <button
            type="button"
            onClick={() => {
              setAddForm({
                first_name: cr.consultant_first_name || '',
                last_name: cr.consultant_last_name || '',
                email: cr.consultant_email || '',
                phone: cr.consultant_phone || '',
              });
              setShowAdd(true);
            }}
            className="ml-2 font-semibold text-prit hover:underline"
          >
            Ajouter maintenant
          </button>
        </p>
      )}

      {/* Consultants list */}
      {consultants.length > 0 && (
        <div className="mt-2">
          {consultants.map((c) => {
            const chip = CONSULTANT_CHARTER_CHIPS[c.charter_status] || CONSULTANT_CHARTER_CHIPS.pending;
            return (
              <div key={c.id} className="doc">
                <div className="dico">
                  <User className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="dn truncate">
                    {c.first_name} {c.last_name}
                  </p>
                  <p className="ds truncate">
                    {c.email}{c.phone ? ` · ${c.phone}` : ''}
                  </p>
                </div>
                <span className={`st shrink-0 ${chip.cls}`}>
                  <span className="dot" />
                  {chip.label}
                </span>
                {c.charter_status === 'pending' && (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => sendChartersMutation.mutate(c.id)}
                    disabled={sendChartersMutation.isPending}
                  >
                    {sendChartersMutation.isPending ? 'Envoi…' : 'Envoyer les chartes'}
                  </Button>
                )}
                <button
                  type="button"
                  onClick={() => removeMutation.mutate(c.id)}
                  className="p-1 rounded-md text-mut2 hover:text-redt hover:bg-red-bg transition-colors shrink-0"
                  title="Supprimer"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {consultants.length === 0 && !showAdd && !cr.consultant_first_name && (
        <p className="notec text-center py-4">
          Aucun consultant. Ajoutez un consultant pour envoyer les chartes.
        </p>
      )}
    </div>
  );
}


/**
 * Bons de commande de CE contrat cadre.
 *
 * Un contrat cadre porte N missions dans le temps. Le filtre porte sur le
 * cadre et non sur le fournisseur : celui-ci peut être sous contrat avec
 * plusieurs sociétés du groupe, et les missions d'une société n'ont rien à
 * faire dans la fiche d'une autre.
 */
function PurchaseOrdersSection({ contractRequestId }: { contractRequestId: string }) {
  const navigate = useNavigate();

  const { data } = useQuery({
    queryKey: ['purchase-orders', 'by-framework', contractRequestId],
    queryFn: () =>
      purchaseOrdersApi.list({ contract_request_id: contractRequestId, limit: 100 }),
  });

  const orders = data?.items ?? [];

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3.5">
        <h3 className="ct">Bons de commande</h3>
        <button type="button" className="alink" onClick={() => navigate('/contracts/bdc')}>
          Tout voir →
        </button>
      </div>

      {orders.length === 0 ? (
        <p className="notec text-center py-4">
          Aucune mission sous ce contrat cadre pour le moment.
        </p>
      ) : (
        <div className="space-y-2">
          {orders.map((po) => (
            <button
              key={po.id}
              type="button"
              onClick={() => navigate(`/contracts/bdc/${po.id}`)}
              className="w-full text-left flex items-center justify-between gap-3 p-2.5 rounded-lg border border-lin hover:bg-srf2 transition-colors"
            >
              <div className="min-w-0">
                <p className="nm truncate">
                  <span className="ref mr-2">{po.reference}</span>
                  {po.mission_title || 'Mission à préciser'}
                </p>
                <p className="ns truncate">
                  {po.consultant_name || 'Consultant à identifier'}
                  {po.client_name ? ` · ${po.client_name}` : ''}
                </p>
              </div>
              <span className={`st ${PURCHASE_ORDER_STATUS_CONFIG[po.status].color} shrink-0`}>
                <span className="dot" />
                {PURCHASE_ORDER_STATUS_CONFIG[po.status].label}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
