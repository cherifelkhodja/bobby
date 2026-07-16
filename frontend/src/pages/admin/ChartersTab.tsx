import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, Trash2, Eye, EyeOff, FileText, FileCheck } from 'lucide-react';
import { toast } from 'sonner';

import { chartersApi } from '../../api/charters';
import type { CharterTemplate, CharterDocumentType, CharterConsultantScope } from '../../api/charters';
import { Button } from '../../components/ui/Button';
import { getErrorMessage } from '../../api/client';

const TARGET_COLORS: Record<string, string> = {
  partner: 'bg-blu-bg text-blu-fg',
  consultant: 'bg-ind-bg text-ind-fg',
};

const DOCUMENT_TYPE_LABELS: Record<CharterDocumentType, string> = {
  charte: 'Charte',
  politique: 'Politique',
  document_unilateral: 'Document unilatéral',
  engagement: 'Engagement',
  autre: 'Autre',
};

const DOCUMENT_TYPE_OPTIONS: CharterDocumentType[] = [
  'charte', 'politique', 'document_unilateral', 'engagement', 'autre',
];

const CONSULTANT_SCOPE_LABELS: Record<CharterConsultantScope, string> = {
  all: 'Tous',
  external: 'Externes',
  internal: 'Internes',
};

interface ChartersTabProps {
  companyId: string;
}

