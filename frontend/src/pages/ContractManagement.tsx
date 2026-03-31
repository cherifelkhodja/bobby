import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { FileSignature, ShoppingCart, X, User, Building2 } from 'lucide-react';
import { toast } from 'sonner';

import { contractsApi, purchaseOrderRequestsApi } from '../api/contracts';
import { useAuthStore } from '../stores/authStore';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';
import { getErrorMessage } from '../api/client';
import type { ContractRequestStatus, PurchaseOrderRequestStatus } from '../types';
import { CONTRACT_STATUS_CONFIG, POR_STATUS_CONFIG } from '../types';

const THIRD_PARTY_TYPE_LABELS: Record<string, string> = {
  freelance: 'Freelance',
  sous_traitant: 'Sous-traitant',
  portage_salarial: 'Portage salarial',
  salarie: 'Salarié',
};

type MainTab = 'contracts' | 'bdc';
type FilterTab = 'all' | 'active' | 'done';

const CR_TERMINAL = new Set(['cancelled', 'signed', 'archived', 'redirected_payfit']);
const POR_TERMINAL = new Set(['cancelled', 'archived']);

export function ContractManagement() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [mainTab, setMainTab] = useState<MainTab>('contracts');
  const [page, setPage] = useState(0);
  const [filterTab, setFilterTab] = useState<FilterTab>('all');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [cancelTarget, setCancelTarget] = useState<{ id: string; reference: string; type: MainTab } | null>(null);
  const pageSize = 20;

  const isAdv = user?.role === 'adv' || user?.role === 'admin';

  // Contract requests query
  const { data: crData, isLoading: crLoading } = useQuery({
    queryKey: ['contract-requests', page, statusFilter],
    queryFn: () =>
      contractsApi.list({
        skip: page * pageSize,
        limit: pageSize,
        ...(statusFilter ? { status_filter: statusFilter as ContractRequestStatus } : {}),
      }),
    enabled: mainTab === 'contracts',
  });

  // Purchase order requests query
  const { data: porData, isLoading: porLoading } = useQuery({
    queryKey: ['purchase-order-requests', page, statusFilter],
    queryFn: () =>
      purchaseOrderRequestsApi.list({
        skip: page * pageSize,
        limit: pageSize,
        ...(statusFilter ? { status_filter: statusFilter as PurchaseOrderRequestStatus } : {}),
      }),
    enabled: mainTab === 'bdc',
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

  const cancelPorMutation = useMutation({
    mutationFn: (id: string) => purchaseOrderRequestsApi.cancel(id),
    onSuccess: () => {
      toast.success('Demande de BDC annulée.');
      setCancelTarget(null);
      queryClient.invalidateQueries({ queryKey: ['purchase-order-requests'] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });

  const handleSwitchMainTab = (tab: MainTab) => {
    setMainTab(tab);
    setPage(0);
    setFilterTab('all');
    setStatusFilter('');
  };

  const isLoading = mainTab === 'contracts' ? crLoading : porLoading;
  if (isLoading) return <PageSpinner />;

  // ── Contract requests tab content ─────────────────────────────────
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
            {filtered.map((cr) => {
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
                    <div className="flex items-start justify-between gap-4">
                      {/* Main content */}
                      <div className="min-w-0 flex-1">
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

                        {/* Line 2: Fournisseur + consultant */}
                        {(cr.third_party_name || consultantName) && (
                          <div className="mt-2 flex items-center gap-2 text-sm">
                            {cr.third_party_name && (
                              <>
                                <Building2 className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                                <span className="font-medium text-gray-700 dark:text-gray-300 truncate">
                                  {cr.third_party_name}
                                </span>
                              </>
                            )}
                            {cr.third_party_name && consultantName && (
                              <span className="text-gray-300 dark:text-gray-600">|</span>
                            )}
                            {consultantName && (
                              <>
                                <User className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                                <span className="text-gray-500 dark:text-gray-400 truncate">
                                  {cr.consultant_civility && <span className="mr-0.5">{cr.consultant_civility}</span>}
                                  {consultantName}
                                </span>
                              </>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Right side: date + actions */}
                      <div className="flex items-center gap-2 shrink-0">
                        <div className="text-right">
                          <p className="text-xs text-gray-400 dark:text-gray-500">{formatDate(cr.created_at)}</p>
                          {isAdv && (cr.commercial_name || cr.commercial_email) && (
                            <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{cr.commercial_name || cr.commercial_email}</p>
                          )}
                        </div>
                        {isAdv && !CR_TERMINAL.has(cr.status) && (
                          <button
                            onClick={(e) => { e.stopPropagation(); setCancelTarget({ id: cr.id, reference: cr.display_reference, type: 'contracts' }); }}
                            className="p-1.5 rounded-md text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all"
                            title="Annuler"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {renderPagination(crData?.total ?? 0)}
      </>
    );
  };

  // ── Purchase order requests tab content ────────────────────────────
  const renderPorList = () => {
    const items = porData?.items ?? [];
    const filtered = items.filter((por) => {
      if (filterTab === 'all') return true;
      const g = POR_STATUS_CONFIG[por.status]?.group;
      if (filterTab === 'active') return g === 'active' || g === 'blocked';
      return g === 'done';
    });

    const counts = {
      all: items.length,
      active: items.filter((p) => { const g = POR_STATUS_CONFIG[p.status]?.group; return g === 'active' || g === 'blocked'; }).length,
      done: items.filter((p) => POR_STATUS_CONFIG[p.status]?.group === 'done').length,
    };

    return (
      <>
        {renderFilterTabs(counts, POR_STATUS_CONFIG)}
        {filtered.length === 0 ? (
          <Card className="text-center py-12">
            <ShoppingCart className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Aucun bon de commande.</p>
          </Card>
        ) : (
          <div className="space-y-3">
            {filtered.map((por) => {
              const config = POR_STATUS_CONFIG[por.status];
              return (
                <Card key={por.id} className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => navigate(`/contracts/po/${por.id}`)}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4 min-w-0">
                      <span className="shrink-0 text-sm font-mono font-semibold text-gray-900 dark:text-white">{por.reference}</span>
                      <span className={`shrink-0 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config?.color ?? 'bg-gray-100 text-gray-600'}`}>{config?.label ?? por.status_display}</span>
                      <div className="min-w-0">
                        {por.consultant_first_name && (
                          <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
                            {por.consultant_first_name} {por.consultant_last_name}
                          </p>
                        )}
                        <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                          {por.client_name && <span>{por.client_name}</span>}
                          {por.client_name && por.daily_rate && <span>·</span>}
                          {por.daily_rate && <span>{por.daily_rate}€/j</span>}
                          {por.start_date && <><span>·</span><span>Début {formatDate(por.start_date)}</span></>}
                          {por.framework_contract_reference && (
                            <><span>·</span><span className="text-emerald-600 dark:text-emerald-400">CC {por.framework_contract_reference}</span></>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0 ml-4">
                      <div className="text-right">
                        <p className="text-xs text-gray-400 dark:text-gray-500">{formatDate(por.created_at)}</p>
                        {isAdv && <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{por.commercial_name || por.commercial_email}</p>}
                      </div>
                      {isAdv && !POR_TERMINAL.has(por.status) && (
                        <button onClick={(e) => { e.stopPropagation(); setCancelTarget({ id: por.id, reference: por.reference, type: 'bdc' }); }} className="p-1.5 rounded-md text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors" title="Annuler">
                          <X className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
        {renderPagination(porData?.total ?? 0)}
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
            onClick={() => { setFilterTab(key); setStatusFilter(''); }}
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
            {isAdv ? 'Tous les contrats et bons de commande' : 'Vos contrats et bons de commande'}
          </p>
        </div>
      </div>

      {/* Main tabs: Contrats cadres / Bons de commande */}
      <div className="flex space-x-1 border-b border-gray-200 dark:border-gray-700 mb-6">
        <button
          onClick={() => handleSwitchMainTab('contracts')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            mainTab === 'contracts'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
        >
          <FileSignature className="h-4 w-4" />
          Contrats cadres
          {crData && <span className="ml-1 text-xs bg-gray-100 dark:bg-gray-700 rounded-full px-2 py-0.5">{crData.total}</span>}
        </button>
        <button
          onClick={() => handleSwitchMainTab('bdc')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            mainTab === 'bdc'
              ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
        >
          <ShoppingCart className="h-4 w-4" />
          Bons de commande
          {porData && <span className="ml-1 text-xs bg-gray-100 dark:bg-gray-700 rounded-full px-2 py-0.5">{porData.total}</span>}
        </button>
      </div>

      {mainTab === 'contracts' ? renderContractsList() : renderPorList()}

      {/* Cancel confirmation modal */}
      <Modal
        isOpen={!!cancelTarget}
        onClose={() => setCancelTarget(null)}
        title={cancelTarget?.type === 'contracts' ? 'Annuler la demande de contrat' : 'Annuler la demande de BDC'}
      >
        {cancelTarget && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Voulez-vous vraiment annuler la demande <span className="font-semibold">{cancelTarget.reference}</span> ?
            </p>
            <p className="text-sm text-red-600 dark:text-red-400">Cette action est irréversible.</p>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setCancelTarget(null)} disabled={cancelCrMutation.isPending || cancelPorMutation.isPending}>Non, garder</Button>
              <Button
                variant="primary"
                onClick={() => {
                  if (cancelTarget.type === 'contracts') cancelCrMutation.mutate(cancelTarget.id);
                  else cancelPorMutation.mutate(cancelTarget.id);
                }}
                isLoading={cancelCrMutation.isPending || cancelPorMutation.isPending}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                Oui, annuler
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
