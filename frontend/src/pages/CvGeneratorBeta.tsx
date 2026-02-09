import { useState, useCallback, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Upload,
  FileText,
  Check,
  AlertCircle,
  Download,
  X,
  Loader2,
  FlaskConical,
} from 'lucide-react';

import { cvGeneratorApi } from '../api/cvGenerator';
import { getErrorMessage } from '../api/client';
import { validateCV } from '../cv-generator/schema';
import { generateCV } from '../cv-generator/renderer';
import type { TemplateConfig } from '../cv-generator/renderer';
import geminiConfig from '../cv-generator/templates/gemini/config.json';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';

type Step = 'idle' | 'uploading' | 'parsing' | 'generating' | 'done' | 'error';

const stepMessages: Record<Step, string> = {
  idle: '',
  uploading: 'Envoi du fichier...',
  parsing: "Analyse par l'IA...",
  generating: 'Génération du document...',
  done: 'CV généré avec succès !',
  error: 'Une erreur est survenue',
};

export function CvGeneratorBeta() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [step, setStep] = useState<Step>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const transformMutation = useMutation({
    mutationFn: async (file: File) => {
      setStep('uploading');

      // Step 1: Send to backend for AI parsing
      setStep('parsing');
      const response = await cvGeneratorApi.parseCv(file);

      if (!response.success) {
        throw new Error('Le parsing a échoué');
      }

      // Step 2: Validate with Zod
      const validation = validateCV(response.data);
      if (!validation.valid) {
        const errorDetails = validation.errors
          .slice(0, 3)
          .map((e) => `${e.path}: ${e.message}`)
          .join('; ');
        throw new Error(`Validation du JSON échouée: ${errorDetails}`);
      }

      // Step 3: Generate DOCX in the browser
      setStep('generating');
      const blob = await generateCV(
        validation.data,
        geminiConfig as TemplateConfig,
        '/logo-gemini.png'
      );

      return blob;
    },
    onSuccess: (blob) => {
      setStep('done');

      // Trigger download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const originalName =
        selectedFile?.name.replace(/\.[^/.]+$/, '') || 'cv';
      a.download = `${originalName}_Gemini.docx`;
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

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file && isValidFile(file)) {
        setSelectedFile(file);
        setStep('idle');
        setErrorMessage(null);
      }
    },
    []
  );

  const isValidFile = (file: File): boolean => {
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ];
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
    if (!selectedFile) return;
    setErrorMessage(null);
    transformMutation.mutate(selectedFile);
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

  const isProcessing = ['uploading', 'parsing', 'generating'].includes(step);
  const canTransform = selectedFile && !isProcessing;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-2">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          CV Generator
        </h1>
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
          <FlaskConical className="h-3 w-3" />
          Beta
        </span>
      </div>
      <p className="text-gray-600 dark:text-gray-400 mb-8">
        Générez un CV au format Gemini Consulting à partir d'un CV existant
      </p>

      {/* File Upload */}
      <Card className="mb-6">
        <CardHeader
          title="1. Importer un CV"
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
              ${
                isDragging
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                  : 'border-gray-300 dark:border-gray-600 hover:border-primary-400 dark:hover:border-primary-500'
              }
            `}
          >
            <Upload
              className={`h-12 w-12 mx-auto mb-4 ${
                isDragging ? 'text-primary-500' : 'text-gray-400'
              }`}
            />
            <p className="text-gray-600 dark:text-gray-400 mb-2">
              Glissez-déposez votre CV ici
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-500">
              ou{' '}
              <span className="text-primary-600 dark:text-primary-400 font-medium">
                parcourez vos fichiers
              </span>
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
                <p className="font-medium text-gray-900 dark:text-gray-100">
                  {selectedFile.name}
                </p>
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

      {/* Generate & Download */}
      <Card>
        <CardHeader
          title="2. Générer le CV"
          subtitle="Le document sera téléchargé automatiquement au format Gemini"
        />

        {/* Progress indicator */}
        {isProcessing && (
          <div className="mb-6">
            <div className="flex items-center mb-2">
              <Loader2 className="h-5 w-5 text-primary-500 animate-spin mr-2" />
              <span className="text-gray-700 dark:text-gray-300">
                {stepMessages[step]}
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className="bg-primary-500 h-2 rounded-full transition-all duration-500"
                style={{
                  width:
                    step === 'uploading'
                      ? '20%'
                      : step === 'parsing'
                        ? '60%'
                        : '90%',
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
                CV généré avec succès !
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
                Erreur lors de la génération
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
            {isProcessing
              ? 'Génération en cours...'
              : 'Générer et télécharger'}
          </Button>

          {(step === 'done' || step === 'error') && (
            <Button variant="outline" onClick={resetForm}>
              Nouveau CV
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
