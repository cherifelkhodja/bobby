/**
 * FileDropzone - Reusable drag-and-drop file upload component
 *
 * Provides a consistent file upload experience across the application.
 */

import { useCallback, useRef, useState } from 'react';
import { Upload, FileText, X, AlertCircle, Loader2 } from 'lucide-react';
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
      <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div className="flex items-center min-w-0">
          <FileText className="h-10 w-10 text-primary-500 flex-shrink-0" />
          <div className="ml-4 min-w-0">
            <p className="font-medium text-gray-900 dark:text-gray-100 truncate">
              {selectedFile.name}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {formatFileSize(selectedFile.size)}
            </p>
          </div>
        </div>
        {onClear && !isLoading && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClear}
            leftIcon={<X className="h-4 w-4" />}
          >
            Supprimer
          </Button>
        )}
        {isLoading && <Loader2 className="h-5 w-5 text-primary-500 animate-spin" />}
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
        className={`
          border-2 border-dashed rounded-lg p-8 text-center transition-colors
          ${disabled || isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          ${
            isDragging
              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
              : 'border-gray-300 dark:border-gray-600 hover:border-primary-400 dark:hover:border-primary-500'
          }
        `}
      >
        {isLoading ? (
          <div className="flex flex-col items-center">
            <Loader2 className="h-12 w-12 text-primary-500 animate-spin" />
            <p className="mt-4 text-gray-600 dark:text-gray-400">
              Traitement en cours...
            </p>
          </div>
        ) : (
          <>
            <Upload
              className={`h-12 w-12 mx-auto ${
                isDragging ? 'text-primary-500' : 'text-gray-400'
              }`}
            />
            <p className="text-gray-600 dark:text-gray-400 mt-4">{label}</p>
            <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">
              ou{' '}
              <span className="text-primary-600 dark:text-primary-400 font-medium">
                parcourez vos fichiers
              </span>
            </p>
            {description && (
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
                {description}
              </p>
            )}
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
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center text-red-700 dark:text-red-400">
          <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
          <span className="text-sm">{errorMessage}</span>
        </div>
      )}
    </div>
  );
}
