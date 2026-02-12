import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search, Plus, Calendar, Briefcase, ArrowRight, Sparkles } from 'lucide-react';

import { listPublishedOpportunities } from '../api/publishedOpportunities';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { PageSpinner } from '../components/ui/Spinner';

export function Opportunities() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

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
        <div className="grid gap-4">
          {data?.items.map((opportunity) => (
            <Card
              key={opportunity.id}
              className="group hover:shadow-lg hover:border-primary-200 dark:hover:border-primary-800 transition-all duration-200 !p-0 overflow-hidden cursor-pointer"
              onClick={() => navigate(`/opportunities/${opportunity.id}`)}
            >
              {/* Accent bar */}
              <div className="h-1 bg-gradient-to-r from-primary-500 to-primary-400" />

              <div className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    {/* Title & Status */}
                    <div className="flex items-start gap-3 mb-3">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                        {opportunity.title}
                      </h3>
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
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/opportunities/${opportunity.id}/proposer`);
                      }}
                      leftIcon={<Plus className="h-4 w-4" />}
                      disabled={opportunity.status !== 'published'}
                      className="whitespace-nowrap"
                    >
                      Proposer
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/opportunities/${opportunity.id}`);
                      }}
                      rightIcon={<ArrowRight className="h-4 w-4" />}
                      className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                      Voir plus
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
    </div>
  );
}
