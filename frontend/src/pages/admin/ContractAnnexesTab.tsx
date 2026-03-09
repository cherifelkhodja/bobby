/**
 * Admin tab for managing contract annex templates (AT contract).
 * Features: editable content with tag insertion, active/inactive toggle.
 * Annexes order is fixed (defined by annexe_number in DB).
 */

import { useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Save,
  Eye,
  EyeOff,
  Tag,
  X,
  ChevronDown,
  ChevronUp,
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

// ─── Annex row ────────────────────────────────────────────────────────────────

function AnnexRow({
  annexe,
  index,
  expanded,
  editingContent,
  onToggleExpand,
  onToggleActive,
  onContentChange,
  onSaveContent,
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
  isDirty: boolean;
  isPending: boolean;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showTags, setShowTags] = useState(false);

  const currentContent = editingContent !== undefined ? editingContent : annexe.content;

  return (
    <div
      className={`border rounded-lg overflow-hidden transition-colors ${
        annexe.is_active
          ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
          : 'border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 opacity-60'
      }`}
    >
      {/* Header row */}
      <div className="flex items-center gap-2 px-3 py-3">
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
            <Badge variant="warning">
              Conditionnelle
            </Badge>
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
        </div>
      </div>

      {/* Expanded content editor */}
      {expanded && (
        <div className="border-t border-gray-100 dark:border-gray-700 px-4 py-3 bg-gray-50 dark:bg-gray-900/50">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Ligne vide = nouveau paragraphe · «&nbsp;-&nbsp;» en début de ligne = puce ·
              {' '}«&nbsp;|&nbsp;» = tableau. Utilisez les balises pour les données dynamiques.
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

// ─── Main tab ─────────────────────────────────────────────────────────────────

export function ContractAnnexesTab() {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState<Record<string, string>>({});

  const { data: annexes, isLoading } = useQuery({
    queryKey: ['contract-annexes'],
    queryFn: contractAnnexesApi.list,
  });

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

  if (isLoading) return <PageSpinner />;

  const displayedAnnexes = annexes ?? [];

  // Sequential numbering for active annexes only
  let counter = 0;
  const activeNumbers = new Map<string, number>();
  displayedAnnexes.forEach((a) => {
    if (a.is_active) activeNumbers.set(a.annexe_key, ++counter);
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title="Annexes du contrat AT"
          subtitle="Gérez le contenu des annexes du contrat d'assistance technique. Les annexes conditionnelles ne sont incluses que si leur condition est remplie lors de la génération."
        />
      </Card>

      <div className="space-y-2">
        {displayedAnnexes.map((annexe) => (
          <AnnexRow
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
            isDirty={
              editingContent[annexe.annexe_key] !== undefined &&
              editingContent[annexe.annexe_key] !== annexe.content
            }
            isPending={updateMutation.isPending}
          />
        ))}
      </div>

      <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
        Les annexes conditionnelles apparaissent uniquement si leur champ de condition est renseigné
        lors de la configuration du contrat.
      </p>
    </div>
  );
}
