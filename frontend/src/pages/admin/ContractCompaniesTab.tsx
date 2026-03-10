import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Building2, Plus, Pencil, Trash2, Star, ImagePlus, X } from 'lucide-react';
import { toast } from 'sonner';
import { contractCompaniesApi, ContractCompany, ContractCompanyRequest } from '../../api/contracts';

const EMPTY_FORM: ContractCompanyRequest = {
  name: '',
  code: '',
  legal_form: '',
  capital: '',
  head_office: '',
  rcs_city: '',
  rcs_number: '',
  representative_is_entity: false,
  representative_name: '',
  representative_quality: '',
  representative_sub_name: '',
  representative_sub_quality: '',
  signatory_name: '',
  invoices_company_mail: '',
  color_code: '#4BBEA8',
  is_default: false,
  is_active: true,
};

const INPUT_CLS =
  'w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary';
const LABEL_CLS = 'block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1';

interface FormProps {
  initial: ContractCompanyRequest;
  onSubmit: (data: ContractCompanyRequest) => void;
  onCancel: () => void;
  isLoading: boolean;
}

function CompanyForm({ initial, onSubmit, onCancel, isLoading }: FormProps) {
  const [form, setForm] = useState<ContractCompanyRequest>(initial);
  const set = (field: keyof ContractCompanyRequest, value: unknown) =>
    setForm((f) => ({ ...f, [field]: value }));

  return (
    <div className="space-y-4">
      {/* Identité société */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-3">
          Identité de la société
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className={LABEL_CLS}>Nom de la société *</label>
            <input className={INPUT_CLS} value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="GEMINI" />
          </div>
          <div>
            <label className={LABEL_CLS}>Code (3 lettres) *</label>
            <input
              className={INPUT_CLS}
              value={form.code}
              onChange={(e) => set('code', e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 3))}
              placeholder="GEM"
              maxLength={3}
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Préfixe utilisé dans les références contrat : <span className="font-mono">{form.code.length === 3 ? form.code : 'XXX'}-2026-0001</span>
            </p>
          </div>
          <div>
            <label className={LABEL_CLS}>Forme juridique *</label>
            <input className={INPUT_CLS} value={form.legal_form} onChange={(e) => set('legal_form', e.target.value)} placeholder="SAS" />
          </div>
          <div>
            <label className={LABEL_CLS}>Capital *</label>
            <input className={INPUT_CLS} value={form.capital} onChange={(e) => set('capital', e.target.value)} placeholder="10 000 €" />
          </div>
          <div>
            <label className={LABEL_CLS}>Siège social *</label>
            <input className={INPUT_CLS} value={form.head_office} onChange={(e) => set('head_office', e.target.value)} placeholder="54 Avenue Hoche – 75008 Paris" />
          </div>
          <div>
            <label className={LABEL_CLS}>Ville RCS *</label>
            <input className={INPUT_CLS} value={form.rcs_city} onChange={(e) => set('rcs_city', e.target.value)} placeholder="Paris" />
          </div>
          <div>
            <label className={LABEL_CLS}>Numéro RCS *</label>
            <input className={INPUT_CLS} value={form.rcs_number} onChange={(e) => set('rcs_number', e.target.value)} placeholder="842 799 959" />
          </div>
        </div>
      </div>

      {/* Représentant légal */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-3">
          Représentant légal
        </p>

        <div className="flex items-center gap-3 mb-3">
          <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700 dark:text-gray-300">
            <input
              type="checkbox"
              checked={form.representative_is_entity}
              onChange={(e) => set('representative_is_entity', e.target.checked)}
              className="rounded border-gray-300"
            />
            Le représentant légal est une personne morale
          </label>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className={LABEL_CLS}>
              {form.representative_is_entity ? 'Nom de la société représentante *' : 'Nom du représentant *'}
            </label>
            <input
              className={INPUT_CLS}
              value={form.representative_name}
              onChange={(e) => set('representative_name', e.target.value)}
              placeholder={form.representative_is_entity ? 'SC Holding' : 'Madame Selma HIZEM'}
            />
          </div>
          <div>
            <label className={LABEL_CLS}>Qualité *</label>
            <input
              className={INPUT_CLS}
              value={form.representative_quality}
              onChange={(e) => set('representative_quality', e.target.value)}
              placeholder="Président"
            />
          </div>

          {form.representative_is_entity && (
            <>
              <div>
                <label className={LABEL_CLS}>Représentant physique de la société *</label>
                <input
                  className={INPUT_CLS}
                  value={form.representative_sub_name ?? ''}
                  onChange={(e) => set('representative_sub_name', e.target.value)}
                  placeholder="Madame Selma HIZEM"
                />
              </div>
              <div>
                <label className={LABEL_CLS}>Qualité du représentant physique</label>
                <input
                  className={INPUT_CLS}
                  value={form.representative_sub_quality ?? ''}
                  onChange={(e) => set('representative_sub_quality', e.target.value)}
                  placeholder="Présidente"
                />
              </div>
            </>
          )}

          <div>
            <label className={LABEL_CLS}>Nom du signataire (bloc signature) *</label>
            <input
              className={INPUT_CLS}
              value={form.signatory_name}
              onChange={(e) => set('signatory_name', e.target.value)}
              placeholder="Mme Selma HIZEM"
            />
          </div>
        </div>
      </div>

      {/* Facturation */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-3">
          Facturation
        </p>
        <div>
          <label className={LABEL_CLS}>Email de réception des factures</label>
          <input
            className={INPUT_CLS}
            type="email"
            value={form.invoices_company_mail ?? ''}
            onChange={(e) => set('invoices_company_mail', e.target.value || null)}
            placeholder="factures@exemple.fr"
          />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Utilisé dans le contrat pour la clause de facturation par email (variable <code>{'{{ invoices_company_mail }}'}</code>).
          </p>
        </div>
      </div>

      {/* Identité visuelle + options */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-3">
          Identité visuelle &amp; options
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className={LABEL_CLS}>Couleur principale</label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={form.color_code}
                onChange={(e) => set('color_code', e.target.value)}
                className="h-9 w-14 rounded border border-gray-300 dark:border-gray-600 cursor-pointer"
              />
              <input
                className={INPUT_CLS}
                value={form.color_code}
                onChange={(e) => set('color_code', e.target.value)}
                placeholder="#4BBEA8"
                maxLength={7}
              />
            </div>
          </div>
          <div className="flex flex-col gap-2 justify-end">
            <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700 dark:text-gray-300">
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={(e) => set('is_default', e.target.checked)}
                className="rounded border-gray-300"
              />
              Société par défaut
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700 dark:text-gray-300">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => set('is_active', e.target.checked)}
                className="rounded border-gray-300"
              />
              Active
            </label>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          Annuler
        </button>
        <button
          type="button"
          onClick={() => onSubmit(form)}
          disabled={isLoading}
          className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50"
        >
          {isLoading ? 'Enregistrement...' : 'Enregistrer'}
        </button>
      </div>
    </div>
  );
}

// ── Logo manager ──────────────────────────────────────────────────────────────

function LogoManager({ company }: { company: ContractCompany }) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loadingUrl, setLoadingUrl] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => contractCompaniesApi.uploadLogo(company.id, file),
    onSuccess: () => {
      toast.success('Logo mis à jour.');
      queryClient.invalidateQueries({ queryKey: ['contract-companies'] });
      setPreviewUrl(null);
    },
    onError: () => toast.error('Erreur lors de l\'upload du logo.'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => contractCompaniesApi.deleteLogo(company.id),
    onSuccess: () => {
      toast.success('Logo supprimé.');
      queryClient.invalidateQueries({ queryKey: ['contract-companies'] });
      setPreviewUrl(null);
    },
    onError: () => toast.error('Erreur lors de la suppression du logo.'),
  });

  const handleFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => setPreviewUrl(e.target?.result as string);
    reader.readAsDataURL(file);
    uploadMutation.mutate(file);
  };

  const handleViewLogo = async () => {
    if (previewUrl) { setPreviewUrl(null); return; }
    setLoadingUrl(true);
    try {
      const url = await contractCompaniesApi.getLogoUrl(company.id);
      setPreviewUrl(url);
    } catch {
      toast.error('Impossible de charger le logo.');
    } finally {
      setLoadingUrl(false);
    }
  };

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* Preview */}
      {previewUrl && (
        <div className="relative inline-block">
          <img
            src={previewUrl}
            alt="Logo"
            className="h-10 max-w-[120px] object-contain border border-gray-200 dark:border-gray-600 rounded p-1 bg-white"
          />
          <button
            onClick={() => setPreviewUrl(null)}
            className="absolute -top-1.5 -right-1.5 bg-gray-200 dark:bg-gray-700 rounded-full p-0.5"
          >
            <X className="h-3 w-3 text-gray-600 dark:text-gray-300" />
          </button>
        </div>
      )}

      {/* Upload button */}
      <button
        onClick={() => inputRef.current?.click()}
        disabled={uploadMutation.isPending}
        className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
        title="Uploader un logo"
      >
        <ImagePlus className="h-3.5 w-3.5" />
        {uploadMutation.isPending ? 'Upload...' : company.has_logo ? 'Remplacer' : 'Ajouter un logo'}
      </button>

      {/* View existing */}
      {company.has_logo && !previewUrl && (
        <button
          onClick={handleViewLogo}
          disabled={loadingUrl}
          className="text-xs px-2.5 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          {loadingUrl ? '...' : 'Voir le logo'}
        </button>
      )}

      {/* Delete */}
      {company.has_logo && (
        <button
          onClick={() => { if (confirm('Supprimer le logo ?')) deleteMutation.mutate(); }}
          disabled={deleteMutation.isPending}
          className="text-xs px-2.5 py-1.5 border border-red-200 dark:border-red-800 rounded text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/svg+xml,image/webp"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = ''; }}
      />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

