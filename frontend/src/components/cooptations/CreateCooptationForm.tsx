import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, X, FileText } from 'lucide-react';

import { cooptationsApi } from '../../api/cooptations';
import { getErrorMessage } from '../../api/client';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import type { Opportunity } from '../../types';

const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];
const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

const cooptationSchema = z.object({
  candidate_first_name: z.string().min(1, 'Prenom requis'),
  candidate_last_name: z.string().min(1, 'Nom requis'),
  candidate_email: z.string().email('Email invalide'),
  candidate_civility: z.enum(['M', 'Mme']),
  candidate_phone: z.string().optional(),
  candidate_daily_rate: z.coerce.number().positive().optional(),
  candidate_note: z.string().max(2000).optional(),
});

type CooptationFormData = z.infer<typeof cooptationSchema>;

interface CreateCooptationFormProps {
  opportunity: Opportunity;
  onSuccess: () => void;
  onCancel: () => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

export function CreateCooptationForm({
  opportunity,
  onSuccess,
  onCancel,
}: CreateCooptationFormProps) {
  const queryClient = useQueryClient();
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [cvError, setCvError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CooptationFormData>({
    resolver: zodResolver(cooptationSchema),
    defaultValues: {
      candidate_civility: 'M',
    },
  });

  const mutation = useMutation({
    mutationFn: cooptationsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-cooptations'] });
      queryClient.invalidateQueries({ queryKey: ['my-stats'] });
      queryClient.invalidateQueries({ queryKey: ['cooptations-by-opportunity'] });
      toast.success('Cooptation soumise avec succes');
      onSuccess();
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setCvError(null);

    if (!file) return;

    const hasValidExtension = ALLOWED_EXTENSIONS.some((ext) =>
      file.name.toLowerCase().endsWith(ext)
    );
    if (!ALLOWED_TYPES.includes(file.type) && !hasValidExtension) {
      setCvError('Format non supporte. Utilisez PDF ou DOCX.');
      return;
    }

    if (file.size > MAX_SIZE) {
      setCvError('Fichier trop volumineux. Maximum 10 Mo.');
      return;
    }

    setCvFile(file);
  };

  const removeFile = () => {
    setCvFile(null);
    setCvError(null);
  };

  const onSubmit = (data: CooptationFormData) => {
    if (!cvFile) {
      setCvError('Le CV est obligatoire');
      return;
    }

    mutation.mutate({
      opportunity_id: opportunity.id,
      ...data,
      cv: cvFile,
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 mb-4">
        <p className="text-sm text-gray-600 dark:text-gray-400">Opportunite :</p>
        <p className="font-medium text-gray-900 dark:text-gray-100">{opportunity.title}</p>
        <p className="text-sm text-gray-500 dark:text-gray-400">{opportunity.reference}</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="label">Civilite</label>
          <select className="input" {...register('candidate_civility')}>
            <option value="M">M.</option>
            <option value="Mme">Mme</option>
          </select>
        </div>
        <Input
          label="Prenom"
          error={errors.candidate_first_name?.message}
          {...register('candidate_first_name')}
        />
        <Input
          label="Nom"
          error={errors.candidate_last_name?.message}
          {...register('candidate_last_name')}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Email"
          type="email"
          error={errors.candidate_email?.message}
          {...register('candidate_email')}
        />
        <Input
          label="Telephone"
          placeholder="0612345678"
          error={errors.candidate_phone?.message}
          {...register('candidate_phone')}
        />
      </div>

      <Input
        label="TJM souhaite (EUR/jour)"
        type="number"
        placeholder="500"
        error={errors.candidate_daily_rate?.message}
        {...register('candidate_daily_rate')}
      />

      {/* CV Upload */}
      <div>
        <label className="label">
          CV <span className="text-red-500">*</span>
        </label>
        {cvFile ? (
          <div className="flex items-center gap-3 p-3 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg">
            <FileText className="h-5 w-5 text-primary-600 dark:text-primary-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                {cvFile.name}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {formatFileSize(cvFile.size)}
              </p>
            </div>
            <button
              type="button"
              onClick={removeFile}
              className="p-1 text-gray-400 hover:text-red-500 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:border-primary-400 dark:hover:border-primary-500 transition-colors bg-gray-50 dark:bg-gray-800/30">
            <div className="flex flex-col items-center">
              <Upload className="h-6 w-6 text-gray-400 mb-1" />
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <span className="font-medium text-primary-600 dark:text-primary-400">
                  Cliquez pour choisir
                </span>{' '}
                ou glissez-deposez
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                PDF ou DOCX (max 10 Mo)
              </p>
            </div>
            <input
              type="file"
              className="hidden"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFileChange}
            />
          </label>
        )}
        {cvError && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{cvError}</p>
        )}
      </div>

      <div>
        <label className="label">Note / Commentaire</label>
        <textarea
          className="input min-h-[100px]"
          placeholder="Informations complementaires sur le candidat..."
          {...register('candidate_note')}
        />
        {errors.candidate_note && (
          <p className="mt-1 text-sm text-error">
            {errors.candidate_note.message}
          </p>
        )}
      </div>

      <div className="flex justify-end space-x-3 pt-4">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Annuler
        </Button>
        <Button type="submit" isLoading={mutation.isPending}>
          Soumettre
        </Button>
      </div>
    </form>
  );
}
