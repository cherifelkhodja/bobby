import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, Calendar, Briefcase, Sparkles } from 'lucide-react';

import { listPublishedOpportunities } from '../api/publishedOpportunities';
import { Button } from '../components/ui/Button';
import { InlineSearchInput } from '../components/ui/SearchInput';
import { EmptyState } from '../components/ui/EmptyState';
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

  const total = data?.total || 0;

  return (
    <div>
      <p className="bc">Cooptation / Opportunités</p>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-[18px]">
        <div>
          <h1 className="h1">Opportunités</h1>
          <p className="sub">
            {total} opportunité{total > 1 ? 's' : ''} ouverte{total > 1 ? 's' : ''} à la cooptation
          </p>
        </div>
        <InlineSearchInput
          value={search}
          onChange={(value) => {
            setSearch(value);
            setPage(1);
          }}
          placeholder="Rechercher par titre, compétence…"
          className="w-full sm:w-72"
        />
      </div>

      {data?.items.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={Sparkles}
            title="Aucune opportunité disponible"
            description={
              search
                ? "Aucun résultat pour votre recherche. Essayez avec d'autres termes."
                : 'Les opportunités seront publiées par les commerciaux. Revenez bientôt !'
            }
          />
        </div>
      ) : (
        <div>
          {data?.items.map((opportunity) => (
            <div key={opportunity.id} className="ocard">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 flex-wrap">
                    <h3 className="oti">{opportunity.title}</h3>
                    <span className={`st ${opportunity.status === 'published' ? 'st-grn' : 'st-sla'}`}>
                      <span className="dot" />
                      {opportunity.status === 'published' ? 'Active' : opportunity.status_display}
                    </span>
                  </div>

                  <p className="odesc line-clamp-2">{opportunity.description}</p>

                  <div className="om">
                    <span className="omi">
                      <Briefcase className="h-3.5 w-3.5" />
                      Publiée le {formatDate(opportunity.created_at)}
                    </span>
                    {opportunity.end_date && (
                      <span className="omi">
                        <Calendar className="h-3.5 w-3.5" />
                        Fin prévue : {formatDate(opportunity.end_date)}
                      </span>
                    )}
                  </div>

                  {opportunity.skills.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {opportunity.skills.slice(0, 5).map((skill) => (
                        <span key={skill} className="sk">
                          {skill}
                        </span>
                      ))}
                      {opportunity.skills.length > 5 && (
                        <span className="sk !bg-transparent !text-mut2">
                          +{opportunity.skills.length - 5}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex flex-col gap-2 shrink-0">
                  <Button
                    size="sm"
                    onClick={() => navigate(`/opportunities/${opportunity.id}/proposer`)}
                    leftIcon={<Plus className="h-3.5 w-3.5" />}
                    disabled={opportunity.status !== 'published'}
                  >
                    Proposer un candidat
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => navigate(`/opportunities/${opportunity.id}`)}
                  >
                    Voir le détail
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.total > data.page_size && (
        <div className="flex justify-center items-center gap-2 pt-4">
          <Button
            variant="secondary"
            size="sm"
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Précédent
          </Button>
          <span className="px-4 text-[12.5px] text-mut">
            Page {page} sur {Math.ceil(data.total / data.page_size)}
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
    </div>
  );
}
