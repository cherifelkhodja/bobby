/**
 * HR Dashboard page - List opportunities from BoondManager where user is HR manager.
 *
 * Fetches opportunities directly from BoondManager API:
 * - For admin users: Shows ALL opportunities
 * - For RH users: Shows only opportunities where they are HR manager
 */

import { useState, useMemo, Fragment } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  Briefcase,
  Plus,
  Eye,
  Search,
  Filter,
  TrendingUp,
  AlertCircle,
  Pencil,
  ChevronDown,
  ChevronRight,
  MapPin,
  Calendar,
  Building2,
  User,
  FileText,
  ExternalLink,
  X,
  Square,
  PanelRight,
  Columns,
  Layout,
} from 'lucide-react';
import { hrApi, type OpportunityDetailResponse } from '../api/hr';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { PageSpinner } from '../components/ui/Spinner';
import type { OpportunityForHR, JobPostingStatus } from '../types';

// Display modes for opportunity details
type DisplayMode = 'modal' | 'drawer' | 'split' | 'inline';

const DISPLAY_MODE_OPTIONS: { value: DisplayMode; label: string; icon: typeof Layout }[] = [
  { value: 'modal', label: 'Pop-up', icon: Square },
  { value: 'drawer', label: 'Panel latéral', icon: PanelRight },
  { value: 'split', label: 'Vue split', icon: Columns },
  { value: 'inline', label: 'Expansion', icon: Layout },
];

