/**
 * BoondManager connection and sync tab component.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, CheckCircle, XCircle, AlertCircle, Zap } from 'lucide-react';
import { toast } from 'sonner';

import { adminApi } from '../../api/admin';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { PageSpinner } from '../../components/ui/Spinner';

export function BoondTab() {
  const queryClient = useQueryClient();
  const [isSyncing, setIsSyncing] = useState(false);
  const [isTesting, setIsTesting] = useState(false);

  const { data: boondStatus, isLoading } = useQuery({
    queryKey: ['boond-status'],
    queryFn: adminApi.getBoondStatus,
    refetchInterval: 30000,
  });

  const testMutation = useMutation({
    mutationFn: adminApi.testConnection,
    onMutate: () => setIsTesting(true),
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message);
      } else {
        toast.error(data.message);
      }
      queryClient.invalidateQueries({ queryKey: ['boond-status'] });
    },
    onError: () => toast.error('Erreur lors du test de connexion'),
    onSettled: () => setIsTesting(false),
  });

  const syncMutation = useMutation({
    mutationFn: adminApi.triggerSync,
    onMutate: () => setIsSyncing(true),
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message);
      } else {
        toast.error(data.message);
      }
      queryClient.invalidateQueries({ queryKey: ['boond-status'] });
      queryClient.invalidateQueries({ queryKey: ['opportunities'] });
    },
    onError: () => toast.error('Erreur lors de la synchronisation'),
    onSettled: () => setIsSyncing(false),
  });

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Jamais';
    return new Date(dateStr).toLocaleString('fr-FR');
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Synchronisation BoondManager"
          subtitle="Statut de la connexion et synchronisation des opportunites"
        />

        <div className="space-y-4">
          {/* Connection Status */}
          <div className="flex items-center justify-between p-4 bg-srf2 border border-lin2 rounded-[10px]">
            <div className="flex items-center space-x-3">
              {boondStatus?.configured ? (
                boondStatus.connected ? (
                  <CheckCircle className="h-6 w-6 text-grn-fg" />
                ) : (
                  <XCircle className="h-6 w-6 text-red-fg" />
                )
              ) : (
                <AlertCircle className="h-6 w-6 text-amb-fg" />
              )}
              <div>
                <p className="text-[13.5px] font-semibold text-ink">
                  {boondStatus?.configured
                    ? boondStatus.connected
                      ? 'Connecte'
                      : 'Deconnecte'
                    : 'Non configure'}
                </p>
                <p className="text-[12.5px] text-mut">{boondStatus?.api_url}</p>
              </div>
            </div>
            <span
              className={`st ${
                boondStatus?.configured
                  ? boondStatus.connected
                    ? 'st-grn'
                    : 'st-red'
                  : 'st-amb'
              }`}
            >
              <span className="dot" />
              {boondStatus?.configured
                ? boondStatus.connected
                  ? 'En ligne'
                  : 'Hors ligne'
                : 'Configuration requise'}
            </span>
          </div>

          {/* Error Message */}
          {boondStatus?.error && (
            <div className="p-4 bg-red-bg rounded-[10px]">
              <p className="text-red-fg text-[13px]">{boondStatus.error}</p>
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-2 gap-4">
            <div className="kpi">
              <p className="kl">Opportunites synchronisees</p>
              <p className="kv">{boondStatus?.opportunities_count || 0}</p>
            </div>
            <div className="kpi">
              <p className="kl">Derniere synchronisation</p>
              <p className="text-[15px] font-semibold text-ink mt-1.5">
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
            <p className="mt-2 text-[12.5px] text-mut">
              Configurez les identifiants BoondManager dans les variables d'environnement
              (BOOND_USERNAME, BOOND_PASSWORD)
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}
