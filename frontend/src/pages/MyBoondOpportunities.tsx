import { useState, useMemo, Fragment } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Sparkles,
  Check,
  AlertCircle,
  Loader2,
  Filter,
  TrendingUp,
  Eye,
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
  Users,
} from 'lucide-react';

import {
  getMyBoondOpportunities,
  getBoondOpportunityDetail,
  anonymizeOpportunity,
  publishOpportunity,
} from '../api/publishedOpportunities';
import { getErrorMessage } from '../api/client';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { PageSpinner } from '../components/ui/Spinner';
import type { BoondOpportunity, BoondOpportunityDetail, AnonymizedPreview, PublishedOpportunityStatus } from '../types';

type ViewStep = 'list' | 'loading-detail' | 'anonymizing' | 'preview' | 'publishing' | 'success' | 'error';

// Display modes for opportunity details
type DisplayMode = 'modal' | 'drawer' | 'split' | 'inline';

const DISPLAY_MODE_OPTIONS: { value: DisplayMode; label: string; icon: typeof Layout }[] = [
  { value: 'modal', label: 'Pop-up', icon: Square },
  { value: 'drawer', label: 'Panel latéral', icon: PanelRight },
  { value: 'split', label: 'Vue split', icon: Columns },
  { value: 'inline', label: 'Expansion', icon: Layout },
];

// State configuration for open/active opportunities only (0, 5, 6, 7, 10)
const STATE_CONFIG: Record<number, { name: string; bgClass: string; textClass: string }> = {
  0: { name: 'En cours', bgClass: 'bg-blue-100 dark:bg-blue-900/30', textClass: 'text-blue-700 dark:text-blue-400' },
  5: { name: 'Piste identifiée', bgClass: 'bg-yellow-100 dark:bg-yellow-900/30', textClass: 'text-yellow-700 dark:text-yellow-400' },
  6: { name: 'Récurrent', bgClass: 'bg-teal-100 dark:bg-teal-900/30', textClass: 'text-teal-700 dark:text-teal-400' },
  7: { name: 'AO ouvert', bgClass: 'bg-cyan-100 dark:bg-cyan-900/30', textClass: 'text-cyan-700 dark:text-cyan-400' },
  10: { name: 'Besoin en avant de phase', bgClass: 'bg-sky-100 dark:bg-sky-900/30', textClass: 'text-sky-700 dark:text-sky-400' },
};

const PUBLISHED_STATUS_BADGES: Record<PublishedOpportunityStatus, { label: string; bgClass: string; textClass: string }> = {
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
    label: 'Clôturée',
    bgClass: 'bg-red-100 dark:bg-red-900/30',
    textClass: 'text-red-800 dark:text-red-300',
  },
};

// Opportunity detail content component (same as HRDashboard)
function OpportunityDetailContent({
  detail,
  opportunityId,
  isLoading,
  compact = false,
}: {
  detail: BoondOpportunityDetail | undefined;
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
      <div>
        <h3 className={`font-semibold text-gray-900 dark:text-white ${compact ? 'text-base' : 'text-lg'}`}>
          {detail.title}
        </h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">{detail.reference}</p>
      </div>

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
            <Sparkles className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <span>{detail.expertise_area}</span>
          </div>
        )}
      </div>

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

