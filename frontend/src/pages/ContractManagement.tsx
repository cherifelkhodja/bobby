import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileSignature } from 'lucide-react';

import { contractsApi } from '../api/contracts';
import { useAuthStore } from '../stores/authStore';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { PageSpinner } from '../components/ui/Spinner';
import type { ContractRequestStatus } from '../types';
import { CONTRACT_STATUS_CONFIG } from '../types';

const THIRD_PARTY_TYPE_LABELS: Record<string, string> = {
  freelance: 'Freelance',
  sous_traitant: 'Sous-traitant',
  salarie: 'Salarié',
};

type FilterTab = 'all' | 'active' | 'done';

export function ContractManagement() {
  const { user } = useAuthStore();
  const [page, setPage] = useState(0);
  const [activeTab, setActiveTab] = useState<FilterTab>('all');
  const [statusFilter, setStatusFilter] = useState<ContractRequestStatus | ''>('');
  const pageSize = 20;

  const isAdv = user?.role === 'adv' || user?.role === 'admin';

  const { data, isLoading } = useQuery({
    queryKey: ['contract-requests', page, statusFilter],
    queryFn: () =>
      contractsApi.list({
        skip: page * pageSize,
        limit: pageSize,
        ...(statusFilter ? { status_filter: statusFilter } : {}),
      }),
  });

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });

  const filteredItems = data?.items.filter((cr) => {
    if (activeTab === 'all') return true;
    const config = CONTRACT_STATUS_CONFIG[cr.status];
    if (activeTab === 'active') return config?.group === 'active' || config?.group === 'blocked';
    if (activeTab === 'done') return config?.group === 'done';
    return true;
  });

  const counts = {
    all: data?.items.length ?? 0,
    active: data?.items.filter((cr) => {
      const g = CONTRACT_STATUS_CONFIG[cr.status]?.group;
      return g === 'active' || g === 'blocked';
    }).length ?? 0,
    done: data?.items.filter((cr) => CONTRACT_STATUS_CONFIG[cr.status]?.group === 'done').length ?? 0,
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Gestion des contrats
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {isAdv ? 'Tous les contrats' : 'Vos contrats'}
            {data && ` — ${data.total} au total`}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 mb-6 bg-gray-100 dark:bg-gray-800 rounded-lg p-1 w-fit">
        {([
          { key: 'all' as FilterTab, label: 'Tous' },
          { key: 'active' as FilterTab, label: 'En cours' },
          { key: 'done' as FilterTab, label: 'Finalisés' },
        ]).map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === key
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            {label}
            <span className="ml-1.5 text-xs text-gray-400 dark:text-gray-500">
              {counts[key]}
            </span>
          </button>
        ))}
      </div>

      {/* Status filter (for ADV/admin) */}
      {isAdv && (
        <div className="mb-4">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as ContractRequestStatus | '');
              setPage(0);
            }}
            className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
          >
            <option value="">Tous les statuts</option>
            {Object.entries(CONTRACT_STATUS_CONFIG).map(([value, { label }]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* List */}
      {!filteredItems || filteredItems.length === 0 ? (
        <Card className="text-center py-12">
          <FileSignature className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <p className="text-gray-500 dark:text-gray-400">
            {activeTab === 'active' ? 'Aucun contrat en cours.' : activeTab === 'done' ? 'Aucun contrat finalisé.' : 'Aucun contrat pour le moment.'}
          </p>
        </Card>
      ) : (
        <>
          <div className="space-y-3">
            {filteredItems.map((cr) => {
              const config = CONTRACT_STATUS_CONFIG[cr.status];
              return (
                <Card key={cr.id} className="hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4 min-w-0">
                      {/* Reference */}
                      <div className="shrink-0">
                        <span className="text-sm font-mono font-semibold text-gray-900 dark:text-white">
                          {cr.reference}
                        </span>
                      </div>

                      {/* Status badge */}
                      <span
                        className={`shrink-0 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config?.color ?? 'bg-gray-100 text-gray-600'}`}
                      >
                        {config?.label ?? cr.status_display}
                      </span>

                      {/* Main info */}
                      <div className="min-w-0">
                        {cr.client_name && (
                          <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
                            {cr.client_name}
                          </p>
                        )}
                        <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                          {cr.third_party_type && (
                            <span>{THIRD_PARTY_TYPE_LABELS[cr.third_party_type] ?? cr.third_party_type}</span>
                          )}
                          {cr.third_party_type && cr.daily_rate && <span>·</span>}
                          {cr.daily_rate && <span>{cr.daily_rate}€/j</span>}
                          {(cr.third_party_type || cr.daily_rate) && cr.start_date && <span>·</span>}
                          {cr.start_date && <span>Début {formatDate(cr.start_date)}</span>}
                        </div>
                      </div>
                    </div>

                    {/* Right side */}
                    <div className="text-right shrink-0 ml-4">
                      <p className="text-xs text-gray-400 dark:text-gray-500">
                        {formatDate(cr.created_at)}
                      </p>
                      {isAdv && (
                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                          {cr.commercial_email}
                        </p>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>

          {/* Pagination */}
          {data && data.total > pageSize && (
            <div className="flex justify-center mt-8 space-x-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                Précédent
              </Button>
              <span className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
                Page {page + 1} / {Math.ceil(data.total / pageSize)}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={(page + 1) * pageSize >= data.total}
                onClick={() => setPage((p) => p + 1)}
              >
                Suivant
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
