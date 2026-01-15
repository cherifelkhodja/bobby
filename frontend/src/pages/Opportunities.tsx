import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Plus, Calendar, Briefcase } from 'lucide-react';

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
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(
    null
  );

  const { data, isLoading } = useQuery({
    queryKey: ['published-opportunities', page, search],
    queryFn: () => listPublishedOpportunities({ page, page_size: 20, search }),
  });

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString('fr-FR');
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
    client_name: null, // Anonymized - no client name
    description: pub.description,
    skills: pub.skills,
    location: null,
    is_open: pub.status === 'published',
    is_shared: true, // Published opportunities are shared
    owner_id: null,
    days_until_deadline: null,
    synced_at: pub.created_at,
    created_at: pub.created_at,
  });

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Opportunités</h1>
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

      {data?.items.length === 0 ? (
        <Card className="text-center py-12">
          <div className="text-gray-400 mb-4">
            <Search className="h-12 w-12 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
            Aucune opportunité disponible
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            {search
              ? 'Aucun résultat pour votre recherche. Essayez avec d\'autres termes.'
              : 'Les opportunités seront publiées par les commerciaux.'}
          </p>
        </Card>
      ) : (
        <div className="grid gap-4">
          {data?.items.map((opportunity) => (
          <Card key={opportunity.id} className="hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {opportunity.title}
                  </h3>
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                    opportunity.status === 'published'
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                  }`}>
                    {opportunity.status_display}
                  </span>
                </div>

                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
                  {opportunity.description}
                </p>

                <div className="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-gray-400">
                  {opportunity.end_date && (
                    <span className="flex items-center">
                      <Calendar className="h-4 w-4 mr-1" />
                      Fin: {formatDate(opportunity.end_date)}
                    </span>
                  )}
                  <span className="flex items-center">
                    <Briefcase className="h-4 w-4 mr-1" />
                    Publiée le {formatDate(opportunity.created_at)}
                  </span>
                </div>

                {opportunity.skills.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {opportunity.skills.slice(0, 6).map((skill) => (
                      <span
                        key={skill}
                        className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-600 dark:text-gray-300"
                      >
                        {skill}
                      </span>
                    ))}
                    {opportunity.skills.length > 6 && (
                      <span className="px-2 py-1 text-xs text-gray-500 dark:text-gray-400">
                        +{opportunity.skills.length - 6} autres
                      </span>
                    )}
                  </div>
                )}
              </div>

              <Button
                size="sm"
                onClick={() => setSelectedOpportunity(toOpportunityFormat(opportunity))}
                leftIcon={<Plus className="h-4 w-4" />}
                disabled={opportunity.status !== 'published'}
              >
                Proposer
              </Button>
            </div>
            </Card>
          ))}
        </div>
      )}

      {data && data.total > data.page_size && (
        <div className="flex justify-center mt-8 space-x-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Précédent
          </Button>
          <span className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
            Page {page} / {Math.ceil(data.total / data.page_size)}
          </span>
          <Button
            variant="secondary"
            size="sm"
            disabled={page >= Math.ceil(data.total / data.page_size)}
            onClick={() => setPage((p) => p + 1)}
          >
            Suivant
          </Button>
        </div>
      )}

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
