/**
 * ApiSettingsTab - Manage and test external API connections.
 */

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  CheckCircle,
  XCircle,
  Loader2,
  RefreshCw,
  Key,
  Cloud,
  Sparkles,
  Users,
  Mail,
} from 'lucide-react';
import { apiClient } from '../../api/client';

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

const SERVICE_CONFIG: Record<
  string,
  { name: string; description: string; icon: typeof Key }
> = {
  turnoverit: {
    name: 'Turnover-IT',
    description: 'Publication des annonces de recrutement',
    icon: Users,
  },
  s3: {
    name: 'S3 Storage',
    description: 'Stockage des CV candidats (Scaleway)',
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

export function ApiSettingsTab() {
  const [testingService, setTestingService] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});

  // Fetch services status
  const { data: statusData, isLoading, refetch } = useQuery({
    queryKey: ['settings-status'],
    queryFn: async () => {
      const response = await apiClient.get<{ services: ServiceStatus[] }>('/settings/status');
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
    },
    onError: (error, service) => {
      setTestResults((prev) => ({
        ...prev,
        [service]: {
          success: false,
          message: error instanceof Error ? error.message : 'Erreur inconnue',
        },
      }));
      setTestingService(null);
    },
  });

  const handleTest = (service: string) => {
    testMutation.mutate(service);
  };

  const handleTestAll = () => {
    statusData?.services.forEach((s) => {
      if (s.configured) {
        testMutation.mutate(s.service);
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
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Configuration des API
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Statut et test des connexions aux services externes
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors inline-flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Rafraîchir
          </button>
          <button
            onClick={handleTestAll}
            disabled={testingService !== null}
            className="px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 rounded-lg transition-colors inline-flex items-center gap-2"
          >
            Tester tout
          </button>
        </div>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {statusData?.services.map((service) => {
          const config = SERVICE_CONFIG[service.service];
          const Icon = config?.icon || Key;
          const testResult = testResults[service.service];
          const isTesting = testingService === service.service;

          return (
            <div
              key={service.service}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div
                    className={`p-2 rounded-lg ${
                      service.configured
                        ? 'bg-green-100 dark:bg-green-900/30'
                        : 'bg-gray-100 dark:bg-gray-700'
                    }`}
                  >
                    <Icon
                      className={`h-5 w-5 ${
                        service.configured
                          ? 'text-green-600 dark:text-green-400'
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
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {service.configured ? (
                    <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 rounded-full">
                      <CheckCircle className="h-3 w-3" />
                      Configuré
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 rounded-full">
                      <XCircle className="h-3 w-3" />
                      Non configuré
                    </span>
                  )}
                </div>
              </div>

              {/* API Key (masked) */}
              {service.masked_key && (
                <div className="mt-3 flex items-center gap-2">
                  <Key className="h-4 w-4 text-gray-400" />
                  <code className="text-sm text-gray-600 dark:text-gray-400 font-mono">
                    {service.masked_key}
                  </code>
                </div>
              )}

              {/* Test Result */}
              {testResult && (
                <div
                  className={`mt-3 p-2 rounded-lg text-sm ${
                    testResult.success
                      ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300'
                      : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {testResult.success ? (
                      <CheckCircle className="h-4 w-4" />
                    ) : (
                      <XCircle className="h-4 w-4" />
                    )}
                    {testResult.message}
                  </div>
                </div>
              )}

              {/* Test Button */}
              <div className="mt-3">
                <button
                  onClick={() => handleTest(service.service)}
                  disabled={!service.configured || isTesting}
                  className="w-full px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors inline-flex items-center justify-center gap-2"
                >
                  {isTesting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Test en cours...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="h-4 w-4" />
                      Tester la connexion
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Info */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <p className="text-sm text-blue-800 dark:text-blue-300">
          <strong>Note :</strong> Les clés API sont configurées via les variables d'environnement du
          serveur. Contactez l'administrateur système pour modifier les valeurs.
        </p>
      </div>
    </div>
  );
}
