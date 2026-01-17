/**
 * HR Dashboard page - List opportunities from BoondManager where user is HR manager.
 *
 * Fetches opportunities directly from BoondManager API:
 * - For admin users: Shows ALL opportunities
 * - For RH users: Shows only opportunities where they are HR manager
 */

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  Briefcase,
  Users,
  Plus,
  Eye,
  Search,
  ExternalLink,
} from 'lucide-react';
import { hrApi } from '../api/hr';
import type { OpportunityForHR, JobPostingStatus } from '../types';

const JOB_POSTING_STATUS_BADGES: Record<JobPostingStatus, { label: string; color: string }> = {
  draft: {
    label: 'Brouillon',
    color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
  },
  published: {
    label: 'Publiée',
    color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  },
  closed: {
    label: 'Fermée',
    color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  },
};

// State color mapping for Boond opportunity states
const STATE_COLOR_CLASSES: Record<string, string> = {
  blue: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  green: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  yellow: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  red: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  gray: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
  cyan: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300',
  indigo: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
  pink: 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300',
};

export default function HRDashboard() {
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['hr-opportunities'],
    queryFn: () => hrApi.getOpportunities(),
  });

  // Client-side filtering for instant search feedback
  const filteredItems = useMemo(() => {
    if (!data?.items) return [];
    if (!searchInput) return data.items;

    const searchLower = searchInput.toLowerCase();
    return data.items.filter(
      (opp) =>
        opp.title.toLowerCase().includes(searchLower) ||
        opp.reference.toLowerCase().includes(searchLower) ||
        (opp.client_name?.toLowerCase().includes(searchLower) ?? false)
    );
  }, [data?.items, searchInput]);

  const handleCreatePosting = (opportunity: OpportunityForHR) => {
    navigate(`/rh/annonces/nouvelle/${opportunity.id}`);
  };

  const handleViewPosting = (opportunity: OpportunityForHR) => {
    if (opportunity.job_posting_id) {
      navigate(`/rh/annonces/${opportunity.job_posting_id}`);
    }
  };

  const getStateColorClass = (color: string | null): string => {
    if (!color) return STATE_COLOR_CLASSES.gray;
    return STATE_COLOR_CLASSES[color] || STATE_COLOR_CLASSES.gray;
  };

  if (error) {
    const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-200">
            Erreur lors du chargement des opportunités: {errorMessage}
          </p>
          <p className="text-sm text-red-600 dark:text-red-400 mt-2">
            Vérifiez que votre identifiant BoondManager est configuré dans votre profil.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Gestion des annonces
        </h1>
        <p className="mt-1 text-gray-600 dark:text-gray-400">
          Opportunités BoondManager où vous êtes responsable RH
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Briefcase className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Opportunités
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {data?.total ?? '-'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <ExternalLink className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Annonces publiées
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {data?.items.filter((o) => o.job_posting_status === 'published').length ?? '-'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Users className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Nouvelles candidatures
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {data?.items.reduce((acc, o) => acc + o.new_applications_count, 0) ?? '-'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Rechercher par titre, référence ou client..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Opportunities Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
            <p className="mt-2 text-gray-600 dark:text-gray-400">Chargement des opportunités BoondManager...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-8 text-center">
            <Briefcase className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              {searchInput
                ? 'Aucune opportunité trouvée pour cette recherche.'
                : 'Aucune opportunité disponible.'}
            </p>
            {!searchInput && (
              <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
                Vous devez être responsable RH d'une opportunité dans BoondManager pour la voir ici.
              </p>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-900/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Opportunité
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Client
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      État Boond
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Annonce
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Candidatures
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredItems.map((opportunity) => (
                    <tr
                      key={opportunity.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">
                            {opportunity.title}
                          </p>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {opportunity.reference}
                          </p>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <p className="text-gray-900 dark:text-white">
                          {opportunity.client_name || '-'}
                        </p>
                      </td>
                      <td className="px-6 py-4">
                        {opportunity.state_name ? (
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStateColorClass(
                              opportunity.state_color
                            )}`}
                          >
                            {opportunity.state_name}
                          </span>
                        ) : (
                          <span className="text-gray-500 dark:text-gray-400 text-sm">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {opportunity.has_job_posting && opportunity.job_posting_status ? (
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              JOB_POSTING_STATUS_BADGES[opportunity.job_posting_status].color
                            }`}
                          >
                            {JOB_POSTING_STATUS_BADGES[opportunity.job_posting_status].label}
                          </span>
                        ) : (
                          <span className="text-gray-500 dark:text-gray-400 text-sm">
                            Pas d'annonce
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {opportunity.has_job_posting ? (
                          <div className="flex items-center gap-2">
                            <span className="text-gray-900 dark:text-white">
                              {opportunity.applications_count}
                            </span>
                            {opportunity.new_applications_count > 0 && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
                                +{opportunity.new_applications_count} nouveau
                                {opportunity.new_applications_count > 1 ? 'x' : ''}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-500 dark:text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {opportunity.has_job_posting ? (
                          <button
                            onClick={() => handleViewPosting(opportunity)}
                            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                          >
                            <Eye className="h-4 w-4" />
                            Voir
                          </button>
                        ) : (
                          <button
                            onClick={() => handleCreatePosting(opportunity)}
                            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                          >
                            <Plus className="h-4 w-4" />
                            Créer annonce
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Results count */}
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-700 dark:text-gray-300">
                {filteredItems.length === data?.items.length
                  ? `${data.total} opportunité${data.total > 1 ? 's' : ''}`
                  : `${filteredItems.length} résultat${filteredItems.length > 1 ? 's' : ''} sur ${data?.total ?? 0}`}
              </p>
            </div>
          </>
        )}
      </div>

      {/* Quick Link to All Postings */}
      <div className="mt-6">
        <Link
          to="/rh/annonces"
          className="text-blue-600 dark:text-blue-400 hover:underline text-sm"
        >
          Voir toutes les annonces →
        </Link>
      </div>
    </div>
  );
}
