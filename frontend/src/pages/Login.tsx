import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';

import { authApi } from '../api/auth';
import { useAuthStore } from '../stores/authStore';
import { getErrorMessage } from '../api/client';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

const loginSchema = z.object({
  email: z.string().email('Email invalide'),
  password: z.string().min(1, 'Mot de passe requis'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export function Login() {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true);
    try {
      const response = await authApi.login(data);
      setAuth(response.user, {
        access_token: response.access_token,
        refresh_token: response.refresh_token,
        token_type: response.token_type,
      });
      toast.success('Connexion réussie');
      navigate('/dashboard');
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="lgwrap">
      <div className="lgcard">
        <div className="text-center mb-[26px]">
          <p className="logo text-[22px]">Bobby</p>
          <p className="sub mt-2">Connectez-vous à votre compte</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
          <Input
            label="Email"
            type="email"
            placeholder="votre@email.fr"
            error={errors.email?.message}
            {...register('email')}
          />

          <Input
            label="Mot de passe"
            type="password"
            placeholder="••••••••"
            error={errors.password?.message}
            {...register('password')}
          />

          <div className="flex items-center justify-between">
            <Link to="/forgot-password" className="text-[12.5px]">
              Mot de passe oublié ?
            </Link>
          </div>

          <Button type="submit" className="w-full !mt-4" isLoading={isLoading}>
            Se connecter
          </Button>
        </form>

        <p className="notec text-center mt-5">
          Pas encore de compte ?{' '}
          <Link to="/register" className="font-semibold">
            S'inscrire
          </Link>
        </p>
      </div>
    </div>
  );
}
