import { useQuery } from '@tanstack/react-query';

import { cooptationsApi } from '../api/cooptations';
import { PageSpinner } from '../components/ui/Spinner';

export function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['my-stats'],
    queryFn: cooptationsApi.getMyStats,
  });

  if (isLoading) {
    return <PageSpinner />;
  }

  const conversionRate = stats?.conversion_rate ?? 0;
  const inProgress = (stats?.in_review ?? 0) + (stats?.interview ?? 0);

  return (
    <div>
      <p className="bc">Pilotage</p>
      <h1 className="h1">Tableau de bord</h1>
      <p className="sub">Vos cooptations et leur avancement</p>

      <div className="kpis">
        <div className="kpi">
          <p className="kl">Total cooptations</p>
          <p className="kv">{stats?.total ?? 0}</p>
          <p className="ks">candidats proposés</p>
        </div>
        <div className="kpi">
          <p className="kl">En attente</p>
          <p className="kv text-amb-fg">{stats?.pending ?? 0}</p>
          <p className="ks">
            {inProgress > 0 ? `${inProgress} en cours d'examen ou entretien` : 'aucune en cours d’examen'}
          </p>
        </div>
        <div className="kpi">
          <p className="kl">Acceptées</p>
          <p className="kv text-grn-fg">{stats?.accepted ?? 0}</p>
          <p className="ks">primes de cooptation</p>
        </div>
        <div className="kpi">
          <p className="kl">Refusées</p>
          <p className="kv red">{stats?.rejected ?? 0}</p>
          <p className="ks">motifs consultables</p>
        </div>
      </div>

      <div className="card max-w-[520px]">
        <h3 className="ct">Taux de conversion</h3>
        <p className="cs mt-1">Pourcentage de cooptations acceptées</p>
        <div className="flex items-center gap-4 mt-3.5">
          <span className="text-[34px] font-bold tracking-[-0.02em] text-prit">
            {conversionRate.toFixed(1).replace('.', ',')} %
          </span>
          <span className="cs">
            {stats?.accepted ?? 0} acceptées sur {stats?.total ?? 0} soumises
          </span>
        </div>
        <div className="dbar !w-full mt-3.5">
          <div
            className="dfill !bg-pri"
            style={{ width: `${Math.min(100, Math.max(0, conversionRate))}%` }}
          />
        </div>
      </div>
    </div>
  );
}
