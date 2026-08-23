import { useState, type ReactNode } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Search, Save, X } from 'lucide-react';
import { toast } from 'sonner';

import { contractsApi } from '../../api/contracts';
import type { ThirdPartyInfoInput } from '../../api/contracts';
import { getErrorMessage } from '../../api/client';
import { Button } from '../ui/Button';
import type { ThirdPartyWithDocuments } from '../../types';

const INPUT_CLS = 'f-in';
const SELECT_CLS = 'f-in !px-2.5';
const LABEL_CLS = 'f-lab';

interface Props {
  contractRequestId: string;
  initial: ThirdPartyWithDocuments;
  onSaved: () => void;
  onCancel: () => void;
}

function buildInitialForm(tp: ThirdPartyWithDocuments): ThirdPartyInfoInput {
  return {
    entity_category: tp.entity_category ?? 'societe',
    company_name: tp.company_name ?? '',
    legal_form: tp.legal_form ?? '',
    capital: tp.capital ?? '',
    siret: tp.siret ?? '',
    vat_number: tp.vat_number ?? '',
    vat_liable: tp.vat_liable ?? true,
    ape_code: tp.ape_code ?? '',
    head_office_street: tp.head_office_street ?? '',
    head_office_postal_code: tp.head_office_postal_code ?? '',
    head_office_city: tp.head_office_city ?? '',
    rcs_city: tp.rcs_city ?? '',
    representative_civility: tp.representative_civility ?? 'M.',
    representative_first_name: tp.representative_first_name ?? '',
    representative_last_name: tp.representative_last_name ?? '',
    representative_email: tp.representative_email ?? '',
    representative_phone: tp.representative_phone ?? '',
    representative_title: tp.representative_title ?? '',
    signatory_same_as_representative: false,
    signatory_civility: tp.signatory_civility ?? 'M.',
    signatory_first_name: tp.signatory_first_name ?? '',
    signatory_last_name: tp.signatory_last_name ?? '',
    signatory_email: tp.signatory_email ?? '',
    signatory_phone: tp.signatory_phone ?? '',
    signatory_is_director: tp.signatory_is_director ?? false,
    adv_contact_same_as_representative: false,
    adv_contact_civility: tp.adv_contact_civility ?? 'M.',
    adv_contact_first_name: tp.adv_contact_first_name ?? '',
    adv_contact_last_name: tp.adv_contact_last_name ?? '',
    adv_contact_email: tp.adv_contact_email ?? '',
    adv_contact_phone: tp.adv_contact_phone ?? '',
    billing_contact_same_as_representative: false,
    billing_contact_civility: tp.billing_contact_civility ?? 'M.',
    billing_contact_first_name: tp.billing_contact_first_name ?? '',
    billing_contact_last_name: tp.billing_contact_last_name ?? '',
    billing_contact_email: tp.billing_contact_email ?? '',
    billing_contact_phone: tp.billing_contact_phone ?? '',
  };
}

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function ThirdPartyInfoForm({ contractRequestId, initial, onSaved, onCancel }: Props) {
  const [form, setForm] = useState<ThirdPartyInfoInput>(() => buildInitialForm(initial));

  const set = <K extends keyof ThirdPartyInfoInput>(key: K, value: ThirdPartyInfoInput[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const lookupMutation = useMutation({
    mutationFn: () => contractsApi.lookupSiret((form.siret ?? '').replace(/\s/g, '')),
    onSuccess: (data) => {
      setForm((f) => ({
        ...f,
        company_name: data.company_name ?? f.company_name,
        legal_form: data.legal_form ?? f.legal_form,
        entity_category: data.entity_category ?? f.entity_category,
        capital: data.capital ?? f.capital,
        ape_code: data.ape_code ?? f.ape_code,
        rcs_city: data.rcs_city ?? f.rcs_city,
        head_office_street: data.head_office_street ?? f.head_office_street,
        head_office_postal_code: data.head_office_postal_code ?? f.head_office_postal_code,
        head_office_city: data.head_office_city ?? f.head_office_city,
      }));
      toast.success('Informations récupérées depuis l\'INSEE.');
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const saveMutation = useMutation({
    // Normalise the SIRET (strip spaces) at send time — setForm is async so we
    // can't rely on it having applied before mutate().
    mutationFn: () =>
      contractsApi.saveThirdPartyInfo(contractRequestId, {
        ...form,
        siret: (form.siret ?? '').replace(/\s/g, ''),
      }),
    onSuccess: () => {
      toast.success('Informations du tiers enregistrées.');
      onSaved();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const siretValid = /^\d{14}$/.test((form.siret ?? '').replace(/\s/g, ''));

  const errors: string[] = [];
  if (!siretValid) errors.push('Le SIRET doit comporter 14 chiffres.');
  if (!form.company_name.trim()) errors.push('La raison sociale est requise.');
  if (!form.legal_form.trim()) errors.push('La forme juridique est requise.');
  if (!form.head_office_street.trim()) errors.push('L\'adresse du siège est requise.');
  if (!/^\d{5}$/.test((form.head_office_postal_code ?? '').trim()))
    errors.push('Le code postal doit comporter 5 chiffres.');
  if (!form.head_office_city.trim()) errors.push('La ville du siège est requise.');
  if (!form.representative_first_name?.trim() || !form.representative_last_name?.trim())
    errors.push('Le nom du représentant légal est requis.');
  if (!EMAIL_RE.test((form.representative_email ?? '').trim()))
    errors.push('L\'email du représentant légal est requis et doit être valide.');
  if (!form.representative_title?.trim()) errors.push('La fonction du représentant est requise.');

  const canSave = errors.length === 0 && !saveMutation.isPending;

  const submit = () => {
    if (errors.length > 0) {
      toast.error(errors[0]);
      return;
    }
    saveMutation.mutate();
  };

  return (
    <div className="space-y-5">
      {/* SIRET + auto-fill */}
      <div>
        <label className={LABEL_CLS}>SIRET *</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={form.siret ?? ''}
            onChange={(e) => set('siret', e.target.value)}
            placeholder="14 chiffres"
            className={INPUT_CLS}
          />
          <Button
            type="button"
            variant="secondary"
            onClick={() => lookupMutation.mutate()}
            disabled={!siretValid || lookupMutation.isPending}
            isLoading={lookupMutation.isPending}
          >
            <Search className="h-4 w-4 mr-2" />
            Rechercher
          </Button>
        </div>
        <p className="f-hint">
          Renseignez le SIRET puis « Rechercher » pour préremplir automatiquement (INSEE + INPI).
        </p>
      </div>

      {/* Identity */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className={LABEL_CLS}>Type d'entité *</label>
          <select
            value={form.entity_category}
            onChange={(e) => set('entity_category', e.target.value)}
            className={SELECT_CLS}
          >
            <option value="societe">Société (SAS, SARL, EURL…)</option>
            <option value="ei">Entreprise individuelle / Micro</option>
            <option value="portage_salarial">Société de portage salarial</option>
          </select>
        </div>
        <div>
          <label className={LABEL_CLS}>Raison sociale *</label>
          <input
            type="text"
            value={form.company_name}
            onChange={(e) => set('company_name', e.target.value)}
            className={INPUT_CLS}
          />
        </div>
        <div>
          <label className={LABEL_CLS}>Forme juridique *</label>
          <input
            type="text"
            value={form.legal_form}
            onChange={(e) => set('legal_form', e.target.value)}
            placeholder="SAS, SARL, EI…"
            className={INPUT_CLS}
          />
        </div>
        <div>
          <label className={LABEL_CLS}>Capital social</label>
          <input
            type="text"
            value={form.capital ?? ''}
            onChange={(e) => set('capital', e.target.value)}
            placeholder="10 000"
            className={INPUT_CLS}
          />
        </div>
        <div>
          <label className={LABEL_CLS}>N° TVA intracommunautaire</label>
          <input
            type="text"
            value={form.vat_number ?? ''}
            onChange={(e) => set('vat_number', e.target.value)}
            placeholder={form.vat_liable === false ? 'Sans objet' : 'Calculé depuis le SIREN si vide'}
            disabled={form.vat_liable === false}
            className={INPUT_CLS}
          />
          <label className="ds flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.vat_liable !== false}
              onChange={(e) => set('vat_liable', e.target.checked)}
            />
            Assujetti à la TVA — décochez en franchise en base ou en autoliquidation, les bons
            de commande sont alors établis sans TVA.
          </label>
        </div>
        <div>
          <label className={LABEL_CLS}>Code APE/NAF</label>
          <input
            type="text"
            value={form.ape_code ?? ''}
            onChange={(e) => set('ape_code', e.target.value)}
            placeholder="6201Z"
            className={INPUT_CLS}
          />
        </div>
      </div>

      {/* Head office */}
      <div className="border-t border-lin2 pt-4">
        <p className="ml mb-3">Siège social</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="md:col-span-2">
            <label className={LABEL_CLS}>Adresse (rue) *</label>
            <input
              type="text"
              value={form.head_office_street}
              onChange={(e) => set('head_office_street', e.target.value)}
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label className={LABEL_CLS}>Code postal *</label>
            <input
              type="text"
              value={form.head_office_postal_code}
              onChange={(e) => set('head_office_postal_code', e.target.value)}
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label className={LABEL_CLS}>Ville *</label>
            <input
              type="text"
              value={form.head_office_city}
              onChange={(e) => set('head_office_city', e.target.value)}
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label className={LABEL_CLS}>Ville du greffe (RCS)</label>
            <input
              type="text"
              value={form.rcs_city ?? ''}
              onChange={(e) => set('rcs_city', e.target.value)}
              placeholder="Par défaut : ville du siège"
              className={INPUT_CLS}
            />
          </div>
        </div>
      </div>

      {/* Legal representative */}
      <div className="border-t border-lin2 pt-4">
        <p className="ml mb-3">Représentant légal</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className={LABEL_CLS}>Civilité *</label>
            <select
              value={form.representative_civility ?? 'M.'}
              onChange={(e) => set('representative_civility', e.target.value)}
              className={SELECT_CLS}
            >
              <option value="M.">M.</option>
              <option value="Mme">Mme</option>
            </select>
          </div>
          <div>
            <label className={LABEL_CLS}>Prénom *</label>
            <input
              type="text"
              value={form.representative_first_name}
              onChange={(e) => set('representative_first_name', e.target.value)}
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label className={LABEL_CLS}>Nom *</label>
            <input
              type="text"
              value={form.representative_last_name}
              onChange={(e) => set('representative_last_name', e.target.value)}
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label className={LABEL_CLS}>Fonction *</label>
            <input
              type="text"
              value={form.representative_title}
              onChange={(e) => set('representative_title', e.target.value)}
              placeholder="Président, Gérant…"
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label className={LABEL_CLS}>Email *</label>
            <input
              type="email"
              value={form.representative_email}
              onChange={(e) => set('representative_email', e.target.value)}
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label className={LABEL_CLS}>Téléphone</label>
            <input
              type="tel"
              value={form.representative_phone ?? ''}
              onChange={(e) => set('representative_phone', e.target.value)}
              className={INPUT_CLS}
            />
          </div>
        </div>
      </div>

      {/* Signatory */}
      <ContactBlock
        title="Signataire du contrat"
        sameChecked={!!form.signatory_same_as_representative}
        onSameChange={(v) => set('signatory_same_as_representative', v)}
        civility={form.signatory_civility}
        onCivility={(v) => set('signatory_civility', v)}
        firstName={form.signatory_first_name ?? ''}
        onFirstName={(v) => set('signatory_first_name', v)}
        lastName={form.signatory_last_name ?? ''}
        onLastName={(v) => set('signatory_last_name', v)}
        email={form.signatory_email ?? ''}
        onEmail={(v) => set('signatory_email', v)}
        phone={form.signatory_phone ?? ''}
        onPhone={(v) => set('signatory_phone', v)}
        extra={
          <label className="flex items-center gap-2.5 text-[12.5px] text-mut mt-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!form.signatory_is_director}
              onChange={(e) => set('signatory_is_director', e.target.checked)}
              className="rounded border-lin text-pri focus:ring-pri"
            />
            Cette personne est le dirigeant de la société
          </label>
        }
      />

      {/* ADV contact */}
      <ContactBlock
        title="Contact ADV"
        sameChecked={!!form.adv_contact_same_as_representative}
        onSameChange={(v) => set('adv_contact_same_as_representative', v)}
        civility={form.adv_contact_civility}
        onCivility={(v) => set('adv_contact_civility', v)}
        firstName={form.adv_contact_first_name ?? ''}
        onFirstName={(v) => set('adv_contact_first_name', v)}
        lastName={form.adv_contact_last_name ?? ''}
        onLastName={(v) => set('adv_contact_last_name', v)}
        email={form.adv_contact_email ?? ''}
        onEmail={(v) => set('adv_contact_email', v)}
        phone={form.adv_contact_phone ?? ''}
        onPhone={(v) => set('adv_contact_phone', v)}
      />

      {/* Billing contact */}
      <ContactBlock
        title="Contact facturation"
        sameChecked={!!form.billing_contact_same_as_representative}
        onSameChange={(v) => set('billing_contact_same_as_representative', v)}
        civility={form.billing_contact_civility}
        onCivility={(v) => set('billing_contact_civility', v)}
        firstName={form.billing_contact_first_name ?? ''}
        onFirstName={(v) => set('billing_contact_first_name', v)}
        lastName={form.billing_contact_last_name ?? ''}
        onLastName={(v) => set('billing_contact_last_name', v)}
        email={form.billing_contact_email ?? ''}
        onEmail={(v) => set('billing_contact_email', v)}
        phone={form.billing_contact_phone ?? ''}
        onPhone={(v) => set('billing_contact_phone', v)}
      />

      {errors.length > 0 && (
        <ul className="text-[12px] text-redt list-disc list-inside space-y-0.5">
          {errors.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          <X className="h-4 w-4 mr-2" />
          Annuler
        </Button>
        <Button type="button" onClick={submit} disabled={!canSave} isLoading={saveMutation.isPending}>
          <Save className="h-4 w-4 mr-2" />
          Enregistrer les informations
        </Button>
      </div>
    </div>
  );
}

interface ContactBlockProps {
  title: string;
  sameChecked: boolean;
  onSameChange: (v: boolean) => void;
  civility: string | null | undefined;
  onCivility: (v: string) => void;
  firstName: string;
  onFirstName: (v: string) => void;
  lastName: string;
  onLastName: (v: string) => void;
  email: string;
  onEmail: (v: string) => void;
  phone: string;
  onPhone: (v: string) => void;
  extra?: ReactNode;
}

function ContactBlock({
  title,
  sameChecked,
  onSameChange,
  civility,
  onCivility,
  firstName,
  onFirstName,
  lastName,
  onLastName,
  email,
  onEmail,
  phone,
  onPhone,
  extra,
}: ContactBlockProps) {
  return (
    <div className="border-t border-lin2 pt-4">
      <div className="flex items-center justify-between mb-3">
        <p className="ml !mb-0">{title}</p>
        <label className="flex items-center gap-2 text-[12px] text-mut cursor-pointer">
          <input
            type="checkbox"
            checked={sameChecked}
            onChange={(e) => onSameChange(e.target.checked)}
            className="rounded border-lin text-pri focus:ring-pri"
          />
          Identique au représentant légal
        </label>
      </div>
      {!sameChecked && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className={LABEL_CLS}>Civilité</label>
            <select
              value={civility ?? 'M.'}
              onChange={(e) => onCivility(e.target.value)}
              className={SELECT_CLS}
            >
              <option value="M.">M.</option>
              <option value="Mme">Mme</option>
            </select>
          </div>
          <div>
            <label className={LABEL_CLS}>Prénom</label>
            <input
              type="text"
              value={firstName}
              onChange={(e) => onFirstName(e.target.value)}
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label className={LABEL_CLS}>Nom</label>
            <input
              type="text"
              value={lastName}
              onChange={(e) => onLastName(e.target.value)}
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label className={LABEL_CLS}>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => onEmail(e.target.value)}
              className={INPUT_CLS}
            />
          </div>
          <div>
            <label className={LABEL_CLS}>Téléphone</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => onPhone(e.target.value)}
              className={INPUT_CLS}
            />
          </div>
        </div>
      )}
      {extra}
    </div>
  );
}
