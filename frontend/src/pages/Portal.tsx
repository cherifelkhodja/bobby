import { useState, useCallback, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import PhoneInput from 'react-phone-number-input';
import 'react-phone-number-input/style.css';
import {
  ShieldCheck,
  Upload,
  FileText,
  Check,
  CheckCircle,
  XCircle,
  X,
  AlertTriangle,
  Building2,
  Loader2,
  Lock,
  PenLine,
  ChevronLeft,
  Download,
} from 'lucide-react';
import { toast } from 'sonner';

import { portalApi } from '../api/portal';
import { Button } from '../components/ui/Button';
import { PageSpinner } from '../components/ui/Spinner';

const DOCUMENT_STATUS_CHIPS: Record<string, string> = {
  validated: 'st-grn',
  rejected: 'st-red',
  received: 'st-blu',
  requested: 'st-amb',
  expiring_soon: 'st-amb',
  expired: 'st-red',
};

const DOCUMENT_STATUS_LABELS: Record<string, string> = {
  validated: 'Validé',
  rejected: 'Rejeté',
  received: 'Reçu',
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
  const currentIndex = steps.findIndex((s) => s.status === 'current');
  const activeIndex = currentIndex >= 0 ? currentIndex : steps.length - 1;
  const fill = steps.length > 1 ? Math.round((activeIndex / (steps.length - 1)) * 84) : 0;

  return (
    <div className="steps">
      <span className="track" />
      <span className="tfill" style={{ width: `${fill}%` }} />
      <div className="nodes">
        {steps.map((step, i) => (
          <div key={i} className="stw">
            <span
              className={`nd ${
                step.status === 'done' ? 'd' : step.status === 'current' ? 'cur' : ''
              }`}
            />
            <p className="lb">{step.label}</p>
          </div>
        ))}
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

  // Charters (partner charters for acknowledgement)
  const { data: chartersData } = useQuery({
    queryKey: ['portal-charters', token],
    queryFn: () => portalApi.getCharters(token!),
    enabled: !!token && !!portalInfo,
  });
  const chartersAcknowledged = !chartersData || chartersData.length === 0 || chartersData.every((c) => c.acknowledged);

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
        <div className="p-card text-center px-[22px] py-9">
          <div className="alert red !inline-flex !mt-0">
            <XCircle className="h-[18px] w-[18px] flex-shrink-0" />
            <span>Lien invalide ou expiré</span>
          </div>
          <p className="notec mt-3.5">
            Ce lien d'accès n'est plus valide. Veuillez contacter votre interlocuteur
            pour obtenir un nouveau lien.
          </p>
        </div>
      </PortalLayout>
    );
  }

  const isDocumentUpload = portalInfo.purpose === 'document_upload';
  const isContractReview = portalInfo.purpose === 'contract_review';

  const hasSiren = !!portalInfo.third_party.company_info_submitted;

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

  // Natural step: 0=infos société, 1=documents, 2=chartes (if any), 3=confirmation
  const hasCharters_ = chartersData && chartersData.length > 0;
  const naturalStep = isDocumentUpload
    ? !hasSiren ? 0
      : !submitted ? 1
      : hasCharters_ && !chartersAcknowledged ? 2
      : (hasCharters_ ? 3 : 2)
    : 0;

  // displayStep: forceStep allows going back; clamp to [0, naturalStep]
  const displayStep = forceStep !== null ? Math.min(forceStep, naturalStep) : naturalStep;

  const buildStepStatus = (stepIndex: number): StepStatus => {
    if (stepIndex < displayStep) return 'done';
    if (stepIndex === displayStep) return 'current';
    return 'upcoming';
  };

  const hasCharters = chartersData && chartersData.length > 0;
  const steps: Step[] = isDocumentUpload
    ? [
        { label: 'Infos société', icon: Building2, status: buildStepStatus(0) },
        { label: 'Documents',     icon: Upload,    status: buildStepStatus(1) },
        ...(hasCharters ? [{ label: 'Chartes', icon: ShieldCheck, status: buildStepStatus(2) }] : []),
        { label: 'Vérification',  icon: ShieldCheck, status: buildStepStatus(hasCharters ? 3 : 2) },
      ]
    : [
        { label: 'Relecture', icon: FileText, status: 'current' },
        { label: 'Signature', icon: PenLine,  status: 'upcoming' },
      ];

  const goBack = () => setForceStep(displayStep - 1);
  const goForward = () => setForceStep(null); // snap back to natural step

  return (
    <PortalLayout>
      {/* Carte d'accueil */}
      <div className="p-card">
        <h1 className="p-h">
          Bonjour {portalInfo.third_party.company_name ?? portalInfo.third_party.contact_email}
        </h1>
        <p className="sub mt-1.5">
          {isDocumentUpload ? (
            <>
              Merci de renseigner les informations de votre structure puis de déposer les
              documents demandés pour finaliser votre dossier. Formats acceptés :{' '}
              <b>PDF, JPG, PNG</b> · 10 Mo max.
            </>
          ) : (
            <>
              Le draft de votre contrat est prêt pour relecture. Consultez le document
              ci-dessous puis donnez votre décision.
            </>
          )}
        </p>
        <PortalStepper steps={steps} />
      </div>

      {/* Back button — hidden after submission */}
      {displayStep > 0 && !submitted && (
        <div className="mt-3.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={goBack}
            leftIcon={<ChevronLeft className="h-4 w-4" />}
          >
            Retour
          </Button>
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
        <div className="p-card mt-3.5">
          <h2 className="ct">Documents de conformité</h2>
          <p className="cs">Veuillez téléverser les documents demandés ci-dessous.</p>

          <div className="mt-3.5">
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
              <div className="text-center py-8">
                <ShieldCheck className="h-9 w-9 text-mut2 mx-auto mb-2.5" />
                <p className="dn">Aucun document demandé pour le moment</p>
                <p className="ds mt-1">Vous serez notifié si des documents sont nécessaires.</p>
              </div>
            )}
          </div>

          {docsData.documents.length > 0 && (
            <>
              <p className="p-note">
                Conformément au RGPD, ne transmettez jamais : pièce d'identité, titre de
                séjour, bulletin de paie ou contrat de travail.
              </p>
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
            </>
          )}
        </div>
      )}

      {/* Chartes step — shown after document submission */}
      {isDocumentUpload && hasCharters && displayStep === 2 && (
        <div className="p-card mt-3.5">
          <h2 className="ct">Chartes et engagements</h2>
          <p className="cs">
            Veuillez prendre connaissance des chartes suivantes et confirmer votre acceptation.
          </p>
          <div className="mt-3.5">
            {chartersData?.map((charter) => (
              <div key={charter.id} className="p-doc flex-wrap">
                <div className="dico">
                  <ShieldCheck className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="dn">{charter.name}</p>
                  <p className="ds mt-0.5">Version {charter.version}</p>
                </div>
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      const { url } = await portalApi.getCharterDownloadUrl(token!, charter.id);
                      window.open(url, '_blank');
                    } catch {
                      toast.error('Impossible de télécharger la charte. Veuillez réessayer.');
                    }
                  }}
                  className="inline-flex items-center gap-1 text-[12px] font-semibold text-prit hover:underline flex-shrink-0"
                >
                  <Download className="h-3.5 w-3.5" />
                  Télécharger
                </button>
                {charter.acknowledged ? (
                  <span className="st st-grn flex-shrink-0">
                    <span className="dot" />
                    Acceptée
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        await portalApi.acknowledgeCharter(token!, charter.id);
                        queryClient.invalidateQueries({ queryKey: ['portal-charters', token] });
                      } catch {
                        toast.error("Impossible d'enregistrer votre acceptation. Veuillez réessayer.");
                      }
                    }}
                    className="ckrow w-full pl-[46px] pt-1 text-left"
                  >
                    <span className="ck">
                      <Check className="h-3 w-3" strokeWidth={3} />
                    </span>
                    J'ai lu et j'accepte cette charte
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Verification message — final step (all docs uploaded + charters acknowledged) */}
      {isDocumentUpload && displayStep === (hasCharters ? 3 : 2) && (
        <div className="p-card mt-3.5 text-center px-[22px] py-9">
          <div className="okbox !inline-flex !m-0 !mb-3.5">
            <CheckCircle className="h-4 w-4 flex-shrink-0" />
            <span>Documents transmis avec succès</span>
          </div>
          <p className="notec">
            Vos documents sont en cours de vérification par notre équipe.
            Vous serez contacté si des informations complémentaires sont nécessaires.
          </p>
        </div>
      )}

      {/* Review du contrat — à venir (flux documents) */}
      {isDocumentUpload && (
        <div className="p-card mt-3.5">
          <div className="flex items-center gap-3">
            <div className="dico">
              <Lock className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="dn">Review du contrat</p>
              <p className="ds mt-0.5">
                Le draft du contrat vous sera soumis ici pour relecture et approbation, une
                fois votre dossier validé.
              </p>
            </div>
            <span className="st st-sla flex-shrink-0">
              <span className="dot" />À venir
            </span>
          </div>
        </div>
      )}

      {/* Contract review section */}
      {isContractReview && (
        <ContractReviewSection token={token!} contractDraft={contractDraft} />
      )}
    </PortalLayout>
  );
}

