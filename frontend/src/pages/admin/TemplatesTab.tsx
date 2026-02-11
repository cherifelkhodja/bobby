/**
 * Templates management tab component (Quotation templates).
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, FileSpreadsheet } from 'lucide-react';
import { toast } from 'sonner';

import { quotationGeneratorApi, type TemplateInfo } from '../../api/quotationGenerator';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { PageSpinner } from '../../components/ui/Spinner';
import { QUOTATION_TEMPLATES } from './constants';

export function TemplatesTab() {
  const queryClient = useQueryClient();
  const [uploadingTemplate, setUploadingTemplate] = useState<string | null>(null);

  // Quotation Templates
  const { data: quotationTemplatesData, isLoading } = useQuery({
    queryKey: ['quotation-templates'],
    queryFn: quotationGeneratorApi.listTemplates,
  });

  const quotationUploadMutation = useMutation({
    mutationFn: async ({ name, file, displayName, description }: {
      name: string;
      file: File;
      displayName: string;
      description?: string;
    }) => {
      return quotationGeneratorApi.uploadTemplate(name, file, displayName, description, false);
    },
    onSuccess: () => {
      toast.success('Template devis mis à jour');
      queryClient.invalidateQueries({ queryKey: ['quotation-templates'] });
      setUploadingTemplate(null);
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast.error(axiosError.response?.data?.detail || 'Erreur lors de l\'upload');
      setUploadingTemplate(null);
    },
  });

  const handleQuotationFileSelect = (templateName: string, displayName: string, description: string) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.xlsx';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        setUploadingTemplate(templateName);
        quotationUploadMutation.mutate({ name: templateName, file, displayName, description });
      }
    };
    input.click();
  };

  const getQuotationTemplateData = (name: string): TemplateInfo | undefined => {
    return quotationTemplatesData?.find(t => t.name === name);
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div className="space-y-6">
      {/* Quotation Templates */}
      <Card>
        <CardHeader
          title="Templates Devis (Thales)"
          subtitle="Uploadez ou mettez à jour les templates Excel pour la génération de devis"
        />

        <div className="space-y-4">
          {QUOTATION_TEMPLATES.map((template) => {
            const existingTemplate = getQuotationTemplateData(template.name);
            const isUploading = uploadingTemplate === template.name;

            return (
              <div
                key={template.name}
                className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg"
              >
                <div className="flex items-center space-x-4">
                  <div className={`p-3 rounded-lg ${existingTemplate ? 'bg-green-100 dark:bg-green-900/30' : 'bg-gray-200 dark:bg-gray-700'}`}>
                    <FileSpreadsheet className={`h-6 w-6 ${existingTemplate ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}`} />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">{template.displayName}</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{template.description}</p>
                    {existingTemplate?.updated_at && (
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
                    onClick={() => handleQuotationFileSelect(template.name, template.displayName, template.description)}
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

        <div className="mt-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <p className="text-sm text-green-700 dark:text-green-400">
            <strong>Format requis :</strong> Les templates doivent être au format .xlsx et utiliser
            les placeholders entre doubles accolades (ex: {'{{ consultant_name }}'}, {'{{ tjm }}'}).
          </p>
        </div>
      </Card>
    </div>
  );
}
