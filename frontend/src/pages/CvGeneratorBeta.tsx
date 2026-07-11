import { useState, useCallback, useRef, useEffect } from 'react';
import {
  Upload,
  FileText,
  AlertCircle,
  CheckCircle,
  Download,
} from 'lucide-react';

import { cvGeneratorApi } from '../api/cvGenerator';
import type { SSEProgressEvent } from '../api/cvGenerator';
import { validateCV } from '../cv-generator/schema';
import { generateCV } from '../cv-generator/renderer';
import type { TemplateConfig } from '../cv-generator/renderer';
import geminiConfig from '../cv-generator/templates/gemini/config.json';
import craftmaniaConfig from '../cv-generator/templates/craftmania/config.json';
import { Button } from '../components/ui/Button';

type TemplateId = 'gemini' | 'craftmania';

interface TemplateOption {
  config: TemplateConfig;
  logoPath: string;
  label: string;
  description: string;
}

const TEMPLATES: Record<TemplateId, TemplateOption> = {
  gemini: {
    config: geminiConfig as TemplateConfig,
    logoPath: '/logo-gemini.png',
    label: 'Template Gemini',
    description: 'Format standard Gemini Consulting',
  },
  craftmania: {
    config: craftmaniaConfig as TemplateConfig,
    logoPath: '/logo-craftmania.png',
    label: 'Template Craftmania',
    description: 'Format standard Craftmania',
  },
};

type Step = 'idle' | 'uploading' | 'extracting' | 'ai_parsing' | 'validating' | 'generating' | 'done' | 'error';

const stepConfig: Record<Step, { message: string }> = {
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
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateId>('gemini');
  const [isDragging, setIsDragging] = useState(false);
  const [step, setStep] = useState<Step>('idle');
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const stepRef = useRef<Step>(step);
  stepRef.current = step;

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

      if (!cvData) {
        if (stepRef.current !== 'error') {
          setStep('error');
          setErrorMessage("Le flux s'est terminé sans résultat");
        }
        return;
      }

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

      setStep('generating');
      setProgress(95);
      setProgressMessage('Génération du document Word...');

      const template = TEMPLATES[selectedTemplate];
      const blob = await generateCV(
        validation.data,
        template.config,
        template.logoPath
      );

      setStep('done');
      setProgress(100);

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const originalName =
        selectedFile?.name.replace(/\.[^/.]+$/, '') || 'cv';
      a.download = `${originalName}_${template.config.name}.docx`;
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
  }, [selectedFile, selectedTemplate]);

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
    const maxSize = 16 * 1024 * 1024;

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
    <div className="max-w-[880px]">
      <p className="bc">Outils / Générateur de CV</p>
      <h1 className="h1">Générateur de CV</h1>
      <p className="sub">
        Générez un CV formaté à partir d'un CV existant · extraction et analyse par IA (Claude)
      </p>

      {/* 1 · Template */}
      <div className="card mt-[18px]">
        <h3 className="ct">1 · Choisir un template</h3>
        <p className="cs mb-3.5">Sélectionnez le format de mise en forme</p>
        <div className="f-grid">
          {(Object.entries(TEMPLATES) as [TemplateId, TemplateOption][]).map(
            ([id, tpl]) => (
              <button
                key={id}
                type="button"
                onClick={() => setSelectedTemplate(id)}
                disabled={isProcessing}
                className={`tcard text-left disabled:opacity-45 disabled:cursor-not-allowed ${
                  selectedTemplate === id ? 'on' : ''
                }`}
              >
                <span className="tt block">{tpl.label}</span>
                <span className="td2 block">{tpl.description}</span>
              </button>
            )
          )}
        </div>
      </div>

      {/* 2 · Import */}
      <div className="card mt-4">
        <h3 className="ct">2 · Importer un CV</h3>
        <p className="cs mb-3.5">PDF ou Word (.docx) · 16 Mo max</p>

        {!selectedFile ? (
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`drop ${isDragging ? 'active' : ''}`}
          >
            <Upload
              className={`h-9 w-9 mx-auto ${isDragging ? 'text-prit' : 'text-mut2'}`}
            />
            <p className="dropt">Glissez-déposez votre CV ici</p>
            <p className="drops">
              ou <b className="text-prit font-semibold">parcourez vos fichiers</b>
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
          <div className="filecard">
            <div className="dico">
              <FileText className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="dn truncate">{selectedFile.name}</p>
              <p className="ds">{formatFileSize(selectedFile.size)}</p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={resetForm}
              disabled={isProcessing}
            >
              Supprimer
            </Button>
          </div>
        )}

        {errorMessage && step !== 'error' && (
          <div className="alert red">
            <AlertCircle className="h-[18px] w-[18px] flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}
      </div>

      {/* 3 · Génération */}
      <div className="card mt-4">
        <h3 className="ct">3 · Générer le CV</h3>
        <p className="cs">
          Le document Word ({TEMPLATES[selectedTemplate].label}) sera téléchargé automatiquement
        </p>

        {/* Progression */}
        {isProcessing && (
          <div className="mt-3.5">
            <div className="flex items-center justify-between gap-4">
              <span className="text-[12.5px] font-semibold text-ink">
                {progressMessage || stepConfig[step]?.message || ''}
              </span>
              <span className="docs">
                {formatElapsed(elapsed)} · {progress} %
              </span>
            </div>
            <div className="pbar">
              <div className="pfill" style={{ width: `${progress}%` }} />
            </div>
            <p className="f-hint">L'analyse IA peut prendre 15 à 30 secondes</p>
          </div>
        )}

        {/* Succès */}
        {step === 'done' && (
          <div className="okbox">
            <CheckCircle className="h-4 w-4 flex-shrink-0" />
            <span>
              CV généré avec succès — le document a été téléchargé ({formatElapsed(elapsed)})
            </span>
          </div>
        )}

        {/* Erreur */}
        {step === 'error' && errorMessage && (
          <div className="alert red">
            <AlertCircle className="h-[18px] w-[18px] flex-shrink-0" />
            <div>
              <p className="font-semibold">Erreur lors de la génération</p>
              <p className="text-xs font-normal mt-0.5">{errorMessage}</p>
            </div>
          </div>
        )}

        <div className="flex items-center gap-2 mt-3.5">
          <Button
            onClick={handleTransform}
            disabled={!canTransform}
            isLoading={isProcessing}
            leftIcon={<Download className="h-4 w-4" />}
          >
            {isProcessing ? 'Génération en cours...' : 'Générer et télécharger'}
          </Button>

          {(step === 'done' || step === 'error') && (
            <Button variant="secondary" onClick={resetForm}>
              Nouveau CV
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
