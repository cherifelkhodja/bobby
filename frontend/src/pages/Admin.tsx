import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Settings,
  Zap,
  Users,
  Mail,
  Trash2,
  Send,
  FileText,
  BarChart3,
  Upload,
} from 'lucide-react';
import { toast } from 'sonner';

import { adminApi } from '../api/admin';
import { cvTransformerApi } from '../api/cvTransformer';
import type { User, UserRole, BoondResource, CvTemplate } from '../types';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';

type TabType = 'users' | 'invitations' | 'boond' | 'templates' | 'stats';

const ROLE_LABELS: Record<UserRole, string> = {
  user: 'Utilisateur',
  commercial: 'Commercial',
  rh: 'RH',
  admin: 'Administrateur',
};

const ROLE_COLORS: Record<UserRole, 'default' | 'primary' | 'success' | 'warning' | 'error'> = {
  user: 'default',
  commercial: 'primary',
  rh: 'success',
  admin: 'warning',
};

export function Admin() {
  const [activeTab, setActiveTab] = useState<TabType>('users');

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Administration</h1>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('users')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'users'
                ? 'border-primary text-primary dark:text-primary-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
            }`}
          >
            <Users className="h-4 w-4 inline-block mr-2" />
            Utilisateurs
          </button>
          <button
            onClick={() => setActiveTab('invitations')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'invitations'
                ? 'border-primary text-primary dark:text-primary-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
            }`}
          >
            <Mail className="h-4 w-4 inline-block mr-2" />
            Invitations
          </button>
          <button
            onClick={() => setActiveTab('boond')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'boond'
                ? 'border-primary text-primary dark:text-primary-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
            }`}
          >
            <Settings className="h-4 w-4 inline-block mr-2" />
            BoondManager
          </button>
          <button
            onClick={() => setActiveTab('templates')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'templates'
                ? 'border-primary text-primary dark:text-primary-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
            }`}
          >
            <FileText className="h-4 w-4 inline-block mr-2" />
            Templates CV
          </button>
          <button
            onClick={() => setActiveTab('stats')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'stats'
                ? 'border-primary text-primary dark:text-primary-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
            }`}
          >
            <BarChart3 className="h-4 w-4 inline-block mr-2" />
            Statistiques CV
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'users' && <UsersTab />}
      {activeTab === 'invitations' && <InvitationsTab />}
      {activeTab === 'boond' && <BoondTab />}
      {activeTab === 'templates' && <TemplatesTab />}
      {activeTab === 'stats' && <StatsTab />}
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
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Utilisateur
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Statut
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Inscription
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {data?.users.map((user) => (
                <tr key={user.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
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
    </div>
  );
}

// ============================================================================
// Invitations Tab
// ============================================================================

function InvitationsTab() {
  const queryClient = useQueryClient();
  const [sendingResourceId, setSendingResourceId] = useState<string | null>(null);
  const [agencyFilter, setAgencyFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [selectedRoles, setSelectedRoles] = useState<Record<string, UserRole>>({});

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

  // Extract unique agencies and types for filter options
  const agencies = [...new Set(boondResourcesData?.resources.map(r => r.agency_name).filter((v): v is string => Boolean(v)) || [])].sort();
  const types = [...new Set(boondResourcesData?.resources.map(r => r.resource_type_name).filter((v): v is string => Boolean(v)) || [])].sort();

  // Filter resources based on selected filters
  const filteredResources = boondResourcesData?.resources.filter(resource => {
    const matchesAgency = agencyFilter === 'all' || resource.agency_name === agencyFilter;
    const matchesType = typeFilter === 'all' || resource.resource_type_name === typeFilter;
    return matchesAgency && matchesType;
  }) || [];

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

  // Get the role for a resource (selected or suggested)
  const getRoleForResource = (resource: BoondResource): UserRole => {
    return selectedRoles[resource.id] || resource.suggested_role;
  };

  const handleRoleChange = (resourceId: string, role: UserRole) => {
    setSelectedRoles(prev => ({ ...prev, [resourceId]: role }));
  };

  const handleSendInvitation = (resource: BoondResource) => {
    setSendingResourceId(resource.id);
    const role = getRoleForResource(resource);
    createMutation.mutate({
      email: resource.email,
      role: role,
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
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Expiration
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {invitationsData.invitations.map((invitation) => (
                  <tr key={invitation.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {invitation.email}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant={ROLE_COLORS[invitation.role]}>
                        {ROLE_LABELS[invitation.role]}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
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
          subtitle={`${filteredResources.length} sur ${boondResourcesData?.resources.length || 0} ressources`}
        />

        {/* Filters */}
        <div className="px-6 pb-4 flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <label htmlFor="agency-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Agence:
            </label>
            <select
              id="agency-filter"
              value={agencyFilter}
              onChange={(e) => setAgencyFilter(e.target.value)}
              className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary focus:ring-primary text-sm"
            >
              <option value="all">Toutes</option>
              {agencies.map((agency) => (
                <option key={agency} value={agency}>
                  {agency}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="type-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Type:
            </label>
            <select
              id="type-filter"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary focus:ring-primary text-sm"
            >
              <option value="all">Tous</option>
              {types.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          {(agencyFilter !== 'all' || typeFilter !== 'all') && (
            <button
              onClick={() => {
                setAgencyFilter('all');
                setTypeFilter('all');
              }}
              className="text-sm text-primary dark:text-primary-400 hover:text-primary-dark underline"
            >
              Réinitialiser les filtres
            </button>
          )}
        </div>

        {filteredResources.length === 0 ? (
          <div className="text-center py-12">
            <Users className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
              Aucune ressource disponible
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Verifiez la configuration BoondManager.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Consultant
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Agence
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Rôle
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {filteredResources.map((resource) => {
                  const { hasAccount, hasPendingInvitation } = getResourceStatus(resource);
                  const isDisabled = hasAccount || hasPendingInvitation;
                  const currentRole = getRoleForResource(resource);

                  return (
                    <tr key={resource.id} className={isDisabled ? 'bg-gray-50 dark:bg-gray-900/50' : ''}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {resource.first_name} {resource.last_name}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">{resource.email}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 dark:text-gray-100">
                          {resource.agency_name || '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 dark:text-gray-100">
                          {resource.resource_type_name || '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {isDisabled ? (
                          <Badge variant={ROLE_COLORS[currentRole]}>
                            {ROLE_LABELS[currentRole]}
                          </Badge>
                        ) : (
                          <select
                            value={currentRole}
                            onChange={(e) => handleRoleChange(resource.id, e.target.value as UserRole)}
                            className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary focus:ring-primary text-sm"
                          >
                            <option value="user">{ROLE_LABELS.user}</option>
                            <option value="commercial">{ROLE_LABELS.commercial}</option>
                            <option value="rh">{ROLE_LABELS.rh}</option>
                            <option value="admin">{ROLE_LABELS.admin}</option>
                          </select>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        {hasAccount ? (
                          <Badge variant="success">Inscrit</Badge>
                        ) : hasPendingInvitation ? (
                          <Badge variant="warning">Invité</Badge>
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
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
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
                <p className="font-medium text-gray-900 dark:text-gray-100">
                  {boondStatus?.configured
                    ? boondStatus.connected
                      ? 'Connecte'
                      : 'Deconnecte'
                    : 'Non configure'}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">{boondStatus?.api_url}</p>
              </div>
            </div>
            <div
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                boondStatus?.configured
                  ? boondStatus.connected
                    ? 'bg-success-light text-success dark:bg-success/20'
                    : 'bg-error-light text-error dark:bg-error/20'
                  : 'bg-warning-light text-warning dark:bg-warning/20'
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
            <div className="p-4 bg-error-light dark:bg-error/20 rounded-lg">
              <p className="text-error text-sm">{boondStatus.error}</p>
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <p className="text-sm text-gray-500 dark:text-gray-400">Opportunites synchronisees</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {boondStatus?.opportunities_count || 0}
              </p>
            </div>
            <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <p className="text-sm text-gray-500 dark:text-gray-400">Derniere synchronisation</p>
              <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
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
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              Configurez les identifiants BoondManager dans les variables d'environnement
              (BOOND_USERNAME, BOOND_PASSWORD)
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}

// ============================================================================
// Templates Tab
// ============================================================================

const PREDEFINED_TEMPLATES = [
  { name: 'gemini', displayName: 'Template Gemini', description: 'Format standard Gemini Consulting' },
  { name: 'craftmania', displayName: 'Template Craftmania', description: 'Format standard Craftmania' },
];

function TemplatesTab() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadingTemplate, setUploadingTemplate] = useState<string | null>(null);

  const { data: templatesData, isLoading } = useQuery({
    queryKey: ['cv-templates'],
    queryFn: cvTransformerApi.getTemplates,
  });

  const uploadMutation = useMutation({
    mutationFn: async ({ name, file, displayName, description }: {
      name: string;
      file: File;
      displayName: string;
      description?: string;
    }) => {
      return cvTransformerApi.uploadTemplate(name, file, displayName, description);
    },
    onSuccess: () => {
      toast.success('Template mis à jour');
      queryClient.invalidateQueries({ queryKey: ['cv-templates'] });
      setUploadingTemplate(null);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'upload');
      setUploadingTemplate(null);
    },
  });

  const handleFileSelect = (templateName: string, displayName: string, description: string) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.docx';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        setUploadingTemplate(templateName);
        uploadMutation.mutate({ name: templateName, file, displayName, description });
      }
    };
    input.click();
  };

  // Get existing template data by name
  const getTemplateData = (name: string): CvTemplate | undefined => {
    return templatesData?.templates.find(t => t.name === name);
  };

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Gestion des templates CV"
          subtitle="Uploadez ou mettez à jour les templates Word pour la transformation de CV"
        />

        <div className="space-y-4">
          {PREDEFINED_TEMPLATES.map((template) => {
            const existingTemplate = getTemplateData(template.name);
            const isUploading = uploadingTemplate === template.name;

            return (
              <div
                key={template.name}
                className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg"
              >
                <div className="flex items-center space-x-4">
                  <div className={`p-3 rounded-lg ${existingTemplate ? 'bg-primary-100 dark:bg-primary-900/30' : 'bg-gray-200 dark:bg-gray-700'}`}>
                    <FileText className={`h-6 w-6 ${existingTemplate ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400'}`} />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">{template.displayName}</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{template.description}</p>
                    {existingTemplate && (
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                        Mis à jour le {new Date(existingTemplate.updated_at).toLocaleDateString('fr-FR')}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  {existingTemplate ? (
                    <Badge variant="success">Configuré</Badge>
                  ) : (
                    <Badge variant="warning">Non configuré</Badge>
                  )}
                  <Button
                    variant={existingTemplate ? 'outline' : 'primary'}
                    size="sm"
                    onClick={() => handleFileSelect(template.name, template.displayName, template.description)}
                    isLoading={isUploading}
                    leftIcon={<Upload className="h-4 w-4" />}
                  >
                    {existingTemplate ? 'Remplacer' : 'Uploader'}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <p className="text-sm text-blue-700 dark:text-blue-400">
            <strong>Format requis :</strong> Les templates doivent être au format .docx et utiliser
            les variables Jinja2 (ex: {'{{ profil.titre_cible }}'}, {'{% for exp in experiences %}'}).
          </p>
        </div>
      </Card>
    </div>
  );
}

// ============================================================================
// Stats Tab
// ============================================================================

function StatsTab() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['cv-transformation-stats'],
    queryFn: cvTransformerApi.getStats,
  });

  if (isLoading) {
    return <PageSpinner />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Statistiques de transformation CV"
          subtitle="Nombre de CVs transformés par utilisateur"
        />

        {/* Total */}
        <div className="mb-6 p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
          <div className="flex items-center">
            <BarChart3 className="h-8 w-8 text-primary-600 dark:text-primary-400 mr-4" />
            <div>
              <p className="text-sm text-primary-600 dark:text-primary-400">Total des transformations</p>
              <p className="text-3xl font-bold text-primary-700 dark:text-primary-300">{stats?.total || 0}</p>
            </div>
          </div>
        </div>

        {/* Per user stats */}
        {stats?.by_user && stats.by_user.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Utilisateur
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    CVs transformés
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {stats.by_user.map((userStat) => (
                  <tr key={userStat.user_id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {userStat.user_name}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {userStat.user_email}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                        {userStat.count}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <BarChart3 className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
              Aucune transformation
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Les statistiques apparaîtront ici après les premières transformations.
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