const INPUT_CLS = 'f-in';

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
        className={`${INPUT_CLS} !px-2.5`}
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
    <div className="border-t border-lin2 pt-4 mt-5">
      <p className="ct text-[13.5px] mb-3.5">{title}</p>
      {checkboxLabel && onToggleSameAsRep !== undefined && (
        <label className="ckrow mb-3 select-none">
          <input
            type="checkbox"
            className="sr-only"
            checked={sameAsRep}
            onChange={onToggleSameAsRep}
          />
          <span className={`ck ${sameAsRep ? 'on' : ''}`}>
            <Check className="h-3 w-3" strokeWidth={3} />
          </span>
          {checkboxLabel}
        </label>
      )}
      {!sameAsRep && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="md:col-span-2">
            <div className="grid grid-cols-[auto_1fr_1fr] gap-2 items-end">
              <div>
                <label className="f-lab">Civilité *</label>
                <CivilitySelect value={contact.civility} onChange={(v) => onChange({ ...contact, civility: v })} />
              </div>
              <div>
                <label className="f-lab">Prénom *</label>
                <input type="text" value={contact.first_name} onChange={set('first_name')} placeholder="Prénom" className={INPUT_CLS} />
              </div>
              <div>
                <label className="f-lab">Nom *</label>
                <input type="text" value={contact.last_name} onChange={set('last_name')} placeholder="Nom" className={INPUT_CLS} />
              </div>
            </div>
          </div>
          <div>
            <label className="f-lab">E-mail *</label>
            <input type="email" value={contact.email} onChange={set('email')} placeholder="Ex : jean.dupont@entreprise.fr" className={INPUT_CLS} />
          </div>
          <div>
            <label className="f-lab">Téléphone</label>
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
    // Une société de portage commercial est toujours une société : la garantie
    // financière, elle, ne concerne que le portage salarial.
    if (thirdPartyType === 'portage_commercial') return 'societe';
    return 'ei';
  };

  const [entityCategory, setEntityCategory] = useState<'ei' | 'societe' | 'portage_salarial'>(resolveCategory);
  const [form, setForm] = useState({
    company_name: initialData?.company_name ?? '',
    legal_form: initialData?.legal_form ?? '',
    capital: initialData?.capital ?? '',
    siret: initialData?.siret ?? '',
    vat_number: initialData?.vat_number ?? '',
    vat_liable: initialData?.vat_liable ?? true,
    ape_code: initialData?.ape_code ?? '',
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
  const [signatoryIsDirector, setSignatoryIsDirector] = useState(initialData?.signatory_is_director ?? false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const computeVatNumber = (siret: string): string => {
    const siren = siret.slice(0, 9);
    const sirenNum = parseInt(siren, 10);
    if (isNaN(sirenNum)) return '';
    const key = (12 + 3 * (sirenNum % 97)) % 97;
    return `FR${String(key).padStart(2, '0')}${siren}`;
  };

  const handleSiretChange = async (value: string) => {
    const digits = value.replace(/\D/g, '').slice(0, 14);
    setForm((f) => {
      const updated = { ...f, siret: digits };
      if (digits.length === 14 && f.vat_liable) {
        updated.vat_number = computeVatNumber(digits);
      }
      return updated;
    });
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
          ape_code: data.ape_code ?? f.ape_code,
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
        ...(form.vat_number ? { vat_number: form.vat_number } : {}),
        vat_liable: form.vat_liable,
        ...(form.ape_code ? { ape_code: form.ape_code } : {}),
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
        signatory_is_director: signatoryIsDirector,
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
        vat_number: form.vat_number || undefined,
        vat_liable: form.vat_liable,
        ape_code: form.ape_code || undefined,
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
        signatory_is_director: signatoryIsDirector,
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

  // Champs texte du formulaire : `vat_liable` est un booléen et se pilote par
  // sa propre case à cocher, pas par ce raccourci.
  type TextFieldKey = {
    [K in keyof typeof form]: (typeof form)[K] extends string ? K : never;
  }[keyof typeof form];

  const field = (key: TextFieldKey) => ({
    value: form[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value })),
    className: INPUT_CLS,
  });

  return (
    <div className="p-card mt-3.5">
      <h2 className="ct">Informations de votre structure</h2>
      <p className="cs">
        Renseignez vos coordonnées légales pour démarrer la collecte de documents.
      </p>

      {/* Entity category */}
      <div className="mt-4">
        <span className="f-lab">Structure juridique *</span>
        {isPortageSalarial ? (
          <div className="tcard on">
            <p className="tt">Société de portage salarial</p>
            <p className="td2">Votre structure est une société de portage salarial</p>
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
                className={`tcard text-left ${entityCategory === value ? 'on' : ''}`}
              >
                <p className="tt">{label}</p>
                <p className="td2">{sub}</p>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Identité */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        <div>
          <label className="f-lab">SIRET *</label>
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
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-prit" />
            )}
          </div>
          <p className="f-hint">Les informations seront pré-remplies automatiquement.</p>
        </div>
        <div>
          <label className="f-lab">
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
            <label className="f-lab">Ville du greffe *</label>
            <input
              type="text"
              {...field('rcs_city')}
              placeholder="Ex : Paris"
              className={INPUT_CLS}
            />
          </div>
        )}
        <div>
          <label className="f-lab">Forme juridique *</label>
          <select
            value={form.legal_form}
            onChange={(e) => setForm((f) => ({ ...f, legal_form: e.target.value }))}
            className={`${INPUT_CLS} !px-2.5`}
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
            <label className="f-lab">Capital social</label>
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
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[11.5px] text-mut2 pointer-events-none">
                EUR
              </span>
            </div>
          </div>
        )}
        <div>
          <label className="f-lab">N° TVA intracommunautaire</label>
          <input
            type="text"
            value={form.vat_liable ? form.vat_number : ''}
            readOnly
            tabIndex={-1}
            placeholder={
              form.vat_liable
                ? 'Calculé automatiquement à partir du SIRET'
                : 'Sans objet — non assujetti'
            }
            className={`${INPUT_CLS} !text-mut cursor-not-allowed`}
          />
          <label className="ds flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.vat_liable}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  vat_liable: e.target.checked,
                  vat_number:
                    e.target.checked && f.siret.length === 14 ? computeVatNumber(f.siret) : '',
                }))
              }
            />
            Ma société est assujettie à la TVA
          </label>
        </div>
        <div>
          <label className="f-lab">Code APE / NAF</label>
          <input
            type="text"
            maxLength={6}
            value={form.ape_code}
            onChange={(e) => setForm((f) => ({ ...f, ape_code: e.target.value }))}
            placeholder="Ex : 6202A"
            className={INPUT_CLS}
          />
        </div>
        <div className="md:col-span-2">
          <label className="f-lab">Numéro et voie *</label>
          <input type="text" {...field('head_office_street')} placeholder="Ex : 12 rue de la Paix" className={INPUT_CLS} />
        </div>
        <div>
          <label className="f-lab">Code postal *</label>
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
          <label className="f-lab">Ville *</label>
          <input type="text" {...field('head_office_city')} placeholder="Ex : Paris" className={INPUT_CLS} />
        </div>
      </div>

      {/* Signataire du contrat (= représentant légal) */}
      <div className="border-t border-lin2 pt-4 mt-5">
        <p className="ct text-[13.5px] mb-3.5">Signataire du contrat</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="md:col-span-2">
            <div className="grid grid-cols-[auto_1fr_1fr] gap-2 items-end">
              <div>
                <label className="f-lab">Civilité *</label>
                <CivilitySelect value={signatory.civility} onChange={(v) => setSignatory((c) => ({ ...c, civility: v }))} />
              </div>
              <div>
                <label className="f-lab">Prénom *</label>
                <input
                  type="text"
                  value={signatory.first_name}
                  onChange={(e) => setSignatory((c) => ({ ...c, first_name: e.target.value }))}
                  placeholder="Prénom"
                  className={INPUT_CLS}
                />
              </div>
              <div>
                <label className="f-lab">Nom *</label>
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
            <label className="f-lab">E-mail *</label>
            <input
              type="email"
              value={signatory.email}
              onChange={(e) => setSignatory((c) => ({ ...c, email: e.target.value }))}
              placeholder="Ex : jean.dupont@entreprise.fr"
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label className="f-lab">Téléphone</label>
            <PhoneInput
              international
              defaultCountry="FR"
              value={signatory.phone}
              onChange={(val) => setSignatory((c) => ({ ...c, phone: val || '' }))}
              className="phone-input-container"
            />
          </div>
          <div className="md:col-span-2">
            <label className="f-lab">Qualité *</label>
            <input
              type="text"
              {...field('representative_title')}
              placeholder={!isSocieteOrPortage ? 'Ex : Entrepreneur individuel' : 'Ex : Président'}
              className={INPUT_CLS}
            />
          </div>
          <div className="md:col-span-2">
            <label className="ckrow select-none">
              <input
                type="checkbox"
                className="sr-only"
                checked={signatoryIsDirector}
                onChange={() => setSignatoryIsDirector((v) => !v)}
              />
              <span className={`ck ${signatoryIsDirector ? 'on' : ''}`}>
                <Check className="h-3 w-3" strokeWidth={3} />
              </span>
              Cette personne est le dirigeant de la société
            </label>
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

      {/* Contact commercial */}
      <ContactSection
        title="Contact commercial"
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
    </div>
  );
}

function PortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="p-bg">
      <div className="p-wrap">
        <div className="p-top">
          <span className="logo">Bobby · Portail partenaire</span>
        </div>
        {children}
        <p className="p-foot">Lien d'accès sécurisé et personnel · ne le partagez pas</p>
      </div>
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
    <div className="mt-5 border-t border-lin2 pt-5 text-center">
      <p className="notec">
        Une fois tous vos documents déposés, validez votre dépôt pour notifier notre équipe.
      </p>
      <Button
        className="mt-3.5 min-w-48"
        onClick={() => submitMutation.mutate()}
        disabled={!enabled || submitMutation.isPending}
        isLoading={submitMutation.isPending}
        leftIcon={<CheckCircle className="h-4 w-4" />}
      >
        Valider le dépôt des documents
      </Button>
      {expiredBlocked && (
        <p className="f-hint !text-redt mt-2.5">
          Un ou plusieurs documents sont expirés. Veuillez les remplacer avant de valider.
        </p>
      )}
      {!enabled && !expiredBlocked && (
        <p className="f-hint mt-2.5">
          Chaque document doit être téléversé ou signalé comme indisponible avec une raison.
        </p>
      )}
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
    // Validate extension too (not just size) — the input `accept` attribute doesn't
    // constrain drag-and-drop, so this also guards the handleDrop path.
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!['pdf', 'jpg', 'jpeg', 'png'].includes(ext)) {
      toast.error('Format non supporté. Formats acceptés : PDF, JPG, PNG.');
      return;
    }
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
    if (!unavailReason.trim()) return;
    // Only call API if value differs from what's already on the server
    if (unavailReason === doc.unavailability_reason) return;
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
    <div
      className="p-doc flex-wrap items-start"
      onDragOver={needsUpload ? (e) => { e.preventDefault(); setDragOver(true); } : undefined}
      onDragLeave={needsUpload ? () => setDragOver(false) : undefined}
      onDrop={needsUpload ? handleDrop : undefined}
    >
      <div className="dico mt-0.5">
        <FileText className="h-4 w-4" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="dn">{doc.display_name}</p>
          {doc.validity_label && <span className="st st-amb">{doc.validity_label}</span>}
        </div>
        <p className="ds mt-0.5 truncate">
          {doc.file_name && !doc.is_unavailable ? doc.file_name : statusLabel}
        </p>
        {doc.rejection_reason && (
          <p className="text-[11.5px] text-redt mt-1">Motif du rejet : {doc.rejection_reason}</p>
        )}

        {/* AI-extracted data */}
        {!doc.is_unavailable && doc.document_type !== 'rib' && (doc.document_date || doc.extracted_info?.expiry_date) && (
          <div className="mt-1.5 space-y-1">
            {doc.document_date && (
              <p className="ds">
                <span className="font-semibold text-ink">Date du document :</span>{' '}
                {new Date(doc.document_date).toLocaleDateString('fr-FR')}
              </p>
            )}
            {doc.extracted_info?.expiry_date && (
              <p className="ds">
                <span className="font-semibold text-ink">Valide jusqu'au :</span>{' '}
                {new Date(doc.extracted_info.expiry_date).toLocaleDateString('fr-FR')}
              </p>
            )}
            {doc.is_valid_at_upload === true && (
              <span className="st st-grn">
                <span className="dot" />Valide
              </span>
            )}
            {doc.is_valid_at_upload === false && (
              <span className="st st-red">
                <span className="dot" />Document périmé
              </span>
            )}
          </div>
        )}
        {!doc.is_unavailable && doc.document_type === 'rib' && doc.extracted_info && (
          <div className="mt-1.5 space-y-0.5">
            {doc.extracted_info.beneficiaire && (
              <p className="ds">
                <span className="font-semibold text-ink">Bénéficiaire :</span> {doc.extracted_info.beneficiaire}
              </p>
            )}
            {doc.extracted_info.iban && (
              <p className="ds font-mono">
                <span className="font-sans font-semibold text-ink">IBAN :</span> {doc.extracted_info.iban}
              </p>
            )}
            {doc.extracted_info.bic && (
              <p className="ds font-mono">
                <span className="font-sans font-semibold text-ink">BIC :</span> {doc.extracted_info.bic}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Right side — status chip / upload button / actions */}
      <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
        {unavailChecked ? (
          <span className="st st-sla">
            <span className="dot" />Indisponible
          </span>
        ) : (
          doc.status !== 'requested' && (
            <span className={`st ${DOCUMENT_STATUS_CHIPS[doc.status] ?? 'st-sla'}`}>
              <span className="dot" />
              {DOCUMENT_STATUS_LABELS[doc.status] ?? doc.status}
            </span>
          )
        )}

        {needsUpload &&
          (uploadMutation.isPending ? (
            <span className="p-up !cursor-default inline-flex items-center gap-1.5">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Envoi en cours…
            </span>
          ) : (
            <label className={`p-up cursor-pointer ${dragOver ? '!border-pri !bg-pris' : ''}`}>
              Déposer le fichier
              <input
                type="file"
                className="hidden"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileSelect(f); }}
              />
            </label>
          ))}

        {/* "Changer" / delete actions for received documents */}
        {doc.status === 'received' && !unavailChecked && !showReplace && (
          <div className="flex items-center gap-2.5">
            {confirmDelete ? (
              <>
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate()}
                  disabled={deleteMutation.isPending}
                  className="text-[11.5px] font-semibold text-redt hover:underline disabled:opacity-50"
                >
                  {deleteMutation.isPending ? 'Suppression…' : 'Confirmer'}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmDelete(false)}
                  className="text-[11.5px] text-mut2 hover:underline"
                >
                  Annuler
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => setShowReplace(true)}
                  className="text-[11.5px] font-semibold text-prit hover:underline"
                >
                  Changer
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmDelete(true)}
                  title="Supprimer ce document"
                  className="p-0.5 rounded-md text-mut2 hover:text-redt hover:bg-red-bg transition-colors"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </>
            )}
          </div>
        )}
        {showReplace && (
          <button
            type="button"
            onClick={() => setShowReplace(false)}
            className="text-[11.5px] text-mut2 hover:underline"
          >
            Annuler
          </button>
        )}
      </div>

      {/* Banner for temporarily validated docs */}
      {isTempValidated && (
        <div className="w-full pl-[46px] mt-1">
          <div className="infob">
            Votre interlocuteur a pris acte de l'indisponibilité de ce document. Si vous
            l'avez obtenu depuis, vous pouvez le déposer ici.
          </div>
        </div>
      )}

      {/* "Je ne dispose pas de ce document" */}
      {!isTempValidated && (doc.status === 'requested' || doc.status === 'rejected' || doc.is_unavailable) && !showReplace && (
        <div className="w-full pl-[46px] mt-1">
          <label className="ckrow select-none">
            <input
              type="checkbox"
              className="sr-only"
              checked={unavailChecked}
              onChange={(e) => handleCheckboxChange(e.target.checked)}
              disabled={availabilityMutation.isPending}
            />
            <span className={`ck ${unavailChecked ? 'on' : ''}`}>
              <Check className="h-3 w-3" strokeWidth={3} />
            </span>
            Je ne dispose pas de ce document
          </label>

          {unavailChecked && (
            <div className="mt-2">
              <textarea
                value={unavailReason}
                onChange={(e) => setUnavailReason(e.target.value)}
                onBlur={handleSaveReason}
                placeholder="Précisez la raison (ex : document en cours d'obtention, non applicable à notre situation…)"
                rows={3}
                maxLength={500}
                className="f-ta !min-h-[64px]"
              />
              <div className="flex items-center justify-between min-h-[1.25rem]">
                <span className="f-hint !mt-0.5">{unavailReason.length}/500</span>
                {availabilityMutation.isPending && (
                  <span className="f-hint !mt-0.5 flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" /> Enregistrement…
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ContractReviewSection({
  token,
  contractDraft,
}: {
  token: string;
  contractDraft?: { contract_request_id: string; status: string; contract_request_status?: string | null; download_url: string | null } | null;
}) {
  const [decision, setDecision] = useState<'approved' | 'changes_requested' | null>(null);
  const [comments, setComments] = useState('');

  const [submitted, setSubmitted] = useState<'approved' | 'changes_requested' | null>(null);

  // Sync submitted state from server once contractDraft loads (handles refresh)
  useEffect(() => {
    if (contractDraft?.contract_request_status === 'partner_approved') {
      setSubmitted('approved');
    } else if (contractDraft?.contract_request_status === 'partner_requested_changes') {
      setSubmitted('changes_requested');
    }
  }, [contractDraft]);

  const reviewMutation = useMutation({
    mutationFn: () => portalApi.submitContractReview(token, decision!, comments || undefined),
    onSuccess: () => {
      setSubmitted(decision);
    },
    onError: () => {
      toast.error('Erreur lors de la soumission.');
    },
  });

  if (submitted) {
    const isApproved = submitted === 'approved';
    return (
      <div className="p-card mt-3.5 text-center px-[22px] py-9">
        {isApproved ? (
          <div className="okbox !inline-flex !m-0 !mb-3.5">
            <CheckCircle className="h-4 w-4 flex-shrink-0" />
            <span>Contrat approuvé</span>
          </div>
        ) : (
          <div className="alert !inline-flex !mt-0 !mb-3.5">
            <AlertTriangle className="h-[18px] w-[18px] flex-shrink-0" />
            <span>Modifications demandées</span>
          </div>
        )}
        <p className="notec max-w-sm mx-auto">
          {isApproved
            ? 'Votre validation a bien été enregistrée. Nous allons procéder à l\'envoi du contrat en signature.'
            : 'Vos commentaires ont bien été transmis à notre équipe. Nous reviendrons vers vous après correction du contrat.'
          }
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="p-card mt-3.5">
        <h2 className="ct">Relecture du contrat</h2>
        <p className="cs">Veuillez relire le contrat ci-dessous et donner votre décision.</p>

        <div className="p-doc mt-3.5">
          <div className="dico">
            <FileText className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="dn">Draft du contrat</p>
            <p className="ds mt-0.5">
              {contractDraft?.download_url
                ? 'Relisez le document puis donnez votre décision ci-dessous.'
                : "Le document n'est pas encore disponible."}
            </p>
          </div>
          {contractDraft?.download_url && (
            <a
              href={contractDraft.download_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[12px] font-semibold text-prit hover:underline flex-shrink-0"
            >
              <Download className="h-3.5 w-3.5" />
              Télécharger
            </a>
          )}
        </div>

        {contractDraft?.download_url && (
          <iframe
            src={contractDraft.download_url}
            title="Brouillon du contrat"
            className="w-full rounded-xl border border-lin"
            style={{ height: '75vh', minHeight: '500px' }}
          />
        )}
      </div>

      <div className="p-card mt-3.5">
        <h3 className="ct">Votre décision</h3>

        <div className="f-grid mt-3.5">
          <button
            type="button"
            onClick={() => setDecision('approved')}
            className={`tcard text-center ${decision === 'approved' ? 'on' : ''}`}
          >
            <CheckCircle className={`h-5 w-5 mx-auto mb-1.5 ${decision === 'approved' ? 'text-prit' : 'text-mut2'}`} />
            <p className="tt">Approuver</p>
          </button>
          <button
            type="button"
            onClick={() => setDecision('changes_requested')}
            className={`tcard text-center ${decision === 'changes_requested' ? 'on' : ''}`}
          >
            <AlertTriangle className={`h-5 w-5 mx-auto mb-1.5 ${decision === 'changes_requested' ? 'text-prit' : 'text-mut2'}`} />
            <p className="tt">Demander des modifications</p>
          </button>
        </div>

        {decision === 'changes_requested' && (
          <textarea
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            placeholder="Décrivez les modifications souhaitées…"
            className="f-ta mt-3.5"
            rows={4}
          />
        )}

        {decision && (
          <Button
            className="w-full mt-4"
            onClick={() => reviewMutation.mutate()}
            disabled={reviewMutation.isPending || (decision === 'changes_requested' && !comments.trim())}
            isLoading={reviewMutation.isPending}
          >
            Confirmer ma décision
          </Button>
        )}
      </div>
    </div>
  );
}
