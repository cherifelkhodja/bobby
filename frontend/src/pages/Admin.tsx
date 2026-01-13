import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Settings,
  Zap,
  Users,
  Trash2,
  Send,
} from 'lucide-react';
import { toast } from 'sonner';

import { adminApi } from '../api/admin';
import type { User, UserRole, BoondResource } from '../types';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';

type TabType = 'users' | 'invitations' | 'boond';

const ROLE_LABELS: Record<UserRole, string> = {
  user: 'Utilisateur',
  commercial: 'Commercial',
  admin: 'Administrateur',
};

const ROLE_COLORS: Record<UserRole, 'default' | 'primary' | 'success' | 'warning' | 'error'> = {
  user: 'default',
  commercial: 'primary',
  admin: 'warning',
};

export function Admin() {
  const [activeTab, setActiveTab] = useState<TabType>('users');

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Administration</h1>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('users')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'users'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Users className="h-4 w-4 inline-block mr-2" />
            Utilisateurs
          </button>
          <button
            onClick={() => setActiveTab('invitations')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'invitations'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Mail className="h-4 w-4 inline-block mr-2" />
            Invitations
          </button>
          <button
            onClick={() => setActiveTab('boond')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'boond'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Settings className="h-4 w-4 inline-block mr-2" />
            BoondManager
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'users' && <UsersTab />}
      {activeTab === 'invitations' && <InvitationsTab />}
      {activeTab === 'boond' && <BoondTab />}
    </div>
  );
}

// ============================================================================
// Users Tab
// ============================================================================

