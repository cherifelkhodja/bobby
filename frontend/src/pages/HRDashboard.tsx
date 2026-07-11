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
  AlertCircle,
  Briefcase,
  Building2,
  Calendar,
  ChevronDown,
  ChevronRight,
  Columns,
  ExternalLink,
  FileText,
  Filter,
  Layout,
  MapPin,
  PanelRight,
  Square,
  User,
  X,
} from 'lucide-react';
import { hrApi, type OpportunityDetailResponse } from '../api/hr';
import { Button } from '../components/ui/Button';
import { InlineSearchInput } from '../components/ui/SearchInput';
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
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-pri"></div>
        <span className="ml-2 text-[13px] text-mut">Chargement…</span>
      </div>
    );
  }

  if (!detail) {
    return <p className="text-[13px] text-mut py-4 px-5">Aucun détail disponible</p>;
  }

  return (
    <div className={`${compact ? 'p-4' : 'p-5'} space-y-4`}>
      {/* Title */}
      <div>
        <h3 className={`font-bold text-ink ${compact ? 'text-[14.5px]' : 'text-[15.5px]'}`}>
          {detail.title}
        </h3>
        <p className="ref !text-[11px] mt-0.5">{detail.reference}</p>
      </div>

      {/* Description */}
      {detail.description && (
        <div>
          <p className="ml flex items-center gap-1.5">
            <FileText className="h-3 w-3" />
            Description
          </p>
          <p
            className={`text-mut whitespace-pre-line leading-relaxed ${compact ? 'text-xs line-clamp-6' : 'text-[13px]'}`}
          >
            {detail.description}
          </p>
        </div>
      )}

      {/* Criteria */}
      {detail.criteria && (
        <div>
          <p className="ml flex items-center gap-1.5">
            <FileText className="h-3 w-3" />
            Critères
          </p>
          <p
            className={`text-mut whitespace-pre-line leading-relaxed ${compact ? 'text-xs line-clamp-4' : 'text-[13px]'}`}
          >
            {detail.criteria}
          </p>
        </div>
      )}

      {/* Metadata grid */}
      <div className={`grid ${compact ? 'grid-cols-1 gap-2' : 'grid-cols-2 gap-3'} text-[13px]`}>
        {detail.place && (
          <div className="flex items-center gap-2 text-mut">
            <MapPin className="h-4 w-4 text-mut2 flex-shrink-0" />
            <span>{detail.place}</span>
          </div>
        )}
        {(detail.start_date || detail.end_date) && (
          <div className="flex items-center gap-2 text-mut">
            <Calendar className="h-4 w-4 text-mut2 flex-shrink-0" />
            <span>
              {detail.start_date && new Date(detail.start_date).toLocaleDateString('fr-FR')}
              {detail.start_date && detail.end_date && ' → '}
              {detail.end_date && new Date(detail.end_date).toLocaleDateString('fr-FR')}
              {detail.duration && ` (${detail.duration} j)`}
            </span>
          </div>
        )}
        {detail.company_name && (
          <div className="flex items-center gap-2 text-mut">
            <Building2 className="h-4 w-4 text-mut2 flex-shrink-0" />
            <span>{detail.company_name}</span>
          </div>
        )}
        {detail.manager_name && (
          <div className="flex items-center gap-2 text-mut">
            <User className="h-4 w-4 text-mut2 flex-shrink-0" />
            <span>Resp: {detail.manager_name}</span>
          </div>
        )}
        {detail.contact_name && (
          <div className="flex items-center gap-2 text-mut">
            <User className="h-4 w-4 text-mut2 flex-shrink-0" />
            <span>Contact: {detail.contact_name}</span>
          </div>
        )}
        {detail.expertise_area && (
          <div className="flex items-center gap-2 text-mut">
            <Briefcase className="h-4 w-4 text-mut2 flex-shrink-0" />
            <span>{detail.expertise_area}</span>
          </div>
        )}
      </div>

      {/* Link to BoondManager */}
      <div className="pt-2 border-t border-lin2">
        <a
          href={`https://ui.boondmanager.com/#opportunity/${opportunityId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs font-medium"
        >
          <ExternalLink className="h-3 w-3" />
          Voir sur BoondManager
        </a>
      </div>
    </div>
  );
}

const JOB_POSTING_STATUS_CHIPS: Record<JobPostingStatus, { label: string; chip: string }> = {
  draft: { label: 'Brouillon', chip: 'st-sla' },
  published: { label: 'Publiée', chip: 'st-grn' },
  closed: { label: 'Fermée', chip: 'st-red' },
};

// All Boond opportunity states (same as MyBoondOpportunities), mapped to v2 chips
const STATE_CONFIG: Record<number, { name: string; chip: string }> = {
  0: { name: 'En cours', chip: 'st-blu' },
  1: { name: 'Gagné', chip: 'st-grn' },
  2: { name: 'Perdu', chip: 'st-red' },
  3: { name: 'Abandonné', chip: 'st-sla' },
  4: { name: 'Gagné attente contrat', chip: 'st-grn' },
  5: { name: 'Piste identifiée', chip: 'st-amb' },
  6: { name: 'Récurrent', chip: 'st-ind' },
  7: { name: 'AO ouvert', chip: 'st-blu' },
  8: { name: 'AO clos', chip: 'st-ind' },
  9: { name: 'Reporté', chip: 'st-amb' },
  10: { name: 'Besoin en avant de phase', chip: 'st-blu' },
};

// Colonnes de la table (thead + row partagent la même grille)
const GRID_COLS = 'grid-cols-[1.6fr_130px_150px_110px_120px_120px]';

export default function HRDashboard() {
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState('');
  const [stateFilter, setStateFilter] = useState<number | 'all'>(0);
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
        <span className="st st-sla">
          <span className="dot" />
          {stateName || '—'}
        </span>
      );
    }
    return (
      <span className={`st ${config.chip}`}>
        <span className="dot" />
        {config.name}
      </span>
    );
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  if (error) {
    return (
      <div>
        <p className="bc">RH / Gestion des annonces</p>
        <h1 className="h1">Gestion des annonces</h1>
        <div className="alert red !items-start">
          <AlertCircle className="h-[18px] w-[18px] shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold m-0">
              Erreur de chargement — {error instanceof Error ? error.message : 'Erreur inconnue'}
            </p>
            <p className="font-normal text-[12px] mt-1 m-0">
              Vérifiez que votre identifiant BoondManager est configuré dans votre profil.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Entête */}
      <p className="bc">RH / Gestion des annonces</p>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="h1">Gestion des annonces</h1>
          <p className="sub">Opportunités BoondManager où vous êtes responsable RH</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {stats.published > 0 && (
            <span className="st st-grn">
              <span className="dot" />
              {stats.published} publiée{stats.published > 1 ? 's' : ''}
            </span>
          )}
          {stats.newApplications > 0 && (
            <span className="st st-blu">
              <span className="dot" />
              +{stats.newApplications} nouvelle{stats.newApplications > 1 ? 's' : ''} candidature
              {stats.newApplications > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Barre de filtres */}
      <div className="card mt-[18px] !py-3 !px-4 flex items-center gap-2.5 flex-wrap">
        <Filter className="h-3.5 w-3.5 text-mut2 shrink-0" />

        {/* Search */}
        <InlineSearchInput
          value={searchInput}
          onChange={setSearchInput}
          placeholder="Rechercher…"
          className="w-60"
        />

        {/* State filter */}
        <select
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value === 'all' ? 'all' : parseInt(e.target.value))}
          className="filter-select"
          aria-label="Filtrer par état Boond"
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
          className="filter-select"
          aria-label="Filtrer par client"
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
          className="filter-select"
          aria-label="Filtrer par annonce"
        >
          <option value="all">Toutes les annonces</option>
          <option value="with">Avec annonce</option>
          <option value="without">Sans annonce</option>
        </select>

        {/* Display mode selector */}
        <div className="seg2 ml-auto">
          {DISPLAY_MODE_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  setDisplayMode(opt.value);
                  if (opt.value !== 'inline') setExpandedOpportunityId(null);
                  if (opt.value === 'inline') setSelectedOpportunity(null);
                }}
                className={`seg2b ${displayMode === opt.value ? 'on' : ''}`}
                title={opt.label}
              >
                <Icon className="h-3.5 w-3.5" />
              </button>
            );
          })}
        </div>
      </div>

      {/* Table */}
      {filteredItems.length === 0 ? (
        <div className="card mt-4 text-center py-12">
          <Briefcase className="h-10 w-10 text-mut2 mx-auto mb-4" />
          <p className="dn">Aucune opportunité trouvée</p>
          <p className="ds mt-1.5 max-w-md mx-auto">
            {searchInput
              ? 'Aucun résultat pour vos critères de recherche.'
              : 'Vous devez être responsable RH d\'une opportunité dans BoondManager pour la voir ici.'}
          </p>
        </div>
      ) : (
        <div className="tbl mt-4">
          <div className={`thead ${GRID_COLS}`}>
            <span>Opportunité</span>
            <span>Client</span>
            <span>État Boond</span>
            <span>Annonce</span>
            <span>Candidatures</span>
            <span className="text-right">Action</span>
          </div>
          {filteredItems.map((opportunity) => {
            const isExpanded = displayMode === 'inline' && expandedOpportunityId === opportunity.id;
            const isSelected = selectedOpportunity?.id === opportunity.id;
            const postingChip = opportunity.job_posting_status
              ? JOB_POSTING_STATUS_CHIPS[opportunity.job_posting_status]
              : null;
            return (
              <Fragment key={opportunity.id}>
                <div className={`row ${GRID_COLS} ${isExpanded || isSelected ? '!bg-srf2' : ''}`}>
                  <div className="min-w-0 flex items-start gap-1.5">
                    {displayMode === 'inline' && (
                      <button
                        type="button"
                        onClick={() => handleOpenOpportunity(opportunity)}
                        className="mt-0.5 p-0.5 chev"
                        title={isExpanded ? 'Replier' : 'Déplier'}
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </button>
                    )}
                    <div className="min-w-0">
                      <button
                        type="button"
                        onClick={() => handleOpenOpportunity(opportunity)}
                        className={`nm block max-w-full truncate text-left hover:text-prit ${
                          isExpanded || isSelected ? '!text-prit' : ''
                        }`}
                      >
                        {opportunity.title}
                      </button>
                      <p className="ns ref !text-[11px] truncate">{opportunity.reference}</p>
                    </div>
                  </div>
                  <span className="cell truncate">{opportunity.client_name || '—'}</span>
                  <div>{getStateBadge(opportunity.state, opportunity.state_name)}</div>
                  <div>
                    {opportunity.has_job_posting && postingChip ? (
                      <span className={`st ${postingChip.chip}`}>
                        <span className="dot" />
                        {postingChip.label}
                      </span>
                    ) : (
                      <span className="cell text-mut2">—</span>
                    )}
                  </div>
                  <div>
                    {opportunity.has_job_posting && opportunity.job_posting_status !== 'draft' ? (
                      <div className="flex items-center gap-2">
                        <span className="cell font-semibold">{opportunity.applications_count}</span>
                        {opportunity.new_applications_count > 0 && (
                          <span className="newb">+{opportunity.new_applications_count}</span>
                        )}
                      </div>
                    ) : (
                      <span className="cell text-mut2">—</span>
                    )}
                  </div>
                  <div className="flex justify-end">
                    {opportunity.has_job_posting ? (
                      opportunity.job_posting_status === 'draft' ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          onClick={() => handleViewPosting(opportunity)}
                          className="!text-amb-fg !border-[color-mix(in_oklab,var(--amb-fg)_40%,transparent)]"
                        >
                          Reprendre
                        </Button>
                      ) : (
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          onClick={() => handleViewPosting(opportunity)}
                        >
                          Voir
                        </Button>
                      )
                    ) : (
                      <Button type="button" size="sm" onClick={() => handleCreatePosting(opportunity)}>
                        Créer
                      </Button>
                    )}
                  </div>
                </div>
                {/* Inline expanded details row */}
                {isExpanded && (
                  <div className="expand !block !p-0">
                    <OpportunityDetailContent
                      detail={opportunityDetail}
                      opportunityId={opportunity.id}
                      isLoading={isLoadingDetail}
                      compact
                    />
                  </div>
                )}
              </Fragment>
            );
          })}
          <div className="tfoot">
            <span>
              {filteredItems.length === data?.items.length
                ? `${stats.total} opportunité${stats.total > 1 ? 's' : ''}`
                : `${filteredItems.length} résultat${filteredItems.length > 1 ? 's' : ''} sur ${stats.total}`}
            </span>
            <Link to="/rh/annonces" className="alink">
              Voir toutes les annonces →
            </Link>
          </div>
        </div>
      )}

      {/* Modal view */}
      {selectedOpportunity && displayMode === 'modal' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-sur border border-lin rounded-2xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between px-5 py-4 border-b border-lin">
              <h2 className="ct">Détails de l'opportunité</h2>
              <button
                type="button"
                onClick={handleCloseDetail}
                className="p-1 text-mut2 hover:text-ink"
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
        <div className="fixed inset-y-0 right-0 z-50 w-96 bg-sur shadow-xl border-l border-lin overflow-y-auto">
          <div className="flex items-center justify-between px-5 py-4 border-b border-lin sticky top-0 bg-sur">
            <h2 className="ct">Détails de l'opportunité</h2>
            <button
              type="button"
              onClick={handleCloseDetail}
              className="p-1 text-mut2 hover:text-ink"
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
        <div className="card !p-0 mt-4 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-lin bg-srf2">
            <h2 className="ct">{selectedOpportunity.title}</h2>
            <button
              type="button"
              onClick={handleCloseDetail}
              className="p-1 text-mut2 hover:text-ink"
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
    </div>
  );
}
