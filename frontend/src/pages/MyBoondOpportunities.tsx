import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Eye, Sparkles, Check, AlertCircle, Loader2, X, Calendar } from 'lucide-react';

import {
  getMyBoondOpportunities,
  anonymizeOpportunity,
  publishOpportunity,
} from '../api/publishedOpportunities';
import { getErrorMessage } from '../api/client';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';
import type { BoondOpportunity, AnonymizedPreview } from '../types';

type ViewStep = 'list' | 'anonymizing' | 'preview' | 'publishing' | 'success' | 'error';

export function MyBoondOpportunities() {
  const [search, setSearch] = useState('');
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
      // Refresh the list to show the published badge
      queryClient.invalidateQueries({ queryKey: ['my-boond-opportunities'] });
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error));
      setStep('error');
    },
  });

  // Filter opportunities by search
  const filteredOpportunities = data?.items.filter((opp) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      opp.title.toLowerCase().includes(searchLower) ||
      opp.reference.toLowerCase().includes(searchLower) ||
      opp.company_name?.toLowerCase().includes(searchLower)
    );
  }) || [];

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

  const getStateBadgeClass = (state: number | null) => {
    switch (state) {
      case 5: // En cours
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      case 6: // Signée
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
      case 10: // En attente
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
      case 0: // Perdue
      case 7: // Abandonnée
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400';
    }
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

  const isProcessing = step === 'anonymizing' || step === 'publishing';

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Mes opportunités Boond
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Publiez vos opportunités anonymisées pour la cooptation
          </p>
        </div>
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Rechercher..."
            className="pl-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {filteredOpportunities.length === 0 ? (
        <Card className="text-center py-12">
          <div className="text-gray-400 mb-4">
            <Search className="h-12 w-12 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
            Aucune opportunité trouvée
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            {search
              ? "Aucun résultat pour votre recherche."
              : "Vous n'avez pas d'opportunité en tant que manager principal dans BoondManager."}
          </p>
        </Card>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">
                  Titre
                </th>
                <th className="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">
                  Référence
                </th>
                <th className="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">
                  Client
                </th>
                <th className="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">
                  État
                </th>
                <th className="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">
                  Date fin
                </th>
                <th className="text-right py-3 px-4 font-medium text-gray-700 dark:text-gray-300">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredOpportunities.map((opportunity) => (
                <tr
                  key={opportunity.id}
                  className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                >
                  <td className="py-3 px-4">
                    <button
                      onClick={() => setDetailModalOpportunity(opportunity)}
                      className="text-left text-primary-600 dark:text-primary-400 hover:underline font-medium"
                    >
                      {opportunity.title}
                    </button>
                    {opportunity.is_published && (
                      <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                        Publiée
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                    {opportunity.reference}
                  </td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                    {opportunity.company_name || '-'}
                  </td>
                  <td className="py-3 px-4">
                    {opportunity.state_name && (
                      <span className={`px-2 py-1 text-xs rounded-full ${getStateBadgeClass(opportunity.state)}`}>
                        {opportunity.state_name}
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
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
                <p className="text-gray-900 dark:text-gray-100">
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
                <p className="text-gray-900 dark:text-gray-100">
                  {detailModalOpportunity.state_name || '-'}
                </p>
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
              <p className="text-gray-900 dark:text-gray-100 whitespace-pre-wrap">
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
