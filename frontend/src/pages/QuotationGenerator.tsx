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
  Upload,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle,
  Download,
  RefreshCw,
  Play,
  Trash2,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';

import { quotationGeneratorApi, type PreviewBatchResponse, type BatchProgressResponse, type QuotationPreviewItem } from '../api/quotationGenerator';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { getErrorMessage } from '../api/client';

type Step = 'upload' | 'preview' | 'generating' | 'complete';

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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Génération de Devis Thales
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Générez automatiquement des devis PSTF pour Thales
          </p>
        </div>
        {step !== 'upload' && (
          <Button variant="outline" onClick={handleReset}>
            Nouvelle génération
          </Button>
        )}
      </div>

      {/* Progress Steps */}
      <StepIndicator currentStep={step} />

      {/* Step Content */}
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
  );
}

// Sub-components

interface StepIndicatorProps {
  currentStep: Step;
}

function StepIndicator({ currentStep }: StepIndicatorProps) {
  const steps = [
    { id: 'upload', label: 'Upload CSV' },
    { id: 'preview', label: 'Aperçu' },
    { id: 'generating', label: 'Génération' },
    { id: 'complete', label: 'Terminé' },
  ];

  const currentIndex = steps.findIndex((s) => s.id === currentStep);

  return (
    <div className="flex items-center justify-center space-x-4">
      {steps.map((step, index) => (
        <div key={step.id} className="flex items-center">
          <div
            className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
              index < currentIndex
                ? 'bg-primary text-white'
                : index === currentIndex
                ? 'bg-primary text-white ring-2 ring-primary ring-offset-2 dark:ring-offset-gray-900'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
            }`}
          >
            {index < currentIndex ? (
              <CheckCircle className="w-5 h-5" />
            ) : (
              index + 1
            )}
          </div>
          <span
            className={`ml-2 text-sm ${
              index <= currentIndex
                ? 'text-gray-900 dark:text-gray-100 font-medium'
                : 'text-gray-500 dark:text-gray-400'
            }`}
          >
            {step.label}
          </span>
          {index < steps.length - 1 && (
            <div
              className={`w-12 h-0.5 mx-4 ${
                index < currentIndex
                  ? 'bg-primary'
                  : 'bg-gray-200 dark:bg-gray-700'
              }`}
            />
          )}
        </div>
      ))}
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
    <Card>
      <CardHeader
        title="Importer le fichier CSV"
        subtitle="Glissez-déposez ou cliquez pour sélectionner votre fichier CSV"
      />

      <div
        className={`mt-4 border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
          isDragging
            ? 'border-primary bg-primary-50 dark:bg-primary-900/20'
            : 'border-gray-300 dark:border-gray-600'
        }`}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
      >
        {isLoading ? (
          <div className="flex flex-col items-center">
            <RefreshCw className="w-12 h-12 text-primary animate-spin" />
            <p className="mt-4 text-gray-600 dark:text-gray-400">
              Analyse du fichier en cours...
            </p>
          </div>
        ) : (
          <>
            <FileSpreadsheet className="w-12 h-12 text-gray-400 mx-auto" />
            <p className="mt-4 text-gray-600 dark:text-gray-400">
              Glissez votre fichier CSV ici
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">
              ou
            </p>
            <Button
              variant="outline"
              className="mt-4"
              onClick={onFileSelect}
            >
              <Upload className="w-4 h-4 mr-2" />
              Parcourir
            </Button>
          </>
        )}
      </div>

      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg flex justify-between items-start">
        <p className="text-sm text-blue-700 dark:text-blue-400">
          <strong>Colonnes requises :</strong> firstName, lastName, po_start_date, po_end_date,
          amount_ht_unit, total_uo, C22_domain, C22_activity, complexity
          <br />
          <span className="text-blue-600 dark:text-blue-300">
            Les IDs BoondManager (ressource, opportunité, société, contact) sont auto-récupérés via l'API.
            <br />
            max_price optionnel pour 124-Data (auto-calculé depuis la grille tarifaire)
          </span>
        </p>
        <Button
          variant="outline"
          size="sm"
          className="ml-4 shrink-0"
          onClick={() => quotationGeneratorApi.downloadExampleCsv()}
        >
          <Download className="w-4 h-4 mr-2" />
          Exemple CSV
        </Button>
      </div>
    </Card>
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

  return (
    <div className="space-y-6">
      {/* Summary */}
      <Card>
        <CardHeader
          title="Résumé de l'analyse"
          subtitle="Vérifiez les données avant de lancer la génération"
        />

        <div className="grid grid-cols-3 gap-4 mt-4">
          <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg text-center">
            <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              {data.total_quotations}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Total devis
            </p>
          </div>
          <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg text-center">
            <p className="text-3xl font-bold text-green-600 dark:text-green-400">
              {data.valid_count}
            </p>
            <p className="text-sm text-green-600 dark:text-green-400">
              Valides
            </p>
          </div>
          <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-center">
            <p className="text-3xl font-bold text-red-600 dark:text-red-400">
              {data.invalid_count}
            </p>
            <p className="text-sm text-red-600 dark:text-red-400">
              Invalides
            </p>
          </div>
        </div>

        {data.invalid_count > 0 && (
          <div className="mt-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
            <p className="text-sm text-yellow-700 dark:text-yellow-400">
              <AlertCircle className="w-4 h-4 inline-block mr-2" />
              Les devis invalides seront ignorés lors de la génération.
            </p>
          </div>
        )}

        <div className="mt-6 flex justify-end space-x-3">
          <Button variant="outline" onClick={onReset}>
            Annuler
          </Button>
          <Button
            onClick={onGenerate}
            isLoading={isGenerating}
            disabled={data.valid_count === 0}
            leftIcon={<Play className="w-4 h-4" />}
          >
            Générer {data.valid_count} devis
          </Button>
        </div>
      </Card>

      {/* Quotation List */}
      <Card>
        <CardHeader title="Détail des devis" />

        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  #
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Consultant
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Client
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Période
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  TJM
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Jours
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Total HT
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Statut
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
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
            </tbody>
          </table>
        </div>
      </Card>

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
    <tr className={quotation.is_valid ? '' : 'bg-red-50 dark:bg-red-900/10'}>
      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
        {quotation.row_index + 1}
      </td>
      <td className="px-4 py-3">
        <button
          onClick={onSelect}
          className="text-left hover:bg-gray-100 dark:hover:bg-gray-700 rounded p-1 -m-1 transition-colors"
        >
          <div className="text-sm font-medium text-primary hover:underline">
            {formatName(quotation.resource_name)}
          </div>
        </button>
      </td>
      <td className="px-4 py-3">
        <div className="text-sm text-gray-900 dark:text-gray-100">
          {quotation.company_name}
        </div>
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
            className="mt-1 text-xs w-full rounded border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 focus:ring-primary focus:border-primary disabled:opacity-50"
          >
            {quotation.available_contacts.map((contact) => (
              <option key={contact.id} value={contact.id}>
                {contact.name}
              </option>
            ))}
          </select>
        ) : (
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {quotation.contact_name}
          </div>
        )}
      </td>
      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
        {quotation.period_name || `${quotation.period.start} → ${quotation.period.end}`}
      </td>
      <td className="px-4 py-3 text-sm text-right text-gray-900 dark:text-gray-100">
        {formatCurrency(quotation.tjm)}
      </td>
      <td className="px-4 py-3 text-sm text-right text-gray-900 dark:text-gray-100">
        {quotation.quantity}
      </td>
      <td className="px-4 py-3 text-sm text-right font-medium text-gray-900 dark:text-gray-100">
        {formatCurrency(quotation.total_ht)}
      </td>
      <td className="px-4 py-3 text-center">
        {quotation.is_valid ? (
          <Badge variant="success">Valide</Badge>
        ) : (
          <div>
            <Badge variant="error">Invalide</Badge>
            {quotation.validation_errors.length > 0 && (
              <div className="mt-1 text-xs text-red-600 dark:text-red-400">
                {quotation.validation_errors[0]}
              </div>
            )}
          </div>
        )}
      </td>
      <td className="px-4 py-3 text-center">
        <button
          onClick={() => onDelete(quotation.row_index)}
          disabled={isDeleting}
          className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400 disabled:opacity-50 transition-colors"
          title="Supprimer"
        >
          {isDeleting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Trash2 className="w-4 h-4" />
          )}
        </button>
      </td>
    </tr>
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
    <div className="py-2 grid grid-cols-2 gap-4 border-b border-gray-100 dark:border-gray-700 last:border-b-0">
      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</dt>
      <dd className="text-sm text-gray-900 dark:text-gray-100">{value || '-'}</dd>
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Détails du devis" size="lg">
      <div className="space-y-6 max-h-[70vh] overflow-y-auto">
        {/* Resource Info */}
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center">
            <span className="w-2 h-2 bg-primary rounded-full mr-2" />
            Consultant
          </h4>
          <dl className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
            <DetailRow label="Nom" value={formatName(quotation.resource_name)} />
            <DetailRow label="Trigramme" value={quotation.resource_trigramme} />
            <DetailRow label="Resource ID" value={quotation.resource_id} />
          </dl>
        </div>

        {/* BoondManager Relationships */}
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center">
            <span className="w-2 h-2 bg-blue-500 rounded-full mr-2" />
            BoondManager
          </h4>
          <dl className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
            <DetailRow label="Opportunité" value={`${quotation.opportunity_id}`} />
            <DetailRow label="Société" value={`${quotation.company_id} - ${quotation.company_name}`} />
            <DetailRow label="Détail facturation" value={quotation.company_detail_id} />
            <DetailRow label="Contact" value={`${quotation.contact_id} - ${quotation.contact_name}`} />
          </dl>
        </div>

        {/* Period & Pricing */}
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center">
            <span className="w-2 h-2 bg-yellow-500 rounded-full mr-2" />
            Période & Tarification
          </h4>
          <dl className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
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
          </dl>
        </div>

        {/* Thales C22 Fields */}
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center">
            <span className="w-2 h-2 bg-purple-500 rounded-full mr-2" />
            C22 Thales
          </h4>
          <dl className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
            <DetailRow label="Domaine C22" value={quotation.c22_domain} />
            <DetailRow label="Activité C22" value={quotation.c22_activity} />
            <DetailRow label="Complexité" value={quotation.complexity} />
            <DetailRow label="GFA (Prix max)" value={formatCurrency(quotation.max_price)} />
            <DetailRow label="Taux présentiel" value={quotation.in_situ_ratio} />
          </dl>
        </div>

        {/* Subcontracting */}
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center">
            <span className="w-2 h-2 bg-pink-500 rounded-full mr-2" />
            Sous-traitance
          </h4>
          <dl className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
            <DetailRow label="Sous-traitance" value={quotation.subcontracting ? 'Oui' : 'Non'} />
            {quotation.subcontracting && (
              <>
                <DetailRow label="Fournisseur Tier 2" value={quotation.tier2_supplier || '-'} />
                <DetailRow label="Fournisseur Tier 3" value={quotation.tier3_supplier || '-'} />
              </>
            )}
          </dl>
        </div>

        {/* Other Fields */}
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center">
            <span className="w-2 h-2 bg-orange-500 rounded-full mr-2" />
            Autres informations
          </h4>
          <dl className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
            <DetailRow label="Référence SOW" value={quotation.sow_reference} />
            <DetailRow label="Objet du besoin" value={quotation.object_of_need} />
            <DetailRow label="Titre du besoin" value={quotation.need_title} />
            <DetailRow label="Commentaires" value={quotation.comments} />
          </dl>
        </div>

        {/* Validation Status */}
        {!quotation.is_valid && quotation.validation_errors.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-red-600 dark:text-red-400 mb-2 flex items-center">
              <span className="w-2 h-2 bg-red-500 rounded-full mr-2" />
              Erreurs de validation
            </h4>
            <ul className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 space-y-1">
              {quotation.validation_errors.map((error, index) => (
                <li key={index} className="text-sm text-red-600 dark:text-red-400">
                  • {error}
                </li>
              ))}
            </ul>
          </div>
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
    <Card>
      <CardHeader
        title="Génération en cours"
        subtitle="Les devis sont en cours de création dans BoondManager et de conversion en PDF"
      />

      <div className="mt-6">
        {/* Progress Bar */}
        <div className="relative pt-1">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Progression
            </span>
            <span className="text-sm font-medium text-primary">
              {progress.progress_percentage.toFixed(0)}%
            </span>
          </div>
          <div className="overflow-hidden h-3 text-xs flex rounded-full bg-gray-200 dark:bg-gray-700">
            <div
              className="transition-all duration-500 ease-out flex flex-col text-center whitespace-nowrap text-white justify-center bg-primary"
              style={{ width: `${progress.progress_percentage}%` }}
            />
          </div>
        </div>

        {/* Stats */}
        <div className="mt-6 grid grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {progress.total}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Total</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-green-600">
              {progress.completed}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Terminés</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-red-600">
              {progress.failed}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Échoués</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-yellow-600">
              {progress.pending}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">En attente</p>
          </div>
        </div>

        {/* Animation */}
        <div className="mt-8 flex items-center justify-center">
          <RefreshCw className="w-8 h-8 text-primary animate-spin" />
          <span className="ml-3 text-gray-600 dark:text-gray-400">
            Génération en cours...
          </span>
        </div>
      </div>
    </Card>
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
    <div className="space-y-6">
      {/* Summary Card */}
      <Card>
        <CardHeader
          title={hasErrors ? 'Génération terminée avec des erreurs' : 'Génération terminée'}
          subtitle={
            hasErrors
              ? `${completedCount} devis générés, ${failedCount} échoués`
              : `${completedCount} devis générés avec succès`
          }
        />

        <div className="mt-6 flex flex-col items-center">
          {hasErrors ? (
            <AlertCircle className="w-16 h-16 text-yellow-500" />
          ) : (
            <CheckCircle className="w-16 h-16 text-green-500" />
          )}

          <div className="mt-6 grid grid-cols-3 gap-8">
            <div className="text-center">
              <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                {totalCount}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-green-600">
                {completedCount}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Réussis</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-red-600">
                {failedCount}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Échoués</p>
            </div>
          </div>

          <div className="mt-8 flex space-x-4">
            <Button variant="outline" onClick={onReset}>
              Nouvelle génération
            </Button>
            {completedCount > 0 && (
              <Button
                onClick={handleDownloadZip}
                isLoading={isDownloadingZip}
                leftIcon={<Download className="w-4 h-4" />}
              >
                Télécharger ZIP
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Quotation Download Table */}
      {batchDetails && batchDetails.quotations.length > 0 && (
        <Card>
          <CardHeader
            title="Téléchargement individuel"
            subtitle="Téléchargez les devis individuellement"
          />

          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    #
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Consultant
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Référence Devis
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Statut
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {batchDetails.quotations.map((q) => (
                  <tr key={q.row_index} className={q.status !== 'completed' ? 'bg-red-50 dark:bg-red-900/10' : ''}>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                      {q.row_index + 1}
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {formatName(q.resource_name)}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {q.resource_trigramme}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                      {q.boond_reference || '-'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {q.status === 'completed' ? (
                        <Badge variant="success">Généré</Badge>
                      ) : (
                        <Badge variant="error">Erreur</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {q.status === 'completed' ? (
                        <Button
                          size="sm"
                          variant="outline"
                          isLoading={downloadingRow === q.row_index}
                          onClick={() => handleDownloadIndividual(q.row_index, q.boond_reference || `row_${q.row_index}`)}
                          leftIcon={<Download className="w-3 h-3" />}
                        >
                          PDF
                        </Button>
                      ) : q.error_message ? (
                        <span className="text-xs text-red-500" title={q.error_message}>
                          {q.error_message.substring(0, 30)}...
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
