import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Plus, Calendar, MapPin, Euro } from 'lucide-react';

import { opportunitiesApi } from '../api/opportunities';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { PageSpinner } from '../components/ui/Spinner';
import { Modal } from '../components/ui/Modal';
import { CreateCooptationForm } from '../components/cooptations/CreateCooptationForm';
import type { Opportunity } from '../types';

export function Opportunities() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(
    null
  );

  const { data, isLoading } = useQuery({
    queryKey: ['opportunities', page, search],
    queryFn: () => opportunitiesApi.list({ page, page_size: 20, search }),
  });

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('fr-FR');
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Opportunités</h1>
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
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Aucune opportunité disponible
          </h3>
          <p className="text-gray-500">
            {search
              ? 'Aucun résultat pour votre recherche. Essayez avec d\'autres termes.'
              : 'Les opportunités seront synchronisées depuis BoondManager.'}
          </p>
        </Card>
      ) : (
        <div className="grid gap-4">
          {data?.items.map((opportunity) => (
          <Card key={opportunity.id} className="hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {opportunity.title}
                  </h3>
                  <span className="text-sm text-gray-500">
                    {opportunity.reference}
                  </span>
                </div>

                <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                  {opportunity.client_name && (
                    <span>{opportunity.client_name}</span>
                  )}
                  {opportunity.budget && (
                    <span className="flex items-center">
                      <Euro className="h-4 w-4 mr-1" />
                      {opportunity.budget}€/jour
                    </span>
                  )}
                  {opportunity.start_date && (
                    <span className="flex items-center">
                      <Calendar className="h-4 w-4 mr-1" />
                      {formatDate(opportunity.start_date)}
                    </span>
                  )}
                  {opportunity.location && (
                    <span className="flex items-center">
                      <MapPin className="h-4 w-4 mr-1" />
                      {opportunity.location}
                    </span>
                  )}
                </div>

                {opportunity.skills.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {opportunity.skills.slice(0, 5).map((skill) => (
                      <span
                        key={skill}
                        className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-600"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <Button
                size="sm"
                onClick={() => setSelectedOpportunity(opportunity)}
                leftIcon={<Plus className="h-4 w-4" />}
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
          <span className="px-4 py-2 text-sm text-gray-600">
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