export function MyBoondOpportunities() {
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState('');
  const [stateFilter, setStateFilter] = useState<number | 'all'>('all');
  const [clientFilter, setClientFilter] = useState<string>('all');
  const [managerFilter, setManagerFilter] = useState<string>('all');
  const [publicationFilter, setPublicationFilter] = useState<string>('all');
  const [displayMode, setDisplayMode] = useState<DisplayMode>('drawer');
  const [selectedOpportunity, setSelectedOpportunity] = useState<BoondOpportunity | null>(null);
  const [expandedOpportunityId, setExpandedOpportunityId] = useState<string | null>(null);

  // Anonymization modal state
  const [anonymizeOpportunity_, setAnonymizeOpportunity] = useState<BoondOpportunity | null>(null);
  const [anonymizeDetail, setAnonymizeDetail] = useState<BoondOpportunityDetail | null>(null);
  const [step, setStep] = useState<ViewStep>('list');
  const [preview, setPreview] = useState<AnonymizedPreview | null>(null);
  const [editedTitle, setEditedTitle] = useState('');
  const [editedDescription, setEditedDescription] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const queryClient = useQueryClient();

  // Fetch Boond opportunities
  const { data, isLoading, error: fetchError } = useQuery({
    queryKey: ['my-boond-opportunities'],
    queryFn: getMyBoondOpportunities,
  });

  // Fetch selected/expanded opportunity details
  const activeOpportunityId = selectedOpportunity?.id || expandedOpportunityId;
  const { data: opportunityDetail, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['boond-opportunity-detail', activeOpportunityId],
    queryFn: () => getBoondOpportunityDetail(activeOpportunityId!),
    enabled: !!activeOpportunityId,
  });

  // Calculate stats and available filters
  const { stats, availableStates, availableClients, availableManagers } = useMemo(() => {
    if (!data?.items) {
      return {
        stats: { total: 0, published: 0, totalCooptations: 0, byState: {} as Record<number, number> },
        availableStates: [] as { state: number; count: number }[],
        availableClients: [] as { name: string; count: number }[],
        availableManagers: [] as { name: string; count: number }[],
      };
    }

    const byState: Record<number, number> = {};
    const clientsMap: Record<string, number> = {};
    const managersMap: Record<string, number> = {};
    let published = 0;
    let totalCooptations = 0;

    data.items.forEach((opp) => {
      if (opp.state !== null) {
        byState[opp.state] = (byState[opp.state] || 0) + 1;
      }

      const clientName = opp.company_name || 'Sans client';
      clientsMap[clientName] = (clientsMap[clientName] || 0) + 1;

      const managerName = opp.manager_name || 'Sans manager';
      managersMap[managerName] = (managersMap[managerName] || 0) + 1;

      if (opp.published_status === 'published') {
        published++;
      }

      totalCooptations += opp.cooptations_count;
    });

    const states = Object.entries(byState)
      .map(([state, count]) => ({ state: parseInt(state), count }))
      .sort((a, b) => b.count - a.count);

    const clients = Object.entries(clientsMap)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    const managers = Object.entries(managersMap)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    return {
      stats: { total: data.items.length, published, totalCooptations, byState },
      availableStates: states,
      availableClients: clients,
      availableManagers: managers,
    };
  }, [data?.items]);

  // Anonymize mutation
  const anonymizeMutation = useMutation({
    mutationFn: anonymizeOpportunity,
    onSuccess: (result) => {
      setPreview(result);
      setEditedTitle(result.anonymized_title);
      setEditedDescription(result.anonymized_description);
      setStep('preview');
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error));
      setStep('error');
    },
  });

  // Publish mutation
  const publishMutation = useMutation({
    mutationFn: publishOpportunity,
    onSuccess: () => {
      setStep('success');
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['my-boond-opportunities'] });
      }, 100);
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error));
      setStep('error');
    },
  });

  // Filter opportunities
  const filteredOpportunities = useMemo(() => {
    return data?.items.filter((opp) => {
      if (searchInput) {
        const searchLower = searchInput.toLowerCase();
        const matchesSearch =
          opp.title.toLowerCase().includes(searchLower) ||
          opp.reference.toLowerCase().includes(searchLower) ||
          (opp.company_name?.toLowerCase().includes(searchLower) ?? false);
        if (!matchesSearch) return false;
      }

      if (stateFilter !== 'all' && opp.state !== stateFilter) return false;

      if (clientFilter !== 'all') {
        const clientName = opp.company_name || 'Sans client';
        if (clientName !== clientFilter) return false;
      }

      if (managerFilter !== 'all') {
        const managerName = opp.manager_name || 'Sans manager';
        if (managerName !== managerFilter) return false;
      }

      // Publication filter
      if (publicationFilter === 'published' && opp.published_status !== 'published') return false;
      if (publicationFilter === 'unpublished' && opp.is_published) return false;
      if (publicationFilter === 'closed' && opp.published_status !== 'closed') return false;

      return true;
    }) || [];
  }, [data?.items, searchInput, stateFilter, clientFilter, managerFilter, publicationFilter]);

  const handleOpenOpportunity = (opportunity: BoondOpportunity) => {
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

  const handlePropose = async (opportunity: BoondOpportunity) => {
    setAnonymizeOpportunity(opportunity);
    setAnonymizeDetail(null);
    setErrorMessage(null);
    setStep('loading-detail');

    try {
      const detail = await getBoondOpportunityDetail(opportunity.id);
      setAnonymizeDetail(detail);
      setStep('anonymizing');

      const fullDescription = [detail.description, detail.criteria]
        .filter(Boolean)
        .join('\n\nCritères:\n');

      anonymizeMutation.mutate({
        boond_opportunity_id: opportunity.id,
        title: opportunity.title,
        description: fullDescription || null,
      });
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
      setStep('error');
    }
  };

  const handleRegenerate = () => {
    if (!anonymizeOpportunity_) return;
    setStep('anonymizing');
    setErrorMessage(null);

    const detail = anonymizeDetail;
    const fullDescription = detail
      ? [detail.description, detail.criteria].filter(Boolean).join('\n\nCritères:\n')
      : anonymizeOpportunity_.description;

    anonymizeMutation.mutate({
      boond_opportunity_id: anonymizeOpportunity_.id,
      title: anonymizeOpportunity_.title,
      description: fullDescription || null,
    });
  };

  const handlePublish = () => {
    if (!anonymizeOpportunity_ || !preview) return;
    setStep('publishing');
    setErrorMessage(null);

    publishMutation.mutate({
      boond_opportunity_id: anonymizeOpportunity_.id,
      title: editedTitle,
      description: editedDescription,
      skills: preview.skills,
      original_title: anonymizeOpportunity_.title,
      original_data: {
        reference: anonymizeOpportunity_.reference,
        company_name: anonymizeOpportunity_.company_name,
        description: anonymizeOpportunity_.description,
      },
      end_date: anonymizeOpportunity_.end_date || null,
    });
  };

  const handleCloseModal = () => {
    setAnonymizeOpportunity(null);
    setAnonymizeDetail(null);
    setPreview(null);
    setStep('list');
    setErrorMessage(null);
    setEditedTitle('');
    setEditedDescription('');
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

  if (fetchError) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Erreur de chargement
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          {getErrorMessage(fetchError)}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Mes opportunités Boond
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1 text-sm">
          Publiez vos opportunités anonymisées pour la cooptation
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
            {stats.totalCooptations > 0 && (
              <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400">
                {stats.totalCooptations} cooptation{stats.totalCooptations > 1 ? 's' : ''}
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

          {availableManagers.length > 1 && (
            <select
              value={managerFilter}
              onChange={(e) => setManagerFilter(e.target.value)}
              className="min-w-[160px] px-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="all">Tous les managers ({availableManagers.length})</option>
              {availableManagers.map(({ name, count }) => (
                <option key={name} value={name}>
                  {name} ({count})
                </option>
              ))}
            </select>
          )}

          {/* Publication filter */}
          <select
            value={publicationFilter}
            onChange={(e) => setPublicationFilter(e.target.value)}
            className="min-w-[160px] px-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="all">Toutes publications</option>
            <option value="published">Publiées</option>
            <option value="unpublished">Non publiées</option>
            <option value="closed">Clôturées</option>
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
      {filteredOpportunities.length === 0 ? (
        <Card className="text-center py-12">
          <div className="text-gray-400 mb-4">
            <Search className="h-12 w-12 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
            Aucune opportunité trouvée
          </h3>
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            {searchInput
              ? 'Aucun résultat pour vos critères de recherche.'
              : 'Aucune opportunité disponible.'}
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
                    Publication
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px]">
                    Cooptations
                  </th>
                  <th className="text-right py-2 px-3 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px]">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {filteredOpportunities.map((opportunity) => {
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
                          {opportunity.company_name || '-'}
                        </td>
                        <td className="py-2 px-3">
                          {getStateBadge(opportunity.state, opportunity.state_name)}
                        </td>
                        <td className="py-2 px-3">
                          {opportunity.is_published && opportunity.published_status ? (
                            <span
                              className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                                PUBLISHED_STATUS_BADGES[opportunity.published_status].bgClass
                              } ${PUBLISHED_STATUS_BADGES[opportunity.published_status].textClass}`}
                            >
                              {PUBLISHED_STATUS_BADGES[opportunity.published_status].label}
                            </span>
                          ) : (
                            <span className="text-gray-500 dark:text-gray-400 text-xs">-</span>
                          )}
                        </td>
                        <td className="py-2 px-3">
                          {opportunity.is_published ? (
                            <div className="flex items-center gap-1.5">
                              <Users className="h-3 w-3 text-gray-400" />
                              <span className="text-gray-900 dark:text-gray-100">
                                {opportunity.cooptations_count}
                              </span>
                            </div>
                          ) : (
                            <span className="text-gray-500 dark:text-gray-400">-</span>
                          )}
                        </td>
                        <td className="py-2 px-3">
                          <div className="flex justify-end">
                            {opportunity.is_published && opportunity.published_opportunity_id ? (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => navigate(`/my-boond-opportunities/${opportunity.published_opportunity_id}`)}
                                leftIcon={<Eye className="h-3 w-3" />}
                                className="text-xs px-2 py-1"
                              >
                                Voir
                              </Button>
                            ) : (
                              <Button
                                size="sm"
                                onClick={() => handlePropose(opportunity)}
                                leftIcon={<Sparkles className="h-3 w-3" />}
                                className="text-xs px-2 py-1"
                              >
                                Proposer
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
            <p className="text-[10px] text-gray-500 dark:text-gray-400">
              {filteredOpportunities.length === data?.items.length
                ? `${stats.total} opportunité${stats.total > 1 ? 's' : ''}`
                : `${filteredOpportunities.length} résultat${filteredOpportunities.length > 1 ? 's' : ''} sur ${stats.total}`}
            </p>
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

      {/* Anonymization/Preview Modal */}
      <Modal
        isOpen={!!anonymizeOpportunity_ && step !== 'list'}
        onClose={handleCloseModal}
        title={
          step === 'loading-detail'
            ? 'Chargement des informations...'
            : step === 'anonymizing'
            ? 'Anonymisation en cours...'
            : step === 'preview'
            ? 'Prévisualisation'
            : step === 'publishing'
            ? 'Publication en cours...'
            : step === 'success'
            ? 'Publication réussie'
            : 'Erreur'
        }
        size="lg"
      >
        {step === 'loading-detail' && (
          <div className="text-center py-8">
            <Loader2 className="h-12 w-12 text-primary-500 animate-spin mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              Récupération des informations de l'opportunité...
            </p>
          </div>
        )}

        {step === 'anonymizing' && (
          <div className="text-center py-8">
            <Loader2 className="h-12 w-12 text-primary-500 animate-spin mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              L'IA anonymise l'opportunité...
            </p>
          </div>
        )}

        {step === 'preview' && preview && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Titre original
              </label>
              <p className="text-gray-500 dark:text-gray-400 line-through">
                {preview.original_title}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Titre anonymisé (modifiable)
              </label>
              <Input
                value={editedTitle}
                onChange={(e) => setEditedTitle(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Description anonymisée (modifiable)
              </label>
              <textarea
                value={editedDescription}
                onChange={(e) => setEditedDescription(e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 min-h-[200px] text-sm"
              />
            </div>

            {preview.skills.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Compétences extraites
                </label>
                <div className="flex flex-wrap gap-2">
                  {preview.skills.map((skill, index) => (
                    <span
                      key={index}
                      className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-sm text-gray-700 dark:text-gray-300"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button variant="outline" onClick={handleRegenerate}>
                Régénérer
              </Button>
              <Button variant="outline" onClick={handleCloseModal}>
                Annuler
              </Button>
              <Button onClick={handlePublish} className="flex-1">
                Publier
              </Button>
            </div>
          </div>
        )}

        {step === 'publishing' && (
          <div className="text-center py-8">
            <Loader2 className="h-12 w-12 text-primary-500 animate-spin mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              Publication en cours...
            </p>
          </div>
        )}

        {step === 'success' && (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check className="h-8 w-8 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              Opportunité publiée !
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              L'opportunité est maintenant visible par tous les consultants.
            </p>
            <Button onClick={handleCloseModal}>Fermer</Button>
          </div>
        )}

        {step === 'error' && (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="h-8 w-8 text-red-600 dark:text-red-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              Erreur
            </h3>
            <p className="text-red-600 dark:text-red-400 mb-6">
              {errorMessage || "Une erreur est survenue"}
            </p>
            <div className="flex gap-3 justify-center">
              <Button variant="outline" onClick={handleCloseModal}>
                Annuler
              </Button>
              <Button onClick={handleRegenerate}>Réessayer</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
