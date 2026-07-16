/**
 * FileDropzone - Reusable drag-and-drop file upload component
 *
 * Provides a consistent file upload experience across the application.
 */

import { useCallback, useRef, useState } from 'react';
import { Upload, FileText, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from './Button';

interface FileDropzoneProps {
  /** Accepted file types (e.g., '.pdf,.docx') */
  accept?: string;
  /** Accepted MIME types for validation */
  acceptedMimeTypes?: string[];
  /** Maximum file size in bytes */
  maxSize?: number;
  /** Callback when file is selected */
  onFileSelect: (file: File) => void;
  /** Callback when error occurs */
  onError?: (message: string) => void;
  /** Whether upload is in progress */
  isLoading?: boolean;
  /** Currently selected file */
  selectedFile?: File | null;
  /** Callback to clear selected file */
  onClear?: () => void;
  /** Label for the dropzone */
  label?: string;
  /** Description text */
  description?: string;
  /** Disabled state */
  disabled?: boolean;
}

export function FileDropzone({
  accept = '*',
  acceptedMimeTypes,
  maxSize,
  onFileSelect,
  onError,
  isLoading = false,
  selectedFile,
  onClear,
  label = 'Glissez-déposez votre fichier ici',
  description,
  disabled = false,
}: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback(
    (file: File): boolean => {
      // Check size
      if (maxSize && file.size > maxSize) {
        const maxSizeMB = (maxSize / (1024 * 1024)).toFixed(0);
        const message = `Le fichier est trop volumineux (max ${maxSizeMB} Mo)`;
        setErrorMessage(message);
        onError?.(message);
        return false;
      }

      // Check MIME type
      if (acceptedMimeTypes && acceptedMimeTypes.length > 0) {
        const extension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
        const isValidType = acceptedMimeTypes.includes(file.type);
        const isValidExtension = accept.split(',').some((ext) => ext.trim() === extension);

        if (!isValidType && !isValidExtension) {
          const message = 'Format de fichier non supporté';
          setErrorMessage(message);
          onError?.(message);
          return false;
        }
      }

      setErrorMessage(null);
      return true;
    },
    [maxSize, acceptedMimeTypes, accept, onError]
  );

  const handleFile = useCallback(
    (file: File) => {
      if (validateFile(file)) {
        onFileSelect(file);
      }
    },
    [validateFile, onFileSelect]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      if (disabled || isLoading) return;

      const file = e.dataTransfer.files[0];
      if (file) {
        handleFile(file);
      }
    },
    [disabled, isLoading, handleFile]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile]
  );

  const handleClick = () => {
    if (!disabled && !isLoading) {
      fileInputRef.current?.click();
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} o`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
  };

  // Show selected file
  if (selectedFile) {
    return (
      <div className="filecard justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <div className="dico">
            <FileText className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="dn truncate">{selectedFile.name}</p>
            <p className="ds">{formatFileSize(selectedFile.size)}</p>
          </div>
        </div>
        {onClear && !isLoading && (
          <Button variant="secondary" size="sm" onClick={onClear}>
            Supprimer
          </Button>
        )}
        {isLoading && <Loader2 className="h-5 w-5 text-prit animate-spin" />}
      </div>
    );
  }

  return (
    <div>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        className={`drop ${disabled || isLoading ? 'opacity-50 cursor-not-allowed' : ''} ${
          isDragging ? 'active' : ''
        }`}
      >
        {isLoading ? (
          <div className="flex flex-col items-center">
            <Loader2 className="h-9 w-9 text-prit animate-spin" />
            <p className="dropt">Traitement en cours...</p>
          </div>
        ) : (
          <>
            <Upload className={`h-9 w-9 mx-auto ${isDragging ? 'text-prit' : 'text-mut2'}`} />
            <p className="dropt">{label}</p>
            <p className="drops">
              ou <b className="text-prit font-semibold">parcourez vos fichiers</b>
            </p>
            {description && <p className="drops mt-1.5">{description}</p>}
          </>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          onChange={handleInputChange}
          className="hidden"
          disabled={disabled || isLoading}
        />
      </div>

      {errorMessage && (
        <div className="alert red mt-3.5">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
}
