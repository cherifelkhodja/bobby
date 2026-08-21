import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  Building2,
  Download,
  FileSignature,
  RefreshCw,
  RotateCcw,
  Send,
  Upload,
  X,
} from 'lucide-react';
import { toast } from 'sonner';

import { purchaseOrdersApi, type PurchaseOrderUpdateInput } from '../api/purchaseOrders';
import { vigilanceApi } from '../api/vigilance';
import { getErrorMessage } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';
import type { PurchaseOrder } from '../types';
import { PURCHASE_ORDER_STATUS_CONFIG } from '../types';

const STEP_LABELS = ['Brouillon', 'Généré', 'Signature', 'Actif'];

interface MissionForm {
  client_name: string;
  mission_title: string;
  mission_description: string;
  mission_site_name: string;
  mission_address: string;
  mission_postal_code: string;
  mission_city: string;
  purchase_daily_rate: string;
  sale_daily_rate: string;
  days_sold: string;
  free_days: string;
  start_date: string;
  end_date: string;
}

function toForm(po: PurchaseOrder): MissionForm {
  return {
    client_name: po.client_name ?? '',
    mission_title: po.mission_title ?? '',
    mission_description: po.mission_description ?? '',
    mission_site_name: po.mission_site_name ?? '',
    mission_address: po.mission_address ?? '',
    mission_postal_code: po.mission_postal_code ?? '',
    mission_city: po.mission_city ?? '',
    purchase_daily_rate: po.purchase_daily_rate?.toString() ?? '',
    sale_daily_rate: po.sale_daily_rate?.toString() ?? '',
    days_sold: po.days_sold?.toString() ?? '',
    free_days: po.free_days?.toString() ?? '0',
    start_date: po.start_date ?? '',
    end_date: po.end_date ?? '',
  };
}

/** Texte vide → null, pour effacer un champ plutôt que d'y écrire "". */
function text(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === '' ? null : trimmed;
}

