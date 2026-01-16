import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Calendar, Briefcase, Plus, Clock, CheckCircle } from 'lucide-react';

import { getPublishedOpportunity } from '../api/publishedOpportunities';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';
import { CreateCooptationForm } from '../components/cooptations/CreateCooptationForm';
import type { Opportunity } from '../types';

export function OpportunityDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [showCooptationForm, setShowCooptationForm] = useState(false);

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

  // Convert to Opportunity format for the cooptation form
  const toOpportunityFormat = (): Opportunity | null => {
    if (!opportunity) return null;
    return {
      id: opportunity.id,
      external_id: opportunity.boond_opportunity_id,
      title: opportunity.title,
      reference: `PUB-${opportunity.boond_opportunity_id}`,
      budget: null,
      start_date: null,
      end_date: opportunity.end_date,
      response_deadline: null,
      manager_name: null,
      manager_boond_id: null,
      client_name: null,
      description: opportunity.description,
      skills: opportunity.skills,
      location: null,
      is_open: opportunity.status === 'published',
      is_shared: true,
      owner_id: null,
      days_until_deadline: null,
      synced_at: opportunity.created_at,
      created_at: opportunity.created_at,
    };
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  if (error || !opportunity) {
    return (
      <div className="text-center py-16">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Opportunité non trouvée
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mb-6">
          Cette opportunité n'existe pas ou a été supprimée.
        </p>
        <Button onClick={() => navigate('/opportunities')}>
          Retour aux opportunités
        </Button>
      </div>
    );
  }

  const opportunityForForm = toOpportunityFormat();

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Back link */}
      <Link
        to="/opportunities"
        className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Retour aux opportunités
      </Link>

      {/* Header Card */}
      <Card className="!p-0 overflow-hidden">
        {/* Accent bar */}
        <div className="h-2 bg-gradient-to-r from-primary-500 to-primary-400" />

        <div className="p-6 md:p-8">
          {/* Title and status */}
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-6">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span className={`px-3 py-1.5 text-sm font-semibold rounded-full ${
                  opportunity.status === 'published'
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400'
                    : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                }`}>
                  {opportunity.status === 'published' ? 'Active' : opportunity.status_display}
                </span>
              </div>
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-gray-100">
                {opportunity.title}
              </h1>
            </div>

            <Button
              size="lg"
              onClick={() => setShowCooptationForm(true)}
              leftIcon={<Plus className="h-5 w-5" />}
              disabled={opportunity.status !== 'published'}
              className="shrink-0"
            >
              Proposer un candidat
            </Button>
          </div>

          {/* Meta info */}
          <div className="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-gray-400">
            <div className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 px-3 py-2 rounded-lg">
              <Briefcase className="h-4 w-4 text-gray-500" />
              <span>Publiée le <strong>{formatDate(opportunity.created_at)}</strong></span>
            </div>
            {opportunity.end_date && (
              <div className="flex items-center gap-2 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 rounded-lg">
                <Calendar className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                <span>Fin prévue : <strong>{formatDate(opportunity.end_date)}</strong></span>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Description Card */}
      <Card>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
          <Clock className="h-5 w-5 text-primary-500" />
          Description de la mission
        </h2>
        <div className="prose prose-gray dark:prose-invert max-w-none">
          <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed text-base">
            {opportunity.description}
          </p>
        </div>
      </Card>

      {/* Skills Card */}
      {opportunity.skills.length > 0 && (
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-primary-500" />
            Compétences recherchées
          </h2>
          <div className="flex flex-wrap gap-2">
            {opportunity.skills.map((skill) => (
              <span
                key={skill}
                className="px-4 py-2 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-lg text-sm font-medium"
              >
                {skill}
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Bottom CTA */}
      <Card className="bg-gradient-to-r from-primary-50 to-primary-100 dark:from-primary-900/20 dark:to-primary-800/20 border-primary-200 dark:border-primary-800">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Vous connaissez le candidat idéal ?
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Proposez un candidat et gagnez une prime de cooptation !
            </p>
          </div>
          <Button
            size="lg"
            onClick={() => setShowCooptationForm(true)}
            leftIcon={<Plus className="h-5 w-5" />}
            disabled={opportunity.status !== 'published'}
          >
            Proposer un candidat
          </Button>
        </div>
      </Card>

      {/* Cooptation Form Modal */}
      <Modal
        isOpen={showCooptationForm}
        onClose={() => setShowCooptationForm(false)}
        title="Proposer un candidat"
        size="lg"
      >
        {opportunityForForm && (
          <CreateCooptationForm
            opportunity={opportunityForForm}
            onSuccess={() => setShowCooptationForm(false)}
            onCancel={() => setShowCooptationForm(false)}
          />
        )}
      </Modal>
    </div>
  );
}
