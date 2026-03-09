/**
 * Admin tab for managing contract article templates (AT contract).
 * Features: drag-and-drop reordering, editable content, tag insertion, active/editable toggles.
 */

import { useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  ChevronDown,
  ChevronUp,
  Save,
  Lock,
  Unlock,
  Eye,
  EyeOff,
  GripVertical,
  Tag,
  X,
} from 'lucide-react';
import { toast } from 'sonner';

import { contractArticlesApi, type ArticleTemplate } from '../../api/contracts';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { PageSpinner } from '../../components/ui/Spinner';
import { ContractAnnexesTab } from './ContractAnnexesTab';

// ─── Available template tags ──────────────────────────────────────────────────

interface TagDef {
  tag: string;
  label: string;
}

interface TagCategory {
  category: string;
  tags: TagDef[];
}

const TAG_CATEGORIES: TagCategory[] = [
  {
    category: 'Société émettrice',
    tags: [
      { tag: '{{ issuer_company_name }}', label: 'Nom société' },
      { tag: '{{ issuer_legal_form }}', label: 'Forme juridique' },
      { tag: '{{ issuer_capital }}', label: 'Capital' },
      { tag: '{{ issuer_head_office }}', label: 'Siège social' },
      { tag: '{{ issuer_rcs_city }}', label: 'Ville RCS' },
      { tag: '{{ issuer_rcs_number }}', label: 'N° RCS' },
      { tag: '{{ issuer_representative_name }}', label: 'Représentant' },
      { tag: '{{ issuer_representative_quality }}', label: 'Qualité représentant' },
      { tag: '{{ issuer_signatory_name }}', label: 'Signataire' },
    ],
  },
  {
    category: 'Partenaire / Tiers',
    tags: [
      { tag: '{{ partner_company_name }}', label: 'Nom société' },
      { tag: '{{ partner_legal_form }}', label: 'Forme juridique' },
      { tag: '{{ partner_capital }}', label: 'Capital' },
      { tag: '{{ partner_head_office }}', label: 'Siège social' },
      { tag: '{{ partner_rcs_city }}', label: 'Ville RCS' },
      { tag: '{{ partner_rcs_number }}', label: 'N° RCS' },
      { tag: '{{ partner_representative_name }}', label: 'Représentant' },
      { tag: '{{ partner_representative_title }}', label: 'Titre représentant' },
      { tag: '{{ partner_siren }}', label: 'SIREN' },
      { tag: '{{ partner_siret }}', label: 'SIRET' },
    ],
  },
  {
    category: 'Consultant',
    tags: [
      { tag: '{{ consultant_civility }}', label: 'Civilité' },
      { tag: '{{ consultant_first_name }}', label: 'Prénom' },
      { tag: '{{ consultant_last_name }}', label: 'Nom' },
    ],
  },
  {
    category: 'Contrat',
    tags: [
      { tag: '{{ mission_title }}', label: 'Titre mission' },
      { tag: '{{ start_date }}', label: 'Date début' },
      { tag: '{{ end_date }}', label: 'Date fin' },
      { tag: '{{ daily_rate }}', label: 'TJM (€)' },
      { tag: '{{ payment_terms_display }}', label: 'Délai de paiement' },
      { tag: '{{ invoice_submission_method_display }}', label: 'Remise factures' },
    ],
  },
];

// ─── Tag panel ────────────────────────────────────────────────────────────────

