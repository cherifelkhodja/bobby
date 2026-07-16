/**
 * Quotation Generator page for Thales quotations.
 *
 * This page allows admins to:
 * 1. Upload a CSV file with quotation data
 * 2. Preview and validate quotations
 * 3. Start async generation (BoondManager + PDF)
 * 4. Monitor progress
 * 5. Download generated ZIP
 */

import { useState, useCallback, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  FileSpreadsheet,
  AlertCircle,
  CheckCircle,
  Download,
  Play,
  Trash2,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';

import { quotationGeneratorApi, type PreviewBatchResponse, type BatchProgressResponse, type QuotationPreviewItem } from '../api/quotationGenerator';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { getErrorMessage } from '../api/client';

type Step = 'upload' | 'preview' | 'generating' | 'complete';

// Colonnes des tables (mêmes valeurs sur thead et row)
const PREVIEW_GRID =
  'grid-cols-[36px_1.3fr_1.3fr_110px_85px_55px_100px_120px_50px]';
const COMPLETE_GRID = 'grid-cols-[130px_1.4fr_1.2fr_170px_110px]';

export function QuotationGenerator() {
  const [step, setStep] = useState<Step>('upload');
  const [batchId, setBatchId] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<PreviewBatchResponse | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: quotationGeneratorApi.previewBatch,
    onSuccess: (data) => {
      setPreviewData(data);
      setBatchId(data.batch_id);
      setStep('preview');
      toast.success(`${data.total_quotations} devis analysés`);
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error, 'Erreur lors de l\'analyse du CSV'));
    },
  });

  // Start generation mutation
  const generateMutation = useMutation({
    mutationFn: () => quotationGeneratorApi.startGeneration(batchId!),
    onSuccess: () => {
      setStep('generating');
      toast.success('Génération démarrée');
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error, 'Erreur lors du démarrage de la génération'));
    },
  });

  // Progress polling
  const { data: progressData } = useQuery({
    queryKey: ['batch-progress', batchId],
    queryFn: () => quotationGeneratorApi.getBatchProgress(batchId!),
    enabled: step === 'generating' && !!batchId,
    refetchInterval: (data) => {
      if (data?.state?.data?.is_complete) {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
  });

  // Check if generation is complete
  useEffect(() => {
    if (progressData?.is_complete && step === 'generating') {
      setStep('complete');
      if (progressData.has_errors) {
        toast.warning('Génération terminée avec des erreurs');
      } else {
        toast.success('Génération terminée avec succès');
      }
    }
  }, [progressData, step]);

  // File handling
  const handleFile = useCallback((file: File) => {
    if (!file.name.endsWith('.csv')) {
      toast.error('Le fichier doit être un CSV');
      return;
    }
    uploadMutation.mutate(file);
  }, [uploadMutation]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileSelect = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.csv';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        handleFile(file);
      }
    };
    input.click();
  }, [handleFile]);

  // Reset to start
  const handleReset = () => {
    setStep('upload');
    setBatchId(null);
    setPreviewData(null);
  };

  return (
    <div className="max-w-[900px]">
      <p className="bc">Outils / Génération Devis Thales</p>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="h1">Génération Devis Thales</h1>
          <p className="sub">Générez automatiquement des devis PSTF pour Thales</p>
        </div>
        {step !== 'upload' && (
          <Button variant="secondary" onClick={handleReset}>
            Nouvelle génération
          </Button>
        )}
      </div>

      {/* Étapes */}
      <StepIndicator currentStep={step} />

      {/* Contenu de l'étape */}
      <div className="mt-5">
        {step === 'upload' && (
          <UploadStep
            isDragging={isDragging}
            isLoading={uploadMutation.isPending}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onFileSelect={handleFileSelect}
          />
        )}

        {step === 'preview' && previewData && batchId && (
          <PreviewStep
            data={previewData}
            batchId={batchId}
            isGenerating={generateMutation.isPending}
            onGenerate={() => generateMutation.mutate()}
            onReset={handleReset}
            onDataUpdate={setPreviewData}
          />
        )}

        {step === 'generating' && progressData && (
          <GeneratingStep progress={progressData} />
        )}

        {step === 'complete' && progressData && batchId && (
          <CompleteStep
            progress={progressData}
            batchId={batchId}
            onReset={handleReset}
          />
        )}
      </div>
    </div>
  );
}

