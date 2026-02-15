/**
 * Users management tab component.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { adminApi } from '../../api/admin';
import type { User, UserRole } from '../../types';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { PageSpinner } from '../../components/ui/Spinner';
import { ROLE_LABELS, ROLE_COLORS } from './constants';

export function UsersTab() {
  const queryClient = useQueryClient();
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<User | null>(null);
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [editForm, setEditForm] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    boond_resource_id: '',
    manager_boond_id: '',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => adminApi.getUsers(0, 100),
  });

  // Filter users based on selected filters
  const filteredUsers = data?.users.filter(user => {
    const matchesRole = roleFilter === 'all' || user.role === roleFilter;
    const matchesStatus = statusFilter === 'all' ||
      (statusFilter === 'active' && user.is_active) ||
      (statusFilter === 'inactive' && !user.is_active) ||
      (statusFilter === 'unverified' && !user.is_verified);
    return matchesRole && matchesStatus;
  }) || [];

  const updateUserMutation = useMutation({
    mutationFn: (data: { userId: string; updates: Parameters<typeof adminApi.updateUser>[1] }) =>
      adminApi.updateUser(data.userId, data.updates),
    onSuccess: () => {
      toast.success('Utilisateur mis a jour');
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setIsDetailsModalOpen(false);
    },
    onError: () => {
      toast.error('Erreur lors de la mise a jour');
    },
  });

  const openDetailsModal = (user: User) => {
    setSelectedUser(user);
    setEditForm({
      first_name: user.first_name,
      last_name: user.last_name,
      phone: user.phone || '',
      boond_resource_id: user.boond_resource_id || '',
      manager_boond_id: user.manager_boond_id || '',
    });
    setIsDetailsModalOpen(true);
  };

  const handleSaveUser = () => {
    if (!selectedUser) return;
    updateUserMutation.mutate({
      userId: selectedUser.id,
      updates: {
        first_name: editForm.first_name,
        last_name: editForm.last_name,
        phone: editForm.phone || null,
        boond_resource_id: editForm.boond_resource_id || null,
        manager_boond_id: editForm.manager_boond_id || null,
      },
    });
  };

  const changeRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: UserRole }) =>
      adminApi.changeUserRole(userId, role),
    onSuccess: () => {
      toast.success('Role mis a jour');
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setIsRoleModalOpen(false);
    },
    onError: () => {
      toast.error('Erreur lors de la mise a jour du role');
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ userId, activate }: { userId: string; activate: boolean }) =>
      activate ? adminApi.activateUser(userId) : adminApi.deactivateUser(userId),
    onSuccess: (_, { activate }) => {
      toast.success(activate ? 'Utilisateur active' : 'Utilisateur desactive');
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: () => {
      toast.error('Erreur lors de la modification');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: string) => adminApi.deleteUser(userId),
    onSuccess: () => {
      toast.success('Utilisateur supprime');
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setIsDeleteModalOpen(false);
      setUserToDelete(null);
    },
    onError: () => {
      toast.error('Erreur lors de la suppression');
    },
  });

  const handleDeleteClick = (user: User) => {
    setUserToDelete(user);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = () => {
    if (userToDelete) {
      deleteMutation.mutate(userToDelete.id);
    }
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Gestion des utilisateurs"
          subtitle={`${filteredUsers.length} sur ${data?.total || 0} utilisateurs`}
        />

        {/* Filters */}
        <div className="px-6 pb-4 flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <label htmlFor="role-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Rôle:
            </label>
            <select
              id="role-filter"
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary focus:ring-primary text-sm"
            >
              <option value="all">Tous</option>
              <option value="user">{ROLE_LABELS.user}</option>
              <option value="commercial">{ROLE_LABELS.commercial}</option>
              <option value="rh">{ROLE_LABELS.rh}</option>
              <option value="admin">{ROLE_LABELS.admin}</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="status-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Statut:
            </label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary focus:ring-primary text-sm"
            >
              <option value="all">Tous</option>
              <option value="active">Actif</option>
              <option value="inactive">Inactif</option>
              <option value="unverified">Non vérifié</option>
            </select>
          </div>

          {(roleFilter !== 'all' || statusFilter !== 'all') && (
            <button
              onClick={() => {
                setRoleFilter('all');
                setStatusFilter('all');
              }}
              className="text-sm text-primary dark:text-primary-400 hover:text-primary-dark underline"
            >
              Réinitialiser les filtres
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Utilisateur
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Rôle
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Statut
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Inscription
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {filteredUsers.map((user) => (
                <tr
                  key={user.id}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div
                        className="text-sm font-medium text-gray-900 dark:text-gray-100 cursor-pointer hover:text-primary dark:hover:text-primary-400 hover:underline"
                        onClick={() => openDetailsModal(user)}
                      >
                        {user.first_name} {user.last_name}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">{user.email}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge variant={ROLE_COLORS[user.role]}>
                      {ROLE_LABELS[user.role]}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-2">
                      {user.is_active ? (
                        <Badge variant="success">Actif</Badge>
                      ) : (
                        <Badge variant="error">Inactif</Badge>
                      )}
                      {!user.is_verified && (
                        <Badge variant="warning">Non verifie</Badge>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {new Date(user.created_at).toLocaleDateString('fr-FR')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <div className="inline-flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setSelectedUser(user);
                          setIsRoleModalOpen(true);
                        }}
                      >
                        Rôle
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          toggleActiveMutation.mutate({
                            userId: user.id,
                            activate: !user.is_active,
                          })
                        }
                      >
                        {user.is_active ? 'Désactiver' : 'Activer'}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteClick(user)}
                        className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Change Role Modal */}
      <Modal
        isOpen={isRoleModalOpen}
        onClose={() => setIsRoleModalOpen(false)}
        title="Changer le role"
      >
        {selectedUser && (
          <div className="space-y-4">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Modifier le role de{' '}
              <strong className="text-gray-900 dark:text-gray-100">
                {selectedUser.first_name} {selectedUser.last_name}
              </strong>
            </p>
            <div className="space-y-2">
              {(['user', 'commercial', 'rh', 'admin'] as UserRole[]).map((role) => (
                <button
                  key={role}
                  onClick={() =>
                    changeRoleMutation.mutate({ userId: selectedUser.id, role })
                  }
                  disabled={changeRoleMutation.isPending}
                  className={`w-full p-3 text-left rounded-lg border ${
                    selectedUser.role === role
                      ? 'border-primary bg-primary-light dark:bg-primary-900/30'
                      : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                  }`}
                >
                  <div className="font-medium text-gray-900 dark:text-gray-100">{ROLE_LABELS[role]}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {role === 'user' && 'Peut soumettre des cooptations'}
                    {role === 'commercial' && 'Peut gerer ses opportunites et voir les cooptations associees'}
                    {role === 'rh' && 'Peut gerer les utilisateurs et voir toutes les cooptations'}
                    {role === 'admin' && 'Acces complet a toutes les fonctionnalites'}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </Modal>

      {/* User Details Modal */}
      <Modal
        isOpen={isDetailsModalOpen}
        onClose={() => setIsDetailsModalOpen(false)}
        title="Details de l'utilisateur"
      >
        {selectedUser && (
          <div className="space-y-4">
            {/* Read-only info */}
            <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-500 dark:text-gray-400">Statut</span>
                <div className="flex items-center space-x-2">
                  {selectedUser.is_active ? (
                    <Badge variant="success">Actif</Badge>
                  ) : (
                    <Badge variant="error">Inactif</Badge>
                  )}
                  {!selectedUser.is_verified && (
                    <Badge variant="warning">Non verifie</Badge>
                  )}
                </div>
              </div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-500 dark:text-gray-400">Role</span>
                <Badge variant={ROLE_COLORS[selectedUser.role]}>
                  {ROLE_LABELS[selectedUser.role]}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Inscription</span>
                <span className="text-sm text-gray-900 dark:text-gray-100">
                  {new Date(selectedUser.created_at).toLocaleDateString('fr-FR')}
                </span>
              </div>
            </div>

            {/* Editable fields */}
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Prenom
                  </label>
                  <input
                    type="text"
                    value={editForm.first_name}
                    onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })}
                    className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Nom
                  </label>
                  <input
                    type="text"
                    value={editForm.last_name}
                    onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })}
                    className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary focus:ring-primary"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={selectedUser.email}
                  disabled
                  className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 shadow-sm cursor-not-allowed"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Telephone
                </label>
                <input
                  type="tel"
                  value={editForm.phone}
                  onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                  placeholder="+33 6 12 34 56 78"
                  className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  ID BoondManager
                </label>
                <input
                  type="text"
                  value={editForm.boond_resource_id}
                  onChange={(e) => setEditForm({ ...editForm, boond_resource_id: e.target.value })}
                  placeholder="Non lie a BoondManager"
                  className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary focus:ring-primary"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button
                variant="outline"
                onClick={() => setIsDetailsModalOpen(false)}
              >
                Annuler
              </Button>
              <Button
                onClick={handleSaveUser}
                isLoading={updateUserMutation.isPending}
              >
                Enregistrer
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => {
          setIsDeleteModalOpen(false);
          setUserToDelete(null);
        }}
        title="Supprimer l'utilisateur"
      >
        {userToDelete && (
          <div className="space-y-4">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Etes-vous sur de vouloir supprimer{' '}
              <strong className="text-gray-900 dark:text-gray-100">
                {userToDelete.first_name} {userToDelete.last_name}
              </strong>{' '}
              ?
            </p>
            <p className="text-sm text-red-600 dark:text-red-400">
              Cette action est irreversible.
            </p>

            <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button
                variant="outline"
                onClick={() => {
                  setIsDeleteModalOpen(false);
                  setUserToDelete(null);
                }}
              >
                Annuler
              </Button>
              <Button
                variant="danger"
                onClick={confirmDelete}
                isLoading={deleteMutation.isPending}
              >
                Supprimer
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
