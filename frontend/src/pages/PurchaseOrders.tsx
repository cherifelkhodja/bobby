import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, ClipboardList, Plus, Search } from 'lucide-react';
import { toast } from 'sonner';

import { purchaseOrdersApi } from '../api/purchaseOrders';
import { contractCompaniesApi } from '../api/contracts';
import { getErrorMessage } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';
import type { PurchaseOrder, PurchaseOrderStatus } from '../types';
import { PURCHASE_ORDER_STATUS_CONFIG } from '../types';

type FilterTab = 'all' | 'todo' | 'waiting' | 'done';

const TODO_STATUSES = new Set<PurchaseOrderStatus>(['draft', 'generated']);
const WAITING_STATUSES = new Set<PurchaseOrderStatus>(['sent_for_signature', 'signed']);

function tabOf(po: PurchaseOrder): Exclude<FilterTab, 'all'> {
  if (TODO_STATUSES.has(po.status)) return 'todo';
  if (WAITING_STATUSES.has(po.status)) return 'waiting';
  return 'done';
}

function formatDate(value: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function formatAmount(value: number): string {
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(value);
}

export function PurchaseOrders() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const isAdv = user?.role === 'adv' || user?.role === 'admin';

  const [filterTab, setFilterTab] = useState<FilterTab>('all');
  const [search, setSearch] = useState('');
  const [companyFilter, setCompanyFilter] = useState('');
  const [page, setPage] = useState(0);
  const [showCreate, setShowCreate] = useState(false);
  const [positioningId, setPositioningId] = useState('');
  const pageSize = 20;
  // Le regroupement par onglet couvre plusieurs statuts, que l'API ne filtre
  // qu'un par un : le tri et la pagination se font côté client sur la liste
  // complète, chargée en une fois (plafonnée à FETCH_LIMIT). Les bons de
  // commande annulés n'en font pas partie : ils ne représentent aucune mission.
  const FETCH_LIMIT = 500;

  const { data: companies = [] } = useQuery({
    queryKey: ['contract-companies-active'],
    queryFn: contractCompaniesApi.listActive,
    enabled: isAdv,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['purchase-orders', search, companyFilter],
    queryFn: () =>
      purchaseOrdersApi.list({
        skip: 0,
        limit: FETCH_LIMIT,
        exclude_cancelled: true,
        ...(search ? { search } : {}),
        ...(companyFilter ? { company_id: companyFilter } : {}),
      }),
  });

  const createMutation = useMutation({
    mutationFn: (id: number) => purchaseOrdersApi.create(id),
    onSuccess: (po) => {
      toast.success(`Bon de commande ${po.display_reference} créé.`);
      setShowCreate(false);
      setPositioningId('');
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      navigate(`/contracts/bdc/${po.id}`);
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const items = data?.items ?? [];
  const counts: Record<FilterTab, number> = {
    all: items.length,
    todo: items.filter((po) => tabOf(po) === 'todo').length,
    waiting: items.filter((po) => tabOf(po) === 'waiting').length,
    done: items.filter((po) => tabOf(po) === 'done').length,
  };
  const toAttach = items.filter((po) => po.needs_third_party).length;
  const activeCount = items.filter((po) => po.status === 'active').length;
  const monthlyVolume = items
    .filter((po) => po.status === 'active')
    .reduce((sum, po) => sum + po.total_amount, 0);

  const filtered = items.filter((po) => (filterTab === 'all' ? true : tabOf(po) === filterTab));
  const paged = filtered.slice(page * pageSize, page * pageSize + pageSize);

  if (isLoading) return <PageSpinner />;

  const gridCols = 'grid-cols-[86px_1.4fr_110px_110px_80px_140px_170px_40px]';

  return (
    <div>
      <p className="bc">Contrats / Bons de commande</p>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="h1">Bons de commande</h1>
          <p className="sub">Une mission, un consultant, sous le contrat cadre du fournisseur</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={companyFilter}
            onChange={(e) => {
              setCompanyFilter(e.target.value);
              setPage(0);
            }}
            className="filter-select"
          >
            <option value="">Toutes les sociétés</option>
            {companies
              .filter((c) => c.is_active)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
          </select>
          <div className="relative">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-mut2" />
            <input
              type="search"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
              placeholder="Réf., consultant, client…"
              className="f-in pl-9 w-64"
            />
          </div>
          {isAdv && (
            <Button onClick={() => setShowCreate(true)} leftIcon={<Plus className="h-3.5 w-3.5" />}>
              Nouvelle mission
            </Button>
          )}
        </div>
      </div>

      <div className="kpis">
        <div className="kpi">
          <p className="kl">À rattacher</p>
          <p className={`kv ${toAttach > 0 ? 'red' : ''}`}>{toAttach}</p>
          <p className="ks">fournisseur à choisir</p>
        </div>
        <div className="kpi">
          <p className="kl">À compléter</p>
          <p className="kv">{counts.todo}</p>
          <p className="ks">brouillons et documents générés</p>
        </div>
        <div className="kpi">
          <p className="kl">En signature</p>
          <p className="kv">{counts.waiting}</p>
          <p className="ks">envoyés au fournisseur</p>
        </div>
        <div className="kpi">
          <p className="kl">Missions actives</p>
          <p className="kv">{activeCount}</p>
          <p className="ks">{formatAmount(monthlyVolume)} € engagés</p>
        </div>
      </div>

      <div className="tabs">
        {(
          [
            { key: 'all' as FilterTab, label: 'Tous' },
            { key: 'todo' as FilterTab, label: 'À compléter' },
            { key: 'waiting' as FilterTab, label: 'En signature' },
            { key: 'done' as FilterTab, label: 'Actifs et clos' },
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
      </div>

      {filtered.length === 0 ? (
        <div className="card text-center py-12">
          <ClipboardList className="h-10 w-10 text-mut2 mx-auto mb-4" />
          <p className="dn">Aucun bon de commande</p>
          <p className="ds mt-1.5">
            Ils arrivent depuis BoondManager quand un positionnement est gagné, ou se créent ici
            depuis un positionnement.
          </p>
        </div>
      ) : (
        <div className="tbl">
          <div className={`thead ${gridCols}`}>
            <span>Réf.</span>
            <span>Consultant / Fournisseur</span>
            <span>Société</span>
            <span>Client</span>
            <span>CJM</span>
            <span>Période</span>
            <span>Statut</span>
            <span></span>
          </div>
          {paged.map((po) => (
            <div
              key={po.id}
              className={`row click ${gridCols} group`}
              onClick={() => navigate(`/contracts/bdc/${po.id}`)}
            >
              <span className="ref">{po.display_reference}</span>
              <div className="min-w-0">
                <p className="nm truncate">{po.consultant_name || 'Consultant à identifier'}</p>
                <p className="ns truncate">
                  {po.third_party_name ?? (
                    <span className="text-redt">Fournisseur à rattacher</span>
                  )}
                </p>
              </div>
              <span className="cell truncate">{po.company_name ?? '—'}</span>
              <span className="cell truncate">{po.client_name || '—'}</span>
              <span className="tjm">
                {po.purchase_daily_rate ? `${formatAmount(po.purchase_daily_rate)} €` : '—'}
              </span>
              <span className="cell">
                {po.start_date ? `${formatDate(po.start_date)} → ${formatDate(po.end_date)}` : '—'}
              </span>
              <div>
                <span className={`st ${PURCHASE_ORDER_STATUS_CONFIG[po.status].color}`}>
                  <span className="dot" />
                  {PURCHASE_ORDER_STATUS_CONFIG[po.status].label}
                </span>
              </div>
              <ChevronRight className="h-4 w-4 chev shrink-0" />
            </div>
          ))}
          <div className="tfoot">
            <span>
              {filtered.length} bon{filtered.length > 1 ? 's' : ''} de commande
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

      <Modal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        title="Nouvelle mission"
        size="md"
      >
        <div className="space-y-4">
          <p className="ds">
            Saisissez l'identifiant du positionnement BoondManager. Le consultant, le besoin, le
            coût journalier et les dates sont repris automatiquement. Le positionnement doit être
            gagné et en attente de contrat.
          </p>
          <div>
            <label className="f-lab" htmlFor="positioning-id">
              ID du positionnement Boond
            </label>
            <input
              id="positioning-id"
              type="number"
              min={1}
              value={positioningId}
              onChange={(e) => setPositioningId(e.target.value)}
              placeholder="41"
              className="f-in"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setShowCreate(false)}>
              Annuler
            </Button>
            <Button
              onClick={() => createMutation.mutate(Number(positioningId))}
              disabled={!positioningId || createMutation.isPending}
              isLoading={createMutation.isPending}
              leftIcon={<Plus className="h-3.5 w-3.5" />}
            >
              Créer le bon de commande
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