export function ChartersTab({ companyId }: ChartersTabProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const arFileInputRef = useRef<HTMLInputElement>(null);

  const [showUpload, setShowUpload] = useState(false);
  const [uploadName, setUploadName] = useState('');
  const [uploadVersion, setUploadVersion] = useState('');
  const [uploadTarget, setUploadTarget] = useState<'partner' | 'consultant'>('partner');
  const [uploadDocumentType, setUploadDocumentType] = useState<CharterDocumentType>('charte');
  const [uploadRequiresAr, setUploadRequiresAr] = useState(false);
  const [uploadConsultantScope, setUploadConsultantScope] = useState<CharterConsultantScope>('all');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadArFile, setUploadArFile] = useState<File | null>(null);

  const { data: charters = [], isLoading } = useQuery({
    queryKey: ['admin-charters', companyId],
    queryFn: () => chartersApi.list(companyId),
  });

  const isEngagement = uploadDocumentType === 'engagement';

  const resetForm = () => {
    setShowUpload(false);
    setUploadName('');
    setUploadVersion('');
    setUploadDocumentType('charte');
    setUploadRequiresAr(false);
    setUploadConsultantScope('all');
    setUploadFile(null);
    setUploadArFile(null);
  };

  const uploadMutation = useMutation({
    mutationFn: () =>
      chartersApi.upload({
        name: uploadName,
        version: uploadVersion,
        target: uploadTarget,
        companyId,
        documentType: uploadDocumentType,
        requiresAcknowledgement: isEngagement ? false : uploadRequiresAr,
        consultantScope: uploadTarget === 'consultant' ? uploadConsultantScope : 'all',
        file: uploadFile!,
        arFile: !isEngagement && uploadRequiresAr ? uploadArFile ?? undefined : undefined,
      }),
    onSuccess: () => {
      toast.success('Document uploade.');
      resetForm();
      queryClient.invalidateQueries({ queryKey: ['admin-charters', companyId] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ name: '', version: '', target: '' as 'partner' | 'consultant', document_type: '' as CharterDocumentType, requires_acknowledgement: false, consultant_scope: '' as CharterConsultantScope });

  const startEdit = (c: CharterTemplate) => {
    setEditingId(c.id);
    setEditForm({ name: c.name, version: c.version, target: c.target, document_type: c.document_type, requires_acknowledgement: c.requires_acknowledgement, consultant_scope: c.consultant_scope });
  };

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof chartersApi.update>[1] }) =>
      chartersApi.update(id, data),
    onSuccess: () => {
      toast.success('Document mis a jour.');
      setEditingId(null);
      queryClient.invalidateQueries({ queryKey: ['admin-charters', companyId] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      chartersApi.update(id, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-charters', companyId] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const replaceMutation = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => chartersApi.replaceFile(id, file),
    onSuccess: () => {
      toast.success('Document remplace.');
      queryClient.invalidateQueries({ queryKey: ['admin-charters', companyId] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const replaceArMutation = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => chartersApi.replaceAr(id, file),
    onSuccess: () => {
      toast.success('AR remplace.');
      queryClient.invalidateQueries({ queryKey: ['admin-charters', companyId] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => chartersApi.delete(id),
    onSuccess: () => {
      toast.success('Document supprime.');
      queryClient.invalidateQueries({ queryKey: ['admin-charters', companyId] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const partnerCharters = charters.filter((c) => c.target === 'partner');
  const consultantCharters = charters.filter((c) => c.target === 'consultant');

  const FileLink = ({ label, onDownload, onReplace }: { label: string; onDownload: () => void; onReplace: (file: File) => void }) => (
    <span className="inline-flex items-center gap-1">
      <button onClick={onDownload} className="text-[10px] text-primary hover:underline truncate max-w-[200px]" title="Telecharger">
        {label}
      </button>
      <label className="text-[10px] text-mut2 hover:text-prit cursor-pointer" title="Remplacer">
        [remplacer]
        <input type="file" accept=".pdf" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) onReplace(f); e.target.value = ''; }} />
      </label>
    </span>
  );

  const INPUT_SM = 'text-xs border border-gray-300 dark:border-gray-600 rounded-md px-2 py-1 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300';

  const renderCharter = (charter: CharterTemplate) => {
    const isEditing = editingId === charter.id;
    const editIsEngagement = editForm.document_type === 'engagement';

    return (
      <div
        key={charter.id}
        className={`rounded-lg border overflow-hidden ${
          charter.is_active
            ? 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700'
            : 'bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700 opacity-60'
        }`}
      >
        {/* Display row */}
        <div className="flex items-center justify-between p-2.5">
          <div className="flex items-center gap-2.5 min-w-0">
            <FileText className="h-3.5 w-3.5 text-gray-400 shrink-0" />
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <button
                  onClick={() => isEditing ? setEditingId(null) : startEdit(charter)}
                  className="text-xs font-medium text-gray-900 dark:text-white truncate hover:text-primary hover:underline"
                  title="Modifier"
                >
                  {charter.name}
                </button>
                <span className="text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded px-1 py-0.5">
                  {charter.version}
                </span>
                <span className="text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 rounded px-1 py-0.5">
                  {DOCUMENT_TYPE_LABELS[charter.document_type] || charter.document_type}
                </span>
                {(charter.requires_acknowledgement || charter.document_type === 'engagement') && (
                  <span className="text-[10px] bg-amb-bg text-amb-fg rounded px-1 py-0.5 flex items-center gap-0.5">
                    <FileCheck className="h-2.5 w-2.5" />
                    {charter.document_type === 'engagement' ? 'Signature' : 'AR'}
                  </span>
                )}
                {charter.target === 'consultant' && charter.consultant_scope !== 'all' && (
                  <span className="text-[10px] bg-sla-bg text-sla-fg rounded px-1 py-0.5">
                    {CONSULTANT_SCOPE_LABELS[charter.consultant_scope]}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <FileLink
                  label={charter.file_name}
                  onDownload={async () => {
                    try { const { url } = await chartersApi.getDownloadUrl(charter.id); window.open(url, '_blank'); }
                    catch { toast.error('Impossible de telecharger.'); }
                  }}
                  onReplace={(file) => replaceMutation.mutate({ id: charter.id, file })}
                />
                {charter.ar_file_name && (
                  <>
                    <span className="text-[10px] text-gray-300">|</span>
                    <FileLink
                      label={charter.ar_file_name}
                      onDownload={async () => {
                        try { const { url } = await chartersApi.getArDownloadUrl(charter.id); window.open(url, '_blank'); }
                        catch { toast.error('Impossible de telecharger.'); }
                      }}
                      onReplace={(file) => replaceArMutation.mutate({ id: charter.id, file })}
                    />
                  </>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-0.5 shrink-0 ml-2">
            <button
              onClick={() => toggleMutation.mutate({ id: charter.id, is_active: !charter.is_active })}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 transition-colors"
              title={charter.is_active ? 'Desactiver' : 'Activer'}
            >
              {charter.is_active ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
            </button>
            <button
              onClick={() => {
                if (confirm(`Supprimer "${charter.name} ${charter.version}" ?`)) {
                  deleteMutation.mutate(charter.id);
                }
              }}
              className="p-1 rounded hover:bg-red-bg text-mut2 hover:text-redt transition-colors"
              title="Supprimer"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Edit form (inline) */}
        {isEditing && (
          <div className="border-t border-gray-100 dark:border-gray-700 px-3 py-2.5 bg-gray-50 dark:bg-gray-800/50">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-2">
              <div>
                <label className="block text-[10px] font-medium text-gray-500 mb-0.5">Nom</label>
                <input className={INPUT_SM} value={editForm.name} onChange={(e) => setEditForm(f => ({ ...f, name: e.target.value }))} />
              </div>
              <div>
                <label className="block text-[10px] font-medium text-gray-500 mb-0.5">Version</label>
                <input className={INPUT_SM} value={editForm.version} onChange={(e) => setEditForm(f => ({ ...f, version: e.target.value }))} />
              </div>
              <div>
                <label className="block text-[10px] font-medium text-gray-500 mb-0.5">Type</label>
                <select className={INPUT_SM} value={editForm.document_type} onChange={(e) => setEditForm(f => ({ ...f, document_type: e.target.value as CharterDocumentType }))}>
                  {DOCUMENT_TYPE_OPTIONS.map(dt => <option key={dt} value={dt}>{DOCUMENT_TYPE_LABELS[dt]}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-medium text-gray-500 mb-0.5">Destinataire</label>
                <select className={INPUT_SM} value={editForm.target} onChange={(e) => setEditForm(f => ({ ...f, target: e.target.value as 'partner' | 'consultant' }))}>
                  <option value="partner">Partenaire</option>
                  <option value="consultant">Collaborateur</option>
                </select>
              </div>
              {editForm.target === 'consultant' && (
                <div>
                  <label className="block text-[10px] font-medium text-gray-500 mb-0.5">Scope</label>
                  <select className={INPUT_SM} value={editForm.consultant_scope} onChange={(e) => setEditForm(f => ({ ...f, consultant_scope: e.target.value as CharterConsultantScope }))}>
                    <option value="all">Tous</option>
                    <option value="external">Externes</option>
                    <option value="internal">Internes</option>
                  </select>
                </div>
              )}
              {!editIsEngagement && (
                <div className="flex items-end pb-1">
                  <label className="flex items-center gap-1.5 text-xs text-gray-700 dark:text-gray-300 cursor-pointer">
                    <input type="checkbox" checked={editForm.requires_acknowledgement} onChange={(e) => setEditForm(f => ({ ...f, requires_acknowledgement: e.target.checked }))} className="rounded border-gray-300" />
                    AR requis
                  </label>
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setEditingId(null)} className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1">Annuler</button>
              <button
                onClick={() => updateMutation.mutate({
                  id: charter.id,
                  data: {
                    name: editForm.name,
                    version: editForm.version,
                    target: editForm.target,
                    document_type: editForm.document_type,
                    requires_acknowledgement: editIsEngagement ? false : editForm.requires_acknowledgement,
                    consultant_scope: editForm.target === 'consultant' ? editForm.consultant_scope : 'all',
                  },
                })}
                disabled={updateMutation.isPending}
                className="text-xs font-medium text-white bg-primary-600 rounded px-3 py-1 hover:bg-primary-700 disabled:opacity-50"
              >
                Enregistrer
              </button>
            </div>
          </div>
        )}
      </div>
    );
  };

  if (isLoading) return <div className="text-xs text-gray-500 py-2">Chargement...</div>;

  return (
    <div className="space-y-3">
      {/* Upload form */}
      {showUpload ? (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 bg-white dark:bg-gray-800">
          <p className="text-xs font-semibold text-gray-900 dark:text-white mb-3">Nouveau document</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-[10px] font-medium text-gray-700 dark:text-gray-300 mb-1">Nom *</label>
              <input
                type="text"
                value={uploadName}
                onChange={(e) => setUploadName(e.target.value)}
                placeholder="Charte informatique"
                className="w-full text-xs border border-gray-300 dark:border-gray-600 rounded-md px-2.5 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-[10px] font-medium text-gray-700 dark:text-gray-300 mb-1">Version *</label>
              <input
                type="text"
                value={uploadVersion}
                onChange={(e) => setUploadVersion(e.target.value)}
                placeholder="V1"
                className="w-full text-xs border border-gray-300 dark:border-gray-600 rounded-md px-2.5 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              />
            </div>
            <div>
              <label className="block text-[10px] font-medium text-gray-700 dark:text-gray-300 mb-1">Type de document *</label>
              <select
                value={uploadDocumentType}
                onChange={(e) => setUploadDocumentType(e.target.value as CharterDocumentType)}
                className="w-full text-xs border border-gray-300 dark:border-gray-600 rounded-md px-2.5 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              >
                {DOCUMENT_TYPE_OPTIONS.map((dt) => (
                  <option key={dt} value={dt}>{DOCUMENT_TYPE_LABELS[dt]}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-medium text-gray-700 dark:text-gray-300 mb-1">Destinataire *</label>
              <select
                value={uploadTarget}
                onChange={(e) => setUploadTarget(e.target.value as 'partner' | 'consultant')}
                className="w-full text-xs border border-gray-300 dark:border-gray-600 rounded-md px-2.5 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
              >
                <option value="partner">Partenaire (societe)</option>
                <option value="consultant">Collaborateur (consultant)</option>
              </select>
            </div>
            {uploadTarget === 'consultant' && (
              <div>
                <label className="block text-[10px] font-medium text-gray-700 dark:text-gray-300 mb-1">Consultants concernes *</label>
                <select
                  value={uploadConsultantScope}
                  onChange={(e) => setUploadConsultantScope(e.target.value as CharterConsultantScope)}
                  className="w-full text-xs border border-gray-300 dark:border-gray-600 rounded-md px-2.5 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                >
                  <option value="all">Tous les consultants</option>
                  <option value="external">Externes uniquement</option>
                  <option value="internal">Internes uniquement</option>
                </select>
              </div>
            )}
          </div>

          {isEngagement && (
            <p className="mb-3 text-[10px] text-amb-fg">
              Les engagements sont signes directement (pas d'accuse de reception).
            </p>
          )}

          {/* Document file */}
          <div className="mb-3">
            <label className="block text-[10px] font-medium text-gray-700 dark:text-gray-300 mb-1">Document PDF *</label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-2 text-xs border border-dashed border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors w-full justify-center"
            >
              <Upload className="h-3.5 w-3.5 text-gray-400" />
              {uploadFile ? uploadFile.name : 'Choisir un fichier PDF...'}
            </button>
          </div>

          {/* AR checkbox (hidden for engagements) */}
          {!isEngagement && (
            <div className="mb-3">
              <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-700 dark:text-gray-300">
                <input
                  type="checkbox"
                  checked={uploadRequiresAr}
                  onChange={(e) => {
                    setUploadRequiresAr(e.target.checked);
                    if (!e.target.checked) setUploadArFile(null);
                  }}
                  className="rounded border-gray-300"
                />
                Accuse de reception requis
              </label>
            </div>
          )}

          {/* AR file */}
          {!isEngagement && uploadRequiresAr && (
            <div className="mb-3">
              <label className="block text-[10px] font-medium text-gray-700 dark:text-gray-300 mb-1">
                Accuse de reception (PDF)
              </label>
              <input
                ref={arFileInputRef}
                type="file"
                accept=".pdf"
                onChange={(e) => setUploadArFile(e.target.files?.[0] ?? null)}
                className="hidden"
              />
              <button
                onClick={() => arFileInputRef.current?.click()}
                className="flex items-center gap-2 text-xs border border-dashed border-[color-mix(in_oklab,var(--amb-fg)_40%,transparent)] rounded-md px-3 py-2 hover:bg-amb-bg transition-colors w-full justify-center"
              >
                <FileCheck className="h-3.5 w-3.5 text-amb-fg" />
                {uploadArFile ? uploadArFile.name : 'Choisir le PDF d\'accuse de reception...'}
              </button>
              <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-1">
                Optionnel. Si non fourni, l'AR sera genere automatiquement.
              </p>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              onClick={resetForm}
              className="px-3 py-1.5 text-xs text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Annuler
            </button>
            <Button
              size="sm"
              onClick={() => uploadMutation.mutate()}
              disabled={!uploadName || !uploadVersion || !uploadFile || uploadMutation.isPending}
              isLoading={uploadMutation.isPending}
            >
              <Upload className="h-3.5 w-3.5 mr-1.5" />
              Uploader
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex justify-end">
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            <Upload className="h-3.5 w-3.5" />
            Nouveau document
          </button>
        </div>
      )}

      {/* Partner charters */}
      <div>
        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5 flex items-center gap-1.5">
          <span className={`text-[10px] rounded-full px-1.5 py-0.5 ${TARGET_COLORS.partner}`}>Partenaire</span>
        </p>
        {partnerCharters.length === 0 ? (
          <p className="text-xs text-gray-400 dark:text-gray-500 py-2 text-center">Aucun document partenaire.</p>
        ) : (
          <div className="space-y-1.5">
            {partnerCharters.map(renderCharter)}
          </div>
        )}
      </div>

      {/* Consultant charters */}
      <div>
        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5 flex items-center gap-1.5">
          <span className={`text-[10px] rounded-full px-1.5 py-0.5 ${TARGET_COLORS.consultant}`}>Collaborateur</span>
        </p>
        {consultantCharters.length === 0 ? (
          <p className="text-xs text-gray-400 dark:text-gray-500 py-2 text-center">Aucun document collaborateur.</p>
        ) : (
          <div className="space-y-1.5">
            {consultantCharters.map(renderCharter)}
          </div>
        )}
      </div>
    </div>
  );
}