// Sub-components

interface StepIndicatorProps {
  currentStep: Step;
}

function StepIndicator({ currentStep }: StepIndicatorProps) {
  const steps = [
    { id: 'upload', label: 'Import CSV' },
    { id: 'preview', label: 'Aperçu' },
    { id: 'generating', label: 'Génération' },
    { id: 'complete', label: 'Terminé' },
  ];

  const currentIndex = steps.findIndex((s) => s.id === currentStep);

  return (
    <div className="steps max-w-[440px] mx-auto">
      <div className="track" />
      <div className="tfill" style={{ width: `${4.5 + currentIndex * 25}%` }} />
      <div className="nodes">
        {steps.map((s, index) => (
          <div key={s.id} className="stw">
            <span
              className={`nd ${
                index < currentIndex || (index === currentIndex && currentStep === 'complete')
                  ? 'd'
                  : index === currentIndex
                    ? 'cur'
                    : ''
              }`}
            />
            <p className="lb">{s.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

interface UploadStepProps {
  isDragging: boolean;
  isLoading: boolean;
  onDrop: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onFileSelect: () => void;
}

function UploadStep({
  isDragging,
  isLoading,
  onDrop,
  onDragOver,
  onDragLeave,
  onFileSelect,
}: UploadStepProps) {
  return (
    <div className="card">
      <h3 className="ct">1 · Importer le fichier CSV</h3>
      <p className="cs mb-3">Une ligne par devis (consultant / période)</p>

      <div
        className={`drop ${isDragging ? 'active' : ''} ${
          isLoading ? 'opacity-60 pointer-events-none' : ''
        }`}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={onFileSelect}
      >
        {isLoading ? (
          <>
            <Loader2 className="h-9 w-9 mx-auto animate-spin text-prit" />
            <p className="dropt">Analyse du fichier en cours...</p>
          </>
        ) : (
          <>
            <FileSpreadsheet
              className={`h-9 w-9 mx-auto ${isDragging ? 'text-prit' : 'text-mut2'}`}
            />
            <p className="dropt">
              <b className="text-prit font-semibold">Cliquez pour choisir</b> ou glissez-déposez
            </p>
            <p className="drops">.csv · devis PSTF Thales</p>
          </>
        )}
      </div>

      <div className="infob mt-3.5 flex items-start justify-between gap-4">
        <p className="!m-0">
          <b>Colonnes requises :</b> firstName, lastName, po_start_date, po_end_date,
          amount_ht_unit, total_uo, C22_domain, C22_activity, complexity.
          <br />
          Les IDs BoondManager (ressource, opportunité, société, contact) sont auto-récupérés via
          l'API · max_price optionnel pour 124-Data (auto-calculé depuis la grille tarifaire).
        </p>
        <Button
          variant="secondary"
          size="sm"
          className="shrink-0"
          onClick={() => quotationGeneratorApi.downloadExampleCsv()}
          leftIcon={<Download className="h-3.5 w-3.5" />}
        >
          Exemple CSV
        </Button>
      </div>
    </div>
  );
}

interface PreviewStepProps {
  data: PreviewBatchResponse;
  batchId: string;
  isGenerating: boolean;
  onGenerate: () => void;
  onReset: () => void;
  onDataUpdate: (data: PreviewBatchResponse) => void;
}

function PreviewStep({ data, batchId, isGenerating, onGenerate, onReset, onDataUpdate }: PreviewStepProps) {
  const [selectedQuotation, setSelectedQuotation] = useState<QuotationPreviewItem | null>(null);
  const [updatingContact, setUpdatingContact] = useState<number | null>(null);
  const [deletingRow, setDeletingRow] = useState<number | null>(null);

  // Handle delete quotation
  const handleDeleteQuotation = async (rowIndex: number) => {
    if (!confirm('Supprimer cette ligne ?')) return;

    setDeletingRow(rowIndex);
    try {
      const updatedData = await quotationGeneratorApi.deleteQuotation(batchId, rowIndex);
      onDataUpdate(updatedData);
      toast.success('Ligne supprimée');
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, 'Erreur lors de la suppression'));
    } finally {
      setDeletingRow(null);
    }
  };

  // Handle contact change
  const handleContactChange = async (rowIndex: number, contactId: string, contactName: string) => {
    setUpdatingContact(rowIndex);
    try {
      await quotationGeneratorApi.updateQuotationContact(batchId, rowIndex, contactId, contactName);
      // Update the quotation in the local data
      const updatedQuotations = data.quotations.map((q) =>
        q.row_index === rowIndex
          ? { ...q, contact_id: contactId, contact_name: contactName }
          : q
      );
      onDataUpdate({
        ...data,
        quotations: updatedQuotations,
      });
      toast.success('Contact mis à jour');
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, 'Erreur lors de la mise à jour du contact'));
    } finally {
      setUpdatingContact(null);
    }
  };

  const formatAmount = (value: number) =>
    new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0,
    }).format(value);

  const validTotalHt = data.quotations
    .filter((q) => q.is_valid)
    .reduce((sum, q) => sum + q.total_ht, 0);

  return (
    <div>
      {/* KPIs */}
      <div className="kpis !my-4">
        <div className="kpi">
          <p className="kl">Lignes traitées</p>
          <p className="kv">{data.total_quotations}</p>
          <p className="ks">fichier CSV analysé</p>
        </div>
        <div className="kpi">
          <p className="kl">Devis valides</p>
          <p className="kv text-grn-fg">{data.valid_count}</p>
          <p className="ks">prêts à être générés</p>
        </div>
        <div className="kpi">
          <p className="kl">Devis invalides</p>
          <p className={`kv ${data.invalid_count > 0 ? 'red' : ''}`}>{data.invalid_count}</p>
          <p className="ks">ignorés à la génération</p>
        </div>
        <div className="kpi">
          <p className="kl">Total HT</p>
          <p className="kv">{formatAmount(validTotalHt)}</p>
          <p className="ks">devis valides uniquement</p>
        </div>
      </div>

      {data.invalid_count > 0 && (
        <div className="alert !mt-0 mb-4">
          <AlertCircle className="h-[18px] w-[18px] flex-shrink-0" />
          <span>Les devis invalides seront ignorés lors de la génération.</span>
        </div>
      )}

      {/* Détail des devis */}
      <div className="tbl">
        <div className={`thead ${PREVIEW_GRID}`}>
          <span>#</span>
          <span>Consultant</span>
          <span>Client / Contact</span>
          <span>Période</span>
          <span>TJM</span>
          <span>Jours</span>
          <span>Total HT</span>
          <span>Statut</span>
          <span></span>
        </div>
        {data.quotations.map((q) => (
          <QuotationRow
            key={q.row_index}
            quotation={q}
            onSelect={() => setSelectedQuotation(q)}
            onContactChange={handleContactChange}
            isUpdatingContact={updatingContact === q.row_index}
            onDelete={handleDeleteQuotation}
            isDeleting={deletingRow === q.row_index}
          />
        ))}
        <div className="tfoot">
          <span>
            {data.valid_count} devis valide{data.valid_count > 1 ? 's' : ''} sur{' '}
            {data.total_quotations} ligne{data.total_quotations > 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2 mt-4">
        <Button variant="secondary" onClick={onReset}>
          Annuler
        </Button>
        <Button
          onClick={onGenerate}
          isLoading={isGenerating}
          disabled={data.valid_count === 0}
          leftIcon={<Play className="h-4 w-4" />}
        >
          Générer {data.valid_count} devis
        </Button>
      </div>

      {/* Quotation Details Modal */}
      <QuotationDetailsModal
        quotation={selectedQuotation}
        isOpen={!!selectedQuotation}
        onClose={() => setSelectedQuotation(null)}
      />
    </div>
  );
}

interface QuotationRowProps {
  quotation: QuotationPreviewItem;
  onSelect: () => void;
  onContactChange: (rowIndex: number, contactId: string, contactName: string) => void;
  isUpdatingContact: boolean;
  onDelete: (rowIndex: number) => void;
  isDeleting: boolean;
}

function QuotationRow({ quotation, onSelect, onContactChange, isUpdatingContact, onDelete, isDeleting }: QuotationRowProps) {
  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(value);

  // Format name: Prénom NOM
  const formatName = (fullName: string) => {
    const parts = fullName.trim().split(/\s+/);
    if (parts.length >= 2) {
      const firstName = parts[0].charAt(0).toUpperCase() + parts[0].slice(1).toLowerCase();
      const lastName = parts.slice(1).join(' ').toUpperCase();
      return `${firstName} ${lastName}`;
    }
    return fullName;
  };

  return (
    <div className={`row ${PREVIEW_GRID}`}>
      <span className="ref">{quotation.row_index + 1}</span>
      <div className="min-w-0">
        <button type="button" onClick={onSelect} className="text-left max-w-full" title="Voir le détail du devis">
          <span className="nm block truncate hover:text-prit hover:underline">
            {formatName(quotation.resource_name)}
          </span>
        </button>
        {quotation.resource_trigramme && (
          <p className="ns truncate">{quotation.resource_trigramme}</p>
        )}
      </div>
      <div className="min-w-0">
        <p className="cell truncate">{quotation.company_name}</p>
        {quotation.available_contacts && quotation.available_contacts.length > 1 ? (
          <select
            value={quotation.contact_id}
            onChange={(e) => {
              const selectedContact = quotation.available_contacts.find(c => c.id === e.target.value);
              if (selectedContact) {
                onContactChange(quotation.row_index, selectedContact.id, selectedContact.name);
              }
            }}
            disabled={isUpdatingContact}
            className="filter-select mt-1.5 w-full !min-w-0 !h-7 !text-[11.5px] disabled:opacity-50"
          >
            {quotation.available_contacts.map((contact) => (
              <option key={contact.id} value={contact.id}>
                {contact.name}
              </option>
            ))}
          </select>
        ) : (
          <p className="ns truncate">{quotation.contact_name}</p>
        )}
      </div>
      <span className="cell">
        {quotation.period_name || `${quotation.period.start} → ${quotation.period.end}`}
      </span>
      <span className="cell">{formatCurrency(quotation.tjm)}</span>
      <span className="cell">{quotation.quantity}</span>
      <span className="tjm">{formatCurrency(quotation.total_ht)}</span>
      <div className="min-w-0">
        {quotation.is_valid ? (
          <span className="st st-grn">
            <span className="dot" />
            Valide
          </span>
        ) : (
          <>
            <span className="st st-red">
              <span className="dot" />
              Invalide
            </span>
            {quotation.validation_errors.length > 0 && (
              <p
                className="ns !text-redt truncate mt-1"
                title={quotation.validation_errors[0]}
              >
                {quotation.validation_errors[0]}
              </p>
            )}
          </>
        )}
      </div>
      <div className="text-right">
        <button
          type="button"
          onClick={() => onDelete(quotation.row_index)}
          disabled={isDeleting}
          className="p-1.5 rounded-md text-mut2 hover:text-redt hover:bg-red-bg disabled:opacity-50 transition-colors"
          title="Supprimer la ligne"
        >
          {isDeleting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Trash2 className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}

interface QuotationDetailsModalProps {
  quotation: QuotationPreviewItem | null;
  isOpen: boolean;
  onClose: () => void;
}

function QuotationDetailsModal({ quotation, isOpen, onClose }: QuotationDetailsModalProps) {
  if (!quotation) return null;

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(value);

  // Format date: YYYY-MM-DD -> DD/MM/YYYY
  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return '-';
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    return dateStr;
  };

  // Format name: Prénom NOM
  const formatName = (fullName: string) => {
    const parts = fullName.trim().split(/\s+/);
    if (parts.length >= 2) {
      const firstName = parts[0].charAt(0).toUpperCase() + parts[0].slice(1).toLowerCase();
      const lastName = parts.slice(1).join(' ').toUpperCase();
      return `${firstName} ${lastName}`;
    }
    return fullName;
  };

  const DetailRow = ({ label, value }: { label: string; value: string | number | null | undefined }) => (
    <div className="py-2 grid grid-cols-2 gap-4 border-b border-lin2 last:border-b-0">
      <dt className="text-[12.5px] font-medium text-mut">{label}</dt>
      <dd className="text-[13px] text-ink">{value || '—'}</dd>
    </div>
  );

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <section>
      <p className="ml mb-2">{title}</p>
      <dl className="bg-srf2 border border-lin2 rounded-[10px] px-3.5 py-1">{children}</dl>
    </section>
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Détails du devis" size="lg">
      <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
        {/* Consultant */}
        <Section title="Consultant">
          <DetailRow label="Nom" value={formatName(quotation.resource_name)} />
          <DetailRow label="Trigramme" value={quotation.resource_trigramme} />
          <DetailRow label="Resource ID" value={quotation.resource_id} />
        </Section>

        {/* BoondManager */}
        <Section title="BoondManager">
          <DetailRow label="Opportunité" value={`${quotation.opportunity_id}`} />
          <DetailRow label="Société" value={`${quotation.company_id} - ${quotation.company_name}`} />
          <DetailRow label="Détail facturation" value={quotation.company_detail_id} />
          <DetailRow label="Contact" value={`${quotation.contact_id} - ${quotation.contact_name}`} />
        </Section>

        {/* Période & tarification */}
        <Section title="Période & tarification">
          <DetailRow label="Date du devis" value={quotation.quotation_date} />
          <DetailRow label="Renouvellement" value={quotation.is_renewal ? 'Oui' : 'Non'} />
          {quotation.is_renewal && (
            <DetailRow label="Date début initiale" value={formatDate(quotation.start_project)} />
          )}
          <DetailRow label="Date début PO" value={formatDate(quotation.period.start)} />
          <DetailRow label="Date fin PO" value={formatDate(quotation.period.end)} />
          <DetailRow label="N° EACQ" value={quotation.eacq_number} />
          <DetailRow label="TJM" value={formatCurrency(quotation.tjm)} />
          <DetailRow label="Quantité (jours)" value={quotation.quantity} />
          <DetailRow label="Total HT" value={formatCurrency(quotation.total_ht)} />
          <DetailRow label="Total TTC" value={formatCurrency(quotation.total_ttc)} />
        </Section>

        {/* C22 Thales */}
        <Section title="C22 Thales">
          <DetailRow label="Domaine C22" value={quotation.c22_domain} />
          <DetailRow label="Activité C22" value={quotation.c22_activity} />
          <DetailRow label="Complexité" value={quotation.complexity} />
          <DetailRow label="GFA (Prix max)" value={formatCurrency(quotation.max_price)} />
          <DetailRow label="Taux présentiel" value={quotation.in_situ_ratio} />
        </Section>

        {/* Sous-traitance */}
        <Section title="Sous-traitance">
          <DetailRow label="Sous-traitance" value={quotation.subcontracting ? 'Oui' : 'Non'} />
          {quotation.subcontracting && (
            <>
              <DetailRow label="Fournisseur Tier 2" value={quotation.tier2_supplier || '—'} />
              <DetailRow label="Fournisseur Tier 3" value={quotation.tier3_supplier || '—'} />
            </>
          )}
        </Section>

        {/* Autres informations */}
        <Section title="Autres informations">
          <DetailRow label="Référence SOW" value={quotation.sow_reference} />
          <DetailRow label="Objet du besoin" value={quotation.object_of_need} />
          <DetailRow label="Titre du besoin" value={quotation.need_title} />
          <DetailRow label="Commentaires" value={quotation.comments} />
        </Section>

        {/* Erreurs de validation */}
        {!quotation.is_valid && quotation.validation_errors.length > 0 && (
          <section>
            <p className="ml mb-2 !text-redt">Erreurs de validation</p>
            <ul className="bg-red-bg text-red-fg rounded-[10px] px-3.5 py-2.5 space-y-1 text-[12.5px]">
              {quotation.validation_errors.map((error, index) => (
                <li key={index}>• {error}</li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </Modal>
  );
}

interface GeneratingStepProps {
  progress: BatchProgressResponse;
}

function GeneratingStep({ progress }: GeneratingStepProps) {
  return (
    <div>
      <div className="card">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5 min-w-0">
            <Loader2 className="h-4 w-4 animate-spin text-prit flex-shrink-0" />
            <div>
              <h3 className="ct">Génération en cours...</h3>
              <p className="cs">Création des devis dans BoondManager puis conversion en PDF</p>
            </div>
          </div>
          <span className="docs">{progress.progress_percentage.toFixed(0)} %</span>
        </div>
        <div className="pbar">
          <div className="pfill" style={{ width: `${progress.progress_percentage}%` }} />
        </div>
        <p className="f-hint">La page s'actualise automatiquement toutes les 2 secondes</p>
      </div>

      <div className="kpis !my-4">
        <div className="kpi">
          <p className="kl">Lignes traitées</p>
          <p className="kv">{progress.total}</p>
          <p className="ks">devis à générer</p>
        </div>
        <div className="kpi">
          <p className="kl">Devis générés</p>
          <p className="kv text-grn-fg">{progress.completed}</p>
          <p className="ks">créés dans BoondManager</p>
        </div>
        <div className="kpi">
          <p className="kl">En attente</p>
          <p className="kv text-amb-fg">{progress.pending}</p>
          <p className="ks">dans la file de génération</p>
        </div>
        <div className="kpi">
          <p className="kl">Erreurs</p>
          <p className={`kv ${progress.failed > 0 ? 'red' : ''}`}>{progress.failed}</p>
          <p className="ks">devis en échec</p>
        </div>
      </div>
    </div>
  );
}

interface CompleteStepProps {
  progress: BatchProgressResponse;
  batchId: string;
  onReset: () => void;
}

function CompleteStep({ progress, batchId, onReset }: CompleteStepProps) {
  const [isDownloadingZip, setIsDownloadingZip] = useState(false);
  const [downloadingRow, setDownloadingRow] = useState<number | null>(null);

  // Format name as "Prénom NOM"
  const formatName = (fullName: string) => {
    const parts = fullName.trim().split(/\s+/);
    if (parts.length >= 2) {
      const firstName = parts[0].charAt(0).toUpperCase() + parts[0].slice(1).toLowerCase();
      const lastName = parts.slice(1).join(' ').toUpperCase();
      return `${firstName} ${lastName}`;
    }
    return fullName;
  };

  // Fetch batch details with quotation statuses (includes latest paths)
  const { data: batchDetails } = useQuery({
    queryKey: ['batch-details', batchId],
    queryFn: () => quotationGeneratorApi.getBatchDetails(batchId),
    enabled: !!batchId,
  });

  // Use batchDetails for accurate data (progress might be stale)
  const hasErrors = batchDetails?.has_errors ?? progress.has_errors;
  const completedCount = batchDetails?.completed ?? progress.completed;
  const failedCount = batchDetails?.failed ?? progress.failed;
  const totalCount = batchDetails?.total ?? progress.total;

  const handleDownloadZip = async () => {
    setIsDownloadingZip(true);
    try {
      await quotationGeneratorApi.downloadZipAsFile(batchId);
      toast.success('Téléchargement du ZIP démarré');
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, 'Erreur lors du téléchargement'));
    } finally {
      setIsDownloadingZip(false);
    }
  };

  const handleDownloadIndividual = async (rowIndex: number, reference: string) => {
    setDownloadingRow(rowIndex);
    try {
      await quotationGeneratorApi.downloadIndividualPdfAsFile(
        batchId,
        rowIndex,
        `devis_${reference}.pdf`
      );
      toast.success(`Téléchargement de ${reference} démarré`);
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, 'Erreur lors du téléchargement'));
    } finally {
      setDownloadingRow(null);
    }
  };

  return (
    <div>
      {/* Résultat */}
      {hasErrors ? (
        <div className="alert !mt-0">
          <AlertCircle className="h-[18px] w-[18px] flex-shrink-0" />
          <span>
            Génération terminée avec des erreurs — {completedCount} devis générés, {failedCount} en
            échec.
          </span>
        </div>
      ) : (
        <div className="okbox !mt-0">
          <CheckCircle className="h-4 w-4 flex-shrink-0" />
          <span>Génération terminée — {completedCount} devis générés avec succès.</span>
        </div>
      )}

      {/* KPIs */}
      <div className="kpis !my-4 !grid-cols-3">
        <div className="kpi">
          <p className="kl">Lignes traitées</p>
          <p className="kv">{totalCount}</p>
          <p className="ks">dans le fichier importé</p>
        </div>
        <div className="kpi">
          <p className="kl">Devis générés</p>
          <p className="kv text-grn-fg">{completedCount}</p>
          <p className="ks">PDF prêts au téléchargement</p>
        </div>
        <div className="kpi">
          <p className="kl">Erreurs</p>
          <p className={`kv ${failedCount > 0 ? 'red' : ''}`}>{failedCount}</p>
          <p className="ks">devis en échec</p>
        </div>
      </div>

      {/* Téléchargement individuel */}
      {batchDetails && batchDetails.quotations.length > 0 && (
        <div className="tbl">
          <div className={`thead ${COMPLETE_GRID}`}>
            <span>Référence</span>
            <span>Consultant</span>
            <span>Société</span>
            <span>Statut</span>
            <span className="text-right">Action</span>
          </div>
          {batchDetails.quotations.map((q) => (
            <div key={q.row_index} className={`row ${COMPLETE_GRID}`}>
              <span className="ref">{q.boond_reference || '—'}</span>
              <div className="min-w-0">
                <p className="nm truncate">{formatName(q.resource_name)}</p>
                {q.resource_trigramme && <p className="ns truncate">{q.resource_trigramme}</p>}
              </div>
              <span className="cell truncate">{q.company_name || '—'}</span>
              <div className="min-w-0">
                {q.status === 'completed' ? (
                  <span className="st st-grn">
                    <span className="dot" />
                    Généré
                  </span>
                ) : q.status === 'failed' ? (
                  <>
                    <span className="st st-red">
                      <span className="dot" />
                      Erreur
                    </span>
                    {q.error_message && (
                      <p className="ns !text-redt truncate mt-1" title={q.error_message}>
                        {q.error_message}
                      </p>
                    )}
                  </>
                ) : q.status === 'pending' ? (
                  <span className="st st-amb">
                    <span className="dot" />
                    En attente
                  </span>
                ) : (
                  <span className="st st-blu">
                    <span className="dot" />
                    En cours
                  </span>
                )}
              </div>
              <div className="text-right">
                {q.status === 'completed' ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    isLoading={downloadingRow === q.row_index}
                    onClick={() =>
                      handleDownloadIndividual(q.row_index, q.boond_reference || `row_${q.row_index}`)
                    }
                    leftIcon={<Download className="h-3 w-3" />}
                  >
                    PDF
                  </Button>
                ) : (
                  <span className="cell text-mut2">—</span>
                )}
              </div>
            </div>
          ))}
          <div className="tfoot">
            <span>
              {completedCount} devis générés sur {totalCount} ligne{totalCount > 1 ? 's' : ''}
            </span>
            {completedCount > 0 && (
              <button
                type="button"
                className="alink disabled:opacity-40"
                onClick={handleDownloadZip}
                disabled={isDownloadingZip}
              >
                {isDownloadingZip ? 'Préparation du ZIP...' : 'Tout télécharger (.zip) →'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-2 mt-4">
        <Button variant="secondary" onClick={onReset}>
          Nouvelle génération
        </Button>
        {completedCount > 0 && (
          <Button
            onClick={handleDownloadZip}
            isLoading={isDownloadingZip}
            leftIcon={<Download className="h-4 w-4" />}
          >
            Télécharger le ZIP
          </Button>
        )}
      </div>
    </div>
  );
}
