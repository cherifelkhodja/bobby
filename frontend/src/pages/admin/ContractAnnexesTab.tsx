/**
 * Admin tab for managing contract annex templates (AT contract).
 * Features: drag-and-drop reordering, editable content, tag insertion,
 *           active/inactive toggle, delete.
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
  Save,
  Eye,
  EyeOff,
  Tag,
  X,
  ChevronDown,
  ChevronUp,
  GripVertical,
  Trash2,
  Plus,
} from 'lucide-react';
import { toast } from 'sonner';

import { contractAnnexesApi, type AnnexTemplate } from '../../api/contracts';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { PageSpinner } from '../../components/ui/Spinner';

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
      { tag: '{{ issuer_signatory_name }}', label: 'Signataire' },
    ],
  },
  {
    category: 'Partenaire / Tiers',
    tags: [
      { tag: '{{ partner_company_name }}', label: 'Nom société' },
      { tag: '{{ partner_legal_form }}', label: 'Forme juridique' },
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
    category: 'Mission',
    tags: [
      { tag: '{{ mission_title }}', label: 'Titre mission' },
      { tag: '{{ start_date }}', label: 'Date début' },
      { tag: '{{ end_date }}', label: 'Date fin' },
      { tag: '{{ daily_rate }}', label: 'TJM (€)' },
      { tag: '{{ client_name }}', label: 'Client final' },
    ],
  },
  {
    category: 'Conditions',
    tags: [
      { tag: '{{ tacit_renewal_months }}', label: 'Mois reconduction' },
      { tag: '{{ special_conditions }}', label: 'Conditions spéciales' },
      { tag: '{{ payment_terms_display }}', label: 'Délai de paiement' },
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
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      HTMLTextAreaElement.prototype,
      'value',
    )?.set;
    nativeInputValueSetter?.call(el, newValue);
    el.dispatchEvent(new Event('input', { bubbles: true }));
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

// ─── Sortable annex row ───────────────────────────────────────────────────────

function SortableAnnexRow({
  annexe,
  index,
  expanded,
  editingContent,
  onToggleExpand,
  onToggleActive,
  onContentChange,
  onSaveContent,
  onDelete,
  isDirty,
  isPending,
}: {
  annexe: AnnexTemplate;
  index: number;
  expanded: boolean;
  editingContent: string | undefined;
  onToggleExpand: () => void;
  onToggleActive: () => void;
  onContentChange: (value: string) => void;
  onSaveContent: () => void;
  onDelete: () => void;
  isDirty: boolean;
  isPending: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: annexe.annexe_key,
  });

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showTags, setShowTags] = useState(false);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const currentContent = editingContent !== undefined ? editingContent : annexe.content;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`border rounded-lg overflow-hidden transition-colors ${
        annexe.is_active
          ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
          : 'border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 opacity-60'
      } ${isDragging ? 'shadow-lg z-10 relative' : ''}`}
    >
      {/* Header row */}
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

        {/* Number badge */}
        <span
          className={`flex-shrink-0 w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center ${
            annexe.is_active
              ? 'bg-violet-100 dark:bg-violet-900 text-violet-700 dark:text-violet-300'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600'
          }`}
        >
          {index}
        </span>

        {/* Title */}
        <div className="flex-1 min-w-0">
          <span
            className={`font-semibold text-sm ${
              annexe.is_active
                ? 'text-gray-900 dark:text-white'
                : 'text-gray-400 dark:text-gray-500'
            }`}
          >
            {annexe.title}
          </span>
        </div>

        {/* Badges */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {annexe.is_conditional && (
            <Badge variant="warning">Conditionnelle</Badge>
          )}
          {annexe.is_conditional && annexe.condition_field && (
            <span className="text-xs text-gray-400 dark:text-gray-500 font-mono">
              si {annexe.condition_field}
            </span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={onToggleActive}
            disabled={isPending}
            title={annexe.is_active ? 'Désactiver (exclure du contrat)' : 'Activer'}
            className="p-1.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            {annexe.is_active ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          </button>

          <button
            onClick={onToggleExpand}
            className="p-1.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          <button
            onClick={() => {
              if (confirm(`Supprimer définitivement l'annexe "${annexe.title}" ?`)) {
                onDelete();
              }
            }}
            disabled={isPending}
            title="Supprimer définitivement"
            className="p-1.5 rounded text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Expanded content editor */}
      {expanded && (
        <div className="border-t border-gray-100 dark:border-gray-700 px-4 py-3 bg-gray-50 dark:bg-gray-900/50">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Ligne vide = nouveau paragraphe · «&nbsp;-&nbsp;» puce ·
              {' '}«&nbsp;|&nbsp;» tableau · «&nbsp;##&nbsp;Titre» sous-section.
              Utilisez les balises pour les données dynamiques.
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
            className="w-full h-44 px-3 py-2 text-sm font-mono border border-gray-200 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-y focus:outline-none focus:ring-2 focus:ring-teal-500"
            value={currentContent}
            onChange={(e) => onContentChange(e.target.value)}
          />

          {showTags && (
            <TagPanel
              textareaRef={textareaRef}
              onInsert={(tag) => onContentChange(currentContent + tag)}
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
        </div>
      )}
    </div>
  );
}

// ─── Create annex modal ────────────────────────────────────────────────────────

function generateKey(title: string): string {
  return title
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')
    .slice(0, 50);
}

function CreateAnnexModal({
  onClose,
  onCreate,
  isPending,
}: {
  onClose: () => void;
  onCreate: (data: { annexe_key: string; title: string; content: string }) => void;
  isPending: boolean;
}) {
  const [title, setTitle] = useState('');
  const [key, setKey] = useState('');
  const [keyTouched, setKeyTouched] = useState(false);
  const [content, setContent] = useState('');

  const handleTitleChange = (v: string) => {
    setTitle(v);
    if (!keyTouched) setKey(generateKey(v));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg mx-4 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Nouvelle annexe</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Titre</label>
            <input
              className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
              value={title}
              onChange={(e) => handleTitleChange(e.target.value)}
              placeholder="Ex : Conditions spéciales"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Clé unique <span className="text-gray-400 font-normal">(identifiant technique)</span>
            </label>
            <input
              className="w-full px-3 py-2 text-sm font-mono border border-gray-200 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
              value={key}
              onChange={(e) => { setKey(e.target.value); setKeyTouched(true); }}
              placeholder="Ex : conditions_speciales"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Contenu <span className="text-gray-400 font-normal">(optionnel, modifiable ensuite)</span>
            </label>
            <textarea
              className="w-full h-28 px-3 py-2 text-sm font-mono border border-gray-200 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-y focus:outline-none focus:ring-2 focus:ring-teal-500"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Rédigez le contenu de l'annexe..."
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" size="sm" onClick={onClose}>Annuler</Button>
          <Button
            size="sm"
            onClick={() => onCreate({ annexe_key: key, title, content })}
            disabled={!title.trim() || !key.trim() || isPending}
          >
            <Plus className="w-3.5 h-3.5 mr-1.5" />
            Créer
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Main tab ─────────────────────────────────────────────────────────────────

export function ContractAnnexesTab({ hideHeader = false }: { hideHeader?: boolean }) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState<Record<string, string>>({});
  const [localOrder, setLocalOrder] = useState<string[] | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const { data: annexes, isLoading } = useQuery({
    queryKey: ['contract-annexes'],
    queryFn: contractAnnexesApi.list,
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
      data: Partial<Pick<AnnexTemplate, 'content' | 'title' | 'is_active'>>;
    }) => contractAnnexesApi.update(key, data),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['contract-annexes'] });
      setEditingContent((prev) => {
        const next = { ...prev };
        delete next[updated.annexe_key];
        return next;
      });
      toast.success('Annexe mise à jour');
    },
    onError: () => toast.error('Erreur lors de la mise à jour'),
  });

  const deleteMutation = useMutation({
    mutationFn: (key: string) => contractAnnexesApi.delete(key),
    onSuccess: (_data, key) => {
      queryClient.setQueryData<AnnexTemplate[]>(['contract-annexes'], (old) =>
        old ? old.filter((a) => a.annexe_key !== key) : old,
      );
      toast.success('Annexe supprimée');
    },
    onError: () => toast.error('Erreur lors de la suppression'),
  });

  const createMutation = useMutation({
    mutationFn: (data: { annexe_key: string; title: string; content: string }) =>
      contractAnnexesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-annexes'] });
      setShowCreateModal(false);
      toast.success('Annexe créée');
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg ?? 'Erreur lors de la création');
    },
  });

  const reorderMutation = useMutation({
    mutationFn: (orderedKeys: string[]) => contractAnnexesApi.reorder(orderedKeys),
    onSuccess: (_data, orderedKeys) => {
      queryClient.setQueryData<AnnexTemplate[]>(['contract-annexes'], (old) => {
        if (!old) return old;
        const byKey = new Map(old.map((a) => [a.annexe_key, a]));
        return orderedKeys
          .map((key, idx) => {
            const a = byKey.get(key);
            return a ? { ...a, annexe_number: idx + 1 } : null;
          })
          .filter((a): a is AnnexTemplate => a !== null);
      });
      setLocalOrder(null);
    },
    onError: () => {
      toast.error('Erreur lors de la réorganisation');
      setLocalOrder(null);
      queryClient.invalidateQueries({ queryKey: ['contract-annexes'] });
    },
  });

  if (isLoading) return <PageSpinner />;

  const serverAnnexes = annexes ?? [];
  const displayedAnnexes = localOrder
    ? localOrder
        .map((key) => serverAnnexes.find((a) => a.annexe_key === key))
        .filter(Boolean as unknown as <T>(x: T | undefined) => x is T)
    : serverAnnexes;

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const keys = displayedAnnexes.map((a) => a.annexe_key);
    const oldIndex = keys.indexOf(active.id as string);
    const newIndex = keys.indexOf(over.id as string);
    const newOrder = arrayMove(keys, oldIndex, newIndex);

    setLocalOrder(newOrder);
    reorderMutation.mutate(newOrder);
  };

  let counter = 0;
  const activeNumbers = new Map<string, number>();
  displayedAnnexes.forEach((a) => {
    if (a.is_active) activeNumbers.set(a.annexe_key, ++counter);
  });

  return (
    <div className="space-y-4">
      {showCreateModal && (
        <CreateAnnexModal
          onClose={() => setShowCreateModal(false)}
          onCreate={(data) => createMutation.mutate(data)}
          isPending={createMutation.isPending}
        />
      )}

      {!hideHeader && (
        <Card>
          <CardHeader
            title="Annexes du contrat AT"
            subtitle="Gérez le contenu des annexes du contrat d'assistance technique. Les annexes conditionnelles ne sont incluses que si leur condition est remplie lors de la génération."
          />
        </Card>
      )}

      <div className="flex justify-end">
        <Button size="sm" onClick={() => setShowCreateModal(true)}>
          <Plus className="w-3.5 h-3.5 mr-1.5" />
          Nouvelle annexe
        </Button>
      </div>

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext
          items={displayedAnnexes.map((a) => a.annexe_key)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-2">
            {displayedAnnexes.map((annexe) => (
              <SortableAnnexRow
                key={annexe.annexe_key}
                annexe={annexe}
                index={activeNumbers.get(annexe.annexe_key) ?? annexe.annexe_number}
                expanded={expanded === annexe.annexe_key}
                editingContent={editingContent[annexe.annexe_key]}
                onToggleExpand={() =>
                  setExpanded((prev) =>
                    prev === annexe.annexe_key ? null : annexe.annexe_key,
                  )
                }
                onToggleActive={() =>
                  updateMutation.mutate({
                    key: annexe.annexe_key,
                    data: { is_active: !annexe.is_active },
                  })
                }
                onContentChange={(value) =>
                  setEditingContent((prev) => ({ ...prev, [annexe.annexe_key]: value }))
                }
                onSaveContent={() => {
                  const newContent = editingContent[annexe.annexe_key];
                  if (newContent === undefined || newContent === annexe.content) return;
                  updateMutation.mutate({ key: annexe.annexe_key, data: { content: newContent } });
                }}
                onDelete={() => deleteMutation.mutate(annexe.annexe_key)}
                isDirty={
                  editingContent[annexe.annexe_key] !== undefined &&
                  editingContent[annexe.annexe_key] !== annexe.content
                }
                isPending={
                  updateMutation.isPending ||
                  reorderMutation.isPending ||
                  deleteMutation.isPending
                }
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
        Les annexes conditionnelles apparaissent uniquement si leur champ de condition est renseigné
        lors de la configuration du contrat.
      </p>
    </div>
  );
}
