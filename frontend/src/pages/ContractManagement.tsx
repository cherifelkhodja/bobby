import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { FileSignature, X, Trash2, Plus, ChevronRight, Building2 } from 'lucide-react';
import { toast } from 'sonner';

import { contractsApi, contractCompaniesApi } from '../api/contracts';
import { useAuthStore } from '../stores/authStore';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';
import { getErrorMessage } from '../api/client';
import type { ContractRequest, ContractRequestStatus, SupplierLookupResult } from '../types';
import { CONTRACT_STATUS_CONFIG } from '../types';

const THIRD_PARTY_TYPE_LABELS: Record<string, string> = {
  freelance: 'Freelance',
  sous_traitant: 'Sous-traitant',
  portage_salarial: 'Portage salarial',
  salarie: 'Salarié',
};

type FilterTab = 'all' | 'todo' | 'waiting' | 'done';

const CR_TERMINAL = new Set(['cancelled', 'signed', 'archived', 'redirected_payfit']);

// Statuts où la balle est chez le tiers (collecte, review, signature)
const WAITING_STATUSES = new Set<ContractRequestStatus>([
  'collecting_documents',
  'draft_sent_to_partner',
  'sent_for_signature',
]);
const DONE_STATUSES = new Set<ContractRequestStatus>([
  'signed',
  'active',
  'archived',
  'redirected_payfit',
  'cancelled',
]);

function tabOf(cr: ContractRequest): Exclude<FilterTab, 'all'> {
  if (DONE_STATUSES.has(cr.status)) return 'done';
  if (WAITING_STATUSES.has(cr.status)) return 'waiting';
  return 'todo';
}

function chipClass(status: ContractRequestStatus): string {
  return `st ${CONTRACT_STATUS_CONFIG[status]?.color ?? 'bg-sla-bg text-sla-fg'}`;
}

function StageSegments({ status }: { status: ContractRequestStatus }) {
  const config = CONTRACT_STATUS_CONFIG[status];
  const stage = config?.stage ?? 0;
  const blocked = config?.group === 'blocked';
  if (stage === 0) return null;
  return (
    <div className="prog">
      {[0, 1, 2, 3, 4, 5].map((j) => {
        let cls = 'seg';
        if (j < stage - 1 || stage === 6) cls = 'seg f';
        else if (j === stage - 1 && blocked) cls = 'seg fr';
        else if (j === stage - 1 && stage > 1) cls = 'seg f';
        return <span key={j} className={cls} />;
      })}
    </div>
  );
}

