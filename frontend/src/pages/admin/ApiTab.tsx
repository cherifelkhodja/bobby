/**
 * API connections test tab component.
 *
 * Tests for all external API connections: BoondManager, Gemini, Turnover-IT, S3, Resend.
 * Also manages Turnover-IT skills synchronization.
 */

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
  Shield,
  Search,
  Tag,
} from 'lucide-react';
import { toast } from 'sonner';

import { apiClient } from '../../api/client';
import { adminApi, type CvAiSettings, type CvAiTestResponse, type CvAiProviderInfo, type CvAiModelInfo } from '../../api/admin';
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
  secrets_source: 'environment' | 'aws';
  aws_secrets_enabled: boolean;
}

const SERVICE_CONFIG: Record<
  string,
  { name: string; icon: typeof Key }
> = {
  turnoverit: {
    name: 'Turnover-IT',
    icon: Briefcase,
  },
  s3: {
    name: 'S3 Storage (AWS)',
    icon: Cloud,
  },
  gemini: {
    name: 'Google Gemini',
    icon: Sparkles,
  },
  boond: {
    name: 'BoondManager',
    icon: Users,
  },
  resend: {
    name: 'Resend',
    icon: Mail,
  },
};

const GEMINI_MODELS = [
  { value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash Lite (Recommandé)' },
  { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
  { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
  { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
];

export function ApiTab() {
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [testingService, setTestingService] = useState<string | null>(null);
  const [geminiModel, setGeminiModel] = useState('gemini-2.5-flash-lite');
  const [showSkillsModal, setShowSkillsModal] = useState(false);
  const [skillsSearch, setSkillsSearch] = useState('');
  const [cvAiProvider, setCvAiProvider] = useState('gemini');
  const [cvAiModel, setCvAiModel] = useState('');
  const [cvAiTestResult, setCvAiTestResult] = useState<CvAiTestResponse | null>(null);
  const queryClient = useQueryClient();

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
      const payload: { service: string; model?: string } = { service };
      if (service === 'gemini') {
        payload.model = geminiModel;
      }
      const response = await apiClient.post<TestResult>('/settings/test', payload);
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

  // Turnover-IT Skills
  const {
    data: skillsData,
    isLoading: isLoadingSkills,
  } = useQuery({
    queryKey: ['turnoverit-skills', skillsSearch],
    queryFn: () => adminApi.getTurnoverITSkills(skillsSearch || undefined),
    enabled: showSkillsModal,
  });

  const syncSkillsMutation = useMutation({
    mutationFn: adminApi.syncTurnoverITSkills,
    onSuccess: (result) => {
      if (result.success) {
        toast.success(result.message);
        queryClient.invalidateQueries({ queryKey: ['turnoverit-skills'] });
      } else {
        toast.error(result.message);
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Erreur lors de la synchronisation');
    },
  });

  // CV AI Settings
  const {
    data: cvAiData,
  } = useQuery<CvAiSettings>({
    queryKey: ['cv-ai-settings'],
    queryFn: adminApi.getCvAiSettings,
  });

  // Initialize state from fetched data
  useEffect(() => {
    if (cvAiData) {
      setCvAiProvider(cvAiData.current_provider);
      setCvAiModel(cvAiData.current_model);
    }
  }, [cvAiData]);

  const currentModels = cvAiProvider === 'claude'
    ? (cvAiData?.available_models_claude || [])
    : (cvAiData?.available_models_gemini || []);

  const saveCvAiMutation = useMutation({
    mutationFn: () => adminApi.setCvAiProvider(cvAiProvider, cvAiModel),
    onSuccess: () => {
      toast.success(`Provider IA CV mis à jour: ${cvAiProvider} / ${cvAiModel}`);
      queryClient.invalidateQueries({ queryKey: ['cv-ai-settings'] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Erreur lors de la sauvegarde');
    },
  });

  const testCvAiMutation = useMutation({
    mutationFn: () => adminApi.testCvAi(cvAiProvider, cvAiModel),
    onSuccess: (result) => {
      setCvAiTestResult(result);
      if (result.success) {
        toast.success(`${result.provider} fonctionne (${result.response_time_ms}ms)`);
      } else {
        toast.error(result.message);
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Erreur lors du test');
    },
  });

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

              {/* Gemini Model Selector */}
              {service.service === 'gemini' && (
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Modèle
                  </label>
                  <select
                    value={geminiModel}
                    onChange={(e) => setGeminiModel(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {GEMINI_MODELS.map((model) => (
                      <option key={model.value} value={model.value}>
                        {model.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

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
              <div className="mt-4 flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleTest(service.service)}
                  disabled={!service.configured || isTesting}
                  isLoading={isTesting}
                  leftIcon={isTesting ? undefined : <RefreshCw className="h-4 w-4" />}
                  className="flex-1"
                >
                  {isTesting ? 'Test en cours...' : 'Tester'}
                </Button>
                {/* Skills button for Turnover-IT */}
                {service.service === 'turnoverit' && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setShowSkillsModal(true)}
                    leftIcon={<Tag className="h-4 w-4" />}
                  >
                    Skills
                  </Button>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      {/* CV AI Provider Settings */}
      <Card>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 rounded-lg bg-purple-100 dark:bg-purple-900/30">
            <Sparkles className="h-6 w-6 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-white">
              IA pour Transformation CV
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Choisir le provider et le modèle IA pour la transformation des CVs
            </p>
          </div>
          {cvAiData && (
            <Badge variant="primary" className="ml-auto">
              {cvAiData.current_provider === 'claude' ? 'Claude' : 'Gemini'} actif
            </Badge>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Provider Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Provider IA
            </label>
            <select
              value={cvAiProvider}
              onChange={(e) => {
                const newProvider = e.target.value;
                setCvAiProvider(newProvider);
                setCvAiTestResult(null);
                // Set default model for new provider
                if (newProvider === 'claude') {
                  setCvAiModel(cvAiData?.available_models_claude?.[0]?.id || 'claude-sonnet-4-5-20250929');
                } else {
                  setCvAiModel(cvAiData?.available_models_gemini?.[0]?.id || 'gemini-2.0-flash');
                }
              }}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            >
              {cvAiData?.available_providers?.map((p: CvAiProviderInfo) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              )) || (
                <>
                  <option value="gemini">Google Gemini</option>
                  <option value="claude">Anthropic Claude</option>
                </>
              )}
            </select>
          </div>

          {/* Model Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Modèle
            </label>
            <select
              value={cvAiModel}
              onChange={(e) => {
                setCvAiModel(e.target.value);
                setCvAiTestResult(null);
              }}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            >
              {currentModels.map((m: CvAiModelInfo) => (
                <option key={m.id} value={m.id}>
                  {m.name}{m.description ? ` - ${m.description}` : ''}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Test Result */}
        {cvAiTestResult && (
          <div
            className={`mt-4 p-3 rounded-lg text-sm flex items-center gap-2 ${
              cvAiTestResult.success
                ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300'
                : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-300'
            }`}
          >
            {cvAiTestResult.success ? (
              <CheckCircle className="h-4 w-4 flex-shrink-0" />
            ) : (
              <XCircle className="h-4 w-4 flex-shrink-0" />
            )}
            <span>
              {cvAiTestResult.message}
              {cvAiTestResult.success && ` (${cvAiTestResult.response_time_ms}ms)`}
            </span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-4 flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => testCvAiMutation.mutate()}
            isLoading={testCvAiMutation.isPending}
            leftIcon={testCvAiMutation.isPending ? undefined : <RefreshCw className="h-4 w-4" />}
          >
            {testCvAiMutation.isPending ? 'Test en cours...' : 'Tester'}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => saveCvAiMutation.mutate()}
            isLoading={saveCvAiMutation.isPending}
            disabled={
              saveCvAiMutation.isPending ||
              (cvAiData?.current_provider === cvAiProvider && cvAiData?.current_model === cvAiModel)
            }
          >
            {saveCvAiMutation.isPending ? 'Sauvegarde...' : 'Sauvegarder'}
          </Button>
        </div>
      </Card>

      {/* Secrets Source Info */}
      {statusData?.secrets_source === 'aws' ? (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-green-600 dark:text-green-400" />
            <p className="text-sm text-green-800 dark:text-green-300">
              <strong>AWS Secrets Manager actif</strong> - Les clés API sont chargées depuis AWS Secrets Manager de maniere securisee.
            </p>
          </div>
        </div>
      ) : (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm text-blue-800 dark:text-blue-300">
            <strong>Note :</strong> Les clés API sont configurées via les variables d'environnement du
            serveur. Pour une sécurité renforcée, activez AWS Secrets Manager (AWS_SECRETS_ENABLED=true).
          </p>
        </div>
      )}

      {/* Turnover-IT Skills Modal */}
      {showSkillsModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setShowSkillsModal(false)} />
            <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
              {/* Modal Header */}
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Skills Turnover-IT
                  </h3>
                  <button
                    onClick={() => setShowSkillsModal(false)}
                    className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
                  >
                    <XCircle className="h-6 w-6" />
                  </button>
                </div>

                {/* Metadata */}
                <div className="mt-2 flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                  <span>
                    <strong>{skillsData?.total || 0}</strong> skills
                  </span>
                  {skillsData?.last_synced_at && (
                    <span>
                      Dernière sync: {new Date(skillsData.last_synced_at).toLocaleDateString('fr-FR')}
                    </span>
                  )}
                  <span>Intervalle: {skillsData?.sync_interval_days || 30} jours</span>
                </div>

                {/* Search and Sync */}
                <div className="mt-4 flex gap-2">
                  <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <input
                      type="text"
                      placeholder="Rechercher un skill..."
                      value={skillsSearch}
                      onChange={(e) => setSkillsSearch(e.target.value)}
                      className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => syncSkillsMutation.mutate()}
                    isLoading={syncSkillsMutation.isPending}
                    leftIcon={syncSkillsMutation.isPending ? undefined : <RefreshCw className="h-4 w-4" />}
                  >
                    Synchroniser
                  </Button>
                </div>
              </div>

              {/* Modal Body - Skills List */}
              <div className="flex-1 overflow-y-auto px-6 py-4">
                {isLoadingSkills ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
                  </div>
                ) : skillsData?.skills.length === 0 ? (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    {skillsSearch ? (
                      <p>Aucun skill trouvé pour "{skillsSearch}"</p>
                    ) : (
                      <div>
                        <p className="mb-2">Aucun skill synchronisé</p>
                        <p className="text-sm">Cliquez sur "Synchroniser" pour récupérer les skills depuis Turnover-IT</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {skillsData?.skills.map((skill) => (
                      <span
                        key={skill.slug}
                        className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300"
                        title={`Slug: ${skill.slug}`}
                      >
                        {skill.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
                <Button
                  variant="outline"
                  onClick={() => setShowSkillsModal(false)}
                  className="w-full"
                >
                  Fermer
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