function UsersTab() {
  const queryClient = useQueryClient();
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => adminApi.getUsers(0, 100),
  });

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

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Gestion des utilisateurs"
          subtitle={`${data?.total || 0} utilisateurs inscrits`}
        />
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Utilisateur
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Statut
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Inscription
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data?.users.map((user) => (
                <tr key={user.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {user.first_name} {user.last_name}
                      </div>
                      <div className="text-sm text-gray-500">{user.email}</div>
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
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(user.created_at).toLocaleDateString('fr-FR')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setSelectedUser(user);
                          setIsRoleModalOpen(true);
                        }}
                      >
                        Changer role
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
                        {user.is_active ? 'Desactiver' : 'Activer'}
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
            <p className="text-sm text-gray-500">
              Modifier le role de{' '}
              <strong>
                {selectedUser.first_name} {selectedUser.last_name}
              </strong>
            </p>
            <div className="space-y-2">
              {(['user', 'commercial', 'admin'] as UserRole[]).map((role) => (
                <button
                  key={role}
                  onClick={() =>
                    changeRoleMutation.mutate({ userId: selectedUser.id, role })
                  }
                  disabled={changeRoleMutation.isPending}
                  className={`w-full p-3 text-left rounded-lg border ${
                    selectedUser.role === role
                      ? 'border-primary bg-primary-light'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-medium">{ROLE_LABELS[role]}</div>
                  <div className="text-sm text-gray-500">
                    {role === 'user' && 'Peut soumettre des cooptations'}
                    {role === 'commercial' && 'Peut gerer ses opportunites et voir les cooptations associees'}
                    {role === 'admin' && 'Acces complet a toutes les fonctionnalites'}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

// ============================================================================
// Invitations Tab
// ============================================================================

function InvitationsTab() {
  const queryClient = useQueryClient();
  const [sendingResourceId, setSendingResourceId] = useState<string | null>(null);

  const { data: invitationsData, isLoading: isLoadingInvitations } = useQuery({
    queryKey: ['admin-invitations'],
    queryFn: () => adminApi.getInvitations(0, 100),
  });

  const { data: boondResourcesData, isLoading: isLoadingResources } = useQuery({
    queryKey: ['boond-resources'],
    queryFn: adminApi.getBoondResources,
  });

  const { data: usersData } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => adminApi.getUsers(0, 500),
  });

  const createMutation = useMutation({
    mutationFn: adminApi.createInvitation,
    onSuccess: () => {
      toast.success('Invitation envoyee');
      queryClient.invalidateQueries({ queryKey: ['admin-invitations'] });
      setSendingResourceId(null);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'envoi');
      setSendingResourceId(null);
    },
  });

  const resendMutation = useMutation({
    mutationFn: adminApi.resendInvitation,
    onSuccess: () => {
      toast.success('Invitation renvoyee');
      queryClient.invalidateQueries({ queryKey: ['admin-invitations'] });
    },
    onError: () => {
      toast.error('Erreur lors du renvoi');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: adminApi.deleteInvitation,
    onSuccess: () => {
      toast.success('Invitation supprimee');
      queryClient.invalidateQueries({ queryKey: ['admin-invitations'] });
    },
    onError: () => {
      toast.error('Erreur lors de la suppression');
    },
  });

  const handleSendInvitation = (resource: BoondResource) => {
    setSendingResourceId(resource.id);
    createMutation.mutate({
      email: resource.email,
      role: resource.suggested_role,
      boond_resource_id: resource.id,
      manager_boond_id: resource.manager_id || undefined,
    });
  };

  // Check if resource already has an account or pending invitation
  const getResourceStatus = (resource: BoondResource) => {
    const hasAccount = usersData?.users.some(
      (u) => u.email.toLowerCase() === resource.email.toLowerCase()
    );
    const hasPendingInvitation = invitationsData?.invitations.some(
      (i) => i.email.toLowerCase() === resource.email.toLowerCase()
    );
    return { hasAccount, hasPendingInvitation };
  };

  if (isLoadingInvitations || isLoadingResources) {
    return <PageSpinner />;
  }

  return (
    <div className="space-y-6">
      {/* Pending Invitations */}
      {invitationsData && invitationsData.invitations.length > 0 && (
        <Card>
          <CardHeader
            title="Invitations en attente"
            subtitle={`${invitationsData.total} invitations`}
          />
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Expiration
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {invitationsData.invitations.map((invitation) => (
                  <tr key={invitation.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {invitation.email}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant={ROLE_COLORS[invitation.role]}>
                        {ROLE_LABELS[invitation.role]}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(invitation.expires_at).toLocaleString('fr-FR')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => resendMutation.mutate(invitation.id)}
                          disabled={resendMutation.isPending}
                        >
                          <Send className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deleteMutation.mutate(invitation.id)}
                          disabled={deleteMutation.isPending}
                        >
                          <Trash2 className="h-4 w-4 text-error" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* BoondManager Resources */}
      <Card>
        <CardHeader
          title="Ressources BoondManager"
          subtitle={`${boondResourcesData?.resources.length || 0} consultants actifs`}
        />

        {boondResourcesData?.resources.length === 0 ? (
          <div className="text-center py-12">
            <Users className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">
              Aucune ressource disponible
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Verifiez la configuration BoondManager.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Consultant
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Agence
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role suggere
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {boondResourcesData?.resources.map((resource) => {
                  const { hasAccount, hasPendingInvitation } = getResourceStatus(resource);
                  const isDisabled = hasAccount || hasPendingInvitation;

                  return (
                    <tr key={resource.id} className={isDisabled ? 'bg-gray-50' : ''}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {resource.first_name} {resource.last_name}
                          </div>
                          <div className="text-sm text-gray-500">{resource.email}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {resource.agency_name || '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {resource.resource_type_name || '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Badge variant={ROLE_COLORS[resource.suggested_role]}>
                          {ROLE_LABELS[resource.suggested_role]}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        {hasAccount ? (
                          <Badge variant="success">Inscrit</Badge>
                        ) : hasPendingInvitation ? (
                          <Badge variant="warning">Invite</Badge>
                        ) : (
                          <Button
                            size="sm"
                            onClick={() => handleSendInvitation(resource)}
                            isLoading={sendingResourceId === resource.id}
                            disabled={createMutation.isPending}
                            leftIcon={<Send className="h-4 w-4" />}
                          >
                            Inviter
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

// ============================================================================
// BoondManager Tab
// ============================================================================

function BoondTab() {
  const queryClient = useQueryClient();
  const [isSyncing, setIsSyncing] = useState(false);
  const [isTesting, setIsTesting] = useState(false);

  const { data: boondStatus, isLoading } = useQuery({
    queryKey: ['boond-status'],
    queryFn: adminApi.getBoondStatus,
    refetchInterval: 30000,
  });

  const testMutation = useMutation({
    mutationFn: adminApi.testConnection,
    onMutate: () => setIsTesting(true),
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message);
      } else {
        toast.error(data.message);
      }
      queryClient.invalidateQueries({ queryKey: ['boond-status'] });
    },
    onError: () => toast.error('Erreur lors du test de connexion'),
    onSettled: () => setIsTesting(false),
  });

  const syncMutation = useMutation({
    mutationFn: adminApi.triggerSync,
    onMutate: () => setIsSyncing(true),
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message);
      } else {
        toast.error(data.message);
      }
      queryClient.invalidateQueries({ queryKey: ['boond-status'] });
      queryClient.invalidateQueries({ queryKey: ['opportunities'] });
    },
    onError: () => toast.error('Erreur lors de la synchronisation'),
    onSettled: () => setIsSyncing(false),
  });

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Jamais';
    return new Date(dateStr).toLocaleString('fr-FR');
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Synchronisation BoondManager"
          subtitle="Statut de la connexion et synchronisation des opportunites"
        />

        <div className="space-y-4">
          {/* Connection Status */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3">
              {boondStatus?.configured ? (
                boondStatus.connected ? (
                  <CheckCircle className="h-6 w-6 text-success" />
                ) : (
                  <XCircle className="h-6 w-6 text-error" />
                )
              ) : (
                <AlertCircle className="h-6 w-6 text-warning" />
              )}
              <div>
                <p className="font-medium text-gray-900">
                  {boondStatus?.configured
                    ? boondStatus.connected
                      ? 'Connecte'
                      : 'Deconnecte'
                    : 'Non configure'}
                </p>
                <p className="text-sm text-gray-500">{boondStatus?.api_url}</p>
              </div>
            </div>
            <div
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                boondStatus?.configured
                  ? boondStatus.connected
                    ? 'bg-success-light text-success'
                    : 'bg-error-light text-error'
                  : 'bg-warning-light text-warning'
              }`}
            >
              {boondStatus?.configured
                ? boondStatus.connected
                  ? 'En ligne'
                  : 'Hors ligne'
                : 'Configuration requise'}
            </div>
          </div>

          {/* Error Message */}
          {boondStatus?.error && (
            <div className="p-4 bg-error-light rounded-lg">
              <p className="text-error text-sm">{boondStatus.error}</p>
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Opportunites synchronisees</p>
              <p className="text-2xl font-bold text-gray-900">
                {boondStatus?.opportunities_count || 0}
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Derniere synchronisation</p>
              <p className="text-lg font-medium text-gray-900">
                {formatDate(boondStatus?.last_sync || null)}
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="pt-4 flex space-x-3">
            <Button
              onClick={() => testMutation.mutate()}
              disabled={!boondStatus?.configured || isTesting}
              isLoading={isTesting}
              variant="outline"
              leftIcon={<Zap className="h-4 w-4" />}
            >
              {isTesting ? 'Test en cours...' : 'Tester la connexion'}
            </Button>
            <Button
              onClick={() => syncMutation.mutate()}
              disabled={!boondStatus?.configured || !boondStatus?.connected || isSyncing}
              isLoading={isSyncing}
              leftIcon={<RefreshCw className="h-4 w-4" />}
            >
              {isSyncing ? 'Synchronisation...' : 'Lancer la synchronisation'}
            </Button>
          </div>
          {!boondStatus?.configured && (
            <p className="mt-2 text-sm text-gray-500">
              Configurez les identifiants BoondManager dans les variables d'environnement
              (BOOND_USERNAME, BOOND_PASSWORD)
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}
