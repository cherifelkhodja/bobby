/**
 * API connections test tab component.
 *
 * Tests for BoondManager and Gemini API connections.
 */

import { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Zap, RefreshCw, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

import { adminApi } from '../../api/admin';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { PageSpinner } from '../../components/ui/Spinner';

export function ApiTab() {
  return (
    <div className="space-y-6">
      <BoondApiCard />
      <GeminiApiCard />
    </div>
  );
}

function BoondApiCard() {
  const [isTesting, setIsTesting] = useState(false);

  const { data: boondStatus, isLoading, refetch } = useQuery({
    queryKey: ['boond-status'],
    queryFn: adminApi.getBoondStatus,
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
      refetch();
    },
    onError: () => toast.error('Erreur lors du test de connexion'),
    onSettled: () => setIsTesting(false),
  });

  if (isLoading) {
    return <PageSpinner />;
  }

  const isConnected = boondStatus?.configured && boondStatus?.connected;
  const isConfigured = boondStatus?.configured;

  return (
    <Card>
      <CardHeader
        title="API BoondManager"
        subtitle="Connexion à l'ERP BoondManager pour la gestion des ressources et opportunités"
      />

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className={`p-3 rounded-lg ${
            isConnected
              ? 'bg-green-100 dark:bg-green-900/30'
              : isConfigured
                ? 'bg-red-100 dark:bg-red-900/30'
                : 'bg-yellow-100 dark:bg-yellow-900/30'
          }`}>
            {isConnected ? (
              <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
            ) : isConfigured ? (
              <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
            ) : (
              <AlertCircle className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
            )}
          </div>
          <div>
            <p className="font-medium text-gray-900 dark:text-gray-100">BoondManager ERP</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {isConnected
                ? `Connecté à ${boondStatus?.api_url}`
                : isConfigured
                  ? boondStatus?.error || 'Connexion échouée'
                  : 'Variables BOOND_USERNAME et BOOND_PASSWORD requises'}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <Badge variant={isConnected ? 'success' : isConfigured ? 'error' : 'warning'}>
            {isConnected ? 'Connecté' : isConfigured ? 'Erreur' : 'Non configuré'}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={() => testMutation.mutate()}
            isLoading={isTesting}
            disabled={!isConfigured}
            leftIcon={<RefreshCw className="h-4 w-4" />}
          >
            Tester
          </Button>
        </div>
      </div>
    </Card>
  );
}

function GeminiApiCard() {
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    response_time_ms?: number;
  } | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Fetch current settings
  const { data: settings, isLoading, refetch } = useQuery({
    queryKey: ['gemini-settings'],
    queryFn: adminApi.getGeminiSettings,
  });

  const [selectedModel, setSelectedModel] = useState<string>('');

  // Update selected model when settings load
  useEffect(() => {
    if (settings?.current_model && !selectedModel) {
      setSelectedModel(settings.current_model);
    }
  }, [settings?.current_model]);

  const handleTest = async () => {
    const modelToTest = selectedModel || settings?.current_model || settings?.default_model;
    if (!modelToTest) return;

    setIsTesting(true);
    setTestResult(null);
    try {
      const result = await adminApi.testGeminiModel(modelToTest);
      setTestResult({
        success: result.success,
        message: result.message,
        response_time_ms: result.response_time_ms,
      });
      if (result.success) {
        toast.success(`${modelToTest}: ${result.response_time_ms}ms`);
      } else {
        toast.error(result.message);
      }
    } catch (error: any) {
      setTestResult({
        success: false,
        message: error.response?.data?.detail || 'Erreur de connexion',
      });
      toast.error('Erreur lors du test');
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = async () => {
    if (!selectedModel) return;

    setIsSaving(true);
    try {
      await adminApi.setGeminiModel(selectedModel);
      toast.success(`Modèle ${selectedModel} configuré`);
      refetch();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erreur lors de la sauvegarde');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader
          title="API Google Gemini"
          subtitle="Intelligence artificielle pour l'anonymisation"
        />
        <div className="flex justify-center py-4">
          <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      </Card>
    );
  }

  const currentModel = settings?.current_model || settings?.default_model || '';
  const effectiveSelected = selectedModel || currentModel;
  const hasChanged = selectedModel && selectedModel !== currentModel;

  return (
    <Card>
      <CardHeader
        title="API Google Gemini"
        subtitle="Intelligence artificielle pour l'anonymisation des opportunités"
      />

      {/* Model Selector */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Modèle Gemini
        </label>
        <div className="flex items-center gap-3">
          <select
            value={effectiveSelected}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="flex-1 px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {settings?.available_models.map((model) => (
              <option key={model} value={model}>
                {model} {model === settings?.default_model ? '(par défaut)' : ''}
              </option>
            ))}
          </select>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSave}
            isLoading={isSaving}
            disabled={!hasChanged}
          >
            Enregistrer
          </Button>
        </div>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          Modèle actuel : <span className="font-medium">{currentModel}</span>
        </p>
      </div>

      {/* Test Section */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-4">
          <div className={`p-3 rounded-lg ${
            testResult?.success
              ? 'bg-green-100 dark:bg-green-900/30'
              : testResult && !testResult.success
                ? 'bg-red-100 dark:bg-red-900/30'
                : 'bg-gray-200 dark:bg-gray-700'
          }`}>
            {testResult?.success ? (
              <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
            ) : testResult && !testResult.success ? (
              <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
            ) : (
              <Zap className="h-6 w-6 text-gray-400" />
            )}
          </div>
          <div>
            <p className="font-medium text-gray-900 dark:text-gray-100">Test API</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {testResult
                ? testResult.message
                : 'Cliquez sur Tester pour vérifier le modèle sélectionné'}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          {testResult && (
            <Badge variant={testResult.success ? 'success' : 'error'}>
              {testResult.success ? `${testResult.response_time_ms}ms` : 'Erreur'}
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleTest}
            isLoading={isTesting}
            leftIcon={<RefreshCw className="h-4 w-4" />}
          >
            Tester
          </Button>
        </div>
      </div>
    </Card>
  );
}
