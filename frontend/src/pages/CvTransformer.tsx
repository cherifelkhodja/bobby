import { useState, useCallback, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Upload, FileText, Check, AlertCircle, Download, X, Loader2 } from 'lucide-react';

import { cvTransformerApi } from '../api/cvTransformer';
import { getErrorMessage } from '../api/client';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { PageSpinner } from '../components/ui/Spinner';
import type { CvTemplate } from '../types';

type TransformStep = 'idle' | 'extracting' | 'analyzing' | 'generating' | 'done' | 'error';

const stepMessages: Record<TransformStep, string> = {
  idle: '',
  extracting: 'Extraction du texte...',
  analyzing: 'Analyse par l\'IA...',
  generating: 'Génération du document...',
  done: 'Transformation terminée !',
  error: 'Une erreur est survenue',
};

export function CvTransformer() {
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [step, setStep] = useState<TransformStep>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch templates
  const { data: templatesData, isLoading: loadingTemplates } = useQuery({
    queryKey: ['cv-templates'],
    queryFn: cvTransformerApi.getTemplates,
  });

  const templates = templatesData?.templates.filter(t => t.is_active) || [];

  // Transform mutation
  const transformMutation = useMutation({
    mutationFn: async ({ file, templateName }: { file: File; templateName: string }) => {
      // Simulate steps for better UX
      setStep('extracting');
      await new Promise(resolve => setTimeout(resolve, 500));

      setStep('analyzing');
      const blob = await cvTransformerApi.transformCv(file, templateName);

      setStep('generating');
      await new Promise(resolve => setTimeout(resolve, 300));

      return blob;
    },
    onSuccess: (blob) => {
      setStep('done');

      // Download the file
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const originalName = selectedFile?.name.replace(/\.[^/.]+$/, '') || 'cv';
      a.download = `${originalName}_formatted.docx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
    onError: (error) => {
      setStep('error');
      setErrorMessage(getErrorMessage(error));
    },
  });

  // Drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file && isValidFile(file)) {
      setSelectedFile(file);
      setStep('idle');
      setErrorMessage(null);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && isValidFile(file)) {
      setSelectedFile(file);
      setStep('idle');
      setErrorMessage(null);
    }
  }, []);

  const isValidFile = (file: File): boolean => {
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const validExtensions = ['.pdf', '.docx'];
    const maxSize = 16 * 1024 * 1024; // 16 MB

    if (file.size > maxSize) {
      setErrorMessage('Le fichier est trop volumineux (max 16 Mo)');
      return false;
    }

    const extension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
    if (!validExtensions.includes(extension) && !validTypes.includes(file.type)) {
      setErrorMessage('Format non supporté. Utilisez PDF ou DOCX');
      return false;
    }

    return true;
  };

  const handleTransform = () => {
    if (!selectedFile || !selectedTemplate) return;
    setErrorMessage(null);
    transformMutation.mutate({ file: selectedFile, templateName: selectedTemplate });
  };

  const resetForm = () => {
    setSelectedFile(null);
    setStep('idle');
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} o`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
  };

  if (loadingTemplates) {
    return <PageSpinner />;
  }

  const isProcessing = ['extracting', 'analyzing', 'generating'].includes(step);
  const canTransform = selectedFile && selectedTemplate && !isProcessing;

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
        Transformateur de CV
      </h1>
      <p className="text-gray-600 dark:text-gray-400 mb-8">
        Convertissez vos CVs en documents Word standardisés
      </p>

      {/* Template Selection */}
      <Card className="mb-6">
        <CardHeader
          title="1. Choisir un template"
          subtitle="Sélectionnez le format de sortie souhaité"
        />

        {templates.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Aucun template disponible</p>
            <p className="text-sm mt-2">Contactez un administrateur pour en ajouter</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {templates.map((template) => (
              <TemplateCard
                key={template.id}
                template={template}
                isSelected={selectedTemplate === template.name}
                onSelect={() => setSelectedTemplate(template.name)}
                disabled={isProcessing}
              />
            ))}
          </div>
        )}
      </Card>

      {/* File Upload */}
      <Card className="mb-6">
        <CardHeader
          title="2. Importer un CV"
          subtitle="PDF ou Word (.docx), max 16 Mo"
        />

        {!selectedFile ? (
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
              ${isDragging
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                : 'border-gray-300 dark:border-gray-600 hover:border-primary-400 dark:hover:border-primary-500'
              }
            `}
          >
            <Upload className={`h-12 w-12 mx-auto mb-4 ${isDragging ? 'text-primary-500' : 'text-gray-400'}`} />
            <p className="text-gray-600 dark:text-gray-400 mb-2">
              Glissez-déposez votre CV ici
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-500">
              ou <span className="text-primary-600 dark:text-primary-400 font-medium">parcourez vos fichiers</span>
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
        ) : (
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div className="flex items-center">
              <FileText className="h-10 w-10 text-primary-500 mr-4" />
              <div>
                <p className="font-medium text-gray-900 dark:text-gray-100">{selectedFile.name}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={resetForm}
              disabled={isProcessing}
              leftIcon={<X className="h-4 w-4" />}
            >
              Supprimer
            </Button>
          </div>
        )}

        {errorMessage && step !== 'error' && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center text-red-700 dark:text-red-400">
            <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
            <span className="text-sm">{errorMessage}</span>
          </div>
        )}
      </Card>

      {/* Transform Button & Progress */}
      <Card>
        <CardHeader
          title="3. Transformer"
          subtitle="Le document sera téléchargé automatiquement"
        />

        {/* Progress indicator */}
        {isProcessing && (
          <div className="mb-6">
            <div className="flex items-center mb-2">
              <Loader2 className="h-5 w-5 text-primary-500 animate-spin mr-2" />
              <span className="text-gray-700 dark:text-gray-300">{stepMessages[step]}</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className="bg-primary-500 h-2 rounded-full transition-all duration-500"
                style={{
                  width: step === 'extracting' ? '33%' : step === 'analyzing' ? '66%' : '90%',
                }}
              />
            </div>
          </div>
        )}

        {/* Success message */}
        {step === 'done' && (
          <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center">
            <Check className="h-6 w-6 text-green-500 mr-3" />
            <div>
              <p className="font-medium text-green-700 dark:text-green-400">
                Transformation réussie !
              </p>
              <p className="text-sm text-green-600 dark:text-green-500">
                Le document a été téléchargé automatiquement
              </p>
            </div>
          </div>
        )}

        {/* Error message */}
        {step === 'error' && errorMessage && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center">
            <AlertCircle className="h-6 w-6 text-red-500 mr-3" />
            <div>
              <p className="font-medium text-red-700 dark:text-red-400">
                Erreur lors de la transformation
              </p>
              <p className="text-sm text-red-600 dark:text-red-500">
                {errorMessage}
              </p>
            </div>
          </div>
        )}

        <div className="flex gap-4">
          <Button
            onClick={handleTransform}
            disabled={!canTransform}
            isLoading={isProcessing}
            leftIcon={<Download className="h-4 w-4" />}
            className="flex-1"
          >
            {isProcessing ? 'Transformation en cours...' : 'Transformer et télécharger'}
          </Button>

          {(step === 'done' || step === 'error') && (
            <Button
              variant="outline"
              onClick={resetForm}
            >
              Nouveau CV
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}

// Template card component
interface TemplateCardProps {
  template: CvTemplate;
  isSelected: boolean;
  onSelect: () => void;
  disabled?: boolean;
}

function TemplateCard({ template, isSelected, onSelect, disabled }: TemplateCardProps) {
  return (
    <button
      onClick={onSelect}
      disabled={disabled}
      className={`
        relative p-4 rounded-lg border-2 text-left transition-all
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${isSelected
          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
          : 'border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-700'
        }
      `}
    >
      {isSelected && (
        <div className="absolute top-2 right-2">
          <Check className="h-5 w-5 text-primary-500" />
        </div>
      )}
      <div className="flex items-center mb-2">
        <FileText className={`h-6 w-6 mr-2 ${isSelected ? 'text-primary-500' : 'text-gray-400'}`} />
        <span className="font-medium text-gray-900 dark:text-gray-100">
          {template.display_name}
        </span>
      </div>
      {template.description && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {template.description}
        </p>
      )}
    </button>
  );
}
