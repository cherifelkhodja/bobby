/**
 * Invitations management tab component.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Users, Trash2, Send } from 'lucide-react';
import { toast } from 'sonner';

import { adminApi } from '../../api/admin';
import type { UserRole, BoondResource } from '../../types';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { PageSpinner } from '../../components/ui/Spinner';
import { ROLE_LABELS, ROLE_COLORS, STATE_NAMES } from './constants';

export function InvitationsTab() {
  const queryClient = useQueryClient();
  const [sendingResourceId, setSendingResourceId] = useState<string | null>(null);
  const [agencyFilter, setAgencyFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [stateFilter, setStateFilter] = useState<string>('1');
  const [selectedRoles, setSelectedRoles] = useState<Record<string, UserRole>>({});
  const [selectedResource, setSelectedResource] = useState<BoondResource | null>(null);
  const [isResourceModalOpen, setIsResourceModalOpen] = useState(false);
  const [emailInviteEmail, setEmailInviteEmail] = useState('');
  const [emailInviteRole, setEmailInviteRole] = useState<UserRole>('user');
  const [isSendingEmailInvite, setIsSendingEmailInvite] = useState(false);

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

  const agencies = [...new Set(boondResourcesData?.resources.map(r => r.agency_name).filter((v): v is string => Boolean(v)) || [])].sort();
  const types = [...new Set(boondResourcesData?.resources.map(r => r.resource_type_name).filter((v): v is string => Boolean(v)) || [])].sort();
  const states = [...new Set(boondResourcesData?.resources.map(r => r.state).filter((v): v is number => v !== null) || [])].sort((a, b) => a - b);

  const filteredResources = boondResourcesData?.resources.filter(resource => {
    const matchesAgency = agencyFilter === 'all' || resource.agency_name === agencyFilter;
    const matchesType = typeFilter === 'all' || resource.resource_type_name === typeFilter;
    const matchesState = stateFilter === 'all' || resource.state === parseInt(stateFilter);
    return matchesAgency && matchesType && matchesState;
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

  const handleEmailInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailInviteEmail.trim()) {
      toast.error('Email requis');
      return;
    }
    setIsSendingEmailInvite(true);
    try {
      await adminApi.createInvitation({
        email: emailInviteEmail.trim(),
        role: emailInviteRole,
      });
      toast.success('Invitation envoyee');
      setEmailInviteEmail('');
      setEmailInviteRole('user');
      queryClient.invalidateQueries({ queryKey: ['admin-invitations'] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'envoi');
    } finally {
      setIsSendingEmailInvite(false);
    }
  };

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
      phone: resource.phone || undefined,
      first_name: resource.first_name,
      last_name: resource.last_name,
    });
  };

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

      {/* Email Invitation Form */}
      <Card>
        <CardHeader
          title="Invitation par email"
          subtitle="Invitez un utilisateur directement par son adresse email"
        />
        <form onSubmit={handleEmailInvite} className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[250px]">
            <label htmlFor="invite-email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Email
            </label>
            <input
              id="invite-email"
              type="email"
              value={emailInviteEmail}
              onChange={(e) => setEmailInviteEmail(e.target.value)}
              placeholder="prenom.nom@exemple.com"
              className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary focus:ring-primary"
              required
            />
          </div>
          <div className="min-w-[150px]">
            <label htmlFor="invite-role" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Role
            </label>
            <select
              id="invite-role"
              value={emailInviteRole}
              onChange={(e) => setEmailInviteRole(e.target.value as UserRole)}
              className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary focus:ring-primary"
            >
              <option value="user">{ROLE_LABELS.user}</option>
              <option value="commercial">{ROLE_LABELS.commercial}</option>
              <option value="rh">{ROLE_LABELS.rh}</option>
              <option value="admin">{ROLE_LABELS.admin}</option>
            </select>
          </div>
          <Button
            type="submit"
            isLoading={isSendingEmailInvite}
            leftIcon={<Send className="h-4 w-4" />}
          >
            Envoyer l'invitation
          </Button>
        </form>
      </Card>

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

          <div className="flex items-center gap-2">
            <label htmlFor="state-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Etat:
            </label>
            <select
              id="state-filter"
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary focus:ring-primary text-sm"
            >
              <option value="all">Tous</option>
              {states.map((state) => (
                <option key={state} value={state.toString()}>
                  {STATE_NAMES[state] || `Etat ${state}`}
                </option>
              ))}
            </select>
          </div>

          {(agencyFilter !== 'all' || typeFilter !== 'all' || stateFilter !== '1') && (
            <button
              onClick={() => {
                setAgencyFilter('all');
                setTypeFilter('all');
                setStateFilter('1');
              }}
              className="text-sm text-primary dark:text-primary-400 hover:text-primary-dark underline"
            >
              Reinitialiser les filtres
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
                          <div
                            className="text-sm font-medium text-gray-900 dark:text-gray-100 cursor-pointer hover:text-primary dark:hover:text-primary-400 hover:underline"
                            onClick={() => {
                              setSelectedResource(resource);
                              setIsResourceModalOpen(true);
                            }}
                          >
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

      {/* Resource Details Modal */}
      <Modal
        isOpen={isResourceModalOpen}
        onClose={() => setIsResourceModalOpen(false)}
        title="Details de la ressource BoondManager"
      >
        {selectedResource && (
          <div className="space-y-4">
            <div className="text-center pb-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {selectedResource.first_name} {selectedResource.last_name}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {selectedResource.email}
              </p>
              <div className="mt-2">
                {(() => {
                  const { hasAccount, hasPendingInvitation } = getResourceStatus(selectedResource);
                  if (hasAccount) return <Badge variant="success">Inscrit</Badge>;
                  if (hasPendingInvitation) return <Badge variant="warning">Invitation en attente</Badge>;
                  return <Badge variant="default">Non inscrit</Badge>;
                })()}
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500 dark:text-gray-400">ID Boond</span>
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {selectedResource.id}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500 dark:text-gray-400">Agence</span>
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {selectedResource.agency_name || '-'}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500 dark:text-gray-400">Type</span>
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {selectedResource.resource_type_name || '-'}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500 dark:text-gray-400">Telephone</span>
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {selectedResource.phone || '-'}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500 dark:text-gray-400">Manager</span>
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {selectedResource.manager_name || '-'}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500 dark:text-gray-400">Role suggere</span>
                <Badge variant={ROLE_COLORS[selectedResource.suggested_role]}>
                  {ROLE_LABELS[selectedResource.suggested_role]}
                </Badge>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              {(() => {
                const { hasAccount, hasPendingInvitation } = getResourceStatus(selectedResource);
                if (hasAccount || hasPendingInvitation) {
                  return (
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => setIsResourceModalOpen(false)}
                    >
                      Fermer
                    </Button>
                  );
                }
                return (
                  <Button
                    className="w-full"
                    onClick={() => {
                      handleSendInvitation(selectedResource);
                      setIsResourceModalOpen(false);
                    }}
                    isLoading={sendingResourceId === selectedResource.id}
                    leftIcon={<Send className="h-4 w-4" />}
                  >
                    Envoyer une invitation
                  </Button>
                );
              })()}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
