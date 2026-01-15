import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Plus, Calendar, Briefcase, Eye, Sparkles } from 'lucide-react';

import { listPublishedOpportunities } from '../api/publishedOpportunities';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { PageSpinner } from '../components/ui/Spinner';
import { Modal } from '../components/ui/Modal';
import { CreateCooptationForm } from '../components/cooptations/CreateCooptationForm';
import type { PublishedOpportunity, Opportunity } from '../types';

export function Opportunities() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(null);
  const [detailOpportunity, setDetailOpportunity] = useState<PublishedOpportunity | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['published-opportunities', page, search],
    queryFn: () => listPublishedOpportunities({ page, page_size: 20, search }),
  });

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  // Convert PublishedOpportunity to Opportunity format for the cooptation form
  const toOpportunityFormat = (pub: PublishedOpportunity): Opportunity => ({
    id: pub.id,
    external_id: pub.boond_opportunity_id,
    title: pub.title,
    reference: `PUB-${pub.boond_opportunity_id}`,
    budget: null,
    start_date: null,
    end_date: pub.end_date,
    response_deadline: null,
    manager_name: null,
    manager_boond_id: null,
    client_name: null,
    description: pub.description,
    skills: pub.skills,
    location: null,
    is_open: pub.status === 'published',
    is_shared: true,
    owner_id: null,
    days_until_deadline: null,
    synced_at: pub.created_at,
    created_at: pub.created_at,
  });

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Opportunités
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {data?.total || 0} opportunité{(data?.total || 0) > 1 ? 's' : ''} disponible{(data?.total || 0) > 1 ? 's' : ''}
          </p>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Rechercher par titre, compétence..."
            className="pl-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {data?.items.length === 0 ? (
        <Card className="text-center py-16">
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
            <Sparkles className="h-8 w-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Aucune opportunité disponible
          </h3>
          <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
            {search
              ? 'Aucun résultat pour votre recherche. Essayez avec d\'autres termes.'
              : 'Les opportunités seront publiées par les commerciaux. Revenez bientôt !'}
          </p>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-1">
          {data?.items.map((opportunity) => (
            <Card
              key={opportunity.id}
              className="group hover:shadow-lg hover:border-primary-200 dark:hover:border-primary-800 transition-all duration-200 !p-0 overflow-hidden"
            >
              {/* Accent bar */}
              <div className="h-1 bg-gradient-to-r from-primary-500 to-primary-400" />

              <div className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    {/* Title & Status */}
                    <div className="flex items-start gap-3 mb-3">
                      <button
                        onClick={() => setDetailOpportunity(opportunity)}
                        className="text-left group/title"
                      >
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 group-hover/title:text-primary-600 dark:group-hover/title:text-primary-400 transition-colors">
                          {opportunity.title}
                        </h3>
                      </button>
                      <span className={`shrink-0 px-2.5 py-1 text-xs font-semibold rounded-full ${
                        opportunity.status === 'published'
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400'
                          : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                      }`}>
                        {opportunity.status === 'published' ? 'Active' : opportunity.status_display}
                      </span>
                    </div>

                    {/* Description */}
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2 leading-relaxed">
                      {opportunity.description}
                    </p>

                    {/* Meta info */}
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-gray-500 dark:text-gray-400 mb-4">
                      <span className="flex items-center gap-1.5">
                        <Briefcase className="h-3.5 w-3.5" />
                        Publiée le {formatDate(opportunity.created_at)}
                      </span>
                      {opportunity.end_date && (
                        <span className="flex items-center gap-1.5">
                          <Calendar className="h-3.5 w-3.5" />
                          Fin prévue : {formatDate(opportunity.end_date)}
                        </span>
                      )}
                    </div>

                    {/* Skills */}
                    {opportunity.skills.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {opportunity.skills.slice(0, 5).map((skill) => (
                          <span
                            key={skill}
                            className="px-2.5 py-1 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-md text-xs font-medium"
                          >
                            {skill}
                          </span>
                        ))}
                        {opportunity.skills.length > 5 && (
                          <span className="px-2.5 py-1 text-xs font-medium text-gray-500 dark:text-gray-400">
                            +{opportunity.skills.length - 5}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col gap-2 shrink-0">
                    <Button
                      size="sm"
                      onClick={() => setSelectedOpportunity(toOpportunityFormat(opportunity))}
                      leftIcon={<Plus className="h-4 w-4" />}
                      disabled={opportunity.status !== 'published'}
                      className="whitespace-nowrap"
                    >
                      Proposer
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDetailOpportunity(opportunity)}
                      leftIcon={<Eye className="h-4 w-4" />}
                      className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                      Détails
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.total > data.page_size && (
        <div className="flex justify-center items-center gap-2 pt-4">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Précédent
          </Button>
          <span className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
            Page {page} sur {Math.ceil(data.total / data.page_size)}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= Math.ceil(data.total / data.page_size)}
            onClick={() => setPage((p) => p + 1)}
          >
            Suivant
          </Button>
        </div>
      )}

      {/* Detail Modal */}
      <Modal
        isOpen={!!detailOpportunity}
        onClose={() => setDetailOpportunity(null)}
        title={detailOpportunity?.title || ''}
        size="2xl"
      >
        {detailOpportunity && (
          <div className="space-y-6">
            {/* Status badge */}
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1.5 text-sm font-semibold rounded-full ${
                detailOpportunity.status === 'published'
                  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400'
                  : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
              }`}>
                {detailOpportunity.status === 'published' ? 'Active' : detailOpportunity.status_display}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Publiée le {formatDate(detailOpportunity.created_at)}
              </span>
            </div>

            {/* Description */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Description de la mission
              </h4>
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
                <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
                  {detailOpportunity.description}
                </p>
              </div>
            </div>

            {/* Skills */}
            {detailOpportunity.skills.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                  Compétences recherchées
                </h4>
                <div className="flex flex-wrap gap-2">
                  {detailOpportunity.skills.map((skill) => (
                    <span
                      key={skill}
                      className="px-3 py-1.5 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-lg text-sm font-medium"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* End date */}
            {detailOpportunity.end_date && (
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 bg-amber-50 dark:bg-amber-900/20 rounded-lg px-4 py-3">
                <Calendar className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                <span>Date de fin prévue : <strong>{formatDate(detailOpportunity.end_date)}</strong></span>
              </div>
            )}

            {/* Action */}
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button
                variant="outline"
                onClick={() => setDetailOpportunity(null)}
              >
                Fermer
              </Button>
              <Button
                onClick={() => {
                  setSelectedOpportunity(toOpportunityFormat(detailOpportunity));
                  setDetailOpportunity(null);
                }}
                leftIcon={<Plus className="h-4 w-4" />}
                disabled={detailOpportunity.status !== 'published'}
              >
                Proposer un candidat
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Cooptation Form Modal */}
      <Modal
        isOpen={!!selectedOpportunity}
        onClose={() => setSelectedOpportunity(null)}
        title="Proposer un candidat"
        size="lg"
      >
        {selectedOpportunity && (
          <CreateCooptationForm
            opportunity={selectedOpportunity}
            onSuccess={() => setSelectedOpportunity(null)}
            onCancel={() => setSelectedOpportunity(null)}
          />
        )}
      </Modal>
    </div>
  );
}
