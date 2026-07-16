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
import { adminApi, type CvAiTestResponse, type CvAiModelInfo, type CvGeneratorBetaSettings, type SireneTestResponse, type InpiTestResponse } from '../../api/admin';
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
  const [betaModel, setBetaModel] = useState('');
  const [betaTestResult, setBetaTestResult] = useState<CvAiTestResponse | null>(null);
  const [sireneTestResult, setSireneTestResult] = useState<SireneTestResponse | null>(null);
  const [inpiTestResult, setInpiTestResult] = useState<InpiTestResponse | null>(null);
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

  // CV Generator Settings
  const {
    data: betaData,
  } = useQuery<CvGeneratorBetaSettings>({
    queryKey: ['cv-generator-beta-settings'],
    queryFn: adminApi.getCvGeneratorBetaSettings,
  });

  useEffect(() => {
    if (betaData) {
      setBetaModel(betaData.current_model);
    }
  }, [betaData]);

  const saveBetaMutation = useMutation({
    mutationFn: () => adminApi.setCvGeneratorBetaModel(betaModel),
    onSuccess: () => {
      toast.success(`Modèle CV Generator mis à jour: ${betaModel}`);
      queryClient.invalidateQueries({ queryKey: ['cv-generator-beta-settings'] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Erreur lors de la sauvegarde');
    },
  });

  const testBetaMutation = useMutation({
    mutationFn: () => adminApi.testCvGeneratorBeta(betaModel),
    onSuccess: (result) => {
      setBetaTestResult(result);
      if (result.success) {
        toast.success(`Claude fonctionne (${result.response_time_ms}ms)`);
      } else {
        toast.error(result.message);
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Erreur lors du test');
    },
  });

  const sireneTestMutation = useMutation({
    mutationFn: adminApi.testSirene,
    onSuccess: (result) => {
      setSireneTestResult(result);
      if (result.success) {
        toast.success(`INSEE Sirene fonctionne (${result.response_time_ms}ms)`);
      } else {
        toast.error(result.message);
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Erreur lors du test INSEE');
    },
  });

  const inpiTestMutation = useMutation({
    mutationFn: adminApi.testInpi,
    onSuccess: (result) => {
      setInpiTestResult(result);
      if (result.success) {
        toast.success(`INPI RNE fonctionne (${result.response_time_ms}ms)`);
      } else {
        toast.error(result.message);
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Erreur lors du test INPI');
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-pri" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[13px] text-mut">
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
                    className={`p-3 rounded-[9px] ${
                      service.configured
                        ? testResult?.success
                          ? 'bg-grn-bg'
                          : testResult && !testResult.success
                            ? 'bg-red-bg'
                            : 'bg-blu-bg'
                        : 'bg-lin2'
                    }`}
                  >
                    <Icon
                      className={`h-6 w-6 ${
                        service.configured
                          ? testResult?.success
                            ? 'text-grn-fg'
                            : testResult && !testResult.success
                              ? 'text-red-fg'
                              : 'text-blu-fg'
                          : 'text-mut2'
                      }`}
                    />
                  </div>
                  <div>
                    <h3 className="text-[13.5px] font-semibold text-ink">
                      {config?.name || service.service}
                    </h3>
                    {service.masked_key && (
                      <div className="mt-1 flex items-center gap-1">
                        <Key className="h-3 w-3 text-mut2" />
                        <code className="text-xs text-mut font-mono">
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
                  <label className="f-lab">
                    Modèle
                  </label>
                  <select
                    value={geminiModel}
                    onChange={(e) => setGeminiModel(e.target.value)}
                    className="f-in !px-2.5"
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
                  className={`mt-4 p-3 rounded-[10px] text-[13px] flex items-center gap-2 ${
                    testResult.success
                      ? 'bg-grn-bg text-grn-fg'
                      : 'bg-red-bg text-red-fg'
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

      {/* CV Generator Settings */}
      <Card>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 rounded-[9px] bg-amb-bg">
            <Sparkles className="h-6 w-6 text-amb-fg" />
          </div>
          <div>
            <h3 className="text-[13.5px] font-semibold text-ink">
              IA pour CV Generator
            </h3>
            <p className="text-[12.5px] text-mut">
              Choisir le modèle Claude pour le CV Generator
            </p>
          </div>
          {betaData && (
            <Badge variant="primary" className="ml-auto">
              Claude actif
            </Badge>
          )}
        </div>

        <div>
          <label className="f-lab">
            Modèle Claude
          </label>
          <select
            value={betaModel}
            onChange={(e) => {
              setBetaModel(e.target.value);
              setBetaTestResult(null);
            }}
            className="f-in !px-2.5"
          >
            {(betaData?.available_models || []).map((m: CvAiModelInfo) => (
              <option key={m.id} value={m.id}>
                {m.name}{m.description ? ` - ${m.description}` : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Test Result */}
        {betaTestResult && (
          <div
            className={`mt-4 p-3 rounded-[10px] text-[13px] flex items-center gap-2 ${
              betaTestResult.success
                ? 'bg-grn-bg text-grn-fg'
                : 'bg-red-bg text-red-fg'
            }`}
          >
            {betaTestResult.success ? (
              <CheckCircle className="h-4 w-4 flex-shrink-0" />
            ) : (
              <XCircle className="h-4 w-4 flex-shrink-0" />
            )}
            <span>
              {betaTestResult.message}
              {betaTestResult.success && ` (${betaTestResult.response_time_ms}ms)`}
            </span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-4 flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => testBetaMutation.mutate()}
            isLoading={testBetaMutation.isPending}
            leftIcon={testBetaMutation.isPending ? undefined : <RefreshCw className="h-4 w-4" />}
          >
            {testBetaMutation.isPending ? 'Test en cours...' : 'Tester'}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => saveBetaMutation.mutate()}
            isLoading={saveBetaMutation.isPending}
            disabled={
              saveBetaMutation.isPending ||
              betaData?.current_model === betaModel
            }
          >
            {saveBetaMutation.isPending ? 'Sauvegarde...' : 'Sauvegarder'}
          </Button>
        </div>
      </Card>

      {/* INSEE Sirene Settings */}
      <Card>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 rounded-[9px] bg-blu-bg">
            <Key className="h-6 w-6 text-blu-fg" />
          </div>
          <div>
            <h3 className="text-[13.5px] font-semibold text-ink">
              INSEE Sirene API
            </h3>
            <p className="text-[12.5px] text-mut">
              Utilisée pour l'auto-remplissage SIRET dans le portail partenaire
            </p>
          </div>
          {sireneTestResult && (
            <Badge variant={sireneTestResult.success ? 'success' : 'error'} className="ml-auto">
              {sireneTestResult.success ? 'Opérationnel' : 'Erreur'}
            </Badge>
          )}
        </div>

        <p className="text-[12.5px] text-mut mb-4">
          Clé API configurée via la variable <code className="text-xs bg-lin2 text-ink px-1 py-0.5 rounded">SIRENE_API_KEY</code> (ou AWS Secrets Manager).
        </p>

        {/* Test Result */}
        {sireneTestResult && (
          <div
            className={`mb-4 p-3 rounded-[10px] text-[13px] flex items-center gap-2 ${
              sireneTestResult.success
                ? 'bg-grn-bg text-grn-fg'
                : 'bg-red-bg text-red-fg'
            }`}
          >
            {sireneTestResult.success ? (
              <CheckCircle className="h-4 w-4 flex-shrink-0" />
            ) : (
              <XCircle className="h-4 w-4 flex-shrink-0" />
            )}
            <span>
              {sireneTestResult.message}
              {sireneTestResult.success && ` (${sireneTestResult.response_time_ms}ms)`}
            </span>
          </div>
        )}

        <Button
          variant="outline"
          size="sm"
          onClick={() => sireneTestMutation.mutate()}
          isLoading={sireneTestMutation.isPending}
          leftIcon={sireneTestMutation.isPending ? undefined : <RefreshCw className="h-4 w-4" />}
          disabled={sireneTestMutation.isPending}
        >
          {sireneTestMutation.isPending ? 'Test en cours...' : 'Tester INSEE Sirene'}
        </Button>
      </Card>

      {/* INPI RNE Settings */}
      <Card>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 rounded-[9px] bg-ind-bg">
            <Key className="h-6 w-6 text-ind-fg" />
          </div>
          <div>
            <h3 className="text-[13.5px] font-semibold text-ink">
              INPI RNE API
            </h3>
            <p className="text-[12.5px] text-mut">
              Ville du greffe, capital social et forme juridique
            </p>
          </div>
          {inpiTestResult && (
            <Badge variant={inpiTestResult.success ? 'success' : 'error'} className="ml-auto">
              {inpiTestResult.success ? 'Opérationnel' : 'Erreur'}
            </Badge>
          )}
        </div>

        <p className="text-[12.5px] text-mut mb-4">
          Token Bearer configuré via la variable <code className="text-xs bg-lin2 text-ink px-1 py-0.5 rounded">INPI_TOKEN</code> (AWS Secrets Manager).
        </p>

        {/* Test Result */}
        {inpiTestResult && (
          <div
            className={`mb-4 p-3 rounded-[10px] text-[13px] flex items-center gap-2 ${
              inpiTestResult.success
                ? 'bg-grn-bg text-grn-fg'
                : 'bg-red-bg text-red-fg'
            }`}
          >
            {inpiTestResult.success ? (
              <CheckCircle className="h-4 w-4 flex-shrink-0" />
            ) : (
              <XCircle className="h-4 w-4 flex-shrink-0" />
            )}
            <span>{inpiTestResult.message}</span>
          </div>
        )}

        <Button
          variant="outline"
          size="sm"
          onClick={() => inpiTestMutation.mutate()}
          isLoading={inpiTestMutation.isPending}
          leftIcon={inpiTestMutation.isPending ? undefined : <RefreshCw className="h-4 w-4" />}
          disabled={inpiTestMutation.isPending}
        >
          {inpiTestMutation.isPending ? 'Test en cours...' : 'Tester INPI RNE'}
        </Button>
      </Card>

      {/* Secrets Source Info */}
      {statusData?.secrets_source === 'aws' ? (
        <div className="okbox !mt-0">
          <Shield className="h-5 w-5 shrink-0" />
          <span>
            <strong>AWS Secrets Manager actif</strong> - Les clés API sont chargées depuis AWS Secrets Manager de maniere securisee.
          </span>
        </div>
      ) : (
        <div className="infob">
          <strong>Note :</strong> Les clés API sont configurées via les variables d'environnement du
          serveur. Pour une sécurité renforcée, activez AWS Secrets Manager (AWS_SECRETS_ENABLED=true).
        </div>
      )}

      {/* Turnover-IT Skills Modal */}
      {showSkillsModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setShowSkillsModal(false)} />
            <div className="relative bg-sur border border-lin rounded-2xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
              {/* Modal Header */}
              <div className="px-6 py-4 border-b border-lin">
                <div className="flex items-center justify-between">
                  <h3 className="text-[15px] font-bold text-ink">
                    Skills Turnover-IT
                  </h3>
                  <button
                    onClick={() => setShowSkillsModal(false)}
                    className="text-mut2 hover:text-ink transition-colors"
                  >
                    <XCircle className="h-6 w-6" />
                  </button>
                </div>

                {/* Metadata */}
                <div className="mt-2 flex items-center gap-4 text-[12.5px] text-mut">
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
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-mut2" />
                    <input
                      type="text"
                      placeholder="Rechercher un skill..."
                      value={skillsSearch}
                      onChange={(e) => setSkillsSearch(e.target.value)}
                      className="f-in !pl-10"
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
                    <Loader2 className="h-6 w-6 animate-spin text-pri" />
                  </div>
                ) : skillsData?.skills.length === 0 ? (
                  <div className="text-center py-8 text-mut">
                    {skillsSearch ? (
                      <p>Aucun skill trouvé pour "{skillsSearch}"</p>
                    ) : (
                      <div>
                        <p className="mb-2">Aucun skill synchronisé</p>
                        <p className="text-[12.5px]">Cliquez sur "Synchroniser" pour récupérer les skills depuis Turnover-IT</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {skillsData?.skills.map((skill) => (
                      <span
                        key={skill.slug}
                        className="sk"
                        title={`Slug: ${skill.slug}`}
                      >
                        {skill.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="px-6 py-4 border-t border-lin">
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