// Opportunity detail content component
function OpportunityDetailContent({
  detail,
  opportunityId,
  isLoading,
  compact = false,
}: {
  detail: OpportunityDetailResponse | undefined;
  opportunityId: string;
  isLoading: boolean;
  compact?: boolean;
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
        <span className="ml-2 text-sm text-gray-500">Chargement...</span>
      </div>
    );
  }

  if (!detail) {
    return <p className="text-sm text-gray-500 py-4">Aucun détail disponible</p>;
  }

  return (
    <div className={`${compact ? 'p-4' : 'p-6'} space-y-4`}>
      {/* Title */}
      <div>
        <h3 className={`font-semibold text-gray-900 dark:text-white ${compact ? 'text-base' : 'text-lg'}`}>
          {detail.title}
        </h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">{detail.reference}</p>
      </div>

      {/* Description */}
      {detail.description && (
        <div>
          <div className="flex items-center gap-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            <FileText className="h-3.5 w-3.5" />
            Description
          </div>
          <p className={`text-gray-700 dark:text-gray-300 whitespace-pre-line ${compact ? 'text-xs line-clamp-6' : 'text-sm'}`}>
            {detail.description}
          </p>
        </div>
      )}

      {/* Criteria */}
      {detail.criteria && (
        <div>
          <div className="flex items-center gap-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            <FileText className="h-3.5 w-3.5" />
            Critères
          </div>
          <p className={`text-gray-700 dark:text-gray-300 whitespace-pre-line ${compact ? 'text-xs line-clamp-4' : 'text-sm'}`}>
            {detail.criteria}
          </p>
        </div>
      )}

      {/* Metadata grid */}
      <div className={`grid ${compact ? 'grid-cols-1 gap-2' : 'grid-cols-2 gap-3'} text-sm`}>
        {detail.place && (
          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <MapPin className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <span>{detail.place}</span>
          </div>
        )}
        {(detail.start_date || detail.end_date) && (
          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <Calendar className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <span>
              {detail.start_date && new Date(detail.start_date).toLocaleDateString('fr-FR')}
              {detail.start_date && detail.end_date && ' → '}
              {detail.end_date && new Date(detail.end_date).toLocaleDateString('fr-FR')}
              {detail.duration && ` (${detail.duration} j)`}
            </span>
          </div>
        )}
        {detail.company_name && (
          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <Building2 className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <span>{detail.company_name}</span>
          </div>
        )}
        {detail.manager_name && (
          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <User className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <span>Resp: {detail.manager_name}</span>
          </div>
        )}
        {detail.contact_name && (
          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <User className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <span>Contact: {detail.contact_name}</span>
          </div>
        )}
        {detail.expertise_area && (
          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <Briefcase className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <span>{detail.expertise_area}</span>
          </div>
        )}
      </div>

      {/* Link to BoondManager */}
      <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
        <a
          href={`https://ui.boondmanager.com/#opportunity/${opportunityId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400"
        >
          <ExternalLink className="h-3 w-3" />
          Voir sur BoondManager
        </a>
      </div>
    </div>
  );
}

const JOB_POSTING_STATUS_BADGES: Record<JobPostingStatus, { label: string; bgClass: string; textClass: string }> = {
  draft: {
    label: 'Brouillon',
    bgClass: 'bg-gray-100 dark:bg-gray-700',
    textClass: 'text-gray-800 dark:text-gray-300',
  },
  published: {
    label: 'Publiée',
    bgClass: 'bg-green-100 dark:bg-green-900/30',
    textClass: 'text-green-800 dark:text-green-300',
  },
  closed: {
    label: 'Fermée',
    bgClass: 'bg-red-100 dark:bg-red-900/30',
    textClass: 'text-red-800 dark:text-red-300',
  },
};

// All Boond opportunity states (same as MyBoondOpportunities)
const STATE_CONFIG: Record<number, { name: string; bgClass: string; textClass: string }> = {
  0: { name: 'En cours', bgClass: 'bg-blue-100 dark:bg-blue-900/30', textClass: 'text-blue-700 dark:text-blue-400' },
  1: { name: 'Gagné', bgClass: 'bg-green-100 dark:bg-green-900/30', textClass: 'text-green-700 dark:text-green-400' },
  2: { name: 'Perdu', bgClass: 'bg-red-100 dark:bg-red-900/30', textClass: 'text-red-700 dark:text-red-400' },
  3: { name: 'Abandonné', bgClass: 'bg-gray-200 dark:bg-gray-700', textClass: 'text-gray-700 dark:text-gray-400' },
  4: { name: 'Gagné attente contrat', bgClass: 'bg-emerald-100 dark:bg-emerald-900/30', textClass: 'text-emerald-700 dark:text-emerald-400' },
  5: { name: 'Piste identifiée', bgClass: 'bg-yellow-100 dark:bg-yellow-900/30', textClass: 'text-yellow-700 dark:text-yellow-400' },
  6: { name: 'Récurrent', bgClass: 'bg-teal-100 dark:bg-teal-900/30', textClass: 'text-teal-700 dark:text-teal-400' },
  7: { name: 'AO ouvert', bgClass: 'bg-cyan-100 dark:bg-cyan-900/30', textClass: 'text-cyan-700 dark:text-cyan-400' },
  8: { name: 'AO clos', bgClass: 'bg-indigo-100 dark:bg-indigo-900/30', textClass: 'text-indigo-700 dark:text-indigo-400' },
  9: { name: 'Reporté', bgClass: 'bg-pink-100 dark:bg-pink-900/30', textClass: 'text-pink-700 dark:text-pink-400' },
  10: { name: 'Besoin en avant de phase', bgClass: 'bg-sky-100 dark:bg-sky-900/30', textClass: 'text-sky-700 dark:text-sky-400' },
};

export default function HRDashboard() {
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState('');
  const [stateFilter, setStateFilter] = useState<number | 'all'>('all');
  const [clientFilter, setClientFilter] = useState<string>('all');
  const [postingFilter, setPostingFilter] = useState<string>('all');
  const [displayMode, setDisplayMode] = useState<DisplayMode>('drawer');
  const [selectedOpportunity, setSelectedOpportunity] = useState<OpportunityForHR | null>(null);
  const [expandedOpportunityId, setExpandedOpportunityId] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['hr-opportunities'],
    queryFn: () => hrApi.getOpportunities(),
  });

  // Fetch selected/expanded opportunity details
  const activeOpportunityId = selectedOpportunity?.id || expandedOpportunityId;
  const { data: opportunityDetail, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['hr-opportunity-detail', activeOpportunityId],
    queryFn: () => hrApi.getOpportunityDetail(activeOpportunityId!),
    enabled: !!activeOpportunityId,
  });

  const handleOpenOpportunity = (opportunity: OpportunityForHR) => {
    if (displayMode === 'inline') {
      setExpandedOpportunityId(prev => prev === opportunity.id ? null : opportunity.id);
      setSelectedOpportunity(null);
    } else {
      setSelectedOpportunity(opportunity);
      setExpandedOpportunityId(null);
    }
  };

  const handleCloseDetail = () => {
    setSelectedOpportunity(null);
    setExpandedOpportunityId(null);
  };

  // Calculate stats and available filters
  const { stats, availableStates, availableClients } = useMemo(() => {
    if (!data?.items) {
      return {
        stats: { total: 0, published: 0, newApplications: 0, byState: {} as Record<number, number> },
        availableStates: [],
        availableClients: [],
      };
    }

    const byState: Record<number, number> = {};
    const clientsMap: Record<string, number> = {};
    let published = 0;
    let newApplications = 0;

    data.items.forEach((opp) => {
      // Count by state
      if (opp.state !== null) {
        byState[opp.state] = (byState[opp.state] || 0) + 1;
      }

      // Count by client
      const clientName = opp.client_name || 'Sans client';
      clientsMap[clientName] = (clientsMap[clientName] || 0) + 1;

      // Count published
      if (opp.job_posting_status === 'published') {
        published++;
      }

      // Count new applications
      newApplications += opp.new_applications_count;
    });

    const states = Object.entries(byState)
      .map(([state, count]) => ({ state: parseInt(state), count }))
      .sort((a, b) => b.count - a.count);

    const clients = Object.entries(clientsMap)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    return {
      stats: { total: data.items.length, published, newApplications, byState },
      availableStates: states,
      availableClients: clients,
    };
  }, [data?.items]);

  // Client-side filtering
  const filteredItems = useMemo(() => {
    if (!data?.items) return [];

    return data.items.filter((opp) => {
      // Search filter
      if (searchInput) {
        const searchLower = searchInput.toLowerCase();
        const matchesSearch =
          opp.title.toLowerCase().includes(searchLower) ||
          opp.reference.toLowerCase().includes(searchLower) ||
          (opp.client_name?.toLowerCase().includes(searchLower) ?? false);
        if (!matchesSearch) return false;
      }

      // State filter
      if (stateFilter !== 'all' && opp.state !== stateFilter) return false;

      // Client filter
      if (clientFilter !== 'all') {
        const clientName = opp.client_name || 'Sans client';
        if (clientName !== clientFilter) return false;
      }

      // Posting filter
      if (postingFilter === 'with' && !opp.has_job_posting) return false;
      if (postingFilter === 'without' && opp.has_job_posting) return false;

      return true;
    });
  }, [data?.items, searchInput, stateFilter, clientFilter, postingFilter]);

  const handleCreatePosting = (opportunity: OpportunityForHR) => {
    navigate(`/rh/annonces/nouvelle/${opportunity.id}`);
  };

  const handleViewPosting = (opportunity: OpportunityForHR) => {
    if (opportunity.job_posting_id) {
      // For drafts, go to edit page; for others, go to details page
      if (opportunity.job_posting_status === 'draft') {
        navigate(`/rh/annonces/edit/${opportunity.job_posting_id}`);
      } else {
        navigate(`/rh/annonces/${opportunity.job_posting_id}`);
      }
    }
  };

  const getStateBadge = (state: number | null, stateName: string | null) => {
    const config = state !== null ? STATE_CONFIG[state] : null;
    if (!config) {
      return (
        <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
          {stateName || '-'}
        </span>
      );
    }
    return (
      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${config.bgClass} ${config.textClass}`}>
        {config.name}
      </span>
    );
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Erreur de chargement
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          {error instanceof Error ? error.message : 'Erreur inconnue'}
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
          Vérifiez que votre identifiant BoondManager est configuré dans votre profil.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Gestion des annonces
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1 text-sm">
          Opportunités BoondManager où vous êtes responsable RH
        </p>
      </div>

      {/* Stats Card */}
      <Card className="!p-3">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center">
            <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
              <TrendingUp className="h-4 w-4 text-primary-600 dark:text-primary-400" />
            </div>
            <div className="ml-3">
              <p className="text-xs text-gray-500 dark:text-gray-400">Opportunités ouvertes</p>
              <p className="text-xl font-bold text-gray-900 dark:text-gray-100">{stats.total}</p>
            </div>
          </div>
          <div className="flex gap-2 flex-wrap">
            {stats.published > 0 && (
              <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
                {stats.published} publiée{stats.published > 1 ? 's' : ''}
              </span>
            )}
            {stats.newApplications > 0 && (
              <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400">
                {stats.newApplications} nouvelle{stats.newApplications > 1 ? 's' : ''} candidature{stats.newApplications > 1 ? 's' : ''}
              </span>
            )}
            {availableStates.map(({ state, count }) => (
              <span
                key={state}
                className={`px-2 py-1 text-xs font-medium rounded-full ${STATE_CONFIG[state]?.bgClass || 'bg-gray-100'} ${STATE_CONFIG[state]?.textClass || 'text-gray-600'}`}
              >
                {STATE_CONFIG[state]?.name || `État ${state}`}: {count}
              </span>
            ))}
          </div>
        </div>
      </Card>

      {/* Filters */}
      <Card className="!p-3">
        <div className="flex items-center gap-3 flex-wrap">
          <Filter className="h-4 w-4 text-gray-400 flex-shrink-0" />

          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Rechercher..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          {/* State filter */}
          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value === 'all' ? 'all' : parseInt(e.target.value))}
            className="min-w-[160px] px-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="all">Tous les états ({stats.total})</option>
            {availableStates.map(({ state, count }) => (
              <option key={state} value={state}>
                {STATE_CONFIG[state]?.name || `État ${state}`} ({count})
              </option>
            ))}
          </select>

          {/* Client filter */}
          <select
            value={clientFilter}
            onChange={(e) => setClientFilter(e.target.value)}
            className="min-w-[160px] px-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="all">Tous les clients ({availableClients.length})</option>
            {availableClients.map(({ name, count }) => (
              <option key={name} value={name}>
                {name} ({count})
              </option>
            ))}
          </select>

          {/* Posting status filter */}
          <select
            value={postingFilter}
            onChange={(e) => setPostingFilter(e.target.value)}
            className="min-w-[160px] px-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="all">Toutes les annonces</option>
            <option value="with">Avec annonce</option>
            <option value="without">Sans annonce</option>
          </select>

          {/* Separator */}
          <span className="text-gray-300 dark:text-gray-600">|</span>

          {/* Display mode selector */}
          <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-700 rounded p-0.5">
            {DISPLAY_MODE_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              return (
                <button
                  key={opt.value}
                  onClick={() => {
                    setDisplayMode(opt.value);
                    if (opt.value !== 'inline') setExpandedOpportunityId(null);
                    if (opt.value === 'inline') setSelectedOpportunity(null);
                  }}
                  className={`p-1 rounded transition-colors ${
                    displayMode === opt.value
                      ? 'bg-white dark:bg-gray-600 shadow-sm text-blue-600 dark:text-blue-400'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}
                  title={opt.label}
                >
                  <Icon className="h-3.5 w-3.5" />
                </button>
              );
            })}
          </div>
        </div>
      </Card>

      {/* Table */}
      {filteredItems.length === 0 ? (
        <Card className="text-center py-12">
          <div className="text-gray-400 mb-4">
            <Briefcase className="h-12 w-12 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
            Aucune opportunité trouvée
          </h3>
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            {searchInput
              ? 'Aucun résultat pour vos critères de recherche.'
              : 'Vous devez être responsable RH d\'une opportunité dans BoondManager pour la voir ici.'}
          </p>
        </Card>
      ) : (
        <Card className="overflow-hidden !p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 dark:bg-gray-800/50">
                <tr>
                  <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px]">
                    Opportunité
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px]">
                    Client
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px]">
                    État Boond
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px]">
                    Annonce
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px]">
                    Candidatures
                  </th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px]">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {filteredItems.map((opportunity) => {
                  const isExpanded = displayMode === 'inline' && expandedOpportunityId === opportunity.id;
                  const isSelected = selectedOpportunity?.id === opportunity.id;
                  return (
                    <Fragment key={opportunity.id}>
                      <tr
                        className={`transition-colors ${
                          isExpanded || isSelected
                            ? 'bg-blue-50 dark:bg-blue-900/20'
                            : 'hover:bg-gray-50 dark:hover:bg-gray-800/30'
                        }`}
                      >
                        <td className="py-2 px-3">
                          <div className="flex items-start gap-2">
                            {displayMode === 'inline' && (
                              <button
                                onClick={() => handleOpenOpportunity(opportunity)}
                                className="mt-0.5 p-0.5 text-gray-400 dark:text-gray-500"
                              >
                                {isExpanded ? (
                                  <ChevronDown className="h-4 w-4" />
                                ) : (
                                  <ChevronRight className="h-4 w-4" />
                                )}
                              </button>
                            )}
                            <div>
                              <button
                                onClick={() => handleOpenOpportunity(opportunity)}
                                className={`font-medium text-left ${
                                  isExpanded || isSelected
                                    ? 'text-blue-700 dark:text-blue-300'
                                    : 'text-gray-900 dark:text-gray-100'
                                }`}
                              >
                                {opportunity.title}
                              </button>
                              <p className="text-gray-500 dark:text-gray-400 font-mono text-[11px]">
                                {opportunity.reference}
                              </p>
                            </div>
                          </div>
                        </td>
                    <td className="py-2 px-3 text-gray-600 dark:text-gray-400">
                      {opportunity.client_name || '-'}
                    </td>
                    <td className="py-2 px-3">
                      {getStateBadge(opportunity.state, opportunity.state_name)}
                    </td>
                    <td className="py-2 px-3">
                      {opportunity.has_job_posting && opportunity.job_posting_status ? (
                        <span
                          className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                            JOB_POSTING_STATUS_BADGES[opportunity.job_posting_status].bgClass
                          } ${JOB_POSTING_STATUS_BADGES[opportunity.job_posting_status].textClass}`}
                        >
                          {JOB_POSTING_STATUS_BADGES[opportunity.job_posting_status].label}
                        </span>
                      ) : (
                        <span className="text-gray-500 dark:text-gray-400 text-xs">
                          -
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3">
                      {opportunity.has_job_posting && opportunity.job_posting_status !== 'draft' ? (
                        <div className="flex items-center gap-1.5">
                          <span className="text-gray-900 dark:text-gray-100">
                            {opportunity.applications_count}
                          </span>
                          {opportunity.new_applications_count > 0 && (
                            <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                              +{opportunity.new_applications_count}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-500 dark:text-gray-400">-</span>
                      )}
                    </td>
                    <td className="py-2 px-3">
                      <div className="flex justify-end">
                        {opportunity.has_job_posting ? (
                          opportunity.job_posting_status === 'draft' ? (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleViewPosting(opportunity)}
                              leftIcon={<Pencil className="h-3 w-3" />}
                              className="text-xs px-2 py-1 border-amber-500 text-amber-600 hover:bg-amber-50 dark:border-amber-400 dark:text-amber-400 dark:hover:bg-amber-900/20"
                            >
                              Reprendre
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleViewPosting(opportunity)}
                              leftIcon={<Eye className="h-3 w-3" />}
                              className="text-xs px-2 py-1"
                            >
                              Voir
                            </Button>
                          )
                        ) : (
                          <Button
                            size="sm"
                            onClick={() => handleCreatePosting(opportunity)}
                            leftIcon={<Plus className="h-3 w-3" />}
                            className="text-xs px-2 py-1"
                          >
                            Créer
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {/* Inline expanded details row */}
                  {isExpanded && (
                    <tr className="bg-blue-50/50 dark:bg-blue-900/10">
                      <td colSpan={6} className="p-0">
                        <div className="border-l-4 border-blue-500">
                          <OpportunityDetailContent
                            detail={opportunityDetail}
                            opportunityId={opportunity.id}
                            isLoading={isLoadingDetail}
                            compact
                          />
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="px-3 py-2 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30">
            <div className="flex items-center justify-between">
              <p className="text-[10px] text-gray-500 dark:text-gray-400">
                {filteredItems.length === data?.items.length
                  ? `${stats.total} opportunité${stats.total > 1 ? 's' : ''}`
                  : `${filteredItems.length} résultat${filteredItems.length > 1 ? 's' : ''} sur ${stats.total}`}
              </p>
              <Link
                to="/rh/annonces"
                className="text-[10px] text-primary-600 dark:text-primary-400 hover:underline"
              >
                Voir toutes les annonces →
              </Link>
            </div>
          </div>
        </Card>
      )}

      {/* Modal view */}
      {selectedOpportunity && displayMode === 'modal' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
              <h2 className="font-semibold text-gray-900 dark:text-white">
                Détails de l'opportunité
              </h2>
              <button
                onClick={handleCloseDetail}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <OpportunityDetailContent
              detail={opportunityDetail}
              opportunityId={selectedOpportunity.id}
              isLoading={isLoadingDetail}
            />
          </div>
        </div>
      )}

      {/* Drawer view */}
      {selectedOpportunity && displayMode === 'drawer' && (
        <div className="fixed inset-y-0 right-0 z-50 w-96 bg-white dark:bg-gray-800 shadow-xl border-l border-gray-200 dark:border-gray-700 overflow-y-auto">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-800">
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Détails de l'opportunité
            </h2>
            <button
              onClick={handleCloseDetail}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <OpportunityDetailContent
            detail={opportunityDetail}
            opportunityId={selectedOpportunity.id}
            isLoading={isLoadingDetail}
          />
        </div>
      )}

      {/* Split view */}
      {selectedOpportunity && displayMode === 'split' && (
        <Card className="mt-4 !p-0 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
            <h2 className="font-semibold text-gray-900 dark:text-white">
              {selectedOpportunity.title}
            </h2>
            <button
              onClick={handleCloseDetail}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <OpportunityDetailContent
            detail={opportunityDetail}
            opportunityId={selectedOpportunity.id}
            isLoading={isLoadingDetail}
          />
        </Card>
      )}
    </div>
  );
}
