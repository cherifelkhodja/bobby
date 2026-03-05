import { useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import PhoneInput from 'react-phone-number-input';
import 'react-phone-number-input/style.css';
import {
  ShieldCheck,
  Upload,
  FileText,
  CheckCircle,
  XCircle,
  X,
  Clock,
  AlertTriangle,
  Building2,
  Loader2,
  PenLine,
  ChevronLeft,
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

// ─── Progress Stepper ───────────────────────────────────────────────────────

type StepStatus = 'done' | 'current' | 'upcoming';

interface Step {
  label: string;
  icon: React.ElementType;
  status: StepStatus;
}

function PortalStepper({ steps }: { steps: Step[] }) {
  return (
    <div className="max-w-3xl mx-auto mb-8">
      <div className="flex items-start">
        {steps.map((step, i) => {
          const Icon = step.icon;
          const isLast = i === steps.length - 1;
          return (
            <div key={i} className={`flex items-start ${isLast ? '' : 'flex-1'} min-w-0`}>
              {/* Step bubble + label */}
              <div className="flex flex-col items-center flex-shrink-0">
                <div
                  className={[
                    'flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all',
                    step.status === 'done'
                      ? 'bg-green-500 border-green-500 text-white shadow-sm'
                      : step.status === 'current'
                      ? 'bg-primary-600 border-primary-600 text-white shadow-md shadow-primary-200 dark:shadow-primary-900/40'
                      : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-600 text-gray-300 dark:text-gray-500',
                  ].join(' ')}
                >
                  {step.status === 'done' ? (
                    <CheckCircle className="h-5 w-5" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>
                <span
                  className={[
                    'mt-2 text-xs font-medium text-center leading-tight max-w-[72px]',
                    step.status === 'done'
                      ? 'text-green-600 dark:text-green-400'
                      : step.status === 'current'
                      ? 'text-primary-600 dark:text-primary-400'
                      : 'text-gray-400 dark:text-gray-500',
                  ].join(' ')}
                >
                  {step.label}
                </span>
              </div>
              {/* Connector — aligned with center of the 40px bubble (mt-5 = 20px) */}
              {!isLast && (
                <div
                  className={[
                    'flex-1 h-0.5 mx-3 self-start mt-5 transition-colors',
                    step.status === 'done'
                      ? 'bg-green-400'
                      : 'bg-gray-200 dark:bg-gray-700',
                  ].join(' ')}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Portal ─────────────────────────────────────────────────────────────────

export default function Portal() {
  const { token } = useParams<{ token: string }>();
  const queryClient = useQueryClient();
  const [forceStep, setForceStep] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(() => {
    // Persist submitted state so magic link always returns to confirmation page
    return token ? localStorage.getItem(`portal-submitted-${token}`) === 'true' : false;
  });

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

  const hasSiren = !!portalInfo.third_party.company_info_submitted;
  const allDocsEmpty = !!docsData && docsData.documents.length === 0;
  const allDocsHandled =
    !!docsData &&
    docsData.documents.length > 0 &&
    docsData.documents.every((d) => {
      // Temporarily validated (no real file) still requires a real upload
      if (d.status === 'validated' && !d.file_name) return false;
      return (
        ['received', 'validated', 'expiring_soon'].includes(d.status) ||
        (d.is_unavailable && !!d.unavailability_reason)
      );
    });

  const hasExpiredDoc =
    !!docsData && docsData.documents.some((d) => d.status === 'expired');

  // Natural step: 0=infos société, 1=documents, 2=confirmation (post-submit)
  const naturalStep = isDocumentUpload
    ? !hasSiren ? 0 : submitted ? 2 : 1
    : 0;

  // displayStep: forceStep allows going back; clamp to [0, naturalStep]
  const displayStep = forceStep !== null ? Math.min(forceStep, naturalStep) : naturalStep;

  const buildStepStatus = (stepIndex: number): StepStatus => {
    if (stepIndex < displayStep) return 'done';
    if (stepIndex === displayStep) return 'current';
    // Steps beyond displayStep: show natural server status
    if (isDocumentUpload) {
      if (stepIndex === 1) return hasSiren ? (submitted || allDocsEmpty ? 'done' : 'upcoming') : 'upcoming';
      if (stepIndex === 2) return 'upcoming';
    }
    return 'upcoming';
  };

  const steps: Step[] = isDocumentUpload
    ? [
        { label: 'Infos société', icon: Building2, status: buildStepStatus(0) },
        { label: 'Documents',     icon: Upload,    status: buildStepStatus(1) },
        { label: 'Vérification',  icon: ShieldCheck, status: buildStepStatus(2) },
      ]
    : [
        { label: 'Relecture', icon: FileText, status: 'current' },
        { label: 'Signature', icon: PenLine,  status: 'upcoming' },
      ];

  const goBack = () => setForceStep(displayStep - 1);
  const goForward = () => setForceStep(null); // snap back to natural step

  return (
    <PortalLayout>
      {/* Header */}
      <div className="max-w-3xl mx-auto mb-8">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 px-5 py-4 flex items-center gap-4 shadow-sm">
          <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center">
            <Building2 className="h-5 w-5 text-primary-600 dark:text-primary-400" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide">Portail partenaire</p>
            <h1 className="text-base font-semibold text-gray-900 dark:text-white truncate">
              {portalInfo.third_party.company_name ?? portalInfo.third_party.contact_email}
            </h1>
          </div>
        </div>
      </div>

      {/* Progress stepper */}
      <PortalStepper steps={steps} />

      {/* Back button — hidden after submission */}
      {displayStep > 0 && !submitted && (
        <div className="max-w-3xl mx-auto mb-4">
          <button
            onClick={goBack}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            Retour
          </button>
        </div>
      )}

      {/* Company info form — step 0 (keep mounted to preserve state when going back) */}
      {isDocumentUpload && displayStep !== 2 && (
        <div className={displayStep !== 0 ? 'hidden' : undefined}>
          <CompanyInfoForm
            token={token!}
            thirdPartyType={portalInfo.third_party.type}
            initialData={portalInfo.third_party}
            onSuccess={() => {
              queryClient.invalidateQueries({ queryKey: ['portal', token] });
              queryClient.invalidateQueries({ queryKey: ['portal-documents', token] });
              goForward();
            }}
          />
        </div>
      )}

      {/* Document upload section — step 1 */}
      {isDocumentUpload && displayStep === 1 && docsData && (
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
                <ShieldCheck className="h-10 w-10 text-gray-400 mx-auto mb-3" />
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Aucun document demandé pour le moment
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Vous serez notifié si des documents sont nécessaires.
                </p>
              </Card>
            )}
          </div>

          {docsData.documents.length > 0 && (
            <SubmitDocumentsButton
              token={token!}
              enabled={allDocsHandled && !hasExpiredDoc}
              expiredBlocked={hasExpiredDoc}
              onSubmitted={() => {
                localStorage.setItem(`portal-submitted-${token}`, 'true');
                setSubmitted(true);
                setForceStep(null);
              }}
            />
          )}
        </div>
      )}

      {/* Verification message — step 2 (all docs uploaded) */}
      {isDocumentUpload && displayStep === 2 && (
        <div className="max-w-3xl mx-auto">
          <Card className="text-center py-10">
            <ShieldCheck className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Documents transmis avec succès
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Vos documents sont en cours de vérification par notre équipe.
              Vous serez contacté si des informations complémentaires sont nécessaires.
            </p>
          </Card>
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

const INPUT_CLS =
  'w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500';

// INSEE nomenclature — catégories juridiques (source : INPI / FORME_JURIDIQUE_LABELS backend)
const LEGAL_FORM_COMMON = [
  'SAS',
  'SASU',
  'SARL',
  'EURL',
  'SA',
  'SNC',
  'Entrepreneur individuel',
  'EARL',
];
const LEGAL_FORM_ALL = [
  'Agriculteur exploitant',
  'Artisan',
  'Association agréée',
  'Association de droit local Alsace-Moselle',
  'Association des Alsaciens-Mosellans',
  "Association d'insertion par l'activité économique",
  'Association déclarée de bienfaisance ou de charité',
  'Association intermédiaire',
  'Association loi 1901',
  'Association loi 1901 (autre)',
  'Association loi 1905 (culte)',
  'Association reconnue d\'utilité publique',
  'Association sportive',
  'Association syndicale libre',
  'Autre organisme professionnel',
  'Autre personne morale de droit privé',
  'Autre personne physique',
  'Autre SA',
  'Autre syndicat',
  "Caisse d'épargne et de prévoyance",
  'Comité central d\'entreprise',
  'Comité d\'établissement',
  'Comité de groupe',
  'Comité interentreprises ou sectoriel d\'activité',
  'Comité social et économique',
  'Commerçant',
  'Coopérative',
  'EARL',
  'Entrepreneur individuel',
  'EURL',
  'EURL (gérant associé)',
  'EURL (gérant non associé)',
  'Fondation',
  'Fonds commun de placement',
  'Fonds de pension',
  'GAEC',
  'GEIE',
  'GIE',
  'Groupement d\'investissement immobilier',
  'Groupement de propriétaires',
  'Indivision avec personne morale',
  'Indivision entre personnes physiques',
  'Mutuelle',
  'Organisme d\'investissement alternatif (OIA)',
  'Organisme de placement collectif en valeurs mobilières (OPCVM)',
  'Organisme gérant des régimes de protection sociale',
  'Organisme mutualiste',
  'Organisme professionnel',
  'SA',
  'SA (autre)',
  'SA à conseil d\'administration',
  'SA à directoire',
  "SA coopérative",
  'SA coopérative à conseil d\'administration',
  "SA coopérative à directoire",
  "SA d'attribution d'immeubles en jouissance à temps partagé",
  'SARL',
  'SARL (avant 1985)',
  'SARL coopérative',
  'SAS',
  'SASU',
  'SCA',
  'SCPI',
  'SE (Societas Europaea)',
  'SE à conseil d\'administration',
  'SE à directoire',
  'SICOMI',
  'SNC',
  'SNC avec conseil d\'administration',
  'Société à intérêt collectif agricole (SICA)',
  'Société anonyme à responsabilité limitée',
  'Société anonyme coopérative de construction',
  "Société anonyme coopérative d'intérêt collectif",
  'Société anonyme de HLM',
  'Société anonyme mixte d\'investissement local (SEMIL)',
  'Société coopérative agricole',
  "Société coopérative de production (SCOP) SA",
  'Société créée de fait avec personne morale',
  'Société créée de fait entre personnes physiques',
  'Société de caution mutuelle',
  "Société d'exercice libéral par actions simplifiée (SELAS)",
  'Société en participation avec personne morale',
  'Société en participation de personnes morales',
  'Société en participation de personnes physiques',
  'Société en participation entre personnes physiques',
  'Société par actions simplifiée',
  'Syndicat',
  'Syndicat de propriétaires',
  'Association foncière',
].filter((v) => !LEGAL_FORM_COMMON.includes(v)).sort();

function formatCapital(raw: string): string {
  const digits = raw.replace(/\D/g, '');
  if (!digits) return '';
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, '\u00a0');
}

type Civility = 'M.' | 'Mme';

interface ContactFields {
  civility: Civility | '';
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
}

function isContactValid(c: ContactFields): boolean {
  return c.civility !== '' && c.first_name !== '' && c.last_name !== '' && /\S+@\S+\.\S+/.test(c.email);
}

function CivilitySelect({ value, onChange }: { value: Civility | ''; onChange: (v: Civility) => void }) {
  return (
    <div className="w-24 flex-shrink-0">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as Civility)}
        className={INPUT_CLS}
      >
        <option value="">—</option>
        <option value="M.">M.</option>
        <option value="Mme">Mme</option>
      </select>
    </div>
  );
}

function ContactSection({
  title,
  contact,
  onChange,
  checkboxLabel,
  sameAsRep,
  onToggleSameAsRep,
}: {
  title: string;
  contact: ContactFields;
  onChange: (c: ContactFields) => void;
  checkboxLabel?: string;
  sameAsRep?: boolean;
  onToggleSameAsRep?: () => void;
}) {
  const set = (key: keyof ContactFields) => (e: React.ChangeEvent<HTMLInputElement>) =>
    onChange({ ...contact, [key]: e.target.value });

  return (
    <div className="border-t border-gray-100 dark:border-gray-700 pt-5 mt-6">
      <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-4 pl-3 border-l-2 border-primary-500">{title}</p>
      {checkboxLabel && onToggleSameAsRep !== undefined && (
        <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 mb-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={sameAsRep}
            onChange={onToggleSameAsRep}
            className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
          />
          {checkboxLabel}
        </label>
      )}
      {!sameAsRep && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="md:col-span-2">
            <div className="grid grid-cols-[auto_1fr_1fr] gap-2 items-end">
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Civilité *</label>
                <CivilitySelect value={contact.civility} onChange={(v) => onChange({ ...contact, civility: v })} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Prénom *</label>
                <input type="text" value={contact.first_name} onChange={set('first_name')} placeholder="Prénom" className={INPUT_CLS} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Nom *</label>
                <input type="text" value={contact.last_name} onChange={set('last_name')} placeholder="Nom" className={INPUT_CLS} />
              </div>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">E-mail *</label>
            <input type="email" value={contact.email} onChange={set('email')} placeholder="Ex : jean.dupont@entreprise.fr" className={INPUT_CLS} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Téléphone</label>
            <PhoneInput
              international
              defaultCountry="FR"
              value={contact.phone}
              onChange={(val) => onChange({ ...contact, phone: val || '' })}
              className="phone-input-container"
            />
          </div>
        </div>
      )}
    </div>
  );
}

interface CompanyInfoFormProps {
  token: string;
  thirdPartyType?: string;
  initialData?: import('../types').PortalInfo['third_party'] | null;
  onSuccess: () => void;
}

function CompanyInfoForm({ token, thirdPartyType, initialData, onSuccess }: CompanyInfoFormProps) {
  const isPortageSalarial = thirdPartyType === 'portage_salarial';

  const resolveCategory = (): 'ei' | 'societe' | 'portage_salarial' => {
    if (isPortageSalarial) return 'portage_salarial';
    if (initialData?.entity_category === 'societe') return 'societe';
    if (initialData?.entity_category === 'portage_salarial') return 'portage_salarial';
    return 'ei';
  };

  const [entityCategory, setEntityCategory] = useState<'ei' | 'societe' | 'portage_salarial'>(resolveCategory);
  const [form, setForm] = useState({
    company_name: initialData?.company_name ?? '',
    legal_form: initialData?.legal_form ?? '',
    capital: initialData?.capital ?? '',
    siret: initialData?.siret ?? '',
    head_office_street: initialData?.head_office_street ?? '',
    head_office_postal_code: initialData?.head_office_postal_code ?? '',
    head_office_city: initialData?.head_office_city ?? '',
    rcs_city: initialData?.rcs_city ?? '',
    representative_title: initialData?.representative_title ?? '',
  });
  const [siretLoading, setSiretLoading] = useState(false);
  const [signatory, setSignatory] = useState<ContactFields>({
    civility: (initialData?.representative_civility as Civility | '') ?? '',
    first_name: initialData?.representative_first_name ?? '',
    last_name: initialData?.representative_last_name ?? '',
    email: initialData?.representative_email ?? '',
    phone: initialData?.representative_phone ?? '',
  });
  const [advContact, setAdvContact] = useState<ContactFields>({
    civility: (initialData?.adv_contact_civility as Civility | '') ?? '',
    first_name: initialData?.adv_contact_first_name ?? '',
    last_name: initialData?.adv_contact_last_name ?? '',
    email: initialData?.adv_contact_email ?? '',
    phone: initialData?.adv_contact_phone ?? '',
  });
  const [advIsSame, setAdvIsSame] = useState(false);
  const [billingContact, setBillingContact] = useState<ContactFields>({
    civility: (initialData?.billing_contact_civility as Civility | '') ?? '',
    first_name: initialData?.billing_contact_first_name ?? '',
    last_name: initialData?.billing_contact_last_name ?? '',
    email: initialData?.billing_contact_email ?? '',
    phone: initialData?.billing_contact_phone ?? '',
  });
  const [billingIsSame, setBillingIsSame] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const handleSiretChange = async (value: string) => {
    const digits = value.replace(/\D/g, '').slice(0, 14);
    setForm((f) => ({ ...f, siret: digits }));
    if (digits.length === 14) {
      setSiretLoading(true);
      try {
        const data = await portalApi.lookupSiret(token, digits);
        setForm((f) => ({
          ...f,
          company_name: data.company_name ?? f.company_name,
          legal_form: data.legal_form ?? f.legal_form,
          head_office_street: data.head_office_street ?? f.head_office_street,
          head_office_postal_code: data.head_office_postal_code ?? f.head_office_postal_code,
          head_office_city: data.head_office_city ?? f.head_office_city,
          capital: data.capital ? formatCapital(data.capital) : f.capital,
          rcs_city: data.rcs_city ?? f.rcs_city,
        }));
        if (!isPortageSalarial && (data.entity_category === 'ei' || data.entity_category === 'societe')) {
          setEntityCategory(data.entity_category);
        }
        toast.success('Données pré-remplies.');
      } catch {
        // Silently ignore — user can fill manually
      } finally {
        setSiretLoading(false);
      }
    }
  };

  const isSocieteOrPortage = entityCategory === 'societe' || entityCategory === 'portage_salarial';

  const isValid =
    /^\d{14}$/.test(form.siret) &&
    form.company_name !== '' &&
    form.legal_form !== '' &&
    form.head_office_street !== '' &&
    /^\d{5}$/.test(form.head_office_postal_code) &&
    form.head_office_city !== '' &&
    (!isSocieteOrPortage || form.rcs_city !== '') &&
    form.representative_title !== '' &&
    isContactValid(signatory) &&
    (advIsSame || isContactValid(advContact)) &&
    (billingIsSame || isContactValid(billingContact));

  const handleSaveDraft = async () => {
    setIsSaving(true);
    try {
      await portalApi.saveCompanyInfoDraft(token, {
        ...(entityCategory ? { entity_category: entityCategory } : {}),
        ...(form.company_name ? { company_name: form.company_name } : {}),
        ...(form.legal_form ? { legal_form: form.legal_form } : {}),
        ...(form.capital ? { capital: form.capital } : {}),
        ...(form.siret ? { siret: form.siret } : {}),
        ...(form.head_office_street ? { head_office_street: form.head_office_street } : {}),
        ...(form.head_office_postal_code ? { head_office_postal_code: form.head_office_postal_code } : {}),
        ...(form.head_office_city ? { head_office_city: form.head_office_city } : {}),
        ...(form.rcs_city ? { rcs_city: form.rcs_city } : {}),
        ...(form.representative_title ? { representative_title: form.representative_title } : {}),
        ...(signatory.civility ? { representative_civility: signatory.civility as 'M.' | 'Mme' } : {}),
        ...(signatory.first_name ? { representative_first_name: signatory.first_name } : {}),
        ...(signatory.last_name ? { representative_last_name: signatory.last_name } : {}),
        ...(signatory.email ? { representative_email: signatory.email } : {}),
        ...(signatory.phone ? { representative_phone: signatory.phone } : {}),
        ...(signatory.civility ? { signatory_civility: signatory.civility as 'M.' | 'Mme' } : {}),
        ...(signatory.first_name ? { signatory_first_name: signatory.first_name } : {}),
        ...(signatory.last_name ? { signatory_last_name: signatory.last_name } : {}),
        ...(signatory.email ? { signatory_email: signatory.email } : {}),
        ...(signatory.phone ? { signatory_phone: signatory.phone } : {}),
        adv_contact_same_as_representative: advIsSame,
        ...(!advIsSame && advContact.civility ? { adv_contact_civility: advContact.civility as 'M.' | 'Mme' } : {}),
        ...(!advIsSame && advContact.first_name ? { adv_contact_first_name: advContact.first_name } : {}),
        ...(!advIsSame && advContact.last_name ? { adv_contact_last_name: advContact.last_name } : {}),
        ...(!advIsSame && advContact.email ? { adv_contact_email: advContact.email } : {}),
        ...(!advIsSame && advContact.phone ? { adv_contact_phone: advContact.phone } : {}),
        billing_contact_same_as_representative: billingIsSame,
        ...(!billingIsSame && billingContact.civility ? { billing_contact_civility: billingContact.civility as 'M.' | 'Mme' } : {}),
        ...(!billingIsSame && billingContact.first_name ? { billing_contact_first_name: billingContact.first_name } : {}),
        ...(!billingIsSame && billingContact.last_name ? { billing_contact_last_name: billingContact.last_name } : {}),
        ...(!billingIsSame && billingContact.email ? { billing_contact_email: billingContact.email } : {}),
        ...(!billingIsSame && billingContact.phone ? { billing_contact_phone: billingContact.phone } : {}),
      });
      toast.success('Brouillon enregistré.');
    } catch {
      toast.error("Erreur lors de l'enregistrement du brouillon.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSubmit = async () => {
    if (!isValid) return;
    setIsSubmitting(true);
    try {
      await portalApi.submitCompanyInfo(token, {
        entity_category: entityCategory,
        company_name: form.company_name,
        legal_form: form.legal_form,
        capital: form.capital || undefined,
        siret: form.siret,
        head_office_street: form.head_office_street,
        head_office_postal_code: form.head_office_postal_code,
        head_office_city: form.head_office_city,
        rcs_city: form.rcs_city || undefined,
        representative_civility: signatory.civility as 'M.' | 'Mme',
        representative_first_name: signatory.first_name,
        representative_last_name: signatory.last_name,
        representative_email: signatory.email,
        representative_phone: signatory.phone || undefined,
        representative_title: form.representative_title,
        signatory_same_as_representative: false,
        signatory_civility: signatory.civility as 'M.' | 'Mme',
        signatory_first_name: signatory.first_name,
        signatory_last_name: signatory.last_name,
        signatory_email: signatory.email,
        signatory_phone: signatory.phone || undefined,
        adv_contact_same_as_representative: advIsSame,
        ...(advIsSame ? {} : {
          adv_contact_civility: advContact.civility as 'M.' | 'Mme',
          adv_contact_first_name: advContact.first_name,
          adv_contact_last_name: advContact.last_name,
          adv_contact_email: advContact.email,
          adv_contact_phone: advContact.phone,
        }),
        billing_contact_same_as_representative: billingIsSame,
        ...(billingIsSame ? {} : {
          billing_contact_civility: billingContact.civility as 'M.' | 'Mme',
          billing_contact_first_name: billingContact.first_name,
          billing_contact_last_name: billingContact.last_name,
          billing_contact_email: billingContact.email,
          billing_contact_phone: billingContact.phone,
        }),
      });
      toast.success('Informations enregistrées.');
      onSuccess();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "Erreur lors de l'enregistrement.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const field = (key: keyof typeof form) => ({
    value: form[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value })),
    className: INPUT_CLS,
  });

  return (
    <div className="max-w-3xl mx-auto">
      <Card>
        <div className="flex items-center gap-3 mb-6">
          <Building2 className="h-6 w-6 text-primary-600" />
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Informations de votre structure
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Renseignez vos coordonnées légales pour démarrer la collecte de documents.
            </p>
          </div>
        </div>

        {/* Entity category */}
        <div className="mb-5">
          <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
            Structure juridique *
          </p>
          {isPortageSalarial ? (
            <div className="p-3 rounded-lg border-2 border-primary-500 bg-primary-50 dark:bg-primary-900/20">
              <p className="text-sm font-medium text-gray-900 dark:text-white">Société de portage salarial</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Votre structure est une société de portage salarial</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {(
                [
                  { value: 'ei', label: 'Entreprise individuelle', sub: 'EI, Micro-entreprise' },
                  { value: 'societe', label: 'Société', sub: 'SAS, SASU, EURL, SARL…' },
                ] as const
              ).map(({ value, label, sub }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setEntityCategory(value)}
                  className={`p-3 rounded-lg border-2 text-left transition-colors ${
                    entityCategory === value
                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                  }`}
                >
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{label}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{sub}</p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Identité */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              SIRET *
            </label>
            <div className="relative">
              <input
                type="text"
                maxLength={14}
                value={form.siret}
                onChange={(e) => handleSiretChange(e.target.value)}
                placeholder="Ex : 44035388200012"
                className={INPUT_CLS}
              />
              {siretLoading && (
                <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-primary-500" />
              )}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              Les informations seront pré-remplies automatiquement.
            </p>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              {!isSocieteOrPortage ? 'Nom commercial / Enseigne *' : 'Raison sociale *'}
            </label>
            <input
              type="text"
              {...field('company_name')}
              placeholder={!isSocieteOrPortage ? 'Ex : Jean Dupont Consulting' : 'Ex : Acme SAS'}
              className={INPUT_CLS}
            />
          </div>
          {isSocieteOrPortage && (
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Ville du greffe *
              </label>
              <input
                type="text"
                {...field('rcs_city')}
                placeholder="Ex : Paris"
                className={INPUT_CLS}
              />
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Forme juridique *
            </label>
            <select
              value={form.legal_form}
              onChange={(e) => setForm((f) => ({ ...f, legal_form: e.target.value }))}
              className={INPUT_CLS}
            >
              <option value="">— Sélectionner —</option>
              {form.legal_form &&
                !LEGAL_FORM_COMMON.includes(form.legal_form) &&
                !LEGAL_FORM_ALL.includes(form.legal_form) && (
                  <option value={form.legal_form}>{form.legal_form}</option>
                )}
              <optgroup label="Formes courantes">
                {LEGAL_FORM_COMMON.map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </optgroup>
              <optgroup label="Autres formes">
                {LEGAL_FORM_ALL.map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </optgroup>
            </select>
          </div>
          {isSocieteOrPortage && (
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Capital social
              </label>
              <div className="relative">
                <input
                  type="text"
                  inputMode="numeric"
                  value={form.capital}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, capital: formatCapital(e.target.value) }))
                  }
                  placeholder="Ex : 10 000"
                  className={INPUT_CLS}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 pointer-events-none">
                  EUR
                </span>
              </div>
            </div>
          )}
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Numéro et voie *
            </label>
            <input type="text" {...field('head_office_street')} placeholder="Ex : 12 rue de la Paix" className={INPUT_CLS} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Code postal *
            </label>
            <input
              type="text"
              maxLength={5}
              {...field('head_office_postal_code')}
              onChange={(e) =>
                setForm((f) => ({ ...f, head_office_postal_code: e.target.value.replace(/\D/g, '') }))
              }
              placeholder="Ex : 75001"
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Ville *
            </label>
            <input type="text" {...field('head_office_city')} placeholder="Ex : Paris" className={INPUT_CLS} />
          </div>
        </div>

        {/* Signataire du contrat (= représentant légal) */}
        <div className="border-t border-gray-100 dark:border-gray-700 pt-5 mt-6">
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-4 pl-3 border-l-2 border-primary-500">
            Signataire du contrat
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="md:col-span-2">
              <div className="grid grid-cols-[auto_1fr_1fr] gap-2 items-end">
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Civilité *</label>
                  <CivilitySelect value={signatory.civility} onChange={(v) => setSignatory((c) => ({ ...c, civility: v }))} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Prénom *</label>
                  <input
                    type="text"
                    value={signatory.first_name}
                    onChange={(e) => setSignatory((c) => ({ ...c, first_name: e.target.value }))}
                    placeholder="Prénom"
                    className={INPUT_CLS}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Nom *</label>
                  <input
                    type="text"
                    value={signatory.last_name}
                    onChange={(e) => setSignatory((c) => ({ ...c, last_name: e.target.value }))}
                    placeholder="Nom"
                    className={INPUT_CLS}
                  />
                </div>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">E-mail *</label>
              <input
                type="email"
                value={signatory.email}
                onChange={(e) => setSignatory((c) => ({ ...c, email: e.target.value }))}
                placeholder="Ex : jean.dupont@entreprise.fr"
                className={INPUT_CLS}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Téléphone</label>
              <PhoneInput
                international
                defaultCountry="FR"
                value={signatory.phone}
                onChange={(val) => setSignatory((c) => ({ ...c, phone: val || '' }))}
                className="phone-input-container"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Qualité *
              </label>
              <input
                type="text"
                {...field('representative_title')}
                placeholder={!isSocieteOrPortage ? 'Ex : Entrepreneur individuel' : 'Ex : Président'}
                className={INPUT_CLS}
              />
            </div>
          </div>
        </div>

        {/* Contact ADV */}
        <ContactSection
          title="Contact ADV"
          contact={advContact}
          onChange={setAdvContact}
          checkboxLabel="Même personne que le signataire du contrat"
          sameAsRep={advIsSame}
          onToggleSameAsRep={() => setAdvIsSame((v) => !v)}
        />

        {/* Contact facturation */}
        <ContactSection
          title="Contact facturation"
          contact={billingContact}
          onChange={setBillingContact}
          checkboxLabel="Même personne que le signataire du contrat"
          sameAsRep={billingIsSame}
          onToggleSameAsRep={() => setBillingIsSame((v) => !v)}
        />

        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={handleSaveDraft} disabled={isSaving || isSubmitting} isLoading={isSaving}>
            Enregistrer
          </Button>
          <Button onClick={handleSubmit} disabled={!isValid || isSubmitting || isSaving} isLoading={isSubmitting}>
            Valider et continuer
          </Button>
        </div>
      </Card>
    </div>
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

function SubmitDocumentsButton({
  token,
  enabled,
  expiredBlocked,
  onSubmitted,
}: {
  token: string;
  enabled: boolean;
  expiredBlocked?: boolean;
  onSubmitted: () => void;
}) {
  const submitMutation = useMutation({
    mutationFn: () => portalApi.submitDocuments(token),
    onSuccess: () => {
      toast.success('Dépôt validé. Notre équipe va examiner vos documents.');
      onSubmitted();
    },
    onError: () => {
      toast.error('Une erreur est survenue. Veuillez réessayer.');
    },
  });

  return (
    <div className="mt-8 border-t border-gray-200 dark:border-gray-700 pt-6">
      <div className="flex flex-col items-center gap-3 text-center">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Une fois tous vos documents déposés, validez votre dépôt pour notifier notre équipe.
        </p>
        <Button
          onClick={() => submitMutation.mutate()}
          disabled={!enabled || submitMutation.isPending}
          className="min-w-48"
        >
          {submitMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Envoi en cours…
            </>
          ) : (
            <>
              <CheckCircle className="h-4 w-4 mr-2" />
              Valider le dépôt des documents
            </>
          )}
        </Button>
        {expiredBlocked && (
          <p className="text-xs text-red-500 dark:text-red-400">
            Un ou plusieurs documents sont expirés. Veuillez les remplacer avant de valider.
          </p>
        )}
        {!enabled && !expiredBlocked && (
          <p className="text-xs text-gray-400 dark:text-gray-500">
            Chaque document doit être téléversé ou signalé comme indisponible avec une raison.
          </p>
        )}
      </div>
    </div>
  );
}

function DocumentUploadCard({
  doc,
  token,
  onSuccess,
}: {
  doc: {
    id: string; document_type: string; display_name: string; validity_label: string | null;
    status: string; file_name: string | null; rejection_reason: string | null;
    document_date: string | null; is_valid_at_upload: boolean | null;
    extracted_info: Record<string, string | null> | null;
    is_unavailable: boolean; unavailability_reason: string | null;
  };
  token: string;
  onSuccess: () => void;
}) {
  const [dragOver, setDragOver] = useState(false);
  const [showReplace, setShowReplace] = useState(false);
  // Unavailability form state — initialised from server data
  const [unavailChecked, setUnavailChecked] = useState(doc.is_unavailable);
  const [unavailReason, setUnavailReason] = useState(doc.unavailability_reason ?? '');

  const Icon = DOCUMENT_STATUS_ICONS[doc.status] ?? FileText;
  const iconColor = doc.is_unavailable
    ? 'text-gray-400'
    : DOCUMENT_STATUS_COLORS[doc.status] ?? 'text-gray-400';
  const statusLabel = doc.is_unavailable
    ? 'Document indisponible'
    : DOCUMENT_STATUS_LABELS[doc.status] ?? doc.status;

  // Temporarily validated by ADV (no real file yet) — third party can still submit
  const isTempValidated = doc.status === 'validated' && !doc.file_name;
  // Upload zone shown for requested/rejected, temporarily validated, or when user clicks "Changer"
  const needsUpload = isTempValidated || (!unavailChecked && (doc.status === 'requested' || doc.status === 'rejected' || showReplace));

  const uploadMutation = useMutation({
    mutationFn: (file: File) => portalApi.uploadDocument(token, doc.id, file),
    onSuccess: () => {
      toast.success('Document téléversé avec succès.');
      setShowReplace(false);
      onSuccess();
    },
    onError: (error: unknown) => {
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? 'Erreur lors du téléversement.');
    },
  });

  const availabilityMutation = useMutation({
    mutationFn: ({ isUnavail, reason }: { isUnavail: boolean; reason?: string }) =>
      portalApi.updateDocumentAvailability(token, doc.id, isUnavail, reason),
    onSuccess: () => {
      toast.success(unavailChecked ? 'Raison enregistrée.' : 'Document remis en attente de téléversement.');
      onSuccess();
    },
    onError: () => { toast.error('Erreur lors de l\'enregistrement.'); },
  });

  const handleFileSelect = useCallback((file: File) => {
    if (file.size > 10 * 1024 * 1024) { toast.error('Le fichier dépasse 10 Mo.'); return; }
    uploadMutation.mutate(file);
  }, [uploadMutation]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  }, [handleFileSelect]);

  const handleCheckboxChange = (checked: boolean) => {
    setUnavailChecked(checked);
    if (!checked) {
      // Immediately reset on the server when unchecked
      setUnavailReason('');
      availabilityMutation.mutate({ isUnavail: false });
    }
  };

  const handleSaveReason = () => {
    if (!unavailReason.trim()) { toast.error('Veuillez indiquer une raison.'); return; }
    availabilityMutation.mutate({ isUnavail: true, reason: unavailReason });
  };

  const [confirmDelete, setConfirmDelete] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => portalApi.deleteDocument(token, doc.id),
    onSuccess: () => {
      toast.success('Document supprimé. Vous pouvez en déposer un nouveau.');
      setConfirmDelete(false);
      onSuccess();
    },
    onError: () => { toast.error('Erreur lors de la suppression.'); },
  });

  return (
    <Card className="relative">
      {/* ── X delete button (top-right) ── */}
      {doc.status === 'received' && !unavailChecked && (
        confirmDelete ? (
          <div className="absolute top-3 right-3 flex items-center gap-2">
            <button
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="text-xs text-red-500 dark:text-red-400 hover:underline disabled:opacity-50"
            >
              {deleteMutation.isPending ? 'Suppression…' : 'Confirmer'}
            </button>
            <button onClick={() => setConfirmDelete(false)}
              className="text-xs text-gray-400 hover:underline">
              Annuler
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirmDelete(true)}
            title="Supprimer ce document"
            className="absolute top-3 right-3 p-1 rounded-full text-gray-300 dark:text-gray-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        )
      )}

      {/* ── Header ── */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <Icon className={`h-5 w-5 mt-0.5 flex-shrink-0 ${iconColor}`} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {doc.display_name}
              </p>
              {doc.validity_label && (
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 border border-amber-200 dark:border-amber-700">
                  {doc.validity_label}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{statusLabel}</p>
            {doc.file_name && !doc.is_unavailable && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Fichier : {doc.file_name}</p>
            )}
            {doc.rejection_reason && (
              <p className="text-xs text-red-600 dark:text-red-400 mt-1">Motif du rejet : {doc.rejection_reason}</p>
            )}

            {/* AI-extracted data */}
            {!doc.is_unavailable && doc.document_type !== 'rib' && (doc.document_date || doc.extracted_info?.expiry_date) && (
              <div className="mt-2 space-y-1">
                {doc.document_date && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    <span className="font-medium text-gray-600 dark:text-gray-300">Date du document :</span>{' '}
                    {new Date(doc.document_date).toLocaleDateString('fr-FR')}
                  </p>
                )}
                {doc.extracted_info?.expiry_date && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    <span className="font-medium text-gray-600 dark:text-gray-300">Valide jusqu'au :</span>{' '}
                    {new Date(doc.extracted_info.expiry_date).toLocaleDateString('fr-FR')}
                  </p>
                )}
                {doc.is_valid_at_upload === true && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300 border border-green-200 dark:border-green-700">
                    <CheckCircle className="h-3 w-3" /> Valide
                  </span>
                )}
                {doc.is_valid_at_upload === false && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300 border border-red-200 dark:border-red-700">
                    <XCircle className="h-3 w-3" /> Document périmé
                  </span>
                )}
              </div>
            )}
            {!doc.is_unavailable && doc.document_type === 'rib' && doc.extracted_info && (
              <div className="mt-2 space-y-0.5">
                {doc.extracted_info.beneficiaire && (
                  <p className="text-xs text-gray-600 dark:text-gray-300">
                    <span className="font-medium">Bénéficiaire :</span> {doc.extracted_info.beneficiaire}
                  </p>
                )}
                {doc.extracted_info.iban && (
                  <p className="text-xs text-gray-600 dark:text-gray-300 font-mono">
                    <span className="font-sans font-medium">IBAN :</span> {doc.extracted_info.iban}
                  </p>
                )}
                {doc.extracted_info.bic && (
                  <p className="text-xs text-gray-600 dark:text-gray-300 font-mono">
                    <span className="font-sans font-medium">BIC :</span> {doc.extracted_info.bic}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* "Changer" button for received documents */}
        {doc.status === 'received' && !showReplace && !unavailChecked && !confirmDelete && (
          <button onClick={() => setShowReplace(true)}
            className="ml-3 mr-6 flex-shrink-0 text-xs text-primary-600 dark:text-primary-400 hover:underline">
            Changer
          </button>
        )}
        {showReplace && (
          <button onClick={() => setShowReplace(false)}
            className="ml-3 mr-6 flex-shrink-0 text-xs text-gray-400 hover:underline">
            Annuler
          </button>
        )}
      </div>

      {/* ── Banner for temporarily validated docs ── */}
      {isTempValidated && (
        <p className="mt-3 text-xs text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/20 rounded-lg px-3 py-2">
          Votre interlocuteur a pris acte de l'indisponibilité de ce document. Si vous l'avez obtenu depuis, vous pouvez le déposer ici.
        </p>
      )}

      {/* ── Upload zone ── */}
      {needsUpload && (
        <div
          className={`mt-3 border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
            dragOver ? 'border-primary-400 bg-primary-50 dark:bg-primary-900/20' : 'border-gray-300 dark:border-gray-600'
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
                  <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileSelect(f); }} />
                </label>
              </p>
              <p className="text-xs text-gray-400 mt-1">PDF, JPG, PNG — max 10 Mo</p>
            </>
          )}
        </div>
      )}

      {/* ── "Je ne dispose pas de ce document" checkbox ── */}
      {!isTempValidated && (doc.status === 'requested' || doc.status === 'rejected' || doc.is_unavailable) && !showReplace && (
        <div className="mt-3 border-t border-gray-100 dark:border-gray-700 pt-3">
          <label className="flex items-start gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={unavailChecked}
              onChange={(e) => handleCheckboxChange(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              disabled={availabilityMutation.isPending}
            />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Je ne dispose pas de ce document
            </span>
          </label>

          {unavailChecked && (
            <div className="mt-2 ml-6 space-y-2">
              <textarea
                value={unavailReason}
                onChange={(e) => setUnavailReason(e.target.value)}
                placeholder="Précisez la raison (ex : document en cours d'obtention, non applicable à notre situation…)"
                rows={3}
                maxLength={500}
                className="w-full text-sm rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
              />
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">{unavailReason.length}/500</span>
                <Button
                  size="sm"
                  onClick={handleSaveReason}
                  disabled={!unavailReason.trim() || availabilityMutation.isPending}
                >
                  {availabilityMutation.isPending ? (
                    <><Loader2 className="h-3 w-3 animate-spin mr-1" /> Enregistrement…</>
                  ) : 'Enregistrer'}
                </Button>
              </div>
              {/* Show saved reason from server */}
              {doc.is_unavailable && doc.unavailability_reason && unavailReason === doc.unavailability_reason && (
                <p className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                  <CheckCircle className="h-3 w-3" /> Raison enregistrée
                </p>
              )}
            </div>
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
