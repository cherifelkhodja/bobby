import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { AlertTriangle, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { adminApi } from '../../api/admin';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Modal } from '../../components/ui/Modal';
import { getErrorMessage } from '../../api/client';

export function DataResetTab() {
  const [step, setStep] = useState<'idle' | 'confirm1' | 'confirm2'>('idle');
  const [typedConfirm, setTypedConfirm] = useState('');

  const resetMutation = useMutation({
    mutationFn: adminApi.resetContracts,
    onSuccess: (data) => {
      toast.success(data.message);
      setStep('idle');
      setTypedConfirm('');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const handleClose = () => {
    if (!resetMutation.isPending) {
      setStep('idle');
      setTypedConfirm('');
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 p-3 bg-red-100 dark:bg-red-900/30 rounded-lg">
            <Trash2 className="h-6 w-6 text-red-600 dark:text-red-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Remise a zero des contrats
            </h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Supprime toutes les demandes de contrats, contrats cadres,
              documents de conformite, tiers et fichiers S3 associes.
            </p>
            <div className="mt-3 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
              <p className="text-sm font-medium text-amber-800 dark:text-amber-300 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                Donnees preservees
              </p>
              <ul className="mt-1.5 text-xs text-amber-700 dark:text-amber-400 space-y-0.5 ml-6 list-disc">
                <li>Articles et annexes du contrat (templates)</li>
                <li>Societes emettrices (configuration)</li>
                <li>Utilisateurs, invitations, opportunites</li>
              </ul>
            </div>
            <div className="mt-4">
              <Button
                variant="secondary"
                onClick={() => setStep('confirm1')}
                className="border-red-300 text-red-700 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Remise a zero
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Step 1: First confirmation */}
      <Modal
        isOpen={step === 'confirm1'}
        onClose={handleClose}
        title="Confirmer la remise a zero"
      >
        <div className="space-y-4">
          <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <p className="text-sm font-medium text-red-800 dark:text-red-300 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Action irreversible
            </p>
            <p className="mt-2 text-sm text-red-700 dark:text-red-400">
              Toutes les donnees operationnelles de contractualisation seront
              definitivement supprimees :
            </p>
            <ul className="mt-2 text-sm text-red-700 dark:text-red-400 space-y-1 ml-4 list-disc">
              <li>Demandes de contrats cadres</li>
              <li>Contrats cadres generes</li>
              <li>Tiers et documents de conformite</li>
              <li>Liens magiques portail</li>
              <li>Fichiers PDF sur S3</li>
            </ul>
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={handleClose}>
              Annuler
            </Button>
            <Button
              variant="secondary"
              onClick={() => setStep('confirm2')}
              className="border-red-300 text-red-700 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
            >
              Je comprends, continuer
            </Button>
          </div>
        </div>
      </Modal>

      {/* Step 2: Type confirmation code */}
      <Modal
        isOpen={step === 'confirm2'}
        onClose={handleClose}
        title="Derniere confirmation"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Pour confirmer, tapez{' '}
            <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-red-600 dark:text-red-400 font-mono font-bold">
              RESET-CONTRATS
            </code>{' '}
            dans le champ ci-dessous :
          </p>
          <input
            type="text"
            value={typedConfirm}
            onChange={(e) => setTypedConfirm(e.target.value)}
            placeholder="RESET-CONTRATS"
            className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-mono"
            autoFocus
          />
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={handleClose}>
              Annuler
            </Button>
            <Button
              onClick={() => resetMutation.mutate()}
              disabled={typedConfirm !== 'RESET-CONTRATS' || resetMutation.isPending}
              isLoading={resetMutation.isPending}
              className="bg-red-600 hover:bg-red-700 text-white disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Supprimer definitivement
            </Button>
          </div>
        </div>
      </Modal>

      {/* Show results after reset */}
      {resetMutation.isSuccess && resetMutation.data && (
        <Card>
          <h4 className="text-sm font-semibold text-green-700 dark:text-green-400 mb-3">
            Remise a zero terminee
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(resetMutation.data.counts).map(([table, count]) => (
              <div key={table} className="text-xs">
                <span className="text-gray-500 dark:text-gray-400">{table.replace('cm_', '').replace('tp_', '').replace('vig_', '').replace(/_/g, ' ')}</span>
                <span className="ml-2 font-mono font-bold text-gray-900 dark:text-white">{count}</span>
              </div>
            ))}
            <div className="text-xs">
              <span className="text-gray-500 dark:text-gray-400">fichiers S3</span>
              <span className="ml-2 font-mono font-bold text-gray-900 dark:text-white">{resetMutation.data.s3_deleted}</span>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
