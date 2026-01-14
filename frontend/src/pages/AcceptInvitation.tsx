import { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { CheckCircle, Loader2, UserPlus, Clock, AlertCircle } from 'lucide-react';

import { invitationsApi } from '../api/invitations';
import { getErrorMessage } from '../api/client';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import type { InvitationValidation } from '../types';

const acceptInvitationSchema = z
  .object({
    first_name: z.string().min(1, 'Prenom requis'),
    last_name: z.string().min(1, 'Nom requis'),
    password: z
      .string()
      .min(8, 'Le mot de passe doit contenir au moins 8 caracteres'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Les mots de passe ne correspondent pas',
    path: ['confirmPassword'],
  });

type AcceptInvitationFormData = z.infer<typeof acceptInvitationSchema>;

const roleLabels: Record<string, string> = {
  user: 'Consultant',
  commercial: 'Commercial',
  rh: 'Ressources Humaines',
  admin: 'Administrateur',
};

export function AcceptInvitation() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');

  const [isLoading, setIsLoading] = useState(false);
  const [isValidating, setIsValidating] = useState(true);
  const [isSuccess, setIsSuccess] = useState(false);
  const [invitation, setInvitation] = useState<InvitationValidation | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AcceptInvitationFormData>({
    resolver: zodResolver(acceptInvitationSchema),
  });

  // Validate the invitation token on mount
  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        setValidationError("Lien d'invitation invalide");
        setIsValidating(false);
        return;
      }

      try {
        const data = await invitationsApi.validateToken(token);
        if (!data.is_valid) {
          setValidationError("Cette invitation n'est plus valide");
        } else {
          setInvitation(data);
        }
      } catch (error) {
        const message = getErrorMessage(error);
        setValidationError(message);
      } finally {
        setIsValidating(false);
      }
    };

    validateToken();
  }, [token]);

  const onSubmit = async (data: AcceptInvitationFormData) => {
    if (!token) {
      toast.error("Token d'invitation manquant");
      return;
    }

    setIsLoading(true);
    try {
      await invitationsApi.acceptInvitation({
        token,
        first_name: data.first_name,
        last_name: data.last_name,
        password: data.password,
      });
      setIsSuccess(true);
      toast.success('Compte cree avec succes !');
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  };

  // Loading state
  if (isValidating) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <Card className="w-full max-w-md text-center">
          <Loader2 className="h-12 w-12 text-primary-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">
            Verification de l'invitation...
          </p>
        </Card>
      </div>
    );
  }

  // Error state
  if (validationError || !invitation) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <Card className="w-full max-w-md text-center">
          <AlertCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-red-600 dark:text-red-400 mb-4">
            Invitation invalide
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            {validationError || "Cette invitation n'est plus valide ou a expire."}
          </p>
          <Link to="/login">
            <Button>Retour a la connexion</Button>
          </Link>
        </Card>
      </div>
    );
  }

  // Success state
  if (isSuccess) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <Card className="w-full max-w-md text-center">
          <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Compte cree !
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            Votre compte a ete cree avec succes. Vous pouvez maintenant vous
            connecter avec votre email et mot de passe.
          </p>
          <Link to="/login">
            <Button>Se connecter</Button>
          </Link>
        </Card>
      </div>
    );
  }

  // Form state
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <div className="text-center mb-8">
          <UserPlus className="h-12 w-12 text-primary-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Rejoignez l'equipe
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Completez votre inscription pour acceder a la plateforme
          </p>
        </div>

        {/* Invitation details */}
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">Email</span>
            <span className="font-medium text-gray-900 dark:text-white">
              {invitation.email}
            </span>
          </div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">Role</span>
            <Badge variant="primary">
              {roleLabels[invitation.role] || invitation.role}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500 dark:text-gray-400">Expire dans</span>
            <span className="text-sm text-gray-600 dark:text-gray-300 flex items-center">
              <Clock className="h-4 w-4 mr-1" />
              {invitation.hours_until_expiry} heures
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Prenom"
              placeholder="Jean"
              error={errors.first_name?.message}
              {...register('first_name')}
            />
            <Input
              label="Nom"
              placeholder="Dupont"
              error={errors.last_name?.message}
              {...register('last_name')}
            />
          </div>

          <Input
            label="Mot de passe"
            type="password"
            placeholder="Minimum 8 caracteres"
            error={errors.password?.message}
            {...register('password')}
          />

          <Input
            label="Confirmer le mot de passe"
            type="password"
            placeholder="Repetez votre mot de passe"
            error={errors.confirmPassword?.message}
            {...register('confirmPassword')}
          />

          <Button type="submit" className="w-full" isLoading={isLoading}>
            Creer mon compte
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
          Deja un compte ?{' '}
          <Link
            to="/login"
            className="text-primary-600 hover:text-primary-700 font-medium"
          >
            Se connecter
          </Link>
        </p>
      </Card>
    </div>
  );
}
