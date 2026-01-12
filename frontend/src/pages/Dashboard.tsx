import { useQuery } from '@tanstack/react-query';
import { TrendingUp, Users, CheckCircle, XCircle } from 'lucide-react';

import { cooptationsApi } from '../api/cooptations';
import { Card, CardHeader } from '../components/ui/Card';
import { PageSpinner } from '../components/ui/Spinner';

export function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['my-stats'],
    queryFn: cooptationsApi.getMyStats,
  });

  if (isLoading) {
    return <PageSpinner />;
  }

  const statCards = [
    {
      title: 'Total cooptations',
      value: stats?.total || 0,
      icon: Users,
      color: 'text-primary-600',
      bgColor: 'bg-primary-50',
    },
    {
      title: 'En attente',
      value: stats?.pending || 0,
      icon: TrendingUp,
      color: 'text-warning',
      bgColor: 'bg-warning-light',
    },
    {
      title: 'Acceptées',
      value: stats?.accepted || 0,
      icon: CheckCircle,
      color: 'text-success',
      bgColor: 'bg-success-light',
    },
    {
      title: 'Refusées',
      value: stats?.rejected || 0,
      icon: XCircle,
      color: 'text-error',
      bgColor: 'bg-error-light',
    },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Tableau de bord</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((stat) => (
          <Card key={stat.title}>
            <div className="flex items-center">
              <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`h-6 w-6 ${stat.color}`} />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500">{stat.title}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader
          title="Taux de conversion"
          subtitle="Pourcentage de cooptations acceptées"
        />
        <div className="flex items-center">
          <div className="text-4xl font-bold text-primary-600">
            {stats?.conversion_rate.toFixed(1)}%
          </div>
          <div className="ml-4 text-sm text-gray-500">
            {stats?.accepted} acceptées sur {stats?.total} soumises
          </div>
        </div>
      </Card>
    </div>
  );
}
