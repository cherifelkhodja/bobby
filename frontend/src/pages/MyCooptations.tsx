import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { cooptationsApi } from '../api/cooptations';
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

  const { data: stats } = useQuery({
    queryKey: ['my-stats'],
    queryFn: cooptationsApi.getMyStats,
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

  const total = stats?.total ?? data?.total ?? 0;
  const accepted = stats?.accepted ?? 0;

  return (
    <div>
      <p className="bc">Cooptation / Mes cooptations</p>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="h1">Mes cooptations</h1>
          <p className="sub">
            {total} candidat{total > 1 ? 's' : ''} proposé{total > 1 ? 's' : ''}
            {accepted > 0 && ` · ${accepted} accepté${accepted > 1 ? 's' : ''}`}
          </p>
        </div>
        {accepted > 0 && (
          <span className="st st-grn">
            <span className="dot" />
            {accepted} cooptation{accepted > 1 ? 's' : ''} acceptée{accepted > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {data?.items.length === 0 ? (
        <div className="card mt-[18px] text-center py-12">
          <p className="dn">Vous n'avez pas encore de cooptation.</p>
          <p className="ds mt-1.5">
            Rendez-vous sur la page Opportunités pour proposer des candidats.
          </p>
        </div>
      ) : (
        <>
          <div className="card mt-[18px] !p-0 pt-0.5">
            {data?.items.map((cooptation, index) => (
              <div key={cooptation.id} className={`crow ${index === 0 ? '!border-t-0' : ''}`}>
                <div className="min-w-0">
                  <div className="flex items-center gap-3 flex-wrap">
                    <p className="dn !text-[14.5px]">{cooptation.candidate_name}</p>
                    <Badge status={cooptation.status as CooptationStatus} />
                  </div>
                  <p className="ds mt-[5px]">{cooptation.opportunity_title}</p>
                  <p className="ds">
                    {cooptation.candidate_email}
                    {cooptation.candidate_phone && ` · ${cooptation.candidate_phone}`}
                  </p>
                  {cooptation.rejection_reason && (
                    <p className="ds !text-red-fg mt-[5px]">
                      Motif : {cooptation.rejection_reason}
                    </p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <p className="ds">Soumis le {formatDate(cooptation.submitted_at)}</p>
                  {cooptation.candidate_daily_rate && (
                    <p className="dn mt-1">{cooptation.candidate_daily_rate} € / jour</p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {data && data.total > data.page_size && (
            <div className="flex justify-center items-center mt-6 gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Précédent
              </Button>
              <span className="px-4 text-[12.5px] text-mut">
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
