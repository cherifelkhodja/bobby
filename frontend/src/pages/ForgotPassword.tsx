import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';

import { authApi } from '../api/auth';
import { getErrorMessage } from '../api/client';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

const forgotPasswordSchema = z.object({
  email: z.string().email('Email invalide'),
});

type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;

export function ForgotPassword() {
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setIsLoading(true);
    try {
      await authApi.forgotPassword(data.email);
      setIsSubmitted(true);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="lgwrap">
        <div className="lgcard text-center">
          <p className="logo text-[22px] mb-2">Bobby</p>
          <h2 className="text-[15px] font-bold text-ink mb-3">Email envoyé !</h2>
          <p className="notec mb-6">
            Si cette adresse email existe dans notre système, vous recevrez un
            lien pour réinitialiser votre mot de passe.
          </p>
          <Link to="/login">
            <Button variant="secondary">Retour à la connexion</Button>
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
          <p className="sub mt-2">Réinitialiser votre mot de passe</p>
        </div>

        <p className="notec mb-3.5">
          Saisissez votre email — nous vous enverrons un lien de
          réinitialisation valide 1 heure.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
          <Input
            label="Email"
            type="email"
            placeholder="votre@email.fr"
            error={errors.email?.message}
            {...register('email')}
          />

          <Button type="submit" className="w-full !mt-4" isLoading={isLoading}>
            Envoyer le lien
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
