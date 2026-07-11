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
          <div className="flex-shrink-0 p-3 bg-red-bg rounded-[9px]">
            <Trash2 className="h-6 w-6 text-red-fg" />
          </div>
          <div className="flex-1">
            <h3 className="ct">
              Remise a zero des contrats
            </h3>
            <p className="mt-1 text-[13px] text-mut">
              Supprime toutes les demandes de contrats, contrats cadres,
              documents de conformite, tiers et fichiers S3 associes.
            </p>
            <div className="mt-3 p-3 bg-amb-bg rounded-[10px] border border-[color-mix(in_oklab,var(--amb-fg)_25%,transparent)]">
              <p className="text-[13px] font-semibold text-amb-fg flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                Donnees preservees
              </p>
              <ul className="mt-1.5 text-xs text-amb-fg space-y-0.5 ml-6 list-disc">
                <li>Articles et annexes du contrat (templates)</li>
                <li>Societes emettrices (configuration)</li>
                <li>Utilisateurs, invitations, opportunites</li>
              </ul>
            </div>
            <div className="mt-4">
              <Button
                variant="secondary"
                onClick={() => setStep('confirm1')}
                className="!text-redt !border-[color-mix(in_oklab,var(--redt)_40%,transparent)] hover:!bg-red-bg"
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
          <div className="p-4 bg-red-bg rounded-[10px] border border-[color-mix(in_oklab,var(--red-fg)_25%,transparent)]">
            <p className="text-[13px] font-semibold text-red-fg flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Action irreversible
            </p>
            <p className="mt-2 text-[13px] text-red-fg">
              Toutes les donnees operationnelles de contractualisation seront
              definitivement supprimees :
            </p>
            <ul className="mt-2 text-[13px] text-red-fg space-y-1 ml-4 list-disc">
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
              className="!text-redt !border-[color-mix(in_oklab,var(--redt)_40%,transparent)] hover:!bg-red-bg"
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
          <p className="text-[13px] text-mut">
            Pour confirmer, tapez{' '}
            <code className="px-1.5 py-0.5 bg-lin2 rounded text-redt font-mono font-bold">
              RESET-CONTRATS
            </code>{' '}
            dans le champ ci-dessous :
          </p>
          <input
            type="text"
            value={typedConfirm}
            onChange={(e) => setTypedConfirm(e.target.value)}
            placeholder="RESET-CONTRATS"
            className="f-in font-mono"
            autoFocus
          />
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={handleClose}>
              Annuler
            </Button>
            <Button
              variant="danger"
              onClick={() => resetMutation.mutate()}
              disabled={typedConfirm !== 'RESET-CONTRATS' || resetMutation.isPending}
              isLoading={resetMutation.isPending}
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
          <h4 className="text-[13px] font-semibold text-grn-fg mb-3">
            Remise a zero terminee
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(resetMutation.data.counts).map(([table, count]) => (
              <div key={table} className="text-xs">
                <span className="text-mut">{table.replace('cm_', '').replace('tp_', '').replace('vig_', '').replace(/_/g, ' ')}</span>
                <span className="ml-2 font-mono font-bold text-ink">{count}</span>
              </div>
            ))}
            <div className="text-xs">
              <span className="text-mut">fichiers S3</span>
              <span className="ml-2 font-mono font-bold text-ink">{resetMutation.data.s3_deleted}</span>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
