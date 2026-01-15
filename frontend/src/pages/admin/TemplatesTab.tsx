/**
 * CV templates management tab component.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, Upload, RefreshCw, Zap } from 'lucide-react';
import { toast } from 'sonner';

import { cvTransformerApi } from '../../api/cvTransformer';
import type { CvTemplate } from '../../types';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { PageSpinner } from '../../components/ui/Spinner';
import { PREDEFINED_TEMPLATES } from './constants';

export function TemplatesTab() {
  const queryClient = useQueryClient();
  const [uploadingTemplate, setUploadingTemplate] = useState<string | null>(null);

  const { data: templatesData, isLoading } = useQuery({
    queryKey: ['cv-templates'],
    queryFn: cvTransformerApi.getTemplates,
  });

  const uploadMutation = useMutation({
    mutationFn: async ({ name, file, displayName, description }: {
      name: string;
      file: File;
      displayName: string;
      description?: string;
    }) => {
      return cvTransformerApi.uploadTemplate(name, file, displayName, description);
    },
    onSuccess: () => {
      toast.success('Template mis à jour');
      queryClient.invalidateQueries({ queryKey: ['cv-templates'] });
      setUploadingTemplate(null);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'upload');
      setUploadingTemplate(null);
    },
  });

  const handleFileSelect = (templateName: string, displayName: string, description: string) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.docx';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        setUploadingTemplate(templateName);
        uploadMutation.mutate({ name: templateName, file, displayName, description });
      }
    };
    input.click();
  };

  const getTemplateData = (name: string): CvTemplate | undefined => {
    return templatesData?.templates.find(t => t.name === name);
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Gestion des templates CV"
          subtitle="Uploadez ou mettez à jour les templates Word pour la transformation de CV"
        />

        <div className="space-y-4">
          {PREDEFINED_TEMPLATES.map((template) => {
            const existingTemplate = getTemplateData(template.name);
            const isUploading = uploadingTemplate === template.name;

            return (
              <div
                key={template.name}
                className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg"
              >
                <div className="flex items-center space-x-4">
                  <div className={`p-3 rounded-lg ${existingTemplate ? 'bg-primary-100 dark:bg-primary-900/30' : 'bg-gray-200 dark:bg-gray-700'}`}>
                    <FileText className={`h-6 w-6 ${existingTemplate ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400'}`} />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">{template.displayName}</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{template.description}</p>
                    {existingTemplate && (
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                        Mis à jour le {new Date(existingTemplate.updated_at).toLocaleDateString('fr-FR')}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  {existingTemplate ? (
                    <Badge variant="success">Configuré</Badge>
                  ) : (
                    <Badge variant="warning">Non configuré</Badge>
                  )}
                  <Button
                    variant={existingTemplate ? 'outline' : 'primary'}
                    size="sm"
                    onClick={() => handleFileSelect(template.name, template.displayName, template.description)}
                    isLoading={isUploading}
                    leftIcon={<Upload className="h-4 w-4" />}
                  >
                    {existingTemplate ? 'Remplacer' : 'Uploader'}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <p className="text-sm text-blue-700 dark:text-blue-400">
            <strong>Format requis :</strong> Les templates doivent être au format .docx et utiliser
            les variables Jinja2 (ex: {'{{ profil.titre_cible }}'}, {'{% for exp in experiences %}'}).
          </p>
        </div>
      </Card>

      {/* Gemini API Test */}
      <GeminiTestCard />
    </div>
  );
}

function GeminiTestCard() {
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
        title="Test API Gemini"
        subtitle="Vérifiez que l'API Gemini est correctement configurée"
      />

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className={`p-3 rounded-lg ${testResult?.success ? 'bg-green-100 dark:bg-green-900/30' : 'bg-gray-200 dark:bg-gray-700'}`}>
            <Zap className={`h-6 w-6 ${testResult?.success ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}`} />
          </div>
          <div>
            <p className="font-medium text-gray-900 dark:text-gray-100">Google Gemini AI</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {testResult ? testResult.message : 'Cliquez pour tester la connexion'}
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
            <strong>Configuration requise :</strong> Ajoutez la variable d'environnement GEMINI_API_KEY dans Railway.
          </p>
        </div>
      )}
    </Card>
  );
}
