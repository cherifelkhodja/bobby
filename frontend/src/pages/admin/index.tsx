/**
 * Admin page with tabbed interface.
 *
 * This module provides the main admin dashboard with the following tabs:
 * - Users: User management + Invitations
 * - Templates: Quotation template management
 * - Sociétés: Contract companies + Charters
 * - Stats: CV transformation statistics
 * - API: API connections tests (Boond, Gemini)
 */

import { useState } from 'react';
import { Users, FileText, Plug, BarChart3, ScrollText, Building2 } from 'lucide-react';

import { UsersTab } from './UsersTab';
import { TemplatesTab } from './TemplatesTab';
import { StatsTab } from './StatsTab';
import { ApiTab } from './ApiTab';
import { ContractArticlesTab } from './ContractArticlesTab';
import { ContractCompaniesTab } from './ContractCompaniesTab';

type TabType = 'users' | 'templates' | 'stats' | 'api' | 'contract-articles' | 'contract-companies';

interface TabConfig {
  id: TabType;
  label: string;
  icon: typeof Users;
}

const TABS: TabConfig[] = [
  { id: 'users', label: 'Utilisateurs', icon: Users },
  { id: 'templates', label: 'Templates', icon: FileText },
  { id: 'contract-articles', label: 'Contrats', icon: ScrollText },
  { id: 'contract-companies', label: 'Sociétés', icon: Building2 },
  { id: 'stats', label: 'Stats', icon: BarChart3 },
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
      {activeTab === 'templates' && <TemplatesTab />}
      {activeTab === 'contract-articles' && <ContractArticlesTab />}
      {activeTab === 'contract-companies' && <ContractCompaniesTab />}
      {activeTab === 'stats' && <StatsTab />}
      {activeTab === 'api' && <ApiTab />}
    </div>
  );
}

// Re-export tabs for potential direct use
export { UsersTab } from './UsersTab';
export { TemplatesTab } from './TemplatesTab';
export { ContractArticlesTab } from './ContractArticlesTab';
export { ContractAnnexesTab } from './ContractAnnexesTab';
export { StatsTab } from './StatsTab';
export { ApiTab } from './ApiTab';
