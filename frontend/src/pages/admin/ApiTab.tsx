/**
 * API connections test tab component.
 *
 * Tests for all external API connections: BoondManager, Gemini, Turnover-IT, S3, Resend.
 */

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  RefreshCw,
  CheckCircle,
  XCircle,
  Loader2,
  Key,
  Cloud,
  Sparkles,
  Users,
  Mail,
  Briefcase,
} from 'lucide-react';
import { toast } from 'sonner';

import { apiClient } from '../../api/client';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';

interface ServiceStatus {
  service: string;
  configured: boolean;
  masked_key: string | null;
}

interface TestResult {
  success: boolean;
  message: string;
  details?: Record<string, unknown>;
}

interface ServicesStatusResponse {
  services: ServiceStatus[];
}

const SERVICE_CONFIG: Record<
  string,
  { name: string; description: string; icon: typeof Key }
> = {
  turnoverit: {
    name: 'Turnover-IT',
    description: 'Publication des annonces de recrutement',
    icon: Briefcase,
  },
  s3: {
    name: 'S3 Storage (Scaleway)',
    description: 'Stockage des CV candidats',
    icon: Cloud,
  },
  gemini: {
    name: 'Google Gemini',
    description: 'IA pour le matching CV et la transformation',
    icon: Sparkles,
  },
  boond: {
    name: 'BoondManager',
    description: 'Synchronisation des opportunités et ressources',
    icon: Users,
  },
  resend: {
    name: 'Resend',
    description: "Envoi d'emails (invitations, notifications)",
    icon: Mail,
  },
};

export function ApiTab() {
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [testingService, setTestingService] = useState<string | null>(null);

  // Fetch services status
  const {
    data: statusData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['settings-status'],
    queryFn: async () => {
      const response = await apiClient.get<ServicesStatusResponse>('/settings/status');
      return response.data;
    },
  });

  // Test mutation
  const testMutation = useMutation({
    mutationFn: async (service: string) => {
      setTestingService(service);
      const response = await apiClient.post<TestResult>('/settings/test', { service });
      return { service, result: response.data };
    },
    onSuccess: ({ service, result }) => {
      setTestResults((prev) => ({ ...prev, [service]: result }));
      setTestingService(null);
      if (result.success) {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
    },
    onError: (error: Error, service: string) => {
      const errorResult = {
        success: false,
        message: error.message || 'Erreur inconnue',
      };
      setTestResults((prev) => ({ ...prev, [service]: errorResult }));
      setTestingService(null);
      toast.error(errorResult.message);
    },
  });

  const handleTest = (service: string) => {
    testMutation.mutate(service);
  };

  const handleTestAll = () => {
    statusData?.services.forEach((s) => {
      if (s.configured) {
        setTimeout(() => testMutation.mutate(s.service), 0);
      }
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Statut et test des connexions aux services externes
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()} leftIcon={<RefreshCw className="h-4 w-4" />}>
            Rafraîchir
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleTestAll}
            disabled={testingService !== null}
          >
            Tester tout
          </Button>
        </div>
      </div>

      {/* Services Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {statusData?.services.map((service) => {
          const config = SERVICE_CONFIG[service.service];
          const Icon = config?.icon || Key;
          const testResult = testResults[service.service];
          const isTesting = testingService === service.service;

          return (
            <Card key={service.service}>
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div
                    className={`p-3 rounded-lg ${
                      service.configured
                        ? testResult?.success
                          ? 'bg-green-100 dark:bg-green-900/30'
                          : testResult && !testResult.success
                            ? 'bg-red-100 dark:bg-red-900/30'
                            : 'bg-blue-100 dark:bg-blue-900/30'
                        : 'bg-gray-100 dark:bg-gray-700'
                    }`}
                  >
                    <Icon
                      className={`h-6 w-6 ${
                        service.configured
                          ? testResult?.success
                            ? 'text-green-600 dark:text-green-400'
                            : testResult && !testResult.success
                              ? 'text-red-600 dark:text-red-400'
                              : 'text-blue-600 dark:text-blue-400'
                          : 'text-gray-400 dark:text-gray-500'
                      }`}
                    />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      {config?.name || service.service}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {config?.description || 'Service externe'}
                    </p>
                    {service.masked_key && (
                      <div className="mt-1 flex items-center gap-1">
                        <Key className="h-3 w-3 text-gray-400" />
                        <code className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                          {service.masked_key}
                        </code>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Badge variant={service.configured ? 'success' : 'warning'}>
                    {service.configured ? 'Configuré' : 'Non configuré'}
                  </Badge>
                </div>
              </div>

              {/* Test Result */}
              {testResult && (
                <div
                  className={`mt-4 p-3 rounded-lg text-sm flex items-center gap-2 ${
                    testResult.success
                      ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300'
                      : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-300'
                  }`}
                >
                  {testResult.success ? (
                    <CheckCircle className="h-4 w-4 flex-shrink-0" />
                  ) : (
                    <XCircle className="h-4 w-4 flex-shrink-0" />
                  )}
                  <span>{testResult.message}</span>
                </div>
              )}

              {/* Test Button */}
              <div className="mt-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleTest(service.service)}
                  disabled={!service.configured || isTesting}
                  isLoading={isTesting}
                  leftIcon={isTesting ? undefined : <RefreshCw className="h-4 w-4" />}
                  className="w-full"
                >
                  {isTesting ? 'Test en cours...' : 'Tester la connexion'}
                </Button>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Info */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <p className="text-sm text-blue-800 dark:text-blue-300">
          <strong>Note :</strong> Les clés API sont configurées via les variables d'environnement du
          serveur (TURNOVERIT_API_KEY, S3_ACCESS_KEY, GEMINI_API_KEY, etc.).
        </p>
      </div>
    </div>
  );
}
