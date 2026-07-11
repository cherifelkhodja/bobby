import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';

import { useAuthStore } from '../stores/authStore';
import { usersApi } from '../api/users';
import { getErrorMessage } from '../api/client';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

const profileSchema = z.object({
  first_name: z.string().min(1, 'Prénom requis'),
  last_name: z.string().min(1, 'Nom requis'),
  boond_resource_id: z.string().optional(),
});

const passwordSchema = z
  .object({
    current_password: z.string().min(1, 'Mot de passe actuel requis'),
    new_password: z.string().min(8, '8 caractères minimum'),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: 'Les mots de passe ne correspondent pas',
    path: ['confirm_password'],
  });

type ProfileFormData = z.infer<typeof profileSchema>;
type PasswordFormData = z.infer<typeof passwordSchema>;

export function Profile() {
  const { user, updateUser } = useAuthStore();
  const [isUpdating, setIsUpdating] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const profileForm = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
      boond_resource_id: user?.boond_resource_id || '',
    },
  });

  const passwordForm = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
  });

  const onUpdateProfile = async (data: ProfileFormData) => {
    setIsUpdating(true);
    try {
      const updatedUser = await usersApi.updateMe({
        first_name: data.first_name,
        last_name: data.last_name,
        boond_resource_id: data.boond_resource_id || undefined,
      });
      updateUser(updatedUser);
      toast.success('Profil mis à jour');
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsUpdating(false);
    }
  };

  const onChangePassword = async (data: PasswordFormData) => {
    setIsChangingPassword(true);
    try {
      await usersApi.changePassword({
        current_password: data.current_password,
        new_password: data.new_password,
      });
      toast.success('Mot de passe modifié');
      passwordForm.reset();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsChangingPassword(false);
    }
  };

  return (
    <div className="max-w-[680px]">
      <p className="bc">Compte</p>
      <h1 className="h1">Mon profil</h1>

      <div className="card mt-[18px]">
        <h3 className="ct">Informations personnelles</h3>
        <p className="cs mb-3.5">Mettez à jour vos informations</p>
        <form onSubmit={profileForm.handleSubmit(onUpdateProfile)}>
          <div className="f-grid">
            <Input
              label="Prénom"
              error={profileForm.formState.errors.first_name?.message}
              {...profileForm.register('first_name')}
            />
            <Input
              label="Nom"
              error={profileForm.formState.errors.last_name?.message}
              {...profileForm.register('last_name')}
            />
          </div>

          <div className="mt-3.5">
            <Input label="Email" value={user?.email} disabled />
          </div>

          <div className="mt-3.5">
            <Input
              label="ID Ressource BoondManager"
              placeholder="Optionnel"
              helperText="Votre identifiant dans BoondManager"
              {...profileForm.register('boond_resource_id')}
            />
          </div>

          <Button type="submit" isLoading={isUpdating} className="mt-4">
            Enregistrer
          </Button>
        </form>
      </div>

      <div className="card mt-4">
        <h3 className="ct">Sécurité</h3>
        <p className="cs mb-3.5">Changez votre mot de passe</p>
        <form onSubmit={passwordForm.handleSubmit(onChangePassword)}>
          <Input
            label="Mot de passe actuel"
            type="password"
            error={passwordForm.formState.errors.current_password?.message}
            {...passwordForm.register('current_password')}
          />

          <div className="mt-3.5">
            <Input
              label="Nouveau mot de passe"
              type="password"
              helperText="8 caractères minimum"
              error={passwordForm.formState.errors.new_password?.message}
              {...passwordForm.register('new_password')}
            />
          </div>

          <div className="mt-3.5">
            <Input
              label="Confirmer le nouveau mot de passe"
              type="password"
              error={passwordForm.formState.errors.confirm_password?.message}
              {...passwordForm.register('confirm_password')}
            />
          </div>

          <Button type="submit" isLoading={isChangingPassword} className="mt-4">
            Changer le mot de passe
          </Button>
        </form>
      </div>
    </div>
  );
}
