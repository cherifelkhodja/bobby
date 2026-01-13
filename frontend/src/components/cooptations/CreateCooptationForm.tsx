import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { cooptationsApi } from '../../api/cooptations';
import { getErrorMessage } from '../../api/client';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import type { Opportunity } from '../../types';

const cooptationSchema = z.object({
  candidate_first_name: z.string().min(1, 'Prénom requis'),
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

export function CreateCooptationForm({
  opportunity,
  onSuccess,
  onCancel,
}: CreateCooptationFormProps) {
  const queryClient = useQueryClient();

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
      toast.success('Cooptation soumise avec succès');
      onSuccess();
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const onSubmit = (data: CooptationFormData) => {
    mutation.mutate({
      opportunity_id: opportunity.id,
      ...data,
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="bg-gray-50 rounded-lg p-4 mb-4">
        <p className="text-sm text-gray-600">Opportunité :</p>
        <p className="font-medium text-gray-900">{opportunity.title}</p>
        <p className="text-sm text-gray-500">{opportunity.reference}</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="label">Civilité</label>
          <select className="input" {...register('candidate_civility')}>
            <option value="M">M.</option>
            <option value="Mme">Mme</option>
          </select>
        </div>
        <Input
          label="Prénom"
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
          label="Téléphone"
          placeholder="0612345678"
          error={errors.candidate_phone?.message}
          {...register('candidate_phone')}
        />
      </div>

      <Input
        label="TJM souhaité (€/jour)"
        type="number"
        placeholder="500"
        error={errors.candidate_daily_rate?.message}
        {...register('candidate_daily_rate')}
      />

      <div>
        <label className="label">Note / Commentaire</label>
        <textarea
          className="input min-h-[100px]"
          placeholder="Informations complémentaires sur le candidat..."
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
