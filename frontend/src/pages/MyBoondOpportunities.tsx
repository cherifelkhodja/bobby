import { useState, useMemo, Fragment } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Search,
  Sparkles,
  Check,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
  MapPin,
  Calendar,
  Building2,
  User,
  ExternalLink,
  X,
  Square,
  PanelRight,
  Columns,
  Layout,
  Pencil,
  Trash2,
} from 'lucide-react';

import {
  getMyBoondOpportunities,
  getBoondOpportunityDetail,
  anonymizeOpportunity,
  publishOpportunity,
  updatePublishedOpportunity,
  getPublishedOpportunity,
  deletePublishedOpportunity,
} from '../api/publishedOpportunities';
import { useAuthStore } from '../stores/authStore';
import { getErrorMessage } from '../api/client';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { InlineSearchInput } from '../components/ui/SearchInput';
import { EmptyState } from '../components/ui/EmptyState';
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

// All Boond opportunity states → v2 chips (blu=en cours, amb=piste, grn=gagné, red=perdu, sla=neutre)
const STATE_CONFIG: Record<number, { name: string; chip: string }> = {
  0: { name: 'En cours', chip: 'st-blu' },
  1: { name: 'Gagné', chip: 'st-grn' },
  2: { name: 'Perdu', chip: 'st-red' },
  3: { name: 'Abandonné', chip: 'st-sla' },
  4: { name: 'Gagné attente contrat', chip: 'st-grn' },
  5: { name: 'Piste identifiée', chip: 'st-amb' },
  6: { name: 'Récurrent', chip: 'st-sla' },
  7: { name: 'AO ouvert', chip: 'st-sla' },
  8: { name: 'AO clos', chip: 'st-sla' },
  9: { name: 'Reporté', chip: 'st-sla' },
  10: { name: 'Besoin en avant de phase', chip: 'st-sla' },
};


