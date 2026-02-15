import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';

import { useAuthStore } from '../stores/authStore';
import { usersApi } from '../api/users';
import { getErrorMessage } from '../api/client';
import { Card, CardHeader } from '../components/ui/Card';
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
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Mon profil</h1>

      <div className="space-y-6">
        <Card>
          <CardHeader
            title="Informations personnelles"
            subtitle="Mettez à jour vos informations"
          />
          <form
            onSubmit={profileForm.handleSubmit(onUpdateProfile)}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-4">
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

            <Input label="Email" value={user?.email} disabled />

            <Input
              label="ID BoondManager"
              placeholder="Optionnel"
              helperText="Votre identifiant dans BoondManager"
              {...profileForm.register('boond_resource_id')}
            />

            <div className="pt-2">
              <Button type="submit" isLoading={isUpdating}>
                Enregistrer
              </Button>
            </div>
          </form>
        </Card>

        <Card>
          <CardHeader
            title="Sécurité"
            subtitle="Changez votre mot de passe"
          />
          <form
            onSubmit={passwordForm.handleSubmit(onChangePassword)}
            className="space-y-4"
          >
            <Input
              label="Mot de passe actuel"
              type="password"
              error={passwordForm.formState.errors.current_password?.message}
              {...passwordForm.register('current_password')}
            />

            <Input
              label="Nouveau mot de passe"
              type="password"
              helperText="8 caractères minimum"
              error={passwordForm.formState.errors.new_password?.message}
              {...passwordForm.register('new_password')}
            />

            <Input
              label="Confirmer le nouveau mot de passe"
              type="password"
              error={passwordForm.formState.errors.confirm_password?.message}
              {...passwordForm.register('confirm_password')}
            />

            <div className="pt-2">
              <Button type="submit" isLoading={isChangingPassword}>
                Changer le mot de passe
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
