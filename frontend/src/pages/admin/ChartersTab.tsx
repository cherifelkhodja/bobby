import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, Trash2, Download, Eye, EyeOff, FileText } from 'lucide-react';
import { toast } from 'sonner';

import { chartersApi } from '../../api/charters';
import type { CharterTemplate } from '../../api/charters';
import { Button } from '../../components/ui/Button';
import { getErrorMessage } from '../../api/client';

const TARGET_LABELS: Record<string, string> = {
  partner: 'Partenaire',
  consultant: 'Collaborateur',
};

const TARGET_COLORS: Record<string, string> = {
  partner: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  consultant: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
};

interface ChartersTabProps {
  companyId: string;
}

export function ChartersTab({ companyId }: ChartersTabProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [showUpload, setShowUpload] = useState(false);
  const [uploadName, setUploadName] = useState('');
  const [uploadVersion, setUploadVersion] = useState('');
  const [uploadTarget, setUploadTarget] = useState<'partner' | 'consultant'>('partner');
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const { data: charters = [], isLoading } = useQuery({
    queryKey: ['admin-charters', companyId],
    queryFn: () => chartersApi.list(companyId),
  });

  const uploadMutation = useMutation({
    mutationFn: () => chartersApi.upload(uploadName, uploadVersion, uploadTarget, companyId, uploadFile!),
    onSuccess: () => {
      toast.success('Charte uploadee.');
      setShowUpload(false);
      setUploadName('');
      setUploadVersion('');
      setUploadFile(null);
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

  const deleteMutation = useMutation({
    mutationFn: (id: string) => chartersApi.delete(id),
    onSuccess: () => {
      toast.success('Charte supprimee.');
      queryClient.invalidateQueries({ queryKey: ['admin-charters', companyId] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const partnerCharters = charters.filter((c) => c.target === 'partner');
  const consultantCharters = charters.filter((c) => c.target === 'consultant');

  const renderCharter = (charter: CharterTemplate) => (
    <div
      key={charter.id}
      className={`flex items-center justify-between p-2.5 rounded-lg border ${
        charter.is_active
          ? 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700'
          : 'bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700 opacity-60'
      }`}
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <FileText className="h-3.5 w-3.5 text-gray-400 shrink-0" />
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <p className="text-xs font-medium text-gray-900 dark:text-white truncate">
              {charter.name}
            </p>
            <span className="text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded px-1 py-0.5">
              {charter.version}
            </span>
            <span className={`text-[10px] rounded-full px-1.5 py-0.5 ${TARGET_COLORS[charter.target]}`}>
              {TARGET_LABELS[charter.target]}
            </span>
          </div>
          <p className="text-[10px] text-gray-500 dark:text-gray-400 truncate">
            {charter.file_name}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-0.5 shrink-0 ml-2">
        <button
          onClick={async () => {
            try {
              const { url } = await chartersApi.getDownloadUrl(charter.id);
              window.open(url, '_blank');
            } catch {
              toast.error('Impossible de telecharger.');
            }
          }}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 transition-colors"
          title="Telecharger"
        >
          <Download className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => toggleMutation.mutate({ id: charter.id, is_active: !charter.is_active })}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 transition-colors"
          title={charter.is_active ? 'Desactiver' : 'Activer'}
        >
          {charter.is_active ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
        </button>
        <button
          onClick={() => {
            if (confirm(`Supprimer la charte "${charter.name} ${charter.version}" ?`)) {
              deleteMutation.mutate(charter.id);
            }
          }}
          className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-colors"
          title="Supprimer"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );

  if (isLoading) return <div className="text-xs text-gray-500 py-2">Chargement...</div>;

  return (
    <div className="space-y-3">
      {/* Upload form */}
      {showUpload ? (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 bg-white dark:bg-gray-800">
          <p className="text-xs font-semibold text-gray-900 dark:text-white mb-3">Nouvelle charte</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
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
          </div>
          <div className="mb-3">
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
          <div className="flex justify-end gap-2">
            <button
              onClick={() => { setShowUpload(false); setUploadFile(null); }}
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
            Nouvelle charte
          </button>
        </div>
      )}

      {/* Partner charters */}
      <div>
        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5 flex items-center gap-1.5">
          <span className={`text-[10px] rounded-full px-1.5 py-0.5 ${TARGET_COLORS.partner}`}>Partenaire</span>
        </p>
        {partnerCharters.length === 0 ? (
          <p className="text-xs text-gray-400 dark:text-gray-500 py-2 text-center">Aucune charte partenaire.</p>
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
          <p className="text-xs text-gray-400 dark:text-gray-500 py-2 text-center">Aucune charte collaborateur.</p>
        ) : (
          <div className="space-y-1.5">
            {consultantCharters.map(renderCharter)}
          </div>
        )}
      </div>
    </div>
  );
}