export function ContractCompaniesTab() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<ContractCompany | null>(null);

  const { data: companies = [], isLoading } = useQuery({
    queryKey: ['contract-companies'],
    queryFn: contractCompaniesApi.list,
  });

  const createMutation = useMutation({
    mutationFn: contractCompaniesApi.create,
    onSuccess: () => {
      toast.success('Société créée.');
      queryClient.invalidateQueries({ queryKey: ['contract-companies'] });
      setShowForm(false);
    },
    onError: () => toast.error('Erreur lors de la création.'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ContractCompanyRequest }) =>
      contractCompaniesApi.update(id, data),
    onSuccess: () => {
      toast.success('Société mise à jour.');
      queryClient.invalidateQueries({ queryKey: ['contract-companies'] });
      setEditing(null);
    },
    onError: () => toast.error('Erreur lors de la mise à jour.'),
  });

  const deleteMutation = useMutation({
    mutationFn: contractCompaniesApi.delete,
    onSuccess: () => {
      toast.success('Société supprimée.');
      queryClient.invalidateQueries({ queryKey: ['contract-companies'] });
    },
    onError: () => toast.error('Erreur lors de la suppression.'),
  });

  const handleDelete = (company: ContractCompany) => {
    if (!confirm(`Supprimer la société "${company.name}" ?`)) return;
    deleteMutation.mutate(company.id);
  };

  if (isLoading) return <div className="text-sm text-gray-500 dark:text-gray-400">Chargement...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Building2 className="h-5 w-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Sociétés émettrices</h2>
          <span className="text-xs text-gray-400">({companies.length})</span>
        </div>
        {!showForm && !editing && (
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700"
          >
            <Plus className="h-4 w-4" />
            Ajouter
          </button>
        )}
      </div>

      {/* Create form */}
      {showForm && (
        <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-5 mb-6">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Nouvelle société</h3>
          <CompanyForm
            initial={EMPTY_FORM}
            onSubmit={(data) => createMutation.mutate(data)}
            onCancel={() => setShowForm(false)}
            isLoading={createMutation.isPending}
          />
        </div>
      )}

      {/* List */}
      {companies.length === 0 && !showForm ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Aucune société configurée. Ajoutez-en une pour l'utiliser comme émetteur de contrats.
        </p>
      ) : (
        <div className="space-y-4">
          {companies.map((company) => (
            <div
              key={company.id}
              className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
            >
              {/* Header */}
              <div
                className="flex items-center justify-between px-4 py-3"
                style={{ borderLeft: `4px solid ${company.color_code}` }}
              >
                <div className="flex items-center gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-gray-900 dark:text-white">
                        {company.legal_form} {company.name}
                      </span>
                      {company.is_default && (
                        <span className="flex items-center gap-1 text-xs bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 px-2 py-0.5 rounded-full">
                          <Star className="h-3 w-3" /> Par défaut
                        </span>
                      )}
                      {!company.is_active && (
                        <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-500 px-2 py-0.5 rounded-full">
                          Inactive
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      <span className="font-mono font-semibold text-primary">{company.code}</span>
                      {' · '}RCS {company.rcs_city} — {company.rcs_number} · {company.head_office}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setEditing(editing?.id === company.id ? null : company)}
                    className="p-1.5 text-gray-500 hover:text-primary rounded"
                    title="Modifier"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(company)}
                    className="p-1.5 text-gray-500 hover:text-red-500 rounded"
                    title="Supprimer"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Logo manager */}
              <div className="px-4 py-2 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-100 dark:border-gray-700">
                <LogoManager company={company} />
              </div>

              {/* Representative info */}
              <div className="px-4 py-2 bg-gray-50 dark:bg-gray-800/50 text-xs text-gray-600 dark:text-gray-400 border-t border-gray-100 dark:border-gray-700">
                {company.representative_is_entity ? (
                  <span>
                    Représentée par la société <strong>{company.representative_name}</strong> ({company.representative_quality})
                    {company.representative_sub_name && (
                      <span> · Représentée par <strong>{company.representative_sub_name}</strong>{company.representative_sub_quality ? `, ${company.representative_sub_quality}` : ''}</span>
                    )}
                  </span>
                ) : (
                  <span>
                    Représentée par <strong>{company.representative_name}</strong> ({company.representative_quality})
                  </span>
                )}
                <span className="ml-3">· Signataire : {company.signatory_name}</span>
                {company.invoices_company_mail && (
                  <span className="ml-3">· Factures : {company.invoices_company_mail}</span>
                )}
                <span className="ml-3 flex items-center gap-1 inline-flex">
                  · Couleur :
                  <span
                    className="inline-block w-3 h-3 rounded-full ml-1"
                    style={{ backgroundColor: company.color_code }}
                  />
                  {company.color_code}
                </span>
              </div>

              {/* Edit form */}
              {editing?.id === company.id && (
                <div className="p-5 border-t border-gray-200 dark:border-gray-700">
                  <CompanyForm
                    initial={{
                      name: company.name,
                      code: company.code,
                      legal_form: company.legal_form,
                      capital: company.capital,
                      head_office: company.head_office,
                      rcs_city: company.rcs_city,
                      rcs_number: company.rcs_number,
                      representative_is_entity: company.representative_is_entity,
                      representative_name: company.representative_name,
                      representative_quality: company.representative_quality,
                      representative_sub_name: company.representative_sub_name ?? '',
                      representative_sub_quality: company.representative_sub_quality ?? '',
                      signatory_name: company.signatory_name,
                      invoices_company_mail: company.invoices_company_mail ?? '',
                      color_code: company.color_code,
                      is_default: company.is_default,
                      is_active: company.is_active,
                    }}
                    onSubmit={(data) => updateMutation.mutate({ id: company.id, data })}
                    onCancel={() => setEditing(null)}
                    isLoading={updateMutation.isPending}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