function TagPanel({
  textareaRef,
  onInsert,
}: {
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  onInsert: (tag: string) => void;
}) {
  const insertTag = (tag: string) => {
    const el = textareaRef.current;
    if (!el) {
      onInsert(tag);
      return;
    }
    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? el.value.length;
    const newValue = el.value.slice(0, start) + tag + el.value.slice(end);
    // Trigger React onChange by setting native value and dispatching event
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      HTMLTextAreaElement.prototype,
      'value',
    )?.set;
    nativeInputValueSetter?.call(el, newValue);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    // Restore cursor after inserted tag
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(start + tag.length, start + tag.length);
    });
  };

  return (
    <div className="mt-3 border border-dashed border-teal-200 dark:border-teal-800 rounded-md p-3 bg-teal-50/50 dark:bg-teal-900/20">
      <p className="text-xs font-semibold text-teal-700 dark:text-teal-400 mb-2 flex items-center gap-1.5">
        <Tag className="w-3.5 h-3.5" />
        Balises disponibles — cliquez pour insérer à la position du curseur
      </p>
      <div className="space-y-2">
        {TAG_CATEGORIES.map((cat) => (
          <div key={cat.category}>
            <p className="text-xs text-gray-500 dark:text-gray-400 font-medium mb-1">
              {cat.category}
            </p>
            <div className="flex flex-wrap gap-1">
              {cat.tags.map(({ tag, label }) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => insertTag(tag)}
                  title={tag}
                  className="text-xs px-2 py-0.5 rounded bg-white dark:bg-gray-800 border border-teal-200 dark:border-teal-700 text-teal-700 dark:text-teal-300 hover:bg-teal-100 dark:hover:bg-teal-900/40 transition-colors font-mono"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Sortable article row ─────────────────────────────────────────────────────

function SortableArticleRow({
  article,
  index,
  expanded,
  editingContent,
  onToggleExpand,
  onToggleActive,
  onToggleEditable,
  onContentChange,
  onSaveContent,
  isDirty,
  isPending,
}: {
  article: ArticleTemplate;
  index: number | 'preambule' | null;
  expanded: boolean;
  editingContent: string | undefined;
  onToggleExpand: () => void;
  onToggleActive: () => void;
  onToggleEditable: () => void;
  onContentChange: (value: string) => void;
  onSaveContent: () => void;
  isDirty: boolean;
  isPending: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: article.article_key,
  });

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showTags, setShowTags] = useState(false);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const currentContent = editingContent !== undefined ? editingContent : article.content;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`border rounded-lg overflow-hidden transition-colors ${
        article.is_active
          ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
          : 'border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 opacity-60'
      } ${isDragging ? 'shadow-lg z-10 relative' : ''}`}
    >
      {/* Article header row */}
      <div className="flex items-center gap-2 px-3 py-3">
        {/* Drag handle */}
        <button
          {...attributes}
          {...listeners}
          className="flex-shrink-0 p-1 text-gray-300 dark:text-gray-600 hover:text-gray-500 dark:hover:text-gray-400 cursor-grab active:cursor-grabbing touch-none"
          title="Réordonner"
        >
          <GripVertical className="w-4 h-4" />
        </button>

        {/* Badge : numéro d'article, "P" pour le préambule, ou "—" si inactif */}
        {index === 'preambule' ? (
          <span className="flex-shrink-0 px-2 h-7 rounded-full text-xs font-bold flex items-center justify-center bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400 whitespace-nowrap">
            Préambule
          </span>
        ) : (
          <span
            className={`flex-shrink-0 w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center ${
              index !== null
                ? 'bg-teal-100 dark:bg-teal-900 text-teal-700 dark:text-teal-300'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600'
            }`}
          >
            {index ?? '—'}
          </span>
        )}

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
            <Badge variant="primary">Modifiable</Badge>
          ) : (
            <Badge variant="default">Fixe</Badge>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={onToggleEditable}
            disabled={isPending}
            title={article.is_editable ? 'Rendre fixe' : 'Rendre modifiable'}
            className="p-1.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            {article.is_editable ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
          </button>

          <button
            onClick={onToggleActive}
            disabled={isPending}
            title={article.is_active ? 'Désactiver (exclure du contrat)' : 'Activer'}
            className="p-1.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            {article.is_active ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          </button>

          <button
            onClick={onToggleExpand}
            className="p-1.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded content editor */}
      {expanded && (
        <div className="border-t border-gray-100 dark:border-gray-700 px-4 py-3 bg-gray-50 dark:bg-gray-900/50">
          {article.is_editable ? (
            <>
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Ligne vide = nouveau paragraphe · «&nbsp;-&nbsp;» en début de ligne = puce.
                  Utilisez les balises ci-dessous pour insérer des données dynamiques.
                </p>
                <button
                  type="button"
                  onClick={() => setShowTags((v) => !v)}
                  className="flex items-center gap-1 text-xs text-teal-600 dark:text-teal-400 hover:underline ml-2 flex-shrink-0"
                >
                  {showTags ? (
                    <>
                      <X className="w-3 h-3" /> Masquer balises
                    </>
                  ) : (
                    <>
                      <Tag className="w-3 h-3" /> Insérer une balise
                    </>
                  )}
                </button>
              </div>

              <textarea
                ref={textareaRef}
                className="w-full h-40 px-3 py-2 text-sm font-mono border border-gray-200 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-y focus:outline-none focus:ring-2 focus:ring-teal-500"
                value={currentContent}
                onChange={(e) => onContentChange(e.target.value)}
              />

              {showTags && (
                <TagPanel
                  textareaRef={textareaRef}
                  onInsert={(tag) => {
                    // Fallback: append at end if textarea ref not accessible
                    onContentChange(currentContent + tag);
                  }}
                />
              )}

              <div className="flex justify-end mt-2">
                {isDirty && (
                  <Button size="sm" onClick={onSaveContent} disabled={isPending}>
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
  );
}

// ─── Main tab ─────────────────────────────────────────────────────────────────

export function ContractArticlesTab() {
  const [subTab, setSubTab] = useState<'articles' | 'annexes'>('articles');
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState<Record<string, string>>({});
  // Local order (article_keys) for optimistic DnD
  const [localOrder, setLocalOrder] = useState<string[] | null>(null);

  const { data: articles, isLoading } = useQuery({
    queryKey: ['contract-articles'],
    queryFn: contractArticlesApi.list,
  });

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

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
      setEditingContent((prev) => {
        const next = { ...prev };
        delete next[updated.article_key];
        return next;
      });
      toast.success('Article mis à jour');
    },
    onError: () => toast.error('Erreur lors de la mise à jour'),
  });

  const reorderMutation = useMutation({
    mutationFn: (orderedKeys: string[]) => contractArticlesApi.reorder(orderedKeys),
    onSuccess: (_data, orderedKeys) => {
      // Mise à jour directe du cache sans refetch pour éviter le flash de numéros
      queryClient.setQueryData<ArticleTemplate[]>(['contract-articles'], (old) => {
        if (!old) return old;
        const byKey = new Map(old.map((a) => [a.article_key, a]));
        return orderedKeys
          .map((key, idx) => {
            const a = byKey.get(key);
            return a ? { ...a, article_number: idx + 1 } : null;
          })
          .filter((a): a is ArticleTemplate => a !== null);
      });
      setLocalOrder(null);
    },
    onError: () => {
      toast.error('Erreur lors de la réorganisation');
      setLocalOrder(null);
      queryClient.invalidateQueries({ queryKey: ['contract-articles'] });
    },
  });

  if (isLoading) return <PageSpinner />;

  // Build the displayed list: use localOrder if dragging, otherwise from server
  const serverArticles = articles ?? [];
  const displayedArticles = localOrder
    ? localOrder
        .map((key) => serverArticles.find((a) => a.article_key === key))
        .filter(Boolean as unknown as <T>(x: T | undefined) => x is T)
    : serverArticles;

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const keys = displayedArticles.map((a) => a.article_key);
    const oldIndex = keys.indexOf(active.id as string);
    const newIndex = keys.indexOf(over.id as string);
    const newOrder = arrayMove(keys, oldIndex, newIndex);

    setLocalOrder(newOrder);
    reorderMutation.mutate(newOrder);
  };

  return (
    <div className="space-y-4">
      {/* Sub-tab selector */}
      <Card>
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
              Contrat AT
            </h2>
            <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
              <button
                onClick={() => setSubTab('articles')}
                className={`px-4 py-1.5 text-sm font-medium transition-colors ${
                  subTab === 'articles'
                    ? 'bg-teal-600 text-white'
                    : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                }`}
              >
                Articles
              </button>
              <button
                onClick={() => setSubTab('annexes')}
                className={`px-4 py-1.5 text-sm font-medium transition-colors border-l border-gray-200 dark:border-gray-700 ${
                  subTab === 'annexes'
                    ? 'bg-teal-600 text-white'
                    : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                }`}
              >
                Annexes
              </button>
            </div>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {subTab === 'articles'
              ? 'Gérez les articles du contrat. Glissez pour réordonner. Les articles actifs apparaissent dans le PDF, numérotés séquentiellement.'
              : 'Gérez le contenu des annexes. Les annexes conditionnelles ne sont incluses que si leur condition est remplie lors de la génération.'}
          </p>
        </div>
      </Card>

      {subTab === 'articles' && (
        <>
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext
              items={displayedArticles.map((a) => a.article_key)}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {(() => {
                  // Numérotation séquentielle sur les articles actifs, le préambule est exclu
                  let counter = 0;
                  const activeNumbers = new Map<string, number | 'preambule'>();
                  displayedArticles.forEach((a) => {
                    if (a.article_key === 'preambule') {
                      activeNumbers.set(a.article_key, 'preambule');
                    } else if (a.is_active) {
                      activeNumbers.set(a.article_key, ++counter);
                    }
                  });
                  return displayedArticles.map((article) => (
                    <SortableArticleRow
                      key={article.article_key}
                      article={article}
                      index={activeNumbers.get(article.article_key) ?? null}
                      expanded={expanded === article.article_key}
                      editingContent={editingContent[article.article_key]}
                      onToggleExpand={() =>
                        setExpanded((prev) =>
                          prev === article.article_key ? null : article.article_key,
                        )
                      }
                      onToggleActive={() =>
                        updateMutation.mutate({
                          key: article.article_key,
                          data: { is_active: !article.is_active },
                        })
                      }
                      onToggleEditable={() =>
                        updateMutation.mutate({
                          key: article.article_key,
                          data: { is_editable: !article.is_editable },
                        })
                      }
                      onContentChange={(value) =>
                        setEditingContent((prev) => ({ ...prev, [article.article_key]: value }))
                      }
                      onSaveContent={() => {
                        const newContent = editingContent[article.article_key];
                        if (newContent === undefined || newContent === article.content) return;
                        updateMutation.mutate({ key: article.article_key, data: { content: newContent } });
                      }}
                      isDirty={
                        editingContent[article.article_key] !== undefined &&
                        editingContent[article.article_key] !== article.content
                      }
                      isPending={updateMutation.isPending || reorderMutation.isPending}
                    />
                  ));
                })()}
              </div>
            </SortableContext>
          </DndContext>

          <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
            Les articles sont numérotés séquentiellement dans le PDF selon leur ordre et leur statut
            actif.
          </p>
        </>
      )}

      {subTab === 'annexes' && <ContractAnnexesTab hideHeader />}
    </div>
  );
}
