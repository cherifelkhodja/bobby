import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { CheckCircle, Loader2, UserPlus, Clock, AlertCircle } from 'lucide-react';

import { invitationsApi } from '../api/invitations';
import { getErrorMessage } from '../api/client';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import type { InvitationValidation } from '../types';

const acceptInvitationSchema = z
  .object({
    first_name: z.string().min(1, 'Prenom requis'),
    last_name: z.string().min(1, 'Nom requis'),
    phone: z.string().optional(),
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
  user: 'Utilisateur',
  commercial: 'Commercial',
  rh: 'Ressources Humaines',
  admin: 'Administrateur',
};

export function AcceptInvitation() {
  const [searchParams] = useSearchParams();
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
    reset,
  } = useForm<AcceptInvitationFormData>({
    resolver: zodResolver(acceptInvitationSchema),
  });

  // Set default values when invitation data is loaded
  useEffect(() => {
    if (invitation) {
      reset({
        first_name: invitation.first_name || '',
        last_name: invitation.last_name || '',
        phone: invitation.phone || '',
        password: '',
        confirmPassword: '',
      });
    }
  }, [invitation, reset]);

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
        phone: data.phone || undefined,
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
      <div className="lgwrap">
        <div className="lgcard text-center">
          <Loader2 className="h-9 w-9 text-prit animate-spin mx-auto mb-4" />
          <p className="notec">Vérification de l'invitation…</p>
        </div>
      </div>
    );
  }

  // Error state
  if (validationError || !invitation) {
    return (
      <div className="lgwrap">
        <div className="lgcard text-center">
          <AlertCircle className="h-12 w-12 text-redt mx-auto mb-4" />
          <h2 className="text-[15px] font-bold text-redt mb-3">
            Invitation invalide
          </h2>
          <p className="notec mb-6">
            {validationError || "Cette invitation n'est plus valide ou a expire."}
          </p>
          <Link to="/login">
            <Button>Retour a la connexion</Button>
          </Link>
        </div>
      </div>
    );
  }

  // Success state
  if (isSuccess) {
    return (
      <div className="lgwrap">
        <div className="lgcard text-center">
          <CheckCircle className="h-12 w-12 text-grn-fg mx-auto mb-4" />
          <h2 className="text-[15px] font-bold text-ink mb-3">
            Compte cree !
          </h2>
          <p className="notec mb-6">
            Votre compte a ete cree avec succes. Vous pouvez maintenant vous
            connecter avec votre email et mot de passe.
          </p>
          <Link to="/login">
            <Button>Se connecter</Button>
          </Link>
        </div>
      </div>
    );
  }

  // Form state
  return (
    <div className="lgwrap">
      <div className="lgcard">
        <div className="text-center mb-[26px]">
          <p className="logo text-[22px]">Bobby</p>
          <UserPlus className="h-8 w-8 text-prit mx-auto mt-4 mb-2" />
          <p className="sub">Completez votre inscription pour acceder a la plateforme</p>
        </div>

        {/* Invitation details */}
        <div className="bg-srf2 border border-lin rounded-[10px] p-4 mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-mut">Email</span>
            <span className="text-[13px] font-semibold text-ink">
              {invitation.email}
            </span>
          </div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-mut">Role</span>
            <Badge variant="primary">
              {roleLabels[invitation.role] || invitation.role}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-mut">Expire dans</span>
            <span className="text-xs text-mut flex items-center">
              <Clock className="h-3.5 w-3.5 mr-1" />
              {invitation.hours_until_expiry} heures
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
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
            label="Telephone (optionnel)"
            type="tel"
            placeholder="+33 6 12 34 56 78"
            error={errors.phone?.message}
            {...register('phone')}
          />

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

          <Button type="submit" className="w-full !mt-4" isLoading={isLoading}>
            Creer mon compte
          </Button>
        </form>

        <p className="notec text-center mt-5">
          Deja un compte ?{' '}
          <Link to="/login" className="font-semibold">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}
