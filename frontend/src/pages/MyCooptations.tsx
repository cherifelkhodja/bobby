import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { cooptationsApi } from '../api/cooptations';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { PageSpinner } from '../components/ui/Spinner';
import type { CooptationStatus } from '../types';

export function MyCooptations() {
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ['my-cooptations', page],
    queryFn: () => cooptationsApi.listMine({ page, page_size: 20 }),
  });

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Mes cooptations</h1>

      {data?.items.length === 0 ? (
        <Card className="text-center py-12">
          <p className="text-gray-500">Vous n'avez pas encore de cooptation.</p>
          <p className="text-sm text-gray-400 mt-2">
            Rendez-vous sur la page Opportunités pour proposer des candidats.
          </p>
        </Card>
      ) : (
        <>
          <div className="space-y-4">
            {data?.items.map((cooptation) => (
              <Card key={cooptation.id}>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="font-semibold text-gray-900">
                        {cooptation.candidate_name}
                      </h3>
                      <Badge status={cooptation.status as CooptationStatus} />
                    </div>
                    <p className="text-sm text-gray-600 mb-1">
                      {cooptation.opportunity_title}
                    </p>
                    <p className="text-sm text-gray-500">
                      {cooptation.candidate_email}
                      {cooptation.candidate_phone &&
                        ` • ${cooptation.candidate_phone}`}
                    </p>
                    {cooptation.rejection_reason && (
                      <p className="text-sm text-error mt-2">
                        Motif : {cooptation.rejection_reason}
                      </p>
                    )}
                  </div>
                  <div className="text-right text-sm text-gray-500">
                    <p>Soumis le {formatDate(cooptation.submitted_at)}</p>
                    {cooptation.candidate_daily_rate && (
                      <p className="font-medium text-gray-700">
                        {cooptation.candidate_daily_rate}€/jour
                      </p>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>

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
        </>
      )}
    </div>
  );
}
