import { api } from './api';
import {
  SupplierItem,
  PurchaseOrderListItem,
  PurchaseOrderDetail,
  PurchaseOrderCreatePayload,
  PurchaseRequisitionItem,
  RFQItem,
} from '../types/procurement';

export const procurementService = {
  // Purchase Orders
  async getPurchaseOrders(params?: {
    supplier_id?: string;
    status?: string;
    search?: string;
    page?: number;
    size?: number;
  }): Promise<{ items: PurchaseOrderListItem[]; total: number }> {
    const queryParams: Record<string, any> = {
      page: params?.page ?? 1,
      size: params?.size ?? 50,
    };
    if (params?.supplier_id && params.supplier_id !== 'All') queryParams.supplier_id = params.supplier_id;
    if (params?.status && params.status !== 'All') queryParams.status = params.status;
    if (params?.search) queryParams.search = params.search;

    const response = await api.get('/api/v1/procurement/orders', { params: queryParams });
    if (response.data && Array.isArray(response.data.items)) {
      return { items: response.data.items, total: response.data.total ?? response.data.items.length };
    }
    if (Array.isArray(response.data)) {
      return { items: response.data, total: response.data.length };
    }
    return { items: [], total: 0 };
  },

  async getPurchaseOrderById(id: string): Promise<PurchaseOrderDetail | null> {
    const response = await api.get(`/api/v1/procurement/orders/${id}`);
    return response.data;
  },

  async createPurchaseOrder(payload: PurchaseOrderCreatePayload): Promise<PurchaseOrderDetail> {
    const response = await api.post('/api/v1/procurement/orders', payload);
    return response.data;
  },

  async submitPurchaseOrder(id: string): Promise<PurchaseOrderDetail> {
    const response = await api.post(`/api/v1/procurement/orders/${id}/submit`);
    return response.data;
  },

  async approvePurchaseOrder(id: string): Promise<PurchaseOrderDetail> {
    const response = await api.post(`/api/v1/procurement/orders/${id}/approve`);
    return response.data;
  },

  async rejectPurchaseOrder(id: string, reason?: string): Promise<PurchaseOrderDetail> {
    const response = await api.post(`/api/v1/procurement/orders/${id}/reject`, { reason });
    return response.data;
  },

  async cancelPurchaseOrder(id: string): Promise<PurchaseOrderDetail> {
    const response = await api.post(`/api/v1/procurement/orders/${id}/cancel`);
    return response.data;
  },

  // Suppliers
  async getSuppliers(): Promise<SupplierItem[]> {
    const response = await api.get('/api/v1/procurement/suppliers');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createSupplier(data: Partial<SupplierItem>): Promise<SupplierItem> {
    const response = await api.post('/api/v1/procurement/suppliers', data);
    return response.data;
  },

  // Requisitions & RFQs
  async getRequisitions(): Promise<PurchaseRequisitionItem[]> {
    const response = await api.get('/api/v1/procurement/requisitions');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createRequisition(data: any): Promise<PurchaseRequisitionItem> {
    const response = await api.post('/api/v1/procurement/requisitions', data);
    return response.data;
  },

  async getRFQs(): Promise<RFQItem[]> {
    const response = await api.get('/api/v1/procurement/rfqs');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },
};