const PUBLISHED_STATUS_BADGES: Record<PublishedOpportunityStatus, { label: string; chip: string }> = {
  draft: { label: 'Brouillon', chip: 'st-sla' },
  published: { label: 'Publiée', chip: 'st-grn' },
  closed: { label: 'Fermée', chip: 'st-red' },
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
      <div className="flex items-center justify-center gap-2 py-8">
        <Loader2 className="h-5 w-5 animate-spin text-prit" />
        <span className="text-[13px] text-mut">Chargement…</span>
      </div>
    );
  }

  if (!detail) {
    return <p className="notec py-4">Aucun détail disponible</p>;
  }

  return (
    <div className={`${compact ? '' : 'p-6'} space-y-4`}>
      <div>
        <h3 className={`font-bold text-ink ${compact ? 'text-[14.5px]' : 'text-[15.5px]'}`}>
          {detail.title}
        </h3>
        <p className="ref !text-[11px] mt-1">{detail.reference}</p>
      </div>

      {detail.description && (
        <div>
          <p className="ml mb-1.5">Description</p>
          <p className={`text-mut whitespace-pre-line leading-relaxed ${compact ? 'text-xs line-clamp-6' : 'text-[13px]'}`}>
            {detail.description}
          </p>
        </div>
      )}

      {detail.criteria && (
        <div>
          <p className="ml mb-1.5">Critères</p>
          <p className={`text-mut whitespace-pre-line leading-relaxed ${compact ? 'text-xs line-clamp-4' : 'text-[13px]'}`}>
            {detail.criteria}
          </p>
        </div>
      )}

      <div className={`grid ${compact ? 'grid-cols-1 gap-2' : 'grid-cols-2 gap-3'}`}>
        {detail.place && (
          <span className="omi text-[12.5px] text-mut">
            <MapPin className="h-3.5 w-3.5 text-mut2 shrink-0" />
            {detail.place}
          </span>
        )}
        {(detail.start_date || detail.end_date) && (
          <span className="omi text-[12.5px] text-mut">
            <Calendar className="h-3.5 w-3.5 text-mut2 shrink-0" />
            <span>
              {detail.start_date && new Date(detail.start_date).toLocaleDateString('fr-FR')}
              {detail.start_date && detail.end_date && ' → '}
              {detail.end_date && new Date(detail.end_date).toLocaleDateString('fr-FR')}
              {detail.duration && ` (${detail.duration} j)`}
            </span>
          </span>
        )}
        {detail.company_name && (
          <span className="omi text-[12.5px] text-mut">
            <Building2 className="h-3.5 w-3.5 text-mut2 shrink-0" />
            {detail.company_name}
          </span>
        )}
        {detail.manager_name && (
          <span className="omi text-[12.5px] text-mut">
            <User className="h-3.5 w-3.5 text-mut2 shrink-0" />
            Resp : {detail.manager_name}
          </span>
        )}
        {detail.contact_name && (
          <span className="omi text-[12.5px] text-mut">
            <User className="h-3.5 w-3.5 text-mut2 shrink-0" />
            Contact : {detail.contact_name}
          </span>
        )}
        {detail.expertise_area && (
          <span className="omi text-[12.5px] text-mut">
            <Sparkles className="h-3.5 w-3.5 text-mut2 shrink-0" />
            {detail.expertise_area}
          </span>
        )}
      </div>

      <div className="pt-2 border-t border-lin2">
        <a
          href={`https://ui.boondmanager.com/#opportunity/${opportunityId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs font-medium text-prit hover:underline"
        >
          <ExternalLink className="h-3 w-3" />
          Voir sur BoondManager
        </a>
      </div>
    </div>
  );
}

function EditPublishedOpportunityModal({
  opportunity,
  isOpen,
  onClose,
  onSaved,
}: {
  opportunity: { id: string; title: string; description: string; skills: string[]; end_date: string | null };
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(opportunity.title);
  const [description, setDescription] = useState(opportunity.description);
  const [skillsText, setSkillsText] = useState(opportunity.skills.join(', '));
  const [endDate, setEndDate] = useState(opportunity.end_date || '');

  const queryClient = useQueryClient();

  const updateMutation = useMutation({
    mutationFn: () =>
      updatePublishedOpportunity(opportunity.id, {
        title,
        description,
        skills: skillsText
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        end_date: endDate,
      }),
    onSuccess: () => {
      toast.success('Opportunité mise à jour');
      queryClient.invalidateQueries({ queryKey: ['my-boond-opportunities'] });
      queryClient.invalidateQueries({ queryKey: ['published-opportunities'] });
      onSaved();
      onClose();
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Modifier l'opportunité" size="lg">
      <div className="space-y-4">
        <Input
          label="Titre"
          value={title}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTitle(e.target.value)}
        />
        <div>
          <label htmlFor="edit-opp-description" className="f-lab">
            Description
          </label>
          <textarea
            id="edit-opp-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="f-ta !min-h-[200px]"
          />
        </div>
        <div>
          <Input
            label="Compétences (séparées par des virgules)"
            value={skillsText}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSkillsText(e.target.value)}
            placeholder="React, TypeScript, Node.js"
          />
        </div>
        <div>
          <Input
            label="Date de fin *"
            type="date"
            value={endDate}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEndDate(e.target.value)}
          />
          {!endDate && (
            <p className="f-hint !text-redt">La date de fin est obligatoire</p>
          )}
        </div>
        <div className="flex justify-end gap-2 pt-3 border-t border-lin2">
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button
            onClick={() => updateMutation.mutate()}
            isLoading={updateMutation.isPending}
            disabled={!title.trim() || !description.trim() || !endDate}
          >
            Enregistrer
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export function MyBoondOpportunities() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const isAdmin = user?.role === 'admin';
  const [searchInput, setSearchInput] = useState('');
  const [deleteOpportunityId, setDeleteOpportunityId] = useState<string | null>(null);
  const [stateFilter, setStateFilter] = useState<number | 'all'>(0);
  const [clientFilter, setClientFilter] = useState<string>('all');
  const [managerFilter, setManagerFilter] = useState<string>('all');
  const [publicationFilter, setPublicationFilter] = useState<string>('all');
  const [displayMode, setDisplayMode] = useState<DisplayMode>('drawer');
  const [selectedOpportunity, setSelectedOpportunity] = useState<BoondOpportunity | null>(null);
  const [expandedOpportunityId, setExpandedOpportunityId] = useState<string | null>(null);

  // Edit modal state
  const [editOpportunity, setEditOpportunity] = useState<{ id: string; title: string; description: string; skills: string[]; end_date: string | null } | null>(null);

  // Anonymization modal state
  const [anonymizeOpportunity_, setAnonymizeOpportunity] = useState<BoondOpportunity | null>(null);
  const [anonymizeDetail, setAnonymizeDetail] = useState<BoondOpportunityDetail | null>(null);
  const [step, setStep] = useState<ViewStep>('list');
  const [preview, setPreview] = useState<AnonymizedPreview | null>(null);
  const [editedTitle, setEditedTitle] = useState('');
  const [editedDescription, setEditedDescription] = useState('');
  const [editedEndDate, setEditedEndDate] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const queryClient = useQueryClient();

  // Fetch Boond opportunities
  const { data, isLoading, error: fetchError, refetch } = useQuery({
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

  // Delete published opportunity mutation (admin only)
  const deleteOpportunityMutation = useMutation({
    mutationFn: (id: string) => deletePublishedOpportunity(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-boond-opportunities'] });
      queryClient.invalidateQueries({ queryKey: ['published-opportunities'] });
      toast.success('Opportunité supprimée');
      setDeleteOpportunityId(null);
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
      setDeleteOpportunityId(null);
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

      if (stateFilter !== 'all' && opp.state !== stateFilter) {
        return false;
      }

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
    setEditedEndDate(opportunity.end_date || '');
    setStep('loading-detail');

    try {
      const detail = await getBoondOpportunityDetail(opportunity.id);
      setAnonymizeDetail(detail);
      if (detail.end_date) setEditedEndDate(detail.end_date);
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
    if (!anonymizeOpportunity_ || !preview || !editedEndDate) return;
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
      end_date: editedEndDate,
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
    setEditedEndDate('');
  };

  const getStateChip = (state: number | null, stateName: string | null) => {
    const config = state !== null ? STATE_CONFIG[state] : null;
    return (
      <span className={`st ${config?.chip || 'st-sla'}`}>
        <span className="dot" />
        {config?.name || stateName || '—'}
      </span>
    );
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  if (fetchError) {
    return (
      <div className="text-center py-16">
        <AlertCircle className="h-10 w-10 text-redt mx-auto mb-4" />
        <h2 className="text-[15px] font-bold text-ink mb-2">Erreur de chargement</h2>
        <p className="notec">{getErrorMessage(fetchError)}</p>
      </div>
    );
  }

  const gridCols = 'grid-cols-[1.6fr_130px_170px_120px_110px_110px]';

  return (
    <div>
      {/* Header */}
      <p className="bc">Commercial / Gestion opportunités</p>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="h1">Gestion opportunités</h1>
          <p className="sub">Vos opportunités BoondManager · publiez-les pour la cooptation</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {(stats.byState[0] ?? 0) > 0 && (
            <span className="st st-blu">
              <span className="dot" />
              En cours : {stats.byState[0]}
            </span>
          )}
          {(stats.byState[5] ?? 0) > 0 && (
            <span className="st st-amb">
              <span className="dot" />
              Piste : {stats.byState[5]}
            </span>
          )}
          {(stats.byState[4] ?? 0) > 0 && (
            <span className="st st-grn">
              <span className="dot" />
              Gagné att. contrat : {stats.byState[4]}
            </span>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="card mt-[18px] !px-4 !py-3 flex items-center gap-2.5 flex-wrap">
        <InlineSearchInput
          value={searchInput}
          onChange={setSearchInput}
          placeholder="Rechercher…"
          className="w-60"
        />

        <select
          value={stateFilter}
          onChange={(e) => {
            const val = e.target.value;
            if (val === 'all') setStateFilter(val);
            else setStateFilter(parseInt(val));
          }}
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

        {availableManagers.length > 1 && (
          <select
            value={managerFilter}
            onChange={(e) => setManagerFilter(e.target.value)}
            className="filter-select"
            aria-label="Filtrer par manager"
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
          className="filter-select"
          aria-label="Filtrer par publication"
        >
          <option value="all">Publication : toutes</option>
          <option value="published">Publiées</option>
          <option value="unpublished">Non publiées</option>
          <option value="closed">Fermées</option>
        </select>

        {/* Display mode selector */}
        <div className="seg2 ml-auto" role="group" aria-label="Mode d'affichage du détail">
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
                aria-label={opt.label}
              >
                <Icon className="h-3.5 w-3.5" />
              </button>
            );
          })}
        </div>
      </div>

      {/* Table */}
      {filteredOpportunities.length === 0 ? (
        <div className="card mt-4">
          <EmptyState
            icon={Search}
            title="Aucune opportunité trouvée"
            description={
              searchInput
                ? 'Aucun résultat pour vos critères de recherche.'
                : 'Aucune opportunité disponible.'
            }
          />
        </div>
      ) : (
        <div className="tbl mt-4">
          <div className={`thead ${gridCols}`}>
            <span>Opportunité</span>
            <span>Client</span>
            <span>État Boond</span>
            <span>Publication</span>
            <span>Cooptations</span>
            <span className="text-right">Action</span>
          </div>
          {filteredOpportunities.map((opportunity) => {
            const isExpanded = displayMode === 'inline' && expandedOpportunityId === opportunity.id;
            const isSelected = selectedOpportunity?.id === opportunity.id;
            const isActive = isExpanded || isSelected;
            return (
              <Fragment key={opportunity.id}>
                <div className={`row ${gridCols} group ${isActive ? 'bg-pris' : ''}`}>
                  <div className="min-w-0 flex items-start gap-1.5">
                    {displayMode === 'inline' && (
                      <button
                        type="button"
                        onClick={() => handleOpenOpportunity(opportunity)}
                        className="mt-0.5 text-mut2 hover:text-mut transition-colors"
                        aria-label={isExpanded ? 'Replier le détail' : 'Déplier le détail'}
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
                        className={`nm block w-full truncate text-left transition-colors hover:text-prit ${
                          isActive ? '!text-prit' : ''
                        }`}
                      >
                        {opportunity.title}
                      </button>
                      <p className="ns ref !text-[11px]">{opportunity.reference}</p>
                    </div>
                  </div>
                  <span className="cell truncate">{opportunity.company_name || '—'}</span>
                  <div>{getStateChip(opportunity.state, opportunity.state_name)}</div>
                  <div>
                    {opportunity.is_published && opportunity.published_status ? (
                      <span className={`st ${PUBLISHED_STATUS_BADGES[opportunity.published_status].chip}`}>
                        <span className="dot" />
                        {PUBLISHED_STATUS_BADGES[opportunity.published_status].label}
                      </span>
                    ) : (
                      <span className="cell text-mut2">—</span>
                    )}
                  </div>
                  <div>
                    {opportunity.is_published ? (
                      <span className="cell font-semibold">{opportunity.cooptations_count}</span>
                    ) : (
                      <span className="cell text-mut2">—</span>
                    )}
                  </div>
                  <div className="flex items-center justify-end gap-0.5">
                    {opportunity.is_published && opportunity.published_opportunity_id ? (
                      <>
                        <button
                          type="button"
                          onClick={async () => {
                            try {
                              const pub = await getPublishedOpportunity(opportunity.published_opportunity_id!);
                              setEditOpportunity({
                                id: pub.id,
                                title: pub.title,
                                description: pub.description,
                                skills: pub.skills,
                                end_date: pub.end_date,
                              });
                            } catch (err) {
                              toast.error(getErrorMessage(err));
                            }
                          }}
                          className="p-1 rounded-md text-mut2 opacity-0 group-hover:opacity-100 hover:text-prit hover:bg-pris transition-all"
                          title="Modifier"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        {isAdmin && (
                          <button
                            type="button"
                            onClick={() => setDeleteOpportunityId(opportunity.published_opportunity_id!)}
                            className="p-1 rounded-md text-mut2 opacity-0 group-hover:opacity-100 hover:text-redt hover:bg-red-bg transition-all"
                            title="Supprimer"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => navigate(`/my-boond-opportunities/${opportunity.published_opportunity_id}`)}
                        >
                          Gérer
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handlePropose(opportunity)}
                        leftIcon={<Sparkles className="h-3 w-3" />}
                      >
                        Publier
                      </Button>
                    )}
                  </div>
                </div>
                {/* Inline expanded details row */}
                {isExpanded && (
                  <div className="expand !block">
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
              {filteredOpportunities.length === data?.items.length
                ? `${stats.total} opportunité${stats.total > 1 ? 's' : ''}`
                : `${filteredOpportunities.length} résultat${filteredOpportunities.length > 1 ? 's' : ''} sur ${stats.total}`}
              {' · synchro BoondManager'}
            </span>
            <button type="button" className="alink" onClick={() => refetch()}>
              Synchroniser maintenant →
            </button>
          </div>
        </div>
      )}

      {/* Modal view */}
      {selectedOpportunity && displayMode === 'modal' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-sur border border-lin rounded-2xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-lin">
              <h2 className="ct">Détails de l'opportunité</h2>
              <button
                type="button"
                onClick={handleCloseDetail}
                className="text-mut2 hover:text-ink transition-colors"
                aria-label="Fermer"
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
        <div className="fixed inset-y-0 right-0 z-50 w-96 bg-sur border-l border-lin shadow-xl overflow-y-auto">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-lin sticky top-0 bg-sur">
            <h2 className="ct">Détails de l'opportunité</h2>
            <button
              type="button"
              onClick={handleCloseDetail}
              className="text-mut2 hover:text-ink transition-colors"
              aria-label="Fermer"
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
        <div className="card mt-4 !p-0 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-lin bg-srf2">
            <h2 className="ct truncate">{selectedOpportunity.title}</h2>
            <button
              type="button"
              onClick={handleCloseDetail}
              className="text-mut2 hover:text-ink transition-colors shrink-0"
              aria-label="Fermer"
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

      {/* Edit Published Opportunity Modal */}
      {editOpportunity && (
        <EditPublishedOpportunityModal
          opportunity={editOpportunity}
          isOpen={!!editOpportunity}
          onClose={() => setEditOpportunity(null)}
          onSaved={() => setEditOpportunity(null)}
        />
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
          <div className="text-center py-10">
            <Loader2 className="h-10 w-10 text-prit animate-spin mx-auto mb-4" />
            <p className="notec">Récupération des informations de l'opportunité…</p>
          </div>
        )}

        {step === 'anonymizing' && (
          <div className="text-center py-10">
            <Loader2 className="h-10 w-10 text-prit animate-spin mx-auto mb-4" />
            <p className="notec">L'IA anonymise l'opportunité…</p>
          </div>
        )}

        {step === 'preview' && preview && (
          <div className="space-y-4">
            <div>
              <p className="f-lab">Titre original</p>
              <p className="text-[13px] text-mut2 line-through">{preview.original_title}</p>
            </div>

            <Input
              label="Titre anonymisé (modifiable)"
              value={editedTitle}
              onChange={(e) => setEditedTitle(e.target.value)}
            />

            <div>
              <label htmlFor="anonymized-description" className="f-lab">
                Description anonymisée (modifiable)
              </label>
              <textarea
                id="anonymized-description"
                value={editedDescription}
                onChange={(e) => setEditedDescription(e.target.value)}
                className="f-ta !min-h-[200px]"
              />
            </div>

            {preview.skills.length > 0 && (
              <div>
                <p className="f-lab">Compétences extraites</p>
                <div className="flex flex-wrap gap-2">
                  {preview.skills.map((skill, index) => (
                    <span key={index} className="sk">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div>
              <Input
                label="Date de fin *"
                type="date"
                value={editedEndDate}
                onChange={(e) => setEditedEndDate(e.target.value)}
                required
              />
              {!editedEndDate && (
                <p className="f-hint !text-redt">La date de fin est obligatoire</p>
              )}
            </div>

            <div className="flex gap-2 pt-3 border-t border-lin2">
              <Button variant="secondary" onClick={handleRegenerate} leftIcon={<Sparkles className="h-3.5 w-3.5" />}>
                Régénérer
              </Button>
              <Button variant="ghost" onClick={handleCloseModal}>
                Annuler
              </Button>
              <Button onClick={handlePublish} className="flex-1" disabled={!editedEndDate}>
                Publier
              </Button>
            </div>
          </div>
        )}

        {step === 'publishing' && (
          <div className="text-center py-10">
            <Loader2 className="h-10 w-10 text-prit animate-spin mx-auto mb-4" />
            <p className="notec">Publication en cours…</p>
          </div>
        )}

        {step === 'success' && (
          <div className="text-center py-6">
            <div className="okbox !inline-flex !mt-0">
              <Check className="h-4 w-4 shrink-0" />
              <span>Opportunité publiée !</span>
            </div>
            <p className="notec mt-3.5">
              L'opportunité est maintenant visible par tous les consultants.
            </p>
            <div className="mt-5">
              <Button onClick={handleCloseModal}>Fermer</Button>
            </div>
          </div>
        )}

        {step === 'error' && (
          <div>
            <div className="alert red !mt-0">
              <AlertCircle className="h-[18px] w-[18px] shrink-0" />
              <span>{errorMessage || 'Une erreur est survenue'}</span>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="secondary" onClick={handleCloseModal}>
                Annuler
              </Button>
              <Button onClick={handleRegenerate}>Réessayer</Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Delete confirmation modal (admin only) */}
      <Modal
        isOpen={!!deleteOpportunityId}
        onClose={() => setDeleteOpportunityId(null)}
        title="Supprimer l'opportunité"
      >
        <div className="space-y-4">
          <p className="notec">
            Êtes-vous sûr de vouloir supprimer définitivement cette opportunité publiée ?
          </p>
          <p className="text-[12.5px] text-redt">Cette action est irréversible.</p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setDeleteOpportunityId(null)}>
              Annuler
            </Button>
            <Button
              variant="danger"
              onClick={() => deleteOpportunityId && deleteOpportunityMutation.mutate(deleteOpportunityId)}
              isLoading={deleteOpportunityMutation.isPending}
            >
              Supprimer
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
