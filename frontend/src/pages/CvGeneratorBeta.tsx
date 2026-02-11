import { useState, useCallback, useRef, useEffect } from 'react';
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
import type { SSEProgressEvent } from '../api/cvGenerator';
import { validateCV } from '../cv-generator/schema';
import { generateCV } from '../cv-generator/renderer';
import type { TemplateConfig } from '../cv-generator/renderer';
import geminiConfig from '../cv-generator/templates/gemini/config.json';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';

type Step = 'idle' | 'uploading' | 'extracting' | 'ai_parsing' | 'validating' | 'generating' | 'done' | 'error';

const stepConfig: Record<Step, { message: string; icon?: string }> = {
  idle: { message: '' },
  uploading: { message: 'Envoi du fichier...' },
  extracting: { message: 'Extraction du texte...' },
  ai_parsing: { message: "Analyse par l'IA (Claude)..." },
  validating: { message: 'Validation des données...' },
  generating: { message: 'Génération du document Word...' },
  done: { message: 'CV généré avec succès !' },
  error: { message: 'Une erreur est survenue' },
};

function useElapsedTimer(isRunning: boolean) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number | null>(null);

  useEffect(() => {
    if (isRunning) {
      startRef.current = Date.now();
      setElapsed(0);
      const interval = setInterval(() => {
        if (startRef.current) {
          setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
        }
      }, 1000);
      return () => clearInterval(interval);
    } else {
      startRef.current = null;
    }
  }, [isRunning]);

  return elapsed;
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return `${min}m ${sec.toString().padStart(2, '0')}s`;
}

export function CvGeneratorBeta() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [step, setStep] = useState<Step>('idle');
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isProcessing = ['uploading', 'extracting', 'ai_parsing', 'validating', 'generating'].includes(step);
  const elapsed = useElapsedTimer(isProcessing);

  const handleTransform = useCallback(async () => {
    if (!selectedFile) return;
    setErrorMessage(null);
    setStep('uploading');
    setProgress(5);
    setProgressMessage('Envoi du fichier...');

    try {
      let cvData: Record<string, unknown> | null = null;

      // Use SSE streaming endpoint
      await cvGeneratorApi.parseCvStream(selectedFile, {
        onProgress: (event: SSEProgressEvent) => {
          setStep(event.step as Step);
          setProgress(event.percent);
          setProgressMessage(event.message);
        },
        onComplete: (event) => {
          cvData = event.data;
        },
        onError: (message: string) => {
          setStep('error');
          setErrorMessage(message);
        },
      });

      // If we got an error during streaming, stop here
      if (!cvData) {
        if (step !== 'error') {
          // Stream ended without complete event and without explicit error
          setStep('error');
          setErrorMessage("Le flux s'est terminé sans résultat");
        }
        return;
      }

      // Validate with Zod
      setStep('validating');
      setProgress(92);
      setProgressMessage('Validation du schéma...');

      const validation = validateCV(cvData);
      if (!validation.valid) {
        const errorDetails = validation.errors
          .slice(0, 3)
          .map((e) => `${e.path}: ${e.message}`)
          .join('; ');
        throw new Error(`Validation du JSON échouée: ${errorDetails}`);
      }

      // Generate DOCX in the browser
      setStep('generating');
      setProgress(95);
      setProgressMessage('Génération du document Word...');

      const blob = await generateCV(
        validation.data,
        geminiConfig as TemplateConfig,
        '/logo-gemini.png'
      );

      setStep('done');
      setProgress(100);

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
    } catch (error) {
      setStep('error');
      setErrorMessage(
        error instanceof Error ? error.message : 'Une erreur est survenue'
      );
    }
  }, [selectedFile]);

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

  const resetForm = () => {
    setSelectedFile(null);
    setStep('idle');
    setProgress(0);
    setProgressMessage('');
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
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center">
                <Loader2 className="h-5 w-5 text-primary-500 animate-spin mr-2" />
                <span className="text-gray-700 dark:text-gray-300">
                  {progressMessage || stepConfig[step]?.message || ''}
                </span>
              </div>
              <span className="text-sm text-gray-500 dark:text-gray-400 tabular-nums">
                {formatElapsed(elapsed)}
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
              <div
                className="bg-primary-500 h-2.5 rounded-full transition-all duration-700 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-xs text-gray-400">{progress}%</span>
              {step === 'ai_parsing' && (
                <span className="text-xs text-gray-400">
                  Cette étape peut prendre 15-30 secondes
                </span>
              )}
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
                Le document a été téléchargé automatiquement ({formatElapsed(elapsed)})
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
