/**
 * Admin tab for managing contract article templates (AT contract).
 * Admins can toggle is_active, is_editable, and edit article content.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronDown, ChevronUp, Save, Lock, Unlock, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';

import { contractArticlesApi, type ArticleTemplate } from '../../api/contracts';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { PageSpinner } from '../../components/ui/Spinner';

export function ContractArticlesTab() {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState<Record<string, string>>({});

  const { data: articles, isLoading } = useQuery({
    queryKey: ['contract-articles'],
    queryFn: contractArticlesApi.list,
  });

  const updateMutation = useMutation({
    mutationFn: ({
      key,
      data,
    }: {
      key: string;
      data: Partial<Pick<ArticleTemplate, 'content' | 'title' | 'is_editable' | 'is_active'>>;
    }) => contractArticlesApi.update(key, data),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['contract-articles'] });
      // Clear local edit state for this article
      setEditingContent((prev) => {
        const next = { ...prev };
        delete next[updated.article_key];
        return next;
      });
      toast.success('Article mis à jour');
    },
    onError: () => toast.error('Erreur lors de la mise à jour'),
  });

  if (isLoading) return <PageSpinner />;

  const handleToggleActive = (article: ArticleTemplate) => {
    updateMutation.mutate({ key: article.article_key, data: { is_active: !article.is_active } });
  };

  const handleToggleEditable = (article: ArticleTemplate) => {
    updateMutation.mutate({
      key: article.article_key,
      data: { is_editable: !article.is_editable },
    });
  };

  const handleSaveContent = (article: ArticleTemplate) => {
    const newContent = editingContent[article.article_key];
    if (newContent === undefined || newContent === article.content) return;
    updateMutation.mutate({ key: article.article_key, data: { content: newContent } });
  };

  const isDirty = (key: string, original: string) =>
    editingContent[key] !== undefined && editingContent[key] !== original;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Articles du contrat AT
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              Gérez les articles du contrat d'assistance technique. Les articles actifs apparaissent
              dans le PDF généré, numérotés séquentiellement.
            </p>
          </div>
        </CardHeader>
      </Card>

      <div className="space-y-2">
        {articles?.map((article) => (
          <div
            key={article.article_key}
            className={`border rounded-lg overflow-hidden transition-colors ${
              article.is_active
                ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                : 'border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 opacity-60'
            }`}
          >
            {/* Article header row */}
            <div className="flex items-center gap-3 px-4 py-3">
              {/* Article number badge */}
              <span className="flex-shrink-0 w-7 h-7 rounded-full bg-teal-100 dark:bg-teal-900 text-teal-700 dark:text-teal-300 text-xs font-bold flex items-center justify-center">
                {article.article_number}
              </span>

              {/* Title */}
              <div className="flex-1 min-w-0">
                <span
                  className={`font-semibold text-sm ${
                    article.is_active
                      ? 'text-gray-900 dark:text-white'
                      : 'text-gray-400 dark:text-gray-500'
                  }`}
                >
                  {article.title}
                </span>
              </div>

              {/* Badges */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {article.is_editable ? (
                  <Badge variant="info">Modifiable</Badge>
                ) : (
                  <Badge variant="default">Fixe</Badge>
                )}
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-1 flex-shrink-0">
                {/* Toggle editable */}
                <button
                  onClick={() => handleToggleEditable(article)}
                  disabled={updateMutation.isPending}
                  title={article.is_editable ? 'Rendre fixe' : 'Rendre modifiable'}
                  className="p-1.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  {article.is_editable ? (
                    <Unlock className="w-4 h-4" />
                  ) : (
                    <Lock className="w-4 h-4" />
                  )}
                </button>

                {/* Toggle active */}
                <button
                  onClick={() => handleToggleActive(article)}
                  disabled={updateMutation.isPending}
                  title={article.is_active ? 'Désactiver (exclure du contrat)' : 'Activer'}
                  className="p-1.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  {article.is_active ? (
                    <Eye className="w-4 h-4" />
                  ) : (
                    <EyeOff className="w-4 h-4" />
                  )}
                </button>

                {/* Expand/collapse */}
                <button
                  onClick={() =>
                    setExpanded((prev) =>
                      prev === article.article_key ? null : article.article_key,
                    )
                  }
                  className="p-1.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  {expanded === article.article_key ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Expanded content editor */}
            {expanded === article.article_key && (
              <div className="border-t border-gray-100 dark:border-gray-700 px-4 py-3 bg-gray-50 dark:bg-gray-900/50">
                {article.is_editable ? (
                  <>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                      Utilisez une ligne vide pour séparer les paragraphes. Commencez une ligne par
                      «&nbsp;-&nbsp;» pour une liste à puces.
                    </p>
                    <textarea
                      className="w-full h-40 px-3 py-2 text-sm font-mono border border-gray-200 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-y focus:outline-none focus:ring-2 focus:ring-teal-500"
                      value={
                        editingContent[article.article_key] !== undefined
                          ? editingContent[article.article_key]
                          : article.content
                      }
                      onChange={(e) =>
                        setEditingContent((prev) => ({
                          ...prev,
                          [article.article_key]: e.target.value,
                        }))
                      }
                    />
                    <div className="flex justify-end mt-2">
                      {isDirty(article.article_key, article.content) && (
                        <Button
                          size="sm"
                          onClick={() => handleSaveContent(article)}
                          disabled={updateMutation.isPending}
                        >
                          <Save className="w-3.5 h-3.5 mr-1.5" />
                          Enregistrer
                        </Button>
                      )}
                    </div>
                  </>
                ) : (
                  <pre className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">
                    {article.content}
                  </pre>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
        Les articles sont numérotés séquentiellement dans le PDF selon leur ordre et leur statut
        actif.
      </p>
    </div>
  );
}
