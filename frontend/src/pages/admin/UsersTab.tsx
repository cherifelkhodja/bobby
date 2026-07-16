/**
 * Users management tab component.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { adminApi } from '../../api/admin';
import type { User, UserRole } from '../../types';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { PageSpinner } from '../../components/ui/Spinner';
import { Input } from '../../components/ui/Input';
import { ROLE_LABELS } from './constants';
import { InvitationsTab } from './InvitationsTab';

/** Chips de rôle v2 : classe `st-*` + libellé court. */
const ROLE_CHIPS: Record<UserRole, { cls: string; label: string }> = {
  admin: { cls: 'st-ind', label: 'Admin' },
  commercial: { cls: 'st-blu', label: 'Commercial' },
  rh: { cls: 'st-grn', label: 'RH' },
  adv: { cls: 'st-amb', label: 'ADV' },
  user: { cls: 'st-sla', label: 'Collaborateur' },
};

function RoleChip({ role }: { role: UserRole }) {
  const chip = ROLE_CHIPS[role];
  return (
    <span className={`st ${chip.cls}`}>
      <span className="dot" />
      {chip.label}
    </span>
  );
}

const GRID_COLS = 'grid-cols-[1.7fr_130px_110px_130px_80px]';

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
    <div className="space-y-8">
      <div>
        {/* Filters */}
        <div className="flex items-center gap-2 flex-wrap mb-3.5">
          <label htmlFor="role-filter" className="sr-only">
            Filtrer par rôle
          </label>
          <select
            id="role-filter"
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">Tous les rôles</option>
            <option value="user">{ROLE_LABELS.user}</option>
            <option value="commercial">{ROLE_LABELS.commercial}</option>
            <option value="rh">{ROLE_LABELS.rh}</option>
            <option value="admin">{ROLE_LABELS.admin}</option>
          </select>

          <label htmlFor="status-filter" className="sr-only">
            Filtrer par statut
          </label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">Tous les statuts</option>
            <option value="active">Actif</option>
            <option value="inactive">Inactif</option>
            <option value="unverified">Non vérifié</option>
          </select>

          {(roleFilter !== 'all' || statusFilter !== 'all') && (
            <button
              type="button"
              onClick={() => {
                setRoleFilter('all');
                setStatusFilter('all');
              }}
              className="text-[12.5px] font-medium text-prit hover:underline"
            >
              Réinitialiser les filtres
            </button>
          )}

          <span className="sort">
            {filteredUsers.length} sur {data?.total || 0} utilisateurs
          </span>
        </div>

        {/* Users table */}
        <div className="tbl">
          <div className={`thead ${GRID_COLS}`}>
            <span>Utilisateur</span>
            <span>Rôle</span>
            <span>Vérifié</span>
            <span>Créé le</span>
            <span className="text-right">Actions</span>
          </div>
          {filteredUsers.map((user) => (
            <div key={user.id} className={`row ${GRID_COLS}`}>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p
                    className="nm truncate cursor-pointer hover:underline"
                    onClick={() => openDetailsModal(user)}
                  >
                    {user.first_name} {user.last_name}
                  </p>
                  {!user.is_active && (
                    <span className="st st-red">
                      <span className="dot" />
                      Inactif
                    </span>
                  )}
                </div>
                <p className="ns truncate">{user.email}</p>
              </div>
              <div>
                <RoleChip role={user.role} />
              </div>
              <div>
                {user.is_verified ? (
                  <span className="st st-grn">
                    <span className="dot" />
                    Oui
                  </span>
                ) : (
                  <span className="st st-amb">
                    <span className="dot" />
                    En attente
                  </span>
                )}
              </div>
              <span className="cell">
                {new Date(user.created_at).toLocaleDateString('fr-FR')}
              </span>
              <div className="text-right">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => openDetailsModal(user)}
                >
                  Modifier
                </Button>
              </div>
            </div>
          ))}
          <div className="tfoot">
            <span>
              {filteredUsers.length} utilisateur{filteredUsers.length > 1 ? 's' : ''}
            </span>
          </div>
        </div>
      </div>

      {/* Change Role Modal */}
      <Modal
        isOpen={isRoleModalOpen}
        onClose={() => setIsRoleModalOpen(false)}
        title="Changer le rôle"
      >
        {selectedUser && (
          <div className="space-y-4">
            <p className="text-[13px] text-mut">
              Modifier le rôle de{' '}
              <strong className="text-ink">
                {selectedUser.first_name} {selectedUser.last_name}
              </strong>
            </p>
            <div className="space-y-2">
              {(['user', 'commercial', 'rh', 'admin'] as UserRole[]).map((role) => (
                <button
                  key={role}
                  type="button"
                  onClick={() =>
                    changeRoleMutation.mutate({ userId: selectedUser.id, role })
                  }
                  disabled={changeRoleMutation.isPending}
                  className={`w-full p-3 text-left rounded-[10px] border transition-colors ${
                    selectedUser.role === role
                      ? 'border-pri bg-pris'
                      : 'border-lin hover:bg-srf2'
                  }`}
                >
                  <div className="text-[13.5px] font-semibold text-ink">{ROLE_LABELS[role]}</div>
                  <div className="text-xs text-mut mt-0.5">
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
        title="Détails de l'utilisateur"
      >
        {selectedUser && (
          <div className="space-y-4">
            {/* Read-only info */}
            <div className="p-3 bg-srf2 border border-lin2 rounded-[10px] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[12.5px] text-mut">Statut</span>
                <div className="flex items-center gap-2">
                  {selectedUser.is_active ? (
                    <span className="st st-grn">
                      <span className="dot" />
                      Actif
                    </span>
                  ) : (
                    <span className="st st-red">
                      <span className="dot" />
                      Inactif
                    </span>
                  )}
                  {!selectedUser.is_verified && (
                    <span className="st st-amb">
                      <span className="dot" />
                      Non vérifié
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[12.5px] text-mut">Rôle</span>
                <RoleChip role={selectedUser.role} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[12.5px] text-mut">Inscription</span>
                <span className="text-[13px] text-ink">
                  {new Date(selectedUser.created_at).toLocaleDateString('fr-FR')}
                </span>
              </div>
            </div>

            {/* Editable fields */}
            <div className="space-y-3.5">
              <div className="f-grid">
                <Input
                  label="Prénom"
                  id="edit-first-name"
                  value={editForm.first_name}
                  onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })}
                />
                <Input
                  label="Nom"
                  id="edit-last-name"
                  value={editForm.last_name}
                  onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })}
                />
              </div>

              <Input label="Email" id="edit-email" type="email" value={selectedUser.email} disabled />

              <Input
                label="Téléphone"
                id="edit-phone"
                type="tel"
                value={editForm.phone}
                onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                placeholder="+33 6 12 34 56 78"
              />

              <Input
                label="ID BoondManager"
                id="edit-boond-id"
                value={editForm.boond_resource_id}
                onChange={(e) => setEditForm({ ...editForm, boond_resource_id: e.target.value })}
                placeholder="Non lie a BoondManager"
              />
            </div>

            {/* Secondary actions */}
            <div className="flex items-center gap-2 flex-wrap pt-1">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setIsDetailsModalOpen(false);
                  setIsRoleModalOpen(true);
                }}
              >
                Changer le rôle
              </Button>
              <Button
                variant="secondary"
                size="sm"
                isLoading={toggleActiveMutation.isPending}
                onClick={() =>
                  toggleActiveMutation.mutate({
                    userId: selectedUser.id,
                    activate: !selectedUser.is_active,
                  })
                }
              >
                {selectedUser.is_active ? 'Désactiver' : 'Activer'}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="!text-redt"
                onClick={() => {
                  setIsDetailsModalOpen(false);
                  handleDeleteClick(selectedUser);
                }}
                leftIcon={<Trash2 className="h-3.5 w-3.5" />}
              >
                Supprimer
              </Button>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-4 border-t border-lin">
              <Button
                variant="secondary"
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
            <p className="text-[13px] text-mut">
              Etes-vous sur de vouloir supprimer{' '}
              <strong className="text-ink">
                {userToDelete.first_name} {userToDelete.last_name}
              </strong>{' '}
              ?
            </p>
            <p className="text-[13px] font-medium text-redt">
              Cette action est irreversible.
            </p>

            <div className="flex justify-end gap-2 pt-4 border-t border-lin">
              <Button
                variant="secondary"
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

      {/* Invitations Section */}
      <InvitationsTab />
    </div>
  );
}
