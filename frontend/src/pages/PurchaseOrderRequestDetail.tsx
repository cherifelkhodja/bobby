import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ShoppingCart, CheckCircle, AlertTriangle, Trash2, Lock } from 'lucide-react';
import { toast } from 'sonner';

import { purchaseOrderRequestsApi } from '../api/contracts';
import { useAuthStore } from '../stores/authStore';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';
import { getErrorMessage } from '../api/client';
import { POR_STATUS_CONFIG } from '../types';

const INPUT_CLS =
  'w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300';

export default function PurchaseOrderRequestDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const isAdv = user?.role === 'adv' || user?.role === 'admin';

  const [showCancelModal, setShowCancelModal] = useState(false);
  const [form, setForm] = useState({
    daily_rate: '',
    quantity_sold: '',
    start_date: '',
    end_date: '',
    client_name: '',
    mission_title: '',
    consultant_civility: '',
    consultant_first_name: '',
    consultant_last_name: '',
    consultant_email: '',
    consultant_phone: '',
  });
  const [formInitialized, setFormInitialized] = useState(false);

  const { data: por, isLoading } = useQuery({
    queryKey: ['purchase-order-request', id],
    queryFn: () => purchaseOrderRequestsApi.get(id!),
    enabled: !!id,
  });

  // Pre-fill form from Boond data
  useEffect(() => {
    if (por && !formInitialized) {
      setForm({
        daily_rate: por.daily_rate?.toString() ?? '',
        quantity_sold: por.quantity_sold?.toString() ?? '',
        start_date: por.start_date ?? '',
        end_date: por.end_date ?? '',
        client_name: por.client_name ?? '',
        mission_title: por.mission_title ?? '',
        consultant_civility: por.consultant_civility ?? '',
        consultant_first_name: por.consultant_first_name ?? '',
        consultant_last_name: por.consultant_last_name ?? '',
        consultant_email: por.consultant_email ?? '',
        consultant_phone: por.consultant_phone ?? '',
      });
      setFormInitialized(true);
    }
  }, [por, formInitialized]);

  const validateMutation = useMutation({
    mutationFn: () =>
      purchaseOrderRequestsApi.validate(id!, {
        daily_rate: parseFloat(form.daily_rate),
        start_date: form.start_date,
        end_date: form.end_date || undefined,
        quantity_sold: form.quantity_sold ? parseInt(form.quantity_sold, 10) : undefined,
        client_name: form.client_name || undefined,
        mission_title: form.mission_title || undefined,
        consultant_civility: form.consultant_civility || undefined,
        consultant_first_name: form.consultant_first_name || undefined,
        consultant_last_name: form.consultant_last_name || undefined,
        consultant_email: form.consultant_email || undefined,
        consultant_phone: form.consultant_phone || undefined,
      }),
    onSuccess: () => {
      toast.success('BDC validé et en vérification de conformité.');
      queryClient.invalidateQueries({ queryKey: ['purchase-order-request', id] });
      queryClient.invalidateQueries({ queryKey: ['purchase-order-requests'] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const finalizeMutation = useMutation({
    mutationFn: () => purchaseOrderRequestsApi.finalize(id!),
    onSuccess: () => {
      toast.success('Bon de commande créé avec succès.');
      queryClient.invalidateQueries({ queryKey: ['purchase-order-request', id] });
      queryClient.invalidateQueries({ queryKey: ['purchase-order-requests'] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const cancelMutation = useMutation({
    mutationFn: () => purchaseOrderRequestsApi.cancel(id!),
    onSuccess: () => {
      toast.success('Demande de BDC annulée.');
      setShowCancelModal(false);
      queryClient.invalidateQueries({ queryKey: ['purchase-order-requests'] });
      navigate('/contracts');
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  if (isLoading || !por) return <PageSpinner />;

  const statusConfig = POR_STATUS_CONFIG[por.status];
  const canValidate = por.status === 'pending_validation';
  const canFinalize = isAdv && (por.status === 'checking_compliance' || por.status === 'validated');
  const canCancel = isAdv && !['cancelled', 'archived'].includes(por.status);

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/contracts')}
          className="flex items-center text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Retour aux contrats
        </button>

        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <ShoppingCart className="h-6 w-6 text-emerald-500" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{por.reference}</h1>
            </div>
            <div className="flex items-center gap-3 mt-2">
              <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${statusConfig?.color ?? 'bg-gray-100 text-gray-600'}`}>
                {statusConfig?.label ?? por.status_display}
              </span>
              {por.framework_contract_reference && (
                <span className="text-sm text-emerald-600 dark:text-emerald-400">
                  Contrat cadre: {por.framework_contract_reference}
                </span>
              )}
              {por.client_name && <span className="text-sm text-gray-600 dark:text-gray-400">{por.client_name}</span>}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {canFinalize && (
              <Button onClick={() => finalizeMutation.mutate()} isLoading={finalizeMutation.isPending}>
                <CheckCircle className="h-4 w-4 mr-2" />
                Créer le bon de commande
              </Button>
            )}
            {canCancel && (
              <Button variant="secondary" onClick={() => setShowCancelModal(true)}>
                <Trash2 className="h-4 w-4 mr-2" />
                Annuler
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Locked: waiting for framework contract */}
      {por.status === 'pending_framework_contract' && (
        <Card className="mb-6 border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20">
          <div className="flex items-start gap-3">
            <Lock className="h-5 w-5 text-amber-500 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                En attente du contrat cadre
              </h3>
              <p className="text-xs text-amber-700 dark:text-amber-400 mt-1">
                Ce bon de commande a été créé depuis le positionnement, mais il ne
                pourra être édité et validé qu'une fois le consultant devenu ressource
                et rattaché à un contrat cadre signé avec son fournisseur. Il se
                débloquera automatiquement à la signature du contrat cadre.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Compliance expired warning */}
      {por.status === 'compliance_expired' && (
        <Card className="mb-6 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-red-800 dark:text-red-300">Documents de conformité expirés</h3>
              <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                Les documents du fournisseur ne sont plus à jour. Veuillez contacter le fournisseur pour mettre à jour ses documents avant de finaliser le bon de commande.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Validation form */}
      {canValidate && (
        <Card className="mb-6 border-yellow-200 dark:border-yellow-800">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Validation commerciale</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">CJM (€) *</label>
              <input type="number" step="0.01" value={form.daily_rate} onChange={(e) => setForm((f) => ({ ...f, daily_rate: e.target.value }))} className={INPUT_CLS} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Quantité (jours)</label>
              <input type="number" value={form.quantity_sold} onChange={(e) => setForm((f) => ({ ...f, quantity_sold: e.target.value }))} className={INPUT_CLS} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Date de début *</label>
              <input type="date" value={form.start_date} onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))} className={INPUT_CLS} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Date de fin</label>
              <input type="date" value={form.end_date} onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))} className={INPUT_CLS} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Client final</label>
              <input type="text" value={form.client_name} onChange={(e) => setForm((f) => ({ ...f, client_name: e.target.value }))} className={INPUT_CLS} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Intitulé mission</label>
              <input type="text" value={form.mission_title} onChange={(e) => setForm((f) => ({ ...f, mission_title: e.target.value }))} className={INPUT_CLS} />
            </div>

            <div className="md:col-span-2 border-t border-gray-200 dark:border-gray-700 pt-4 mt-2">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">Consultant</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Prénom</label>
              <input type="text" value={form.consultant_first_name} onChange={(e) => setForm((f) => ({ ...f, consultant_first_name: e.target.value }))} className={INPUT_CLS} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Nom</label>
              <input type="text" value={form.consultant_last_name} onChange={(e) => setForm((f) => ({ ...f, consultant_last_name: e.target.value }))} className={INPUT_CLS} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
              <input type="email" value={form.consultant_email} onChange={(e) => setForm((f) => ({ ...f, consultant_email: e.target.value }))} className={INPUT_CLS} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Téléphone</label>
              <input type="tel" value={form.consultant_phone} onChange={(e) => setForm((f) => ({ ...f, consultant_phone: e.target.value }))} className={INPUT_CLS} />
            </div>
          </div>
          <div className="mt-6 flex justify-end">
            <Button onClick={() => validateMutation.mutate()} isLoading={validateMutation.isPending} disabled={!form.daily_rate || !form.start_date}>
              Valider le bon de commande
            </Button>
          </div>
        </Card>
      )}

      {/* Summary (when already validated) */}
      {por.status !== 'pending_validation' && (
        <Card className="mb-6">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Récapitulatif</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">CJM</p>
              <p className="font-medium text-gray-900 dark:text-white">{por.daily_rate ? `${por.daily_rate}€/j` : '-'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Date de début</p>
              <p className="font-medium text-gray-900 dark:text-white">{por.start_date ? formatDate(por.start_date) : '-'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Date de fin</p>
              <p className="font-medium text-gray-900 dark:text-white">{por.end_date ? formatDate(por.end_date) : '-'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Consultant</p>
              <p className="font-medium text-gray-900 dark:text-white">
                {por.consultant_first_name} {por.consultant_last_name}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Client final</p>
              <p className="font-medium text-gray-900 dark:text-white">{por.client_name || '-'}</p>
            </div>
          </div>
        </Card>
      )}

      {/* Status history */}
      {por.status_history.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Historique</h3>
          <ol className="relative border-l border-gray-200 dark:border-gray-700 ml-2">
            {[...por.status_history].reverse().map((entry, idx) => {
              const cfg = POR_STATUS_CONFIG[entry.status as keyof typeof POR_STATUS_CONFIG];
              return (
                <li key={idx} className="ml-4 mb-3">
                  <span className="absolute -left-1.5 mt-1 h-3 w-3 rounded-full border-2 border-white dark:border-gray-800 bg-gray-400" />
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cfg?.color ?? 'bg-gray-100 text-gray-700'}`}>
                      {cfg?.label ?? entry.status}
                    </span>
                    <span className="text-xs text-gray-400">{formatDate(entry.entered_at)}</span>
                  </div>
                </li>
              );
            })}
          </ol>
        </Card>
      )}

      {/* Cancel modal */}
      <Modal isOpen={showCancelModal} onClose={() => setShowCancelModal(false)} title="Annuler la demande de BDC">
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Voulez-vous vraiment annuler la demande <span className="font-semibold">{por.reference}</span> ?
          </p>
          <p className="text-sm text-red-600 dark:text-red-400">Cette action est irréversible.</p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setShowCancelModal(false)} disabled={cancelMutation.isPending}>Non, garder</Button>
            <Button variant="primary" onClick={() => cancelMutation.mutate()} isLoading={cancelMutation.isPending} className="bg-red-600 hover:bg-red-700 text-white">Oui, annuler</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
