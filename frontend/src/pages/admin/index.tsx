/**
 * Admin page with tabbed interface.
 *
 * This module provides the main admin dashboard with the following tabs:
 * - Users: User management (list, edit, role change, delete)
 * - Invitations: Invite users via email or from BoondManager
 * - BoondManager: Connection status and synchronization
 * - API: API connections tests (Boond, Gemini)
 */

import { useState } from 'react';
import { Users, Mail, Settings, Plug } from 'lucide-react';

import { UsersTab } from './UsersTab';
import { InvitationsTab } from './InvitationsTab';
import { BoondTab } from './BoondTab';
import { ApiTab } from './ApiTab';

type TabType = 'users' | 'invitations' | 'boond' | 'api';

interface TabConfig {
  id: TabType;
  label: string;
  icon: typeof Users;
}

const TABS: TabConfig[] = [
  { id: 'users', label: 'Utilisateurs', icon: Users },
  { id: 'invitations', label: 'Invitations', icon: Mail },
  { id: 'boond', label: 'BoondManager', icon: Settings },
  { id: 'api', label: 'API', icon: Plug },
];

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
          {TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-primary text-primary dark:text-primary-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <Icon className="h-4 w-4 inline-block mr-2" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'users' && <UsersTab />}
      {activeTab === 'invitations' && <InvitationsTab />}
      {activeTab === 'boond' && <BoondTab />}
      {activeTab === 'api' && <ApiTab />}
    </div>
  );
}

// Re-export tabs for potential direct use
export { UsersTab } from './UsersTab';
export { InvitationsTab } from './InvitationsTab';
export { BoondTab } from './BoondTab';
export { ApiTab } from './ApiTab';
