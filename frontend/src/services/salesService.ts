import { api } from './api';
import {
  CustomerItem,
  SalesOrderListItem,
  SalesOrderDetail,
  SalesOrderCreatePayload,
  SalesQuotationItem,
  DeliveryOrderItem,
} from '../types/sales';

export const salesService = {
  // Sales Orders
  async getSalesOrders(params?: {
    customer_id?: string;
    status?: string;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<{ items: SalesOrderListItem[]; total: number }> {
    const queryParams: Record<string, any> = {
      skip: params?.skip ?? 0,
      limit: params?.limit ?? 50,
    };
    if (params?.customer_id && params.customer_id !== 'All') queryParams.customer_id = params.customer_id;
    if (params?.status && params.status !== 'All') queryParams.status = params.status;
    if (params?.search) queryParams.search = params.search;

    const response = await api.get('/api/v1/sales/orders', { params: queryParams });
    if (response.data && Array.isArray(response.data.items)) {
      return { items: response.data.items, total: response.data.total ?? response.data.items.length };
    }
    if (Array.isArray(response.data)) {
      return { items: response.data, total: response.data.length };
    }
    return { items: [], total: 0 };
  },

  async getSalesOrderById(id: string): Promise<SalesOrderDetail | null> {
    const response = await api.get(`/api/v1/sales/orders/${id}`);
    return response.data;
  },

  async createSalesOrder(payload: SalesOrderCreatePayload): Promise<SalesOrderDetail> {
    const response = await api.post('/api/v1/sales/orders', payload);
    return response.data;
  },

  async submitSalesOrder(id: string): Promise<SalesOrderDetail> {
    const response = await api.post(`/api/v1/sales/orders/${id}/submit`);
    return response.data;
  },

  async approveSalesOrder(id: string): Promise<SalesOrderDetail> {
    const response = await api.post(`/api/v1/sales/orders/${id}/approve`);
    return response.data;
  },

  async rejectSalesOrder(id: string, reason?: string): Promise<SalesOrderDetail> {
    const response = await api.post(`/api/v1/sales/orders/${id}/reject`, { reason });
    return response.data;
  },

  async cancelSalesOrder(id: string): Promise<SalesOrderDetail> {
    const response = await api.post(`/api/v1/sales/orders/${id}/cancel`);
    return response.data;
  },

  async closeSalesOrder(id: string): Promise<SalesOrderDetail> {
    const response = await api.post(`/api/v1/sales/orders/${id}/close`);
    return response.data;
  },

  // Customers
  async getCustomers(params?: { search?: string }): Promise<CustomerItem[]> {
    const response = await api.get('/api/v1/sales/customers', { params });
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async getCustomerById(id: string): Promise<CustomerItem | null> {
    const response = await api.get(`/api/v1/sales/customers/${id}`);
    return response.data;
  },

  async createCustomer(data: Partial<CustomerItem>): Promise<CustomerItem> {
    const response = await api.post('/api/v1/sales/customers', data);
    return response.data;
  },

  async updateCustomer(id: string, data: Partial<CustomerItem>): Promise<CustomerItem> {
    const response = await api.put(`/api/v1/sales/customers/${id}`, data);
    return response.data;
  },

  // Quotations
  async getQuotations(): Promise<SalesQuotationItem[]> {
    const response = await api.get('/api/v1/sales/quotations');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createQuotation(data: any): Promise<SalesQuotationItem> {
    const response = await api.post('/api/v1/sales/quotations', data);
    return response.data;
  },

  async submitQuotation(id: string): Promise<SalesQuotationItem> {
    const response = await api.post(`/api/v1/sales/quotations/${id}/submit`);
    return response.data;
  },

  async approveQuotation(id: string): Promise<SalesQuotationItem> {
    const response = await api.post(`/api/v1/sales/quotations/${id}/approve`);
    return response.data;
  },

  async convertQuotationToOrder(quotationId: string): Promise<SalesOrderDetail> {
    const response = await api.post(`/api/v1/sales-orders/from-quotation/${quotationId}`, {});
    return response.data;
  },

  // Delivery Orders
  async getDeliveryOrders(): Promise<DeliveryOrderItem[]> {
    const response = await api.get('/api/v1/sales/deliveries');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createDeliveryOrder(data: any): Promise<DeliveryOrderItem> {
    const response = await api.post('/api/v1/sales/deliveries', data);
    return response.data;
  },
};