export function ContractManagement() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [page, setPage] = useState(0);
  const [filterTab, setFilterTab] = useState<FilterTab>('all');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [cancelTarget, setCancelTarget] = useState<{ id: string; reference: string } | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showSupplier, setShowSupplier] = useState(false);
  const [supplierForm, setSupplierForm] = useState({
    siret: '',
    third_party_type: 'sous_traitant',
    contact_email: '',
    company_id: '',
    collection: 'portal' as 'portal' | 'in_person',
    skip_documents: false,
    reuse_third_party_id: '' as string,
  });
  const [supplierLookup, setSupplierLookup] = useState<SupplierLookupResult | null>(null);
  const [createForm, setCreateForm] = useState<{
    boond_consultant_id: string;
    consultant_type: 'candidate' | 'resource';
    company_id: string;
  }>({ boond_consultant_id: '', consultant_type: 'candidate', company_id: '' });
  const pageSize = 20;
  // The group tabs span several statuses, and the API status_filter only accepts a
  // single status — so group filtering, counts and pagination are done client-side
  // over the full list, loaded in one request (capped at FETCH_LIMIT). Limitation:
  // beyond FETCH_LIMIT rows, counts/pages are capped; a server-side group-aware
  // filter would be needed to lift the cap.
  const FETCH_LIMIT = 500;

  const isAdv = user?.role === 'adv' || user?.role === 'admin';

  const { data: companies = [] } = useQuery({
    queryKey: ['contract-companies-active'],
    queryFn: contractCompaniesApi.listActive,
    enabled: isAdv,
  });

  // Contract requests query
  const { data: crData, isLoading: crLoading } = useQuery({
    queryKey: ['contract-requests', statusFilter],
    queryFn: () =>
      contractsApi.list({
        skip: 0,
        limit: FETCH_LIMIT,
        ...(statusFilter ? { status_filter: statusFilter as ContractRequestStatus } : {}),
      }),
  });

  const lookupSupplierMutation = useMutation({
    mutationFn: (siret: string) =>
      contractsApi.lookupSupplier(siret, supplierForm.company_id || null),
    onSuccess: (result) => {
      setSupplierLookup(result);
      if (result.exists && result.third_party_id) {
        setSupplierForm((f) => ({ ...f, reuse_third_party_id: result.third_party_id ?? '' }));
      }
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const createSupplierMutation = useMutation({
    mutationFn: () =>
      contractsApi.createSupplierDossier({
        third_party_type: supplierForm.third_party_type,
        contact_email: supplierForm.contact_email.trim(),
        company_id: supplierForm.company_id || null,
        siret: supplierForm.siret.trim() || null,
        reuse_third_party_id: supplierForm.reuse_third_party_id || null,
        notify_third_party: supplierForm.collection === 'portal',
        skip_documents: supplierForm.collection === 'in_person' && supplierForm.skip_documents,
      }),
    onSuccess: (cr) => {
      toast.success(`Dossier ${cr.display_reference} ouvert.`);
      setShowSupplier(false);
      setSupplierLookup(null);
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
      navigate(`/contracts/${cr.id}`);
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const cancelCrMutation = useMutation({
    mutationFn: (id: string) => contractsApi.cancel(id),
    onSuccess: () => {
      toast.success('Demande de contrat annulée.');
      setCancelTarget(null);
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const purgeCrMutation = useMutation({
    mutationFn: (id: string) => contractsApi.purge(id),
    onSuccess: () => {
      toast.success('Demande supprimée.');
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const createManualMutation = useMutation({
    mutationFn: () =>
      contractsApi.createManual({
        boond_consultant_id: parseInt(createForm.boond_consultant_id, 10),
        consultant_type: createForm.consultant_type,
        company_id: createForm.company_id || undefined,
      }),
    onSuccess: (cr) => {
      toast.success('Dossier de contrat créé.');
      setShowCreate(false);
      setCreateForm({ boond_consultant_id: '', consultant_type: 'candidate', company_id: '' });
      queryClient.invalidateQueries({ queryKey: ['contract-requests'] });
      navigate(`/contracts/${cr.id}`);
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const createConsultantIdValid = /^\d+$/.test(createForm.boond_consultant_id.trim());

  if (crLoading) return <PageSpinner />;

  const items = crData?.items ?? [];

  // KPIs
  const activeItems = items.filter((cr) => !DONE_STATUSES.has(cr.status));
  const waitingCount = items.filter((cr) => tabOf(cr) === 'waiting').length;
  const todoCount = items.filter((cr) => tabOf(cr) === 'todo').length;
  const blockedCount = items.filter((cr) => cr.status === 'compliance_blocked').length;

  const counts: Record<FilterTab, number> = {
    all: items.length,
    todo: todoCount,
    waiting: waitingCount,
    done: items.filter((cr) => tabOf(cr) === 'done').length,
  };

  const filtered = items
    .filter((cr) => (filterTab === 'all' ? true : tabOf(cr) === filterTab))
    .sort((a, b) => {
      // Tri : échéance de démarrage (nulls en dernier)
      if (!a.start_date && !b.start_date) return 0;
      if (!a.start_date) return 1;
      if (!b.start_date) return -1;
      return a.start_date.localeCompare(b.start_date);
    });

  const paged = filtered.slice(page * pageSize, page * pageSize + pageSize);

  const gridCols = 'grid-cols-[92px_1.5fr_120px_120px_80px_210px_60px]';

  const selectedCompanyName =
    companies.find((c) => c.id === supplierForm.company_id)?.name ?? 'cette société';
  // Cadres signés avec les AUTRES sociétés du groupe : ils n'autorisent rien
  // ici, mais disent à l'ADV que le fournisseur est déjà connu contractuellement.
  const otherCompanyFrameworks = (supplierLookup?.framework_contracts ?? []).filter(
    (f) => f.issuer_company_id !== supplierForm.company_id,
  );

  return (
    <div>
      <p className="bc">Contrats / Fournisseurs</p>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="h1">Fournisseurs</h1>
          <p className="sub">
            {isAdv
              ? 'Un contrat cadre par fournisseur et par société émettrice · les missions se rattachent en bons de commande'
              : 'Vos dossiers fournisseurs'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(0);
            }}
            className="filter-select"
          >
            <option value="">Tous les statuts</option>
            {Object.entries(CONTRACT_STATUS_CONFIG).map(([value, { label }]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          {isAdv && (
            <>
              <Button
                variant="secondary"
                onClick={() => setShowCreate(true)}
                leftIcon={<Plus className="h-3.5 w-3.5" />}
              >
                Depuis un consultant
              </Button>
              <Button
                onClick={() => setShowSupplier(true)}
                leftIcon={<Building2 className="h-3.5 w-3.5" />}
              >
                Nouveau fournisseur
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="kpis">
        <div className="kpi">
          <p className="kl">Dossiers en cours</p>
          <p className="kv">{activeItems.length}</p>
          <p className="ks">sur {items.length} au total</p>
        </div>
        <div className="kpi">
          <p className="kl">En attente du tiers</p>
          <p className="kv">{waitingCount}</p>
          <p className="ks">Relances auto J+3 · J+7 · J+14</p>
        </div>
        <div className="kpi">
          <p className="kl">À traiter par l'ADV</p>
          <p className="kv">{todoCount}</p>
          <p className="ks">validation, conformité, brouillons</p>
        </div>
        <div className="kpi">
          <p className="kl">Bloquées conformité</p>
          <p className={`kv ${blockedCount > 0 ? 'red' : ''}`}>{blockedCount}</p>
          <p className="ks">documents manquants ou expirés</p>
        </div>
      </div>

      <div className="tabs">
        {(
          [
            { key: 'all' as FilterTab, label: 'Tous' },
            { key: 'todo' as FilterTab, label: 'À traiter' },
            { key: 'waiting' as FilterTab, label: 'En attente du tiers' },
            { key: 'done' as FilterTab, label: 'Sous contrat' },
          ]
        ).map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => {
              setFilterTab(key);
              setPage(0);
            }}
            className={`tab ${filterTab === key ? 'on' : ''}`}
          >
            {label} · {counts[key]}
          </button>
        ))}
        <span className="sort">Trier : dossier le plus récent</span>
      </div>

      {filtered.length === 0 ? (
        <div className="card text-center py-12">
          <FileSignature className="h-10 w-10 text-mut2 mx-auto mb-4" />
          <p className="dn">Aucun dossier fournisseur</p>
          <p className="ds mt-1.5">
            Ouvrez-en un avec « Nouveau fournisseur », ou depuis un consultant déjà connu de
            BoondManager.
          </p>
        </div>
      ) : (
        <div className="tbl">
          <div className={`thead ${gridCols}`}>
            <span>Réf.</span>
            <span>Fournisseur</span>
            <span>Type</span>
            <span>Société émettrice</span>
            <span>Missions</span>
            <span>Étape</span>
            <span></span>
          </div>
          {paged.map((cr) => {
            // Le fournisseur est le sujet du dossier ; le consultant, quand il
            // y en a un, n'est que ce qui l'a fait ouvrir.
            const consultantName = [cr.consultant_first_name, cr.consultant_last_name]
              .filter(Boolean)
              .join(' ');
            const thirdPartyLabel = cr.third_party_type
              ? THIRD_PARTY_TYPE_LABELS[cr.third_party_type] ?? cr.third_party_type
              : '—';
            return (
              <div
                key={cr.id}
                className={`row click ${gridCols} group`}
                onClick={() => navigate(`/contracts/${cr.id}`)}
              >
                <span className="ref">{cr.display_reference}</span>
                <div className="min-w-0">
                  <p className="nm truncate">
                    {cr.third_party_name ?? 'Société à identifier'}
                  </p>
                  <p className="ns truncate">
                    {consultantName
                      ? `Ouvert pour ${cr.consultant_civility ? `${cr.consultant_civility} ` : ''}${consultantName}`
                      : 'Dossier fournisseur'}
                  </p>
                </div>
                <span className="cell truncate">{thirdPartyLabel}</span>
                <span className="cell truncate">{cr.company_name ?? '—'}</span>
                <span className="cell">
                  {cr.purchase_orders_count > 0 ? cr.purchase_orders_count : '—'}
                </span>
                <div>
                  <span className={chipClass(cr.status)}>
                    <span className="dot" />
                    {CONTRACT_STATUS_CONFIG[cr.status]?.label ?? cr.status_display}
                  </span>
                  <StageSegments status={cr.status} />
                </div>
                <div className="flex items-center justify-end gap-1">
                  {isAdv && !CR_TERMINAL.has(cr.status) && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setCancelTarget({ id: cr.id, reference: cr.display_reference });
                      }}
                      className="p-1 rounded-md text-mut2 opacity-0 group-hover:opacity-100 hover:text-redt hover:bg-red-bg transition-all"
                      title="Annuler"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                  {isAdv && cr.status === 'cancelled' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`Supprimer définitivement ${cr.display_reference} ?`)) {
                          purgeCrMutation.mutate(cr.id);
                        }
                      }}
                      className="p-1 rounded-md text-mut2 opacity-0 group-hover:opacity-100 hover:text-redt hover:bg-red-bg transition-all"
                      title="Supprimer définitivement"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                  <ChevronRight className="h-4 w-4 chev shrink-0" />
                </div>
              </div>
            );
          })}
          <div className="tfoot">
            <span>
              {filtered.length} dossier{filtered.length > 1 ? 's' : ''}
              {statusFilter &&
                ` · filtre : ${CONTRACT_STATUS_CONFIG[statusFilter as ContractRequestStatus]?.label ?? statusFilter}`}
            </span>
            {filtered.length > pageSize && (
              <span className="flex items-center gap-2">
                <button
                  type="button"
                  className="alink disabled:opacity-40"
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                >
                  ← Précédent
                </button>
                <span>
                  Page {page + 1} / {Math.ceil(filtered.length / pageSize)}
                </span>
                <button
                  type="button"
                  className="alink disabled:opacity-40"
                  disabled={(page + 1) * pageSize >= filtered.length}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Suivant →
                </button>
              </span>
            )}
          </div>
        </div>
      )}

      {/* Cancel confirmation modal */}
      <Modal
        isOpen={!!cancelTarget}
        onClose={() => setCancelTarget(null)}
        title="Annuler la demande de contrat"
      >
        {cancelTarget && (
          <div className="space-y-4">
            <p className="notec">
              Voulez-vous vraiment annuler la demande{' '}
              <span className="font-semibold text-ink">{cancelTarget.reference}</span> ?
            </p>
            <p className="text-[12.5px] text-redt">Cette action est irréversible.</p>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="secondary"
                onClick={() => setCancelTarget(null)}
                disabled={cancelCrMutation.isPending}
              >
                Non, garder
              </Button>
              <Button
                variant="danger"
                onClick={() => cancelCrMutation.mutate(cancelTarget.id)}
                isLoading={cancelCrMutation.isPending}
              >
                Oui, annuler
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Manual creation modal */}
      <Modal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        title="Nouveau contrat (saisie manuelle)"
      >
        <div className="space-y-4">
          <p className="notec">
            Créez un dossier de contrat sans déclencheur Boond. Saisissez l'ID Boond du
            consultant : son identité est récupérée automatiquement depuis Boond.
          </p>
          <div>
            <label className="f-lab">Le consultant est un… *</label>
            <div className="grid grid-cols-2 gap-2">
              {(
                [
                  {
                    key: 'candidate' as const,
                    label: 'Candidat',
                    hint: 'Converti en ressource à la signature',
                  },
                  {
                    key: 'resource' as const,
                    label: 'Ressource',
                    hint: 'Déjà une ressource dans Boond',
                  },
                ]
              ).map(({ key, label, hint }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setCreateForm((f) => ({ ...f, consultant_type: key }))}
                  className={`tcard text-left ${createForm.consultant_type === key ? 'on' : ''}`}
                >
                  <span className="tt">{label}</span>
                  <span className="td2 block">{hint}</span>
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="f-lab">ID Boond du consultant *</label>
            <input
              type="text"
              inputMode="numeric"
              value={createForm.boond_consultant_id}
              onChange={(e) =>
                setCreateForm((f) => ({
                  ...f,
                  boond_consultant_id: e.target.value.replace(/[^\d]/g, ''),
                }))
              }
              placeholder="Ex : 4242"
              className="f-in"
              autoFocus
            />
          </div>
          <div>
            <label className="f-lab">Société émettrice</label>
            <select
              value={createForm.company_id}
              onChange={(e) => setCreateForm((f) => ({ ...f, company_id: e.target.value }))}
              className="f-in !px-2.5"
            >
              <option value="">Sélectionner (optionnel)…</option>
              {companies
                .filter((c) => c.is_active)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.code})
                  </option>
                ))}
            </select>
          </div>
          <p className="f-hint">
            Le type de tiers et les autres informations seront renseignés à l'étape de validation
            commerciale.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="secondary"
              onClick={() => setShowCreate(false)}
              disabled={createManualMutation.isPending}
            >
              Annuler
            </Button>
            <Button
              onClick={() => createManualMutation.mutate()}
              disabled={!createConsultantIdValid || createManualMutation.isPending}
              isLoading={createManualMutation.isPending}
            >
              Créer le dossier
            </Button>
          </div>
        </div>
      </Modal>

      {/* Ouverture d'un dossier fournisseur : ni consultant, ni positionnement */}
      <Modal
        isOpen={showSupplier}
        onClose={() => setShowSupplier(false)}
        title="Nouveau fournisseur"
        size="lg"
      >
        <div className="space-y-4">
          <p className="notec">
            Ouvre un contrat cadre pour une société, indépendamment de toute mission. Les missions
            se rattachent ensuite via des bons de commande.
          </p>

          <div>
            <label className="f-lab">Société émettrice *</label>
            <select
              value={supplierForm.company_id}
              onChange={(e) => {
                setSupplierForm((f) => ({ ...f, company_id: e.target.value }));
                setSupplierLookup(null);
              }}
              className="f-in !px-2.5"
            >
              <option value="">Sélectionner…</option>
              {companies
                .filter((c) => c.is_active)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.code})
                  </option>
                ))}
            </select>
            <p className="f-hint">
              Le contrat cadre lie le fournisseur à cette société : un contrat signé avec
              l'une du groupe ne couvre pas les missions émises par une autre.
            </p>
          </div>

          <div>
            <label className="f-lab">SIRET du fournisseur</label>
            <div className="flex gap-2">
              <input
                type="text"
                inputMode="numeric"
                value={supplierForm.siret}
                onChange={(e) => {
                  setSupplierForm((f) => ({ ...f, siret: e.target.value, reuse_third_party_id: '' }));
                  setSupplierLookup(null);
                }}
                placeholder="Ex : 894 213 669 00017"
                className="f-in"
                autoFocus
              />
              <Button
                variant="secondary"
                onClick={() => lookupSupplierMutation.mutate(supplierForm.siret.trim())}
                disabled={
                  !supplierForm.company_id ||
                  supplierForm.siret.replace(/\D/g, '').length < 9 ||
                  lookupSupplierMutation.isPending
                }
                isLoading={lookupSupplierMutation.isPending}
              >
                Rechercher
              </Button>
            </div>
            <p className="f-hint">
              Recherche la société dans le panel pour éviter d'ouvrir une seconde fiche.
            </p>
          </div>

          {supplierLookup && (
            <div className="alert">
              {supplierLookup.exists ? (
                <span>
                  <b>{supplierLookup.company_name ?? 'Fournisseur connu'}</b> est déjà au panel.{' '}
                  {supplierLookup.has_framework_contract ? (
                    <>
                      Contrat cadre signé avec <b>{selectedCompanyName}</b> (
                      {supplierLookup.framework_contract_reference}).
                    </>
                  ) : otherCompanyFrameworks.length > 0 ? (
                    <>
                      Sous contrat avec{' '}
                      <b>
                        {otherCompanyFrameworks
                          .map((f) => f.issuer_company_name ?? f.reference)
                          .join(', ')}
                      </b>
                      , mais aucun cadre avec <b>{selectedCompanyName}</b> : ce dossier en
                      ouvrira un.
                    </>
                  ) : (
                    <>Aucun contrat cadre signé à ce jour.</>
                  )}
                  {supplierLookup.open_contract_request_id
                    ? ' Un dossier est déjà en cours pour cette société.'
                    : ''}{' '}
                  Ses documents de vigilance encore valides seront réutilisés.
                </span>
              ) : (
                <span>Aucune société connue avec ce SIRET : une nouvelle fiche sera créée.</span>
              )}
            </div>
          )}

          <div>
            <label className="f-lab">Type de tiers *</label>
            <div className="grid grid-cols-2 gap-2">
              {(
                [
                  { key: 'sous_traitant', label: 'Sous-traitant', hint: 'Société de prestation' },
                  { key: 'freelance', label: 'Freelance', hint: 'Indépendant, EI ou société' },
                  { key: 'portage_salarial', label: 'Portage salarial', hint: 'Société de portage' },
                  { key: 'salarie', label: 'Salarié', hint: 'Redirigé vers PayFit' },
                ] as const
              ).map(({ key, label, hint }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setSupplierForm((f) => ({ ...f, third_party_type: key }))}
                  className={`tcard text-left ${supplierForm.third_party_type === key ? 'on' : ''}`}
                >
                  <span className="tt">{label}</span>
                  <span className="td2 block">{hint}</span>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="f-lab">Email de contact contractualisation *</label>
            <input
              type="email"
              value={supplierForm.contact_email}
              onChange={(e) => setSupplierForm((f) => ({ ...f, contact_email: e.target.value }))}
              placeholder="contact@fournisseur.fr"
              className="f-in"
            />
          </div>

          <div>
            <label className="f-lab">Collecte des documents *</label>
            <div className="grid grid-cols-2 gap-2">
              {(
                [
                  {
                    key: 'portal' as const,
                    label: 'Portail fournisseur',
                    hint: 'Lien sécurisé envoyé au contact',
                  },
                  {
                    key: 'in_person' as const,
                    label: 'Je saisis en personne',
                    hint: 'Aucun email au fournisseur',
                  },
                ]
              ).map(({ key, label, hint }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() =>
                    setSupplierForm((f) => ({
                      ...f,
                      collection: key,
                      skip_documents: key === 'portal' ? false : f.skip_documents,
                    }))
                  }
                  className={`tcard text-left ${supplierForm.collection === key ? 'on' : ''}`}
                >
                  <span className="tt">{label}</span>
                  <span className="td2 block">{hint}</span>
                </button>
              ))}
            </div>
            {supplierForm.collection === 'in_person' && (
              <label className="flex items-center gap-2 mt-3 ds">
                <input
                  type="checkbox"
                  checked={supplierForm.skip_documents}
                  onChange={(e) =>
                    setSupplierForm((f) => ({ ...f, skip_documents: e.target.checked }))
                  }
                />
                Vigilance documentaire traitée hors Bobby (dérogation tracée)
              </label>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="secondary"
              onClick={() => setShowSupplier(false)}
              disabled={createSupplierMutation.isPending}
            >
              Annuler
            </Button>
            <Button
              onClick={() => createSupplierMutation.mutate()}
              disabled={
                !supplierForm.company_id ||
                !supplierForm.contact_email.includes('@') ||
                createSupplierMutation.isPending
              }
              isLoading={createSupplierMutation.isPending}
            >
              Ouvrir le dossier
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
