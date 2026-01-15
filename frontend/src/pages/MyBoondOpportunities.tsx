import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Eye, Sparkles, Check, AlertCircle, Loader2, Filter, TrendingUp, Clock, CheckCircle2, XCircle } from 'lucide-react';

import {
  getMyBoondOpportunities,
  anonymizeOpportunity,
  publishOpportunity,
} from '../api/publishedOpportunities';
import { getErrorMessage } from '../api/client';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';
import type { BoondOpportunity, AnonymizedPreview } from '../types';

type ViewStep = 'list' | 'anonymizing' | 'preview' | 'publishing' | 'success' | 'error';

// State configuration with colors matching Boond
const STATE_CONFIG: Record<number, { name: string; color: string; bgClass: string; textClass: string }> = {
  0: { name: 'En cours', color: 'blue', bgClass: 'bg-blue-100 dark:bg-blue-900/30', textClass: 'text-blue-700 dark:text-blue-400' },
  1: { name: 'Gagné', color: 'green', bgClass: 'bg-green-100 dark:bg-green-900/30', textClass: 'text-green-700 dark:text-green-400' },
  2: { name: 'Perdu', color: 'red', bgClass: 'bg-red-100 dark:bg-red-900/30', textClass: 'text-red-700 dark:text-red-400' },
  3: { name: 'Abandonné', color: 'gray', bgClass: 'bg-gray-200 dark:bg-gray-700', textClass: 'text-gray-700 dark:text-gray-300' },
  4: { name: 'Gagné attente contrat', color: 'green', bgClass: 'bg-emerald-100 dark:bg-emerald-900/30', textClass: 'text-emerald-700 dark:text-emerald-400' },
  5: { name: 'Piste identifiée', color: 'yellow', bgClass: 'bg-yellow-100 dark:bg-yellow-900/30', textClass: 'text-yellow-700 dark:text-yellow-400' },
  6: { name: 'Récurrent', color: 'green', bgClass: 'bg-teal-100 dark:bg-teal-900/30', textClass: 'text-teal-700 dark:text-teal-400' },
  7: { name: 'AO ouvert', color: 'cyan', bgClass: 'bg-cyan-100 dark:bg-cyan-900/30', textClass: 'text-cyan-700 dark:text-cyan-400' },
  8: { name: 'AO clos', color: 'indigo', bgClass: 'bg-indigo-100 dark:bg-indigo-900/30', textClass: 'text-indigo-700 dark:text-indigo-400' },
  9: { name: 'Reporté', color: 'pink', bgClass: 'bg-pink-100 dark:bg-pink-900/30', textClass: 'text-pink-700 dark:text-pink-400' },
  10: { name: 'Besoin en avant de phase', color: 'blue', bgClass: 'bg-sky-100 dark:bg-sky-900/30', textClass: 'text-sky-700 dark:text-sky-400' },
};

