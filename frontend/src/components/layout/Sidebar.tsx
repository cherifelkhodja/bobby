import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Briefcase, Users, FileText, FileSpreadsheet, UserCheck, Sparkles } from 'lucide-react';

import { useAuthStore } from '../../stores/authStore';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Tableau de bord' },
  { to: '/opportunities', icon: Briefcase, label: 'Opportunités' },
  { to: '/my-cooptations', icon: Users, label: 'Mes cooptations' },
];

const commercialItems = [
  { to: '/my-boond-opportunities', icon: Sparkles, label: 'Gestion opportunités' },
];

const toolsItems = [
  { to: '/cv-generator', icon: FileText, label: 'Générateur de CV' },
];

const adminToolsItems = [
  { to: '/quotation-generator', icon: FileSpreadsheet, label: 'Génération Devis Thales' },
];

const hrItems = [
  { to: '/rh', icon: UserCheck, label: 'Gestion des annonces' },
];

export function Sidebar() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';
  const isCommercialOrAdmin = user?.role && ['admin', 'commercial'].includes(user.role);
  const canAccessTools = user?.role && ['admin', 'commercial', 'rh'].includes(user.role);
  const canAccessHR = user?.role && ['admin', 'rh'].includes(user.role);

  return (
    <aside className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 min-h-[calc(100vh-73px)]">
      <nav className="p-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                  : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100'
              }`
            }
          >
            <Icon className="h-5 w-5" />
            <span>{label}</span>
          </NavLink>
        ))}

        {isCommercialOrAdmin && (
          <>
            <div className="pt-4 mt-4 border-t border-gray-200 dark:border-gray-700">
              <p className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                Commercial
              </p>
            </div>
            {commercialItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100'
                  }`
                }
              >
                <Icon className="h-5 w-5" />
                <span>{label}</span>
              </NavLink>
            ))}
          </>
        )}

        {(canAccessTools || isAdmin) && (
          <>
            <div className="pt-4 mt-4 border-t border-gray-200 dark:border-gray-700">
              <p className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                Outils
              </p>
            </div>
            {canAccessTools && toolsItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100'
                  }`
                }
              >
                <Icon className="h-5 w-5" />
                <span>{label}</span>
              </NavLink>
            ))}
            {isAdmin && adminToolsItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100'
                  }`
                }
              >
                <Icon className="h-5 w-5" />
                <span>{label}</span>
              </NavLink>
            ))}
          </>
        )}

        {canAccessHR && (
          <>
            <div className="pt-4 mt-4 border-t border-gray-200 dark:border-gray-700">
              <p className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                RH
              </p>
            </div>
            {hrItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100'
                  }`
                }
              >
                <Icon className="h-5 w-5" />
                <span>{label}</span>
              </NavLink>
            ))}
          </>
        )}

      </nav>
    </aside>
  );
}
