/**
 * API connections test tab component.
 *
 * Tests for BoondManager and Gemini API connections.
 */

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Zap, RefreshCw, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

import { adminApi } from '../../api/admin';
import { cvTransformerApi } from '../../api/cvTransformer';
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
    api_key_configured: boolean;
  } | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const result = await cvTransformerApi.testGemini();
      setTestResult(result);
      if (result.success) {
        toast.success('API Gemini fonctionnelle');
      } else {
        toast.error(result.message);
      }
    } catch (error: any) {
      setTestResult({
        success: false,
        message: error.response?.data?.detail || 'Erreur de connexion',
        api_key_configured: false,
      });
      toast.error('Erreur lors du test');
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <Card>
      <CardHeader
        title="API Google Gemini"
        subtitle="Intelligence artificielle pour l'extraction des données CV"
      />

      <div className="flex items-center justify-between">
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
            <p className="font-medium text-gray-900 dark:text-gray-100">Google Gemini AI</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {testResult
                ? testResult.message
                : 'Cliquez sur Tester pour vérifier la connexion'}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          {testResult && (
            <Badge variant={testResult.success ? 'success' : 'error'}>
              {testResult.success ? 'OK' : 'Erreur'}
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

      {testResult && !testResult.api_key_configured && (
        <div className="mt-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
          <p className="text-sm text-yellow-700 dark:text-yellow-400">
            <strong>Configuration requise :</strong> Ajoutez la variable d'environnement GEMINI_API_KEY.
          </p>
        </div>
      )}
    </Card>
  );
}
