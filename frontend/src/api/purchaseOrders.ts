import { apiClient } from './client';

import type {
  BoondDeletion,
  PanelSupplierListResponse,
  PurchaseOrder,
  PurchaseOrderListResponse,
  PurchaseOrderStatus,
} from '../types';

/**
 * Champs de mission modifiables d'un bon de commande.
 *
 * Seules les clés transmises sont appliquées côté serveur : envoyer `null`
 * efface la valeur, omettre la clé la laisse intacte.
 */
export interface PurchaseOrderUpdateInput {
  third_party_id?: string | null;
  company_id?: string | null;
  client_name?: string | null;
  mission_title?: string | null;
  mission_description?: string | null;
  mission_site_name?: string | null;
  mission_address?: string | null;
  mission_postal_code?: string | null;
  mission_city?: string | null;
  sale_daily_rate?: number | null;
  purchase_daily_rate?: number | null;
  days_sold?: number | null;
  free_days?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  consultant_civility?: string | null;
  consultant_first_name?: string | null;
  consultant_last_name?: string | null;
  consultant_email?: string | null;
  consultant_phone?: string | null;
  boond_need_id?: number | null;
  commercial_email?: string | null;
}

export const purchaseOrdersApi = {
  /**
   * Fournisseurs rattachables : ceux du panel de la société émettrice, c'est-à-dire
   * avec qui elle a un contrat cadre signé ou en cours. Sans `company_id`, tout
   * le panel du groupe est renvoyé.
   */
  panelSuppliers: async (companyId?: string | null): Promise<PanelSupplierListResponse> => {
    const response = await apiClient.get<PanelSupplierListResponse>(
      '/purchase-orders/suppliers',
      { params: companyId ? { company_id: companyId } : undefined },
    );
    return response.data;
  },

  /**
   * `company_id` et `contract_request_id` isolent les missions d'une société
   * émettrice : un fournisseur travaillant avec plusieurs sociétés du groupe a
   * des missions distinctes pour chacune.
   */
  list: async (params?: {
    skip?: number;
    limit?: number;
    status_filter?: PurchaseOrderStatus;
    third_party_id?: string;
    company_id?: string;
    contract_request_id?: string;
    search?: string;
  }): Promise<PurchaseOrderListResponse> => {
    const response = await apiClient.get<PurchaseOrderListResponse>('/purchase-orders', {
      params,
    });
    return response.data;
  },

  get: async (id: string): Promise<PurchaseOrder> => {
    const response = await apiClient.get<PurchaseOrder>(`/purchase-orders/${id}`);
    return response.data;
  },

  /** Ouvre un bon de commande depuis un positionnement Boond gagné. */
  create: async (boondPositioningId: number): Promise<PurchaseOrder> => {
    const response = await apiClient.post<PurchaseOrder>('/purchase-orders', {
      boond_positioning_id: boondPositioningId,
    });
    return response.data;
  },

  update: async (id: string, data: PurchaseOrderUpdateInput): Promise<PurchaseOrder> => {
    const response = await apiClient.patch<PurchaseOrder>(`/purchase-orders/${id}`, data);
    return response.data;
  },

  /** Reconduit la mission : nouveau bon de commande, numéroté à la suite. */
  renew: async (
    id: string,
    data: {
      start_date: string;
      end_date: string;
      days_sold?: number | null;
      free_days?: number | null;
      purchase_daily_rate?: number | null;
      sale_daily_rate?: number | null;
    },
  ): Promise<PurchaseOrder> => {
    const response = await apiClient.post<PurchaseOrder>(`/purchase-orders/${id}/renew`, data);
    return response.data;
  },

  cancel: async (id: string): Promise<PurchaseOrder> => {
    const response = await apiClient.post<PurchaseOrder>(`/purchase-orders/${id}/cancel`);
    return response.data;
  },

  generate: async (id: string): Promise<PurchaseOrder> => {
    const response = await apiClient.post<PurchaseOrder>(`/purchase-orders/${id}/generate`);
    return response.data;
  },

  documentUrl: async (id: string, signed = false): Promise<{ url: string }> => {
    const response = await apiClient.get<{ url: string }>(`/purchase-orders/${id}/document`, {
      params: { signed },
    });
    return response.data;
  },

  sendForSignature: async (id: string): Promise<PurchaseOrder> => {
    const response = await apiClient.post<PurchaseOrder>(
      `/purchase-orders/${id}/send-for-signature`,
    );
    return response.data;
  },

  markAsSigned: async (id: string, file: File): Promise<PurchaseOrder> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<PurchaseOrder>(
      `/purchase-orders/${id}/mark-as-signed`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
    return response.data;
  },

  /**
   * Rattache à la main la prestation Boond que le report n'a pas su retrouver.
   * L'achat fournisseur s'y accroche : sans elle, le report s'arrête là.
   */
  attachDelivery: async (id: string, deliveryId: number): Promise<PurchaseOrder> => {
    const response = await apiClient.post<PurchaseOrder>(
      `/purchase-orders/${id}/attach-delivery`,
      { delivery_id: deliveryId },
    );
    return response.data;
  },

  pushToBoond: async (id: string): Promise<PurchaseOrder> => {
    const response = await apiClient.post<PurchaseOrder>(`/purchase-orders/${id}/push-to-boond`);
    return response.data;
  },

  // Outil de test : défait le report pour pouvoir le rejouer.
  deleteFromBoond: async (id: string): Promise<BoondDeletion> => {
    const response = await apiClient.post<BoondDeletion>(
      `/purchase-orders/${id}/delete-from-boond`,
    );
    return response.data;
  },
};
