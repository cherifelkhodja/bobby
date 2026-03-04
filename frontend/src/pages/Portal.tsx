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
  Loader2,
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
              {portalInfo.third_party.company_name ?? portalInfo.third_party.contact_email}
            </p>
          </div>
        </div>
      </div>

      {/* Company info form — shown when SIRET not yet filled */}
      {isDocumentUpload && !portalInfo.third_party.siren && (
        <CompanyInfoForm
          token={token!}
          onSuccess={() => queryClient.invalidateQueries({ queryKey: ['portal', token] })}
        />
      )}

      {/* Document upload section — shown once company info is filled */}
      {isDocumentUpload && portalInfo.third_party.siren && docsData && (
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

const INPUT_CLS =
  'w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500';

type Civility = 'M.' | 'Mme';

interface ContactFields {
  civility: Civility | '';
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
}

const EMPTY_CONTACT: ContactFields = { civility: '', first_name: '', last_name: '', email: '', phone: '' };

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
    <div className="border-t border-gray-100 dark:border-gray-700 pt-5 mt-5">
      <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">{title}</p>
      {checkboxLabel && onToggleSameAsRep !== undefined && (
        <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 mb-3 cursor-pointer">
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
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Civilité / Prénom / Nom *</label>
            <div className="flex gap-2">
              <CivilitySelect value={contact.civility} onChange={(v) => onChange({ ...contact, civility: v })} />
              <input type="text" value={contact.first_name} onChange={set('first_name')} placeholder="Prénom" className={INPUT_CLS} />
              <input type="text" value={contact.last_name} onChange={set('last_name')} placeholder="Nom" className={INPUT_CLS} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">E-mail *</label>
            <input type="email" value={contact.email} onChange={set('email')} placeholder="Ex : jean.dupont@entreprise.fr" className={INPUT_CLS} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Téléphone</label>
            <input type="tel" value={contact.phone} onChange={set('phone')} placeholder="Ex : +33 6 12 34 56 78" className={INPUT_CLS} />
          </div>
        </div>
      )}
    </div>
  );
}

function CompanyInfoForm({ token, onSuccess }: { token: string; onSuccess: () => void }) {
  const [entityCategory, setEntityCategory] = useState<'ei' | 'societe'>('ei');
  const [form, setForm] = useState({
    company_name: '',
    legal_form: '',
    capital: '',
    siret: '',
    head_office_street: '',
    head_office_postal_code: '',
    head_office_city: '',
    rcs_city: '',
    representative_title: '',
  });
  const [siretLoading, setSiretLoading] = useState(false);
  const [signatory, setSignatory] = useState<ContactFields>(EMPTY_CONTACT);
  const [advContact, setAdvContact] = useState<ContactFields>(EMPTY_CONTACT);
  const [advIsSame, setAdvIsSame] = useState(false);
  const [billingContact, setBillingContact] = useState<ContactFields>(EMPTY_CONTACT);
  const [billingIsSame, setBillingIsSame] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

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
          capital: data.capital ?? f.capital,
          rcs_city: data.rcs_city ?? f.rcs_city,
        }));
        if (data.entity_category === 'ei' || data.entity_category === 'societe') {
          setEntityCategory(data.entity_category);
        }
        toast.success('Informations pré-remplies depuis INSEE Sirene + INPI.');
      } catch {
        // Silently ignore — user can fill manually
      } finally {
        setSiretLoading(false);
      }
    }
  };

  const isValid =
    /^\d{14}$/.test(form.siret) &&
    form.company_name !== '' &&
    form.legal_form !== '' &&
    form.head_office_street !== '' &&
    /^\d{5}$/.test(form.head_office_postal_code) &&
    form.head_office_city !== '' &&
    (entityCategory === 'ei' || form.rcs_city !== '') &&
    form.representative_title !== '' &&
    isContactValid(signatory) &&
    (advIsSame || isContactValid(advContact)) &&
    (billingIsSame || isContactValid(billingContact));

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
    } catch {
      toast.error("Erreur lors de l'enregistrement.");
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
              {entityCategory === 'ei' ? 'Nom commercial / Enseigne *' : 'Raison sociale *'}
            </label>
            <input
              type="text"
              {...field('company_name')}
              placeholder={entityCategory === 'ei' ? 'Ex : Jean Dupont Consulting' : 'Ex : Acme SAS'}
              className={INPUT_CLS}
            />
          </div>
          {entityCategory === 'societe' && (
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
            <input
              type="text"
              {...field('legal_form')}
              placeholder={entityCategory === 'ei' ? 'Ex : EI' : 'Ex : SAS'}
              className={INPUT_CLS}
            />
          </div>
          {entityCategory === 'societe' && (
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Capital social
              </label>
              <input type="text" {...field('capital')} placeholder="Ex : 10 000" className={INPUT_CLS} />
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
        <div className="border-t border-gray-100 dark:border-gray-700 pt-5 mt-5">
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
            Signataire du contrat
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Civilité / Prénom / Nom *</label>
              <div className="flex gap-2">
                <CivilitySelect value={signatory.civility} onChange={(v) => setSignatory((c) => ({ ...c, civility: v }))} />
                <input
                  type="text"
                  value={signatory.first_name}
                  onChange={(e) => setSignatory((c) => ({ ...c, first_name: e.target.value }))}
                  placeholder="Prénom"
                  className={INPUT_CLS}
                />
                <input
                  type="text"
                  value={signatory.last_name}
                  onChange={(e) => setSignatory((c) => ({ ...c, last_name: e.target.value }))}
                  placeholder="Nom"
                  className={INPUT_CLS}
                />
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
              <input
                type="tel"
                value={signatory.phone}
                onChange={(e) => setSignatory((c) => ({ ...c, phone: e.target.value }))}
                placeholder="Ex : +33 6 12 34 56 78"
                className={INPUT_CLS}
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Qualité *
              </label>
              <input
                type="text"
                {...field('representative_title')}
                placeholder={entityCategory === 'ei' ? 'Ex : Entrepreneur individuel' : 'Ex : Président'}
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

        <div className="flex justify-end mt-6">
          <Button onClick={handleSubmit} disabled={!isValid || isSubmitting} isLoading={isSubmitting}>
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