/** Nombre saisi → null quand le champ est vide, pour distinguer 0 de « non saisi ». */
function num(value: string): number | null {
  const trimmed = value.trim().replace(',', '.');
  if (trimmed === '') return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatAmount(value: number | null): string {
  if (value === null) return '—';
  return `${new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(value)} €`;
}

function formatDate(value: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export function PurchaseOrderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const isAdv = user?.role === 'adv' || user?.role === 'admin';

  const [form, setForm] = useState<MissionForm | null>(null);
  const [supplierId, setSupplierId] = useState('');
  const [showRenew, setShowRenew] = useState(false);
  const [renewForm, setRenewForm] = useState({
    start_date: '',
    end_date: '',
    days_sold: '',
    free_days: '0',
    purchase_daily_rate: '',
  });
  const signedInputRef = useRef<HTMLInputElement>(null);

  const { data: po, isLoading } = useQuery({
    queryKey: ['purchase-order', id],
    queryFn: () => purchaseOrdersApi.get(id!),
    enabled: Boolean(id),
  });

  const { data: suppliers } = useQuery({
    queryKey: ['third-parties', 'picker'],
    queryFn: () => vigilanceApi.listThirdParties({ limit: 200 }),
    enabled: isAdv,
  });

  useEffect(() => {
    if (po && form === null) {
      setForm(toForm(po));
      setSupplierId(po.third_party_id ?? '');
    }
  }, [po, form]);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['purchase-order', id] });
    queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
  };

  const updateMutation = useMutation({
    mutationFn: (data: PurchaseOrderUpdateInput) => purchaseOrdersApi.update(id!, data),
    onSuccess: (updated) => {
      toast.success('Bon de commande mis à jour.');
      setForm(toForm(updated));
      invalidate();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const actionMutation = useMutation({
    mutationFn: async (action: 'generate' | 'send' | 'push' | 'cancel') => {
      if (action === 'generate') return purchaseOrdersApi.generate(id!);
      if (action === 'send') return purchaseOrdersApi.sendForSignature(id!);
      if (action === 'push') return purchaseOrdersApi.pushToBoond(id!);
      return purchaseOrdersApi.cancel(id!);
    },
    onSuccess: () => {
      toast.success('Action effectuée.');
      invalidate();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => purchaseOrdersApi.markAsSigned(id!, file),
    onSuccess: () => {
      toast.success('Bon de commande signé enregistré.');
      invalidate();
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const renewMutation = useMutation({
    mutationFn: () =>
      purchaseOrdersApi.renew(id!, {
        start_date: renewForm.start_date,
        end_date: renewForm.end_date,
        days_sold: num(renewForm.days_sold),
        free_days: num(renewForm.free_days) ?? 0,
        purchase_daily_rate: num(renewForm.purchase_daily_rate),
      }),
    onSuccess: (renewal) => {
      toast.success(`Reconduction ouverte : ${renewal.reference}.`);
      setShowRenew(false);
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      navigate(`/contracts/bdc/${renewal.id}`);
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const downloadDocument = async (signed: boolean) => {
    try {
      const { url } = await purchaseOrdersApi.documentUrl(id!, signed);
      window.open(url, '_blank', 'noopener');
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  // Aperçu des montants pendant la saisie, avant même l'enregistrement.
  const preview = useMemo(() => {
    if (!form) return { billable: null, total: null, margin: null };
    const days = num(form.days_sold);
    const free = num(form.free_days) ?? 0;
    const purchase = num(form.purchase_daily_rate);
    const sale = num(form.sale_daily_rate);
    if (days === null) return { billable: null, total: null, margin: null };
    const billable = Math.max(0, days - free);
    return {
      billable,
      total: purchase === null ? null : billable * purchase,
      margin: purchase === null || sale === null ? null : (sale - purchase) * billable,
    };
  }, [form]);

  if (isLoading || !po || !form) return <PageSpinner />;

  const config = PURCHASE_ORDER_STATUS_CONFIG[po.status];
  const editable = isAdv && po.is_editable;

  const saveMission = () => {
    updateMutation.mutate({
      client_name: text(form.client_name),
      mission_title: text(form.mission_title),
      mission_description: text(form.mission_description),
      mission_site_name: text(form.mission_site_name),
      mission_address: text(form.mission_address),
      mission_postal_code: text(form.mission_postal_code),
      mission_city: text(form.mission_city),
      purchase_daily_rate: num(form.purchase_daily_rate),
      sale_daily_rate: num(form.sale_daily_rate),
      days_sold: num(form.days_sold),
      free_days: num(form.free_days) ?? 0,
      start_date: text(form.start_date),
      end_date: text(form.end_date),
    });
  };

  const field = (key: keyof MissionForm) => ({
    value: form[key],
    disabled: !editable,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm({ ...form, [key]: e.target.value }),
  });

  return (
    <div>
      <button type="button" className="alink mb-3" onClick={() => navigate('/contracts/bdc')}>
        <ArrowLeft className="h-3.5 w-3.5 inline mr-1" />
        Bons de commande
      </button>

      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="h1">
            {po.reference}
            <span className={`st ${config.color} ml-3 align-middle`}>
              <span className="dot" />
              {config.label}
            </span>
          </h1>
          <p className="sub">
            {po.mission_title || 'Mission à préciser'}
            {po.consultant_name ? ` · ${po.consultant_name}` : ''}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {po.has_draft && (
            <Button
              variant="secondary"
              onClick={() => downloadDocument(false)}
              leftIcon={<Download className="h-3.5 w-3.5" />}
            >
              Bon de commande
            </Button>
          )}
          {po.has_signed_document && (
            <Button
              variant="secondary"
              onClick={() => downloadDocument(true)}
              leftIcon={<Download className="h-3.5 w-3.5" />}
            >
              Document signé
            </Button>
          )}
          {isAdv && (po.status === 'draft' || po.status === 'generated') && (
            <Button
              onClick={() => actionMutation.mutate('generate')}
              disabled={po.missing_fields.length > 0 || actionMutation.isPending}
              isLoading={actionMutation.isPending}
              leftIcon={<FileSignature className="h-3.5 w-3.5" />}
            >
              {po.status === 'generated' ? 'Régénérer' : 'Générer le bon de commande'}
            </Button>
          )}
          {isAdv && po.status === 'generated' && (
            <Button
              onClick={() => actionMutation.mutate('send')}
              disabled={!po.can_send_for_signature || actionMutation.isPending}
              title={
                po.framework_contract_signed
                  ? undefined
                  : "Le contrat cadre du fournisseur n'est pas signé"
              }
              leftIcon={<Send className="h-3.5 w-3.5" />}
            >
              Envoyer en signature
            </Button>
          )}
          {isAdv && po.status === 'sent_for_signature' && (
            <>
              <input
                ref={signedInputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) uploadMutation.mutate(file);
                  e.target.value = '';
                }}
              />
              <Button
                onClick={() => signedInputRef.current?.click()}
                isLoading={uploadMutation.isPending}
                leftIcon={<Upload className="h-3.5 w-3.5" />}
              >
                Déposer le document signé
              </Button>
            </>
          )}
          {isAdv && po.status === 'signed' && (
            <Button
              onClick={() => actionMutation.mutate('push')}
              isLoading={actionMutation.isPending}
              leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
            >
              Reporter dans BoondManager
            </Button>
          )}
          {isAdv && (po.status === 'active' || po.status === 'closed') && (
            <Button
              onClick={() => {
                setRenewForm({
                  start_date: '',
                  end_date: '',
                  days_sold: po.days_sold?.toString() ?? '',
                  free_days: '0',
                  purchase_daily_rate: po.purchase_daily_rate?.toString() ?? '',
                });
                setShowRenew(true);
              }}
              leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
            >
              Reconduire
            </Button>
          )}
          {isAdv && po.is_editable && (
            <Button
              variant="secondary"
              onClick={() => {
                if (confirm(`Annuler le bon de commande ${po.reference} ?`)) {
                  actionMutation.mutate('cancel');
                }
              }}
              leftIcon={<X className="h-3.5 w-3.5" />}
            >
              Annuler
            </Button>
          )}
        </div>
      </div>

      {po.needs_third_party && po.status !== 'cancelled' && (
        <div className="alert">
          <AlertTriangle className="h-[18px] w-[18px] shrink-0" />
          <span>
            Ce bon de commande n'est rattaché à aucun fournisseur. Choisissez la société qui porte
            le consultant pour poursuivre.
          </span>
        </div>
      )}

      {!po.needs_third_party && !po.framework_contract_signed && po.status !== 'cancelled' && (
        <div className="alert">
          <AlertTriangle className="h-[18px] w-[18px] shrink-0" />
          <span>
            Contrat cadre en cours de contractualisation
            {po.framework_contract_reference ? ` (${po.framework_contract_reference})` : ''} : le
            bon de commande pourra être envoyé en signature dès qu'il sera signé.
          </span>
          {po.contract_request_id && (
            <button
              type="button"
              className="alink"
              onClick={() => navigate(`/contracts/${po.contract_request_id}`)}
            >
              Ouvrir le contrat cadre →
            </button>
          )}
        </div>
      )}

      {po.boond_sync_error && (
        <div className="alert">
          <AlertTriangle className="h-[18px] w-[18px] shrink-0" />
          <span>BoondManager : {po.boond_sync_error}</span>
        </div>
      )}

      <div className="hdcard">
        <div className="meta">
          <div>
            <p className="ml">Fournisseur</p>
            <p className="mv">{po.third_party_name ?? '—'}</p>
          </div>
          <div>
            <p className="ml">Contrat cadre</p>
            <p className="mv">{po.framework_contract_reference ?? '—'}</p>
          </div>
          <div>
            <p className="ml">Consultant</p>
            <p className="mv">{po.consultant_name || '—'}</p>
          </div>
          <div>
            <p className="ml">Client final</p>
            <p className="mv">{po.client_name ?? '—'}</p>
          </div>
          <div>
            <p className="ml">Période</p>
            <p className="mv">
              {formatDate(po.start_date)} → {formatDate(po.end_date)}
            </p>
          </div>
          <div>
            <p className="ml">Montant HT</p>
            <p className="mv">{formatAmount(po.total_amount)}</p>
          </div>
        </div>
        <div className="steps">
          <div className="track" />
          <div
            className="tfill"
            style={{ width: `${config.stage === 0 ? 0 : ((config.stage - 1) / 3) * 84}%` }}
          />
          <div className="nodes">
            {STEP_LABELS.map((label, index) => (
              <div key={label} className="stw">
                <span
                  className={`nd ${
                    config.stage === 0
                      ? ''
                      : index + 1 < config.stage
                        ? 'd'
                        : index + 1 === config.stage
                          ? 'cur'
                          : ''
                  }`}
                />
                <p className="lb">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {isAdv && (
        <div className="card">
          <h2 className="ct">
            <Building2 className="h-4 w-4 inline mr-2" />
            Fournisseur
          </h2>
          <p className="ds mb-3">
            La société qui porte le consultant. Son contrat cadre est rattaché automatiquement.
          </p>
          <div className="flex items-end gap-2 flex-wrap">
            <div className="flex-1 min-w-64">
              <label className="f-lab" htmlFor="supplier">
                Société du panel
              </label>
              <select
                id="supplier"
                value={supplierId}
                disabled={!editable}
                onChange={(e) => setSupplierId(e.target.value)}
                className="f-in"
              >
                <option value="">— Choisir un fournisseur —</option>
                {(suppliers?.items ?? []).map((tp) => (
                  <option key={tp.id} value={tp.id}>
                    {tp.company_name ?? tp.contact_email}
                    {tp.siren ? ` · ${tp.siren}` : ''}
                  </option>
                ))}
              </select>
            </div>
            <Button
              onClick={() => updateMutation.mutate({ third_party_id: supplierId || null })}
              disabled={!editable || supplierId === (po.third_party_id ?? '')}
              isLoading={updateMutation.isPending}
            >
              Rattacher
            </Button>
          </div>
        </div>
      )}

      <div className="card">
        <h2 className="ct">Mission</h2>
        <div className="f-grid">
          <div>
            <label className="f-lab" htmlFor="client">Client final</label>
            <input id="client" className="f-in" {...field('client_name')} />
          </div>
          <div>
            <label className="f-lab" htmlFor="title">Intitulé</label>
            <input id="title" className="f-in" {...field('mission_title')} />
          </div>
          <div className="col-span-2">
            <label className="f-lab" htmlFor="description">Description</label>
            <textarea id="description" rows={3} className="f-ta" {...field('mission_description')} />
          </div>
          <div>
            <label className="f-lab" htmlFor="site">Site</label>
            <input id="site" className="f-in" {...field('mission_site_name')} />
          </div>
          <div>
            <label className="f-lab" htmlFor="address">Adresse</label>
            <input id="address" className="f-in" {...field('mission_address')} />
          </div>
          <div>
            <label className="f-lab" htmlFor="postal">Code postal</label>
            <input id="postal" className="f-in" {...field('mission_postal_code')} />
          </div>
          <div>
            <label className="f-lab" htmlFor="city">Ville</label>
            <input id="city" className="f-in" {...field('mission_city')} />
          </div>
          <div>
            <label className="f-lab" htmlFor="start">Date de début</label>
            <input id="start" type="date" className="f-in" {...field('start_date')} />
          </div>
          <div>
            <label className="f-lab" htmlFor="end">Date de fin</label>
            <input id="end" type="date" className="f-in" {...field('end_date')} />
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="ct">Conditions financières</h2>
        <div className="f-grid">
          <div>
            <label className="f-lab" htmlFor="cjm">CJM — coût d'achat fournisseur (€)</label>
            <input id="cjm" type="number" step="0.01" className="f-in" {...field('purchase_daily_rate')} />
            <p className="ds mt-1">Seul taux imprimé sur le bon de commande.</p>
          </div>
          <div>
            <label className="f-lab" htmlFor="tjm">TJM — vente client (€)</label>
            <input id="tjm" type="number" step="0.01" className="f-in" {...field('sale_daily_rate')} />
            <p className="ds mt-1">Interne : jamais transmis au fournisseur.</p>
          </div>
          <div>
            <label className="f-lab" htmlFor="days">Jours vendus</label>
            <input id="days" type="number" step="0.5" className="f-in" {...field('days_sold')} />
          </div>
          <div>
            <label className="f-lab" htmlFor="free">Jours de gratuité</label>
            <input id="free" type="number" step="0.5" className="f-in" {...field('free_days')} />
          </div>
        </div>

        <div className="kpis mt-4">
          <div className="kpi">
            <p className="kl">Jours facturables</p>
            <p className="kv">{preview.billable ?? '—'}</p>
            <p className="ks">jours vendus moins gratuité</p>
          </div>
          <div className="kpi">
            <p className="kl">Montant HT</p>
            <p className="kv">{formatAmount(preview.total)}</p>
            <p className="ks">facturable par le fournisseur</p>
          </div>
          <div className="kpi">
            <p className="kl">Marge indicative</p>
            <p className="kv">{formatAmount(preview.margin)}</p>
            <p className="ks">interne, hors document</p>
          </div>
        </div>

        {editable && (
          <div className="flex justify-end mt-4">
            <Button onClick={saveMission} isLoading={updateMutation.isPending}>
              Enregistrer
            </Button>
          </div>
        )}
      </div>

      {po.missing_fields.length > 0 && po.status !== 'cancelled' && (
        <div className="card">
          <p className="dn">Il manque pour générer le bon de commande</p>
          <ul className="mt-2 list-disc pl-5 space-y-1">
            {po.missing_fields.map((label) => (
              <li key={label} className="ds">
                {label}
              </li>
            ))}
          </ul>
        </div>
      )}

      <Modal
        isOpen={showRenew}
        onClose={() => setShowRenew(false)}
        title={`Reconduire ${po.reference}`}
        size="md"
      >
        <div className="space-y-4">
          <p className="ds">
            La reconduction ouvre un nouveau bon de commande, numéroté à la suite, qui reprend le
            consultant, le fournisseur et la mission. Seule la période change — et les conditions,
            si elles ont été revues.
          </p>
          <div className="f-grid">
            <div>
              <label className="f-lab" htmlFor="renew-start">Nouvelle date de début</label>
              <input
                id="renew-start"
                type="date"
                className="f-in"
                value={renewForm.start_date}
                onChange={(e) => setRenewForm({ ...renewForm, start_date: e.target.value })}
              />
            </div>
            <div>
              <label className="f-lab" htmlFor="renew-end">Nouvelle date de fin</label>
              <input
                id="renew-end"
                type="date"
                className="f-in"
                value={renewForm.end_date}
                onChange={(e) => setRenewForm({ ...renewForm, end_date: e.target.value })}
              />
            </div>
            <div>
              <label className="f-lab" htmlFor="renew-days">Jours vendus</label>
              <input
                id="renew-days"
                type="number"
                step="0.5"
                className="f-in"
                value={renewForm.days_sold}
                onChange={(e) => setRenewForm({ ...renewForm, days_sold: e.target.value })}
              />
            </div>
            <div>
              <label className="f-lab" htmlFor="renew-free">Jours de gratuité</label>
              <input
                id="renew-free"
                type="number"
                step="0.5"
                className="f-in"
                value={renewForm.free_days}
                onChange={(e) => setRenewForm({ ...renewForm, free_days: e.target.value })}
              />
            </div>
            <div>
              <label className="f-lab" htmlFor="renew-cjm">CJM (€)</label>
              <input
                id="renew-cjm"
                type="number"
                step="0.01"
                className="f-in"
                value={renewForm.purchase_daily_rate}
                onChange={(e) =>
                  setRenewForm({ ...renewForm, purchase_daily_rate: e.target.value })
                }
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setShowRenew(false)}>
              Annuler
            </Button>
            <Button
              onClick={() => renewMutation.mutate()}
              disabled={!renewForm.start_date || !renewForm.end_date || renewMutation.isPending}
              isLoading={renewMutation.isPending}
            >
              Ouvrir la reconduction
            </Button>
          </div>
        </div>
      </Modal>

      <div className="card">
        <h2 className="ct">BoondManager</h2>
        <div className="meta">
          <div>
            <p className="ml">Positionnement</p>
            <p className="mv font-mono">{po.boond_positioning_id ?? '—'}</p>
          </div>
          <div>
            <p className="ml">Besoin</p>
            <p className="mv font-mono">{po.boond_need_id ?? '—'}</p>
          </div>
          <div>
            <p className="ml">Consultant</p>
            <p className="mv font-mono">
              {po.boond_consultant_id ?? '—'}
              {po.boond_consultant_type ? ` (${po.boond_consultant_type})` : ''}
            </p>
          </div>
          <div>
            <p className="ml">Contrat Boond</p>
            <p className="mv font-mono">{po.boond_contract_id ?? '—'}</p>
          </div>
          <div>
            <p className="ml">Bon de commande Boond</p>
            <p className="mv font-mono">{po.boond_purchase_order_id ?? '—'}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
