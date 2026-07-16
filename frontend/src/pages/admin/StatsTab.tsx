/**
 * CV transformation statistics tab component (admin only).
 */

import { useQuery } from '@tanstack/react-query';
import { BarChart3 } from 'lucide-react';

import { cvTransformerApi } from '../../api/cvTransformer';
import { PageSpinner } from '../../components/ui/Spinner';

const GRID_COLS = 'grid-cols-[1fr_160px]';

export function StatsTab() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['cv-transformation-stats'],
    queryFn: cvTransformerApi.getStats,
  });

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div>
      <div className="kpi max-w-[340px] mb-4">
        <p className="kl">Total des transformations CV</p>
        <p className="kv">{stats?.total || 0}</p>
        <p className="ks">tous utilisateurs confondus</p>
      </div>

      {stats?.by_user && stats.by_user.length > 0 ? (
        <div className="tbl">
          <div className={`thead ${GRID_COLS}`}>
            <span>Utilisateur</span>
            <span className="text-right">CVs transformés</span>
          </div>
          {stats.by_user.map((userStat) => (
            <div key={userStat.user_id} className={`row ${GRID_COLS}`}>
              <div className="min-w-0">
                <p className="nm truncate">{userStat.user_name}</p>
                <p className="ns truncate">{userStat.user_email}</p>
              </div>
              <span className="cell font-semibold text-right">{userStat.count}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <BarChart3 className="mx-auto h-10 w-10 text-mut2" />
          <p className="dn mt-3">Aucune transformation pour le moment</p>
        </div>
      )}
    </div>
  );
}
