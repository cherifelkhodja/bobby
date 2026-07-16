import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { CheckCircle } from 'lucide-react';

import { authApi } from '../api/auth';
import { getErrorMessage } from '../api/client';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

const resetPasswordSchema = z
  .object({
    password: z
      .string()
      .min(8, 'Le mot de passe doit contenir au moins 8 caractères'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Les mots de passe ne correspondent pas',
    path: ['confirmPassword'],
  });

type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
  });

  const onSubmit = async (data: ResetPasswordFormData) => {
    if (!token) {
      toast.error('Token de réinitialisation manquant');
      return;
    }

    setIsLoading(true);
    try {
      await authApi.resetPassword(token, data.password);
      setIsSuccess(true);
      toast.success('Mot de passe réinitialisé avec succès');
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="lgwrap">
        <div className="lgcard text-center">
          <p className="logo text-[22px] mb-2">Bobby</p>
          <h2 className="text-[15px] font-bold text-redt mb-3">Lien invalide</h2>
          <p className="notec mb-6">
            Le lien de réinitialisation est invalide ou a expiré.
          </p>
          <Link to="/forgot-password">
            <Button>Demander un nouveau lien</Button>
          </Link>
        </div>
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div className="lgwrap">
        <div className="lgcard text-center">
          <CheckCircle className="h-12 w-12 text-grn-fg mx-auto mb-4" />
          <h2 className="text-[15px] font-bold text-ink mb-3">
            Mot de passe réinitialisé !
          </h2>
          <p className="notec mb-6">
            Votre mot de passe a été changé avec succès. Vous pouvez maintenant
            vous connecter avec votre nouveau mot de passe.
          </p>
          <Link to="/login">
            <Button>Se connecter</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="lgwrap">
      <div className="lgcard">
        <div className="text-center mb-[26px]">
          <p className="logo text-[22px]">Bobby</p>
          <p className="sub mt-2">Choisissez un nouveau mot de passe</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
          <Input
            label="Nouveau mot de passe"
            type="password"
            placeholder="••••••••"
            error={errors.password?.message}
            {...register('password')}
          />

          <Input
            label="Confirmer le mot de passe"
            type="password"
            placeholder="••••••••"
            error={errors.confirmPassword?.message}
            {...register('confirmPassword')}
          />

          <Button type="submit" className="w-full !mt-4" isLoading={isLoading}>
            Réinitialiser le mot de passe
          </Button>
        </form>

        <p className="notec text-center mt-5">
          <Link to="/login" className="font-semibold">
            ← Retour à la connexion
          </Link>
        </p>
      </div>
    </div>
  );
}
