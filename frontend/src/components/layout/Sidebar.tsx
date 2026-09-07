import { NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  LayoutDashboard,
  Briefcase,
  Users,
  FileText,
  FileSpreadsheet,
  UserCheck,
  Sparkles,
  FileSignature,
  ClipboardList,
  ShieldCheck,
  Inbox,
  Shield,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import { useAuthStore } from '../../stores/authStore';
import { contractsApi } from '../../api/contracts';
import { purchaseOrdersApi } from '../../api/purchaseOrders';
import { vigilanceApi } from '../../api/vigilance';

interface NavItemProps {
  to: string;
  icon: LucideIcon;
  label: string;
  count?: number;
  hot?: boolean;
}

function NavItem({ to, icon: Icon, label, count, hot }: NavItemProps) {
  return (
    <NavLink to={to} className={({ isActive }) => `it ${isActive ? 'on' : ''}`}>
      <Icon className="h-4 w-4 shrink-0" />
      <span className="truncate">{label}</span>
      {count !== undefined && count > 0 && (
        <span className={`cnt ${hot ? 'hot' : ''}`}>{count}</span>
      )}
    </NavLink>
  );
}

function GroupHeading({ children, first = false }: { children: React.ReactNode; first?: boolean }) {
  return <div className={`gh ${first ? '!pt-1' : ''}`}>{children}</div>;
}

export function Sidebar() {
  const { user } = useAuthStore();
  const role = user?.role;
  const isAdmin = role === 'admin';
  const isCommercialOrAdmin = !!role && ['admin', 'commercial'].includes(role);
  const canAccessContracts = !!role && ['admin', 'commercial', 'adv'].includes(role);
  const isAdvOrAdmin = !!role && ['admin', 'adv'].includes(role);
  const canAccessCv = !!role && ['admin', 'commercial', 'rh'].includes(role);
  const canAccessHR = !!role && ['admin', 'rh'].includes(role);

  const { data: contractsData } = useQuery({
    queryKey: ['contracts', 'nav-count'],
    queryFn: () => contractsApi.list({ limit: 1 }),
    enabled: canAccessContracts,
    staleTime: 60_000,
    refetchInterval: 120_000,
  });

  const { data: purchaseOrdersData } = useQuery({
    queryKey: ['purchase-orders', 'nav-count'],
    queryFn: () => purchaseOrdersApi.list({ limit: 1, exclude_cancelled: true }),
    enabled: canAccessContracts,
  });

  const { data: complianceData } = useQuery({
    queryKey: ['compliance', 'nav-count'],
    queryFn: () => vigilanceApi.getDashboard(),
    enabled: isAdvOrAdmin,
    staleTime: 60_000,
    refetchInterval: 120_000,
  });

  return (
    <aside className="side min-h-[calc(100vh-56px)]">
      <nav>
        <GroupHeading first>Pilotage</GroupHeading>
        <NavItem to="/dashboard" icon={LayoutDashboard} label="Tableau de bord" />

        <GroupHeading>Cooptation</GroupHeading>
        <NavItem to="/opportunities" icon={Briefcase} label="Opportunités" />
        <NavItem to="/my-cooptations" icon={Users} label="Mes cooptations" />

        {isCommercialOrAdmin && (
          <>
            <GroupHeading>Commercial</GroupHeading>
            <NavItem to="/my-boond-opportunities" icon={Sparkles} label="Gestion opportunités" />
          </>
        )}

        {canAccessContracts && (
          <>
            <GroupHeading>Contrats</GroupHeading>
            <NavItem
              to="/contracts"
              icon={FileSignature}
              label="Fournisseurs"
              count={contractsData?.total}
              hot
            />
            <NavItem
              to="/contracts/bdc"
              icon={ClipboardList}
              label="Bons de commande"
              count={purchaseOrdersData?.total}
            />
            {isAdvOrAdmin && (
              <>
                <NavItem to="/compliance" icon={ShieldCheck} label="Tiers & conformité" />
                <NavItem
                  to="/documents-a-valider"
                  icon={Inbox}
                  label="Documents à valider"
                  count={complianceData?.documents_pending_review}
                />
              </>
            )}
          </>
        )}

        {(canAccessCv || isAdmin || canAccessHR) && (
          <>
            <GroupHeading>Outils</GroupHeading>
            {canAccessCv && <NavItem to="/cv-generator" icon={FileText} label="Générateur de CV" />}
            {isAdmin && (
              <NavItem to="/quotation-generator" icon={FileSpreadsheet} label="Génération Devis Thales" />
            )}
            {canAccessHR && <NavItem to="/rh" icon={UserCheck} label="Gestion des annonces" />}
          </>
        )}

        {isAdmin && (
          <>
            <GroupHeading>Admin</GroupHeading>
            <NavItem to="/admin" icon={Shield} label="Administration" />
          </>
        )}
      </nav>
    </aside>
  );
}
