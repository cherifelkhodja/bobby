import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { FileSignature, X, Trash2, User, Building2, Plus } from 'lucide-react';
import { toast } from 'sonner';

import { contractsApi, contractCompaniesApi } from '../api/contracts';
import { useAuthStore } from '../stores/authStore';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';
import { getErrorMessage } from '../api/client';
import type { ContractRequestStatus } from '../types';
import { CONTRACT_STATUS_CONFIG } from '../types';

const THIRD_PARTY_TYPE_LABELS: Record<string, string> = {
  freelance: 'Freelance',
  sous_traitant: 'Sous-traitant',
  portage_salarial: 'Portage salarial',
  salarie: 'Salarié',
};

type FilterTab = 'all' | 'active' | 'done';

const CR_TERMINAL = new Set(['cancelled', 'signed', 'archived', 'redirected_payfit']);

export function ContractManagement() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [page, setPage] = useState(0);
  const [filterTab, setFilterTab] = useState<FilterTab>('all');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [cancelTarget, setCancelTarget] = useState<{ id: string; reference: string } | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<{
    boond_consultant_id: string;
    consultant_type: 'candidate' | 'resource';
    company_id: string;
  }>({ boond_consultant_id: '', consultant_type: 'candidate', company_id: '' });
  const pageSize = 20;
  // The group tabs (Tous / En cours / Finalisés) span several statuses, and the API
  // status_filter only accepts a single status — so group filtering, counts and
  // pagination are done client-side over the full list, loaded in one request (capped
  // at FETCH_LIMIT). Limitation: beyond FETCH_LIMIT rows, counts/pages are capped;
  // a server-side group-aware filter would be needed to lift the cap.
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

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });

  if (crLoading) return <PageSpinner />;

  // ── Contract requests list ────────────────────────────────────────
  const renderContractsList = () => {
    const items = crData?.items ?? [];
    const filtered = items.filter((cr) => {
      if (filterTab === 'all') return true;
      const g = CONTRACT_STATUS_CONFIG[cr.status]?.group;
      if (filterTab === 'active') return g === 'active' || g === 'blocked';
      return g === 'done';
    });

    const counts = {
      all: items.length,
      active: items.filter((cr) => { const g = CONTRACT_STATUS_CONFIG[cr.status]?.group; return g === 'active' || g === 'blocked'; }).length,
      done: items.filter((cr) => CONTRACT_STATUS_CONFIG[cr.status]?.group === 'done').length,
    };

    const paged = filtered.slice(page * pageSize, page * pageSize + pageSize);

    return (
      <>
        {renderFilterTabs(counts, CONTRACT_STATUS_CONFIG)}
        {filtered.length === 0 ? (
          <Card className="text-center py-12">
            <FileSignature className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Aucun contrat cadre.</p>
          </Card>
        ) : (
          <div className="space-y-3">
            {paged.map((cr) => {
              const config = CONTRACT_STATUS_CONFIG[cr.status];
              const consultantName = [cr.consultant_first_name, cr.consultant_last_name].filter(Boolean).join(' ');
              const thirdPartyLabel = cr.third_party_type ? (THIRD_PARTY_TYPE_LABELS[cr.third_party_type] ?? cr.third_party_type) : null;
              return (
                <div
                  key={cr.id}
                  onClick={() => navigate(`/contracts/${cr.id}`)}
                  className="group relative bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-md transition-all cursor-pointer overflow-hidden"
                >
                  {/* Left accent bar */}
                  <div className={`absolute inset-y-0 left-0 w-1 ${
                    cr.status === 'cancelled' || cr.status === 'compliance_blocked' ? 'bg-red-400' :
                    cr.status === 'signed' || cr.status === 'active' ? 'bg-green-400' :
                    cr.status === 'archived' || cr.status === 'redirected_payfit' ? 'bg-gray-300 dark:bg-gray-600' :
                    'bg-blue-400'
                  }`} />

                  <div className="pl-5 pr-4 py-4">
                    {/* Line 1: Status + Reference + Third party type */}
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className={`shrink-0 inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${config?.color ?? 'bg-gray-100 text-gray-600'}`}>
                        {config?.label ?? cr.status_display}
                      </span>
                      <span className="text-sm font-mono font-bold text-gray-900 dark:text-white">
                        {cr.display_reference}
                      </span>
                      {thirdPartyLabel && (
                        <span className="text-xs text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800 rounded-full px-2 py-0.5">
                          {thirdPartyLabel}
                        </span>
                      )}
                    </div>

                    {/* Line 2: Fournisseur + date */}
                    <div className="mt-2 flex items-center justify-between">
                      <div className="flex items-center gap-2 min-w-0">
                        <Building2 className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
                          {cr.third_party_name || 'Fournisseur en attente'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-4">
                        <p className="text-xs text-gray-400 dark:text-gray-500">{formatDate(cr.created_at)}</p>
                        {isAdv && !CR_TERMINAL.has(cr.status) && (
                          <button
                            onClick={(e) => { e.stopPropagation(); setCancelTarget({ id: cr.id, reference: cr.display_reference }); }}
                            className="p-1.5 rounded-md text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all"
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
                            className="p-1.5 rounded-md text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all"
                            title="Supprimer définitivement"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Line 3: Consultant */}
                    {consultantName && (
                      <div className="mt-1 flex items-center gap-2">
                        <User className="h-3.5 w-3.5 text-gray-300 dark:text-gray-600 shrink-0" />
                        <span className="text-xs text-gray-500 dark:text-gray-400 truncate">
                          {cr.consultant_civility && <span className="mr-0.5">{cr.consultant_civility}</span>}
                          {consultantName}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {renderPagination(filtered.length)}
      </>
    );
  };

  // ── Shared filter tabs ─────────────────────────────────────────────
  const renderFilterTabs = (counts: Record<FilterTab, number>, statusConfig: Record<string, { label: string }>) => (
    <div className="flex items-center gap-4 mb-6">
      <div className="flex space-x-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
        {([
          { key: 'all' as FilterTab, label: 'Tous' },
          { key: 'active' as FilterTab, label: 'En cours' },
          { key: 'done' as FilterTab, label: 'Finalisés' },
        ]).map(({ key, label }) => (
          <button
            key={key}
            onClick={() => { setFilterTab(key); setStatusFilter(''); setPage(0); }}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              filterTab === key
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            {label}
            <span className="ml-1.5 text-xs text-gray-400 dark:text-gray-500">{counts[key]}</span>
          </button>
        ))}
      </div>
      <select
        value={statusFilter}
        onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
        className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
      >
        <option value="">Tous les statuts</option>
        {Object.entries(statusConfig).map(([value, { label }]) => (
          <option key={value} value={value}>{label}</option>
        ))}
      </select>
    </div>
  );

  // ── Shared pagination ──────────────────────────────────────────────
  const renderPagination = (total: number) => {
    if (total <= pageSize) return null;
    return (
      <div className="flex justify-center mt-8 space-x-2">
        <Button variant="secondary" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>Précédent</Button>
        <span className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">Page {page + 1} / {Math.ceil(total / pageSize)}</span>
        <Button variant="secondary" size="sm" disabled={(page + 1) * pageSize >= total} onClick={() => setPage((p) => p + 1)}>Suivant</Button>
      </div>
    );
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Gestion des contrats</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {isAdv ? 'Tous les contrats' : 'Vos contrats'}
          </p>
        </div>
        {isAdv && (
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Nouveau contrat
          </Button>
        )}
      </div>

      {renderContractsList()}

      {/* Cancel confirmation modal */}
      <Modal
        isOpen={!!cancelTarget}
        onClose={() => setCancelTarget(null)}
        title="Annuler la demande de contrat"
      >
        {cancelTarget && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Voulez-vous vraiment annuler la demande <span className="font-semibold">{cancelTarget.reference}</span> ?
            </p>
            <p className="text-sm text-red-600 dark:text-red-400">Cette action est irréversible.</p>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setCancelTarget(null)} disabled={cancelCrMutation.isPending}>Non, garder</Button>
              <Button
                variant="primary"
                onClick={() => cancelCrMutation.mutate(cancelTarget.id)}
                isLoading={cancelCrMutation.isPending}
                className="bg-red-600 hover:bg-red-700 text-white"
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
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Créez un dossier de contrat sans déclencheur Boond. Saisissez l'ID Boond du
            consultant : son identité est récupérée automatiquement depuis Boond.
          </p>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Le consultant est un… *
            </label>
            <div className="grid grid-cols-2 gap-2">
              {([
                { key: 'candidate' as const, label: 'Candidat', hint: 'Converti en ressource à la signature' },
                { key: 'resource' as const, label: 'Ressource', hint: 'Déjà une ressource dans Boond' },
              ]).map(({ key, label, hint }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setCreateForm((f) => ({ ...f, consultant_type: key }))}
                  className={`text-left rounded-lg border px-3 py-2 transition-colors ${
                    createForm.consultant_type === key
                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                      : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                  }`}
                >
                  <span className="block text-sm font-medium text-gray-900 dark:text-white">{label}</span>
                  <span className="block text-xs text-gray-500 dark:text-gray-400">{hint}</span>
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              ID Boond du consultant *
            </label>
            <input
              type="text"
              inputMode="numeric"
              value={createForm.boond_consultant_id}
              onChange={(e) =>
                setCreateForm((f) => ({ ...f, boond_consultant_id: e.target.value.replace(/[^\d]/g, '') }))
              }
              placeholder="Ex : 4242"
              className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Société émettrice
            </label>
            <select
              value={createForm.company_id}
              onChange={(e) => setCreateForm((f) => ({ ...f, company_id: e.target.value }))}
              className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
            >
              <option value="">Sélectionner (optionnel)…</option>
              {companies.filter((c) => c.is_active).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.code})
                </option>
              ))}
            </select>
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500">
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
    </div>
  );
}