export function MyBoondOpportunities() {
  const [search, setSearch] = useState('');
  const [stateFilter, setStateFilter] = useState<number | 'all'>('all');
  const [selectedOpportunity, setSelectedOpportunity] = useState<BoondOpportunity | null>(null);
  const [detailModalOpportunity, setDetailModalOpportunity] = useState<BoondOpportunity | null>(null);
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

  // Calculate stats
  const stats = useMemo(() => {
    if (!data?.items) return { total: 0, byState: {}, won: 0, inProgress: 0, lost: 0 };

    const byState: Record<number, number> = {};
    let won = 0;
    let inProgress = 0;
    let lost = 0;

    data.items.forEach((opp) => {
      if (opp.state !== null) {
        byState[opp.state] = (byState[opp.state] || 0) + 1;

        // Categorize
        if ([1, 4, 6].includes(opp.state)) won++;
        else if ([0, 5, 7, 10].includes(opp.state)) inProgress++;
        else if ([2, 3, 8, 9].includes(opp.state)) lost++;
      }
    });

    return { total: data.items.length, byState, won, inProgress, lost };
  }, [data?.items]);

  // Available states for filter (only states that have opportunities)
  const availableStates = useMemo(() => {
    return Object.entries(stats.byState)
      .map(([state, count]) => ({ state: parseInt(state), count }))
      .sort((a, b) => b.count - a.count);
  }, [stats.byState]);

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
      queryClient.invalidateQueries({ queryKey: ['my-boond-opportunities'] });
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error));
      setStep('error');
    },
  });

  // Filter opportunities by search and state
  const filteredOpportunities = useMemo(() => {
    return data?.items.filter((opp) => {
      // State filter
      if (stateFilter !== 'all' && opp.state !== stateFilter) return false;

      // Search filter
      if (!search) return true;
      const searchLower = search.toLowerCase();
      return (
        opp.title.toLowerCase().includes(searchLower) ||
        opp.reference.toLowerCase().includes(searchLower) ||
        opp.company_name?.toLowerCase().includes(searchLower)
      );
    }) || [];
  }, [data?.items, search, stateFilter]);

  const handlePropose = (opportunity: BoondOpportunity) => {
    setSelectedOpportunity(opportunity);
    setErrorMessage(null);
    setStep('anonymizing');

    anonymizeMutation.mutate({
      boond_opportunity_id: opportunity.id,
      title: opportunity.title,
      description: opportunity.description,
    });
  };

  const handleRegenerate = () => {
    if (!selectedOpportunity) return;
    setStep('anonymizing');
    setErrorMessage(null);

    anonymizeMutation.mutate({
      boond_opportunity_id: selectedOpportunity.id,
      title: selectedOpportunity.title,
      description: selectedOpportunity.description,
    });
  };

  const handlePublish = () => {
    if (!selectedOpportunity || !preview) return;
    setStep('publishing');
    setErrorMessage(null);

    publishMutation.mutate({
      boond_opportunity_id: selectedOpportunity.id,
      title: editedTitle,
      description: editedDescription,
      skills: preview.skills,
      original_title: selectedOpportunity.title,
      original_data: {
        reference: selectedOpportunity.reference,
        company_name: selectedOpportunity.company_name,
        description: selectedOpportunity.description,
      },
      end_date: selectedOpportunity.end_date,
    });
  };

  const handleCloseModal = () => {
    setSelectedOpportunity(null);
    setPreview(null);
    setStep('list');
    setErrorMessage(null);
    setEditedTitle('');
    setEditedDescription('');
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('fr-FR');
  };

  const getStateBadge = (state: number | null, stateName: string | null) => {
    const config = state !== null ? STATE_CONFIG[state] : null;
    if (!config) {
      return (
        <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
          {stateName || 'Inconnu'}
        </span>
      );
    }
    return (
      <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${config.bgClass} ${config.textClass}`}>
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
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Publiez vos opportunités anonymisées pour la cooptation
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="!p-4">
          <div className="flex items-center">
            <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
              <TrendingUp className="h-5 w-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">Total</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.total}</p>
            </div>
          </div>
        </Card>

        <Card className="!p-4">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Clock className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">En cours</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.inProgress}</p>
            </div>
          </div>
        </Card>

        <Card className="!p-4">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">Gagnées</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.won}</p>
            </div>
          </div>
        </Card>

        <Card className="!p-4">
          <div className="flex items-center">
            <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
              <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">Perdues/Fermées</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.lost}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card className="!p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Rechercher par titre, référence ou client..."
              className="pl-10"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value === 'all' ? 'all' : parseInt(e.target.value))}
              className="px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="all">Tous les états ({stats.total})</option>
              {availableStates.map(({ state, count }) => (
                <option key={state} value={state}>
                  {STATE_CONFIG[state]?.name || `État ${state}`} ({count})
                </option>
              ))}
            </select>
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
          <p className="text-gray-500 dark:text-gray-400">
            {search || stateFilter !== 'all'
              ? "Aucun résultat pour vos critères de recherche."
              : "Vous n'avez pas d'opportunité en tant que manager principal dans BoondManager."}
          </p>
        </Card>
      ) : (
        <Card className="overflow-hidden !p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800/50">
                <tr>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300 text-sm">
                    Titre
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300 text-sm">
                    Référence
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300 text-sm">
                    Client
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300 text-sm">
                    État
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300 text-sm">
                    Date fin
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300 text-sm">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {filteredOpportunities.map((opportunity) => (
                  <tr
                    key={opportunity.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setDetailModalOpportunity(opportunity)}
                          className="text-left text-primary-600 dark:text-primary-400 hover:underline font-medium"
                        >
                          {opportunity.title}
                        </button>
                        {opportunity.is_published && (
                          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                            Publiée
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-gray-500 dark:text-gray-400 font-mono text-sm">
                        {opportunity.reference}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                      {opportunity.company_name || '-'}
                    </td>
                    <td className="py-3 px-4">
                      {getStateBadge(opportunity.state, opportunity.state_name)}
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400 text-sm">
                      {formatDate(opportunity.end_date)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setDetailModalOpportunity(opportunity)}
                          leftIcon={<Eye className="h-4 w-4" />}
                        >
                          Voir
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handlePropose(opportunity)}
                          disabled={opportunity.is_published}
                          leftIcon={<Sparkles className="h-4 w-4" />}
                        >
                          {opportunity.is_published ? 'Déjà publiée' : 'Proposer'}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-3 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {filteredOpportunities.length} opportunité{filteredOpportunities.length > 1 ? 's' : ''} affichée{filteredOpportunities.length > 1 ? 's' : ''}
              {(search || stateFilter !== 'all') && ` sur ${stats.total}`}
            </p>
          </div>
        </Card>
      )}

      {/* Detail Modal */}
      <Modal
        isOpen={!!detailModalOpportunity}
        onClose={() => setDetailModalOpportunity(null)}
        title="Détail de l'opportunité"
        size="lg"
      >
        {detailModalOpportunity && (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Titre
              </label>
              <p className="text-gray-900 dark:text-gray-100">
                {detailModalOpportunity.title}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Référence
                </label>
                <p className="text-gray-900 dark:text-gray-100 font-mono">
                  {detailModalOpportunity.reference}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Client
                </label>
                <p className="text-gray-900 dark:text-gray-100">
                  {detailModalOpportunity.company_name || '-'}
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  État
                </label>
                <div className="mt-1">
                  {getStateBadge(detailModalOpportunity.state, detailModalOpportunity.state_name)}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Date de fin
                </label>
                <p className="text-gray-900 dark:text-gray-100">
                  {formatDate(detailModalOpportunity.end_date)}
                </p>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Description
              </label>
              <p className="text-gray-900 dark:text-gray-100 whitespace-pre-wrap mt-1 max-h-64 overflow-y-auto">
                {detailModalOpportunity.description || 'Aucune description'}
              </p>
            </div>
          </div>
        )}
      </Modal>

      {/* Anonymization/Preview Modal */}
      <Modal
        isOpen={!!selectedOpportunity && step !== 'list'}
        onClose={handleCloseModal}
        title={
          step === 'anonymizing'
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
        {/* Anonymizing state */}
        {step === 'anonymizing' && (
          <div className="text-center py-8">
            <Loader2 className="h-12 w-12 text-primary-500 animate-spin mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              L'IA anonymise l'opportunité...
            </p>
          </div>
        )}

        {/* Preview state */}
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
                className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 min-h-[200px]"
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

        {/* Publishing state */}
        {step === 'publishing' && (
          <div className="text-center py-8">
            <Loader2 className="h-12 w-12 text-primary-500 animate-spin mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              Publication en cours...
            </p>
          </div>
        )}

        {/* Success state */}
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

        {/* Error state */}
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
