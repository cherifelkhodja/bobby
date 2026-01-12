import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, CheckCircle, XCircle, AlertCircle, Settings, Zap } from 'lucide-react';
import { toast } from 'sonner';

import { adminApi } from '../api/admin';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { PageSpinner } from '../components/ui/Spinner';

export function Admin() {
  const queryClient = useQueryClient();
  const [isSyncing, setIsSyncing] = useState(false);
  const [isTesting, setIsTesting] = useState(false);

  const { data: boondStatus, isLoading } = useQuery({
    queryKey: ['boond-status'],
    queryFn: adminApi.getBoondStatus,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const testMutation = useMutation({
    mutationFn: adminApi.testConnection,
    onMutate: () => {
      setIsTesting(true);
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message);
      } else {
        toast.error(data.message);
      }
      queryClient.invalidateQueries({ queryKey: ['boond-status'] });
    },
    onError: () => {
      toast.error('Erreur lors du test de connexion');
    },
    onSettled: () => {
      setIsTesting(false);
    },
  });

  const syncMutation = useMutation({
    mutationFn: adminApi.triggerSync,
    onMutate: () => {
      setIsSyncing(true);
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message);
      } else {
        toast.error(data.message);
      }
      queryClient.invalidateQueries({ queryKey: ['boond-status'] });
      queryClient.invalidateQueries({ queryKey: ['opportunities'] });
    },
    onError: () => {
      toast.error('Erreur lors de la synchronisation');
    },
    onSettled: () => {
      setIsSyncing(false);
    },
  });

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Jamais';
    return new Date(dateStr).toLocaleString('fr-FR');
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Administration</h1>
      </div>

      <div className="space-y-6">
        <Card>
          <CardHeader
            title="Synchronisation BoondManager"
            subtitle="Statut de la connexion et synchronisation des opportunites"
          />

          <div className="space-y-4">
            {/* Connection Status */}
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center space-x-3">
                {boondStatus?.configured ? (
                  boondStatus.connected ? (
                    <CheckCircle className="h-6 w-6 text-success" />
                  ) : (
                    <XCircle className="h-6 w-6 text-error" />
                  )
                ) : (
                  <AlertCircle className="h-6 w-6 text-warning" />
                )}
                <div>
                  <p className="font-medium text-gray-900">
                    {boondStatus?.configured
                      ? boondStatus.connected
                        ? 'Connecte'
                        : 'Deconnecte'
                      : 'Non configure'}
                  </p>
                  <p className="text-sm text-gray-500">{boondStatus?.api_url}</p>
                </div>
              </div>
              <div
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  boondStatus?.configured
                    ? boondStatus.connected
                      ? 'bg-success-light text-success'
                      : 'bg-error-light text-error'
                    : 'bg-warning-light text-warning'
                }`}
              >
                {boondStatus?.configured
                  ? boondStatus.connected
                    ? 'En ligne'
                    : 'Hors ligne'
                  : 'Configuration requise'}
              </div>
            </div>

            {/* Error Message */}
            {boondStatus?.error && (
              <div className="p-4 bg-error-light rounded-lg">
                <p className="text-error text-sm">{boondStatus.error}</p>
              </div>
            )}

            {/* Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Opportunites synchronisees</p>
                <p className="text-2xl font-bold text-gray-900">
                  {boondStatus?.opportunities_count || 0}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Derniere synchronisation</p>
                <p className="text-lg font-medium text-gray-900">
                  {formatDate(boondStatus?.last_sync || null)}
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="pt-4 flex space-x-3">
              <Button
                onClick={() => testMutation.mutate()}
                disabled={!boondStatus?.configured || isTesting}
                isLoading={isTesting}
                variant="outline"
                leftIcon={<Zap className="h-4 w-4" />}
              >
                {isTesting ? 'Test en cours...' : 'Tester la connexion'}
              </Button>
              <Button
                onClick={() => syncMutation.mutate()}
                disabled={!boondStatus?.configured || !boondStatus?.connected || isSyncing}
                isLoading={isSyncing}
                leftIcon={<RefreshCw className="h-4 w-4" />}
              >
                {isSyncing ? 'Synchronisation...' : 'Lancer la synchronisation'}
              </Button>
            </div>
            {!boondStatus?.configured && (
              <p className="mt-2 text-sm text-gray-500">
                Configurez les identifiants BoondManager dans les variables d'environnement
                (BOOND_USERNAME, BOOND_PASSWORD)
              </p>
            )}
          </div>
        </Card>

        {/* Configuration Help */}
        <Card>
          <CardHeader
            title="Configuration"
            subtitle="Variables d'environnement requises"
          />
          <div className="space-y-2">
            <div className="flex items-center space-x-2 p-3 bg-gray-50 rounded font-mono text-sm">
              <Settings className="h-4 w-4 text-gray-400" />
              <span>BOOND_USERNAME</span>
              <span className="text-gray-400">- Nom d'utilisateur BoondManager</span>
            </div>
            <div className="flex items-center space-x-2 p-3 bg-gray-50 rounded font-mono text-sm">
              <Settings className="h-4 w-4 text-gray-400" />
              <span>BOOND_PASSWORD</span>
              <span className="text-gray-400">- Mot de passe BoondManager</span>
            </div>
            <div className="flex items-center space-x-2 p-3 bg-gray-50 rounded font-mono text-sm">
              <Settings className="h-4 w-4 text-gray-400" />
              <span>BOOND_API_URL</span>
              <span className="text-gray-400">- URL de l'API (defaut: https://ui.boondmanager.com/api)</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
