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
}

const TABS: TabConfig[] = [
  { id: 'users', label: 'Utilisateurs' },
  { id: 'templates', label: 'Templates' },
  { id: 'contract-articles', label: 'Contrats' },
  { id: 'contract-companies', label: 'Sociétés' },
  { id: 'stats', label: 'Stats' },
  { id: 'api', label: 'API' },
];

export function Admin() {
  const [activeTab, setActiveTab] = useState<TabType>('users');

  return (
    <div>
      <p className="bc">Admin</p>
      <h1 className="h1">Administration</h1>

      {/* Tabs */}
      <div className="tabs mt-4">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`tab ${activeTab === tab.id ? 'on' : ''}`}
          >
            {tab.label}
          </button>
        ))}
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
