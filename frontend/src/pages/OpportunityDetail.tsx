import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Calendar, Briefcase, Plus } from 'lucide-react';

import { getPublishedOpportunity } from '../api/publishedOpportunities';
import { Button } from '../components/ui/Button';
import { PageSpinner } from '../components/ui/Spinner';

export function OpportunityDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: opportunity, isLoading, error } = useQuery({
    queryKey: ['published-opportunity', id],
    queryFn: () => getPublishedOpportunity(id!),
    enabled: !!id,
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

  if (error || !opportunity) {
    return (
      <div className="text-center py-16">
        <h2 className="text-[15px] font-bold text-ink mb-2">Opportunité non trouvée</h2>
        <p className="notec mb-6">Cette opportunité n'existe pas ou a été supprimée.</p>
        <Button onClick={() => navigate('/opportunities')}>Retour aux opportunités</Button>
      </div>
    );
  }

  const isActive = opportunity.status === 'published';

  return (
    <div className="max-w-[900px]">
      <Link to="/opportunities" className="bc block cursor-pointer !text-mut2 hover:!text-mut">
        ← Retour aux opportunités
      </Link>

      {/* Header card */}
      <div className="hdcard !mt-2">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <span className={`st ${isActive ? 'st-grn' : 'st-sla'}`}>
              <span className="dot" />
              {isActive ? 'Active' : opportunity.status_display}
            </span>
            <h1 className="h1 !text-[26px] mt-2.5">{opportunity.title}</h1>
            <div className="om !mt-3.5 !mb-0">
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
          </div>
          <Button
            onClick={() => navigate(`/opportunities/${id}/proposer`)}
            leftIcon={<Plus className="h-3.5 w-3.5" />}
            disabled={!isActive}
            className="shrink-0"
          >
            Proposer un candidat
          </Button>
        </div>
      </div>

      {/* Description */}
      <div className="card mt-4">
        <h3 className="ct">Description de la mission</h3>
        <p className="odesc !max-w-none mt-2.5 whitespace-pre-wrap">{opportunity.description}</p>
      </div>

      {/* Skills */}
      {opportunity.skills.length > 0 && (
        <div className="card mt-4">
          <h3 className="ct mb-3">Compétences recherchées</h3>
          <div className="flex flex-wrap gap-2">
            {opportunity.skills.map((skill) => (
              <span key={skill} className="sk">
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Bottom CTA */}
      <div className="card mt-4 !bg-pris !border-[color-mix(in_oklab,var(--pri)_30%,transparent)]">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <h3 className="ct">Vous connaissez le candidat idéal ?</h3>
            <p className="cs mt-1">Proposez un candidat et gagnez une prime de cooptation !</p>
          </div>
          <Button
            onClick={() => navigate(`/opportunities/${id}/proposer`)}
            leftIcon={<Plus className="h-3.5 w-3.5" />}
            disabled={!isActive}
          >
            Proposer un candidat
          </Button>
        </div>
      </div>
    </div>
  );
}
