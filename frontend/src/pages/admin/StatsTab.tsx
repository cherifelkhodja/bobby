/**
 * CV transformation statistics tab component (admin only).
 */

import { useQuery } from '@tanstack/react-query';
import { BarChart3 } from 'lucide-react';

import { cvTransformerApi } from '../../api/cvTransformer';
import { Card, CardHeader } from '../../components/ui/Card';
import { PageSpinner } from '../../components/ui/Spinner';

export function StatsTab() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['cv-transformation-stats'],
    queryFn: cvTransformerApi.getStats,
  });

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Statistiques CV Generator"
          subtitle="Nombre de CVs transformés par utilisateur"
        />

        <div className="mb-6 p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
          <div className="flex items-center">
            <BarChart3 className="h-8 w-8 text-primary-600 dark:text-primary-400 mr-4" />
            <div>
              <p className="text-sm text-primary-600 dark:text-primary-400">Total des transformations</p>
              <p className="text-3xl font-bold text-primary-700 dark:text-primary-300">{stats?.total || 0}</p>
            </div>
          </div>
        </div>

        {stats?.by_user && stats.by_user.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Utilisateur
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    CVs transformés
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {stats.by_user.map((userStat) => (
                  <tr key={userStat.user_id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {userStat.user_name}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {userStat.user_email}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                        {userStat.count}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8">
            <BarChart3 className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              Aucune transformation pour le moment
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
