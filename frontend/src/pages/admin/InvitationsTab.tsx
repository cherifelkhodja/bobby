/**
 * Invitations management tab component.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Users, Trash2, Send } from 'lucide-react';
import { toast } from 'sonner';

import { adminApi } from '../../api/admin';
import type { UserRole, BoondResource } from '../../types';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { PageSpinner } from '../../components/ui/Spinner';
import { Input } from '../../components/ui/Input';
import { ROLE_LABELS, STATE_NAMES } from './constants';

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

const INVITATIONS_GRID = 'grid-cols-[1.7fr_150px_190px_90px]';
const RESOURCES_GRID = 'grid-cols-[1.7fr_150px_150px_170px_120px]';

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
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast.error(axiosError.response?.data?.detail || 'Erreur lors de l\'envoi');
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
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast.error(axiosError.response?.data?.detail || 'Erreur lors de l\'envoi');
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
    <div className="space-y-8">
      {/* Pending Invitations */}
      {invitationsData && invitationsData.invitations.length > 0 && (
        <div>
          <h3 className="ct">Invitations en attente</h3>
          <p className="cs mb-3">
            {invitationsData.total} invitation{invitationsData.total > 1 ? 's' : ''}
          </p>
          <div className="tbl">
            <div className={`thead ${INVITATIONS_GRID}`}>
              <span>Email</span>
              <span>Rôle</span>
              <span>Expiration</span>
              <span className="text-right">Actions</span>
            </div>
            {invitationsData.invitations.map((invitation) => (
              <div key={invitation.id} className={`row ${INVITATIONS_GRID}`}>
                <p className="nm truncate">{invitation.email}</p>
                <div>
                  <RoleChip role={invitation.role} />
                </div>
                <span className="cell">
                  {new Date(invitation.expires_at).toLocaleString('fr-FR')}
                </span>
                <div className="flex items-center justify-end gap-1">
                  <button
                    type="button"
                    onClick={() => resendMutation.mutate(invitation.id)}
                    disabled={resendMutation.isPending}
                    className="p-1.5 rounded-md text-mut2 hover:text-prit hover:bg-pris transition-colors disabled:opacity-45"
                    title="Renvoyer l'invitation"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteMutation.mutate(invitation.id)}
                    disabled={deleteMutation.isPending}
                    className="p-1.5 rounded-md text-mut2 hover:text-redt hover:bg-red-bg transition-colors disabled:opacity-45"
                    title="Supprimer l'invitation"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Email Invitation Form */}
      <div className="card">
        <h3 className="ct">Invitation par email</h3>
        <p className="cs mb-3.5">Invitez un utilisateur directement par son adresse email</p>
        <form onSubmit={handleEmailInvite} className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[250px]">
            <Input
              label="Email"
              id="invite-email"
              type="email"
              value={emailInviteEmail}
              onChange={(e) => setEmailInviteEmail(e.target.value)}
              placeholder="prenom.nom@exemple.com"
              required
            />
          </div>
          <div className="min-w-[150px]">
            <label htmlFor="invite-role" className="f-lab">
              Rôle
            </label>
            <select
              id="invite-role"
              value={emailInviteRole}
              onChange={(e) => setEmailInviteRole(e.target.value as UserRole)}
              className="f-in !px-2.5"
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
      </div>

      {/* BoondManager Resources */}
      <div>
        <h3 className="ct">Ressources BoondManager</h3>
        <p className="cs mb-3">Invitez les collaborateurs depuis BoondManager</p>

        {/* Filters */}
        <div className="flex items-center gap-2 flex-wrap mb-3.5">
          <label htmlFor="agency-filter" className="sr-only">
            Filtrer par agence
          </label>
          <select
            id="agency-filter"
            value={agencyFilter}
            onChange={(e) => setAgencyFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">Toutes les agences</option>
            {agencies.map((agency) => (
              <option key={agency} value={agency}>
                {agency}
              </option>
            ))}
          </select>

          <label htmlFor="type-filter" className="sr-only">
            Filtrer par type
          </label>
          <select
            id="type-filter"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">Tous les types</option>
            {types.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>

          <label htmlFor="state-filter" className="sr-only">
            Filtrer par état
          </label>
          <select
            id="state-filter"
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">Tous les états</option>
            {states.map((state) => (
              <option key={state} value={state.toString()}>
                {STATE_NAMES[state] || `Etat ${state}`}
              </option>
            ))}
          </select>

          {(agencyFilter !== 'all' || typeFilter !== 'all' || stateFilter !== '1') && (
            <button
              type="button"
              onClick={() => {
                setAgencyFilter('all');
                setTypeFilter('all');
                setStateFilter('1');
              }}
              className="text-[12.5px] font-medium text-prit hover:underline"
            >
              Réinitialiser les filtres
            </button>
          )}

          <span className="sort">
            {filteredResources.length} sur {boondResourcesData?.resources.length || 0} ressources
          </span>
        </div>

        {filteredResources.length === 0 ? (
          <div className="card text-center py-12">
            <Users className="mx-auto h-10 w-10 text-mut2" />
            <p className="dn mt-3">Aucune ressource disponible</p>
            <p className="ds mt-1.5">Verifiez la configuration BoondManager.</p>
          </div>
        ) : (
          <div className="tbl">
            <div className={`thead ${RESOURCES_GRID}`}>
              <span>Consultant</span>
              <span>Agence</span>
              <span>Type</span>
              <span>Rôle</span>
              <span className="text-right">Action</span>
            </div>
            {filteredResources.map((resource) => {
              const { hasAccount, hasPendingInvitation } = getResourceStatus(resource);
              const isDisabled = hasAccount || hasPendingInvitation;
              const currentRole = getRoleForResource(resource);

              return (
                <div
                  key={resource.id}
                  className={`row ${RESOURCES_GRID} ${isDisabled ? 'bg-srf2' : ''}`}
                >
                  <div className="min-w-0">
                    <p
                      className="nm truncate cursor-pointer hover:underline"
                      onClick={() => {
                        setSelectedResource(resource);
                        setIsResourceModalOpen(true);
                      }}
                    >
                      {resource.first_name} {resource.last_name}
                    </p>
                    <p className="ns truncate">{resource.email}</p>
                  </div>
                  <span className="cell truncate">{resource.agency_name || '—'}</span>
                  <span className="cell truncate">{resource.resource_type_name || '—'}</span>
                  <div>
                    {isDisabled ? (
                      <RoleChip role={currentRole} />
                    ) : (
                      <select
                        value={currentRole}
                        onChange={(e) => handleRoleChange(resource.id, e.target.value as UserRole)}
                        className="filter-select w-full !min-w-0"
                        aria-label={`Rôle pour ${resource.first_name} ${resource.last_name}`}
                      >
                        <option value="user">{ROLE_LABELS.user}</option>
                        <option value="commercial">{ROLE_LABELS.commercial}</option>
                        <option value="rh">{ROLE_LABELS.rh}</option>
                        <option value="admin">{ROLE_LABELS.admin}</option>
                      </select>
                    )}
                  </div>
                  <div className="flex justify-end">
                    {hasAccount ? (
                      <span className="st st-grn">
                        <span className="dot" />
                        Inscrit
                      </span>
                    ) : hasPendingInvitation ? (
                      <span className="st st-amb">
                        <span className="dot" />
                        Invité
                      </span>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleSendInvitation(resource)}
                        isLoading={sendingResourceId === resource.id}
                        disabled={createMutation.isPending}
                        leftIcon={<Send className="h-3.5 w-3.5" />}
                      >
                        Inviter
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
            <div className="tfoot">
              <span>
                {filteredResources.length} ressource{filteredResources.length > 1 ? 's' : ''}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Resource Details Modal */}
      <Modal
        isOpen={isResourceModalOpen}
        onClose={() => setIsResourceModalOpen(false)}
        title="Détails de la ressource BoondManager"
      >
        {selectedResource && (
          <div className="space-y-4">
            <div className="text-center pb-4 border-b border-lin">
              <h3 className="text-[15px] font-bold text-ink">
                {selectedResource.first_name} {selectedResource.last_name}
              </h3>
              <p className="text-[12.5px] text-mut mt-1">
                {selectedResource.email}
              </p>
              <div className="mt-2.5 flex justify-center">
                {(() => {
                  const { hasAccount, hasPendingInvitation } = getResourceStatus(selectedResource);
                  if (hasAccount) {
                    return (
                      <span className="st st-grn">
                        <span className="dot" />
                        Inscrit
                      </span>
                    );
                  }
                  if (hasPendingInvitation) {
                    return (
                      <span className="st st-amb">
                        <span className="dot" />
                        Invitation en attente
                      </span>
                    );
                  }
                  return (
                    <span className="st st-sla">
                      <span className="dot" />
                      Non inscrit
                    </span>
                  );
                })()}
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-[12.5px] text-mut">ID BoondManager</span>
                <span className="ref">{selectedResource.id}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-[12.5px] text-mut">Agence</span>
                <span className="text-[13px] font-medium text-ink">
                  {selectedResource.agency_name || '—'}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-[12.5px] text-mut">Type</span>
                <span className="text-[13px] font-medium text-ink">
                  {selectedResource.resource_type_name || '—'}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-[12.5px] text-mut">Téléphone</span>
                <span className="text-[13px] font-medium text-ink">
                  {selectedResource.phone || '—'}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-[12.5px] text-mut">Manager</span>
                <span className="text-[13px] font-medium text-ink">
                  {selectedResource.manager_name || '—'}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-[12.5px] text-mut">Rôle suggéré</span>
                <RoleChip role={selectedResource.suggested_role} />
              </div>
            </div>

            <div className="pt-4 border-t border-lin">
              {(() => {
                const { hasAccount, hasPendingInvitation } = getResourceStatus(selectedResource);
                if (hasAccount || hasPendingInvitation) {
                  return (
                    <Button
                      variant="secondary"
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
