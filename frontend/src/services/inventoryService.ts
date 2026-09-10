import { api } from './api';
import {
  ProductItem,
  ProductCreatePayload,
  CategoryOption,
  UnitOfMeasureOption,
  WarehouseOption,
  StockBalanceItem,
  StockLedgerItem,
  GoodsReceiptItem,
  GoodsIssueItem,
  StockTransferItem,
} from '../types/inventory';

export const inventoryService = {
  // Products
  async getProducts(params?: {
    search?: string;
    category_id?: string;
    warehouse_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<{ items: ProductItem[]; total: number }> {
    const queryParams: Record<string, any> = {
      skip: params?.skip ?? 0,
      limit: params?.limit ?? 100,
    };
    if (params?.search) queryParams.search = params.search;
    if (params?.category_id && params.category_id !== 'All') queryParams.category_id = params.category_id;
    if (params?.warehouse_id && params.warehouse_id !== 'All') queryParams.warehouse_id = params.warehouse_id;

    const response = await api.get('/api/v1/inventory/products', { params: queryParams });
    if (response.data && Array.isArray(response.data.items)) {
      return { items: response.data.items, total: response.data.total ?? response.data.items.length };
    }
    if (Array.isArray(response.data)) {
      return { items: response.data, total: response.data.length };
    }
    return { items: [], total: 0 };
  },

  async getProductById(id: string): Promise<ProductItem | null> {
    const response = await api.get(`/api/v1/inventory/products/${id}`);
    return response.data;
  },

  async createProduct(payload: ProductCreatePayload): Promise<ProductItem> {
    const response = await api.post('/api/v1/inventory/products', payload);
    return response.data;
  },

  async updateProduct(id: string, payload: Partial<ProductCreatePayload>): Promise<ProductItem> {
    const response = await api.put(`/api/v1/inventory/products/${id}`, payload);
    return response.data;
  },

  async deleteProduct(id: string): Promise<boolean> {
    await api.delete(`/api/v1/inventory/products/${id}`);
    return true;
  },

  // Categories & UOMs
  async getCategories(): Promise<CategoryOption[]> {
    const response = await api.get('/api/v1/inventory/categories');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createCategory(data: { name: string; code: string; description?: string }): Promise<CategoryOption> {
    const response = await api.post('/api/v1/inventory/categories', data);
    return response.data;
  },

  async getUOMs(): Promise<UnitOfMeasureOption[]> {
    const response = await api.get('/api/v1/inventory/uoms');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createUOM(data: { name: string; code: string; symbol: string }): Promise<UnitOfMeasureOption> {
    const response = await api.post('/api/v1/inventory/uoms', data);
    return response.data;
  },

  // Warehouses
  async getWarehouses(): Promise<WarehouseOption[]> {
    const response = await api.get('/api/v1/inventory/warehouses');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createWarehouse(data: { name: string; code: string; address?: string }): Promise<WarehouseOption> {
    const response = await api.post('/api/v1/inventory/warehouses', data);
    return response.data;
  },

  // Stock Balances & Ledger
  async getStockBalances(params?: { warehouse_id?: string; product_id?: string }): Promise<StockBalanceItem[]> {
    const response = await api.get('/api/v1/stock/balances', { params });
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async getStockLedger(params?: { warehouse_id?: string; product_id?: string; limit?: number }): Promise<StockLedgerItem[]> {
    const response = await api.get('/api/v1/stock/ledger', { params });
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  // Goods Receipts (GRN)
  async getGoodsReceipts(): Promise<GoodsReceiptItem[]> {
    const response = await api.get('/api/v1/inventory/goods-receipts');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createGoodsReceipt(payload: {
    warehouse_id: string;
    supplier_id?: string;
    po_id?: string;
    receipt_date: string;
    items: Array<{ product_id: string; received_quantity: number; unit_cost?: number }>;
  }): Promise<GoodsReceiptItem> {
    const response = await api.post('/api/v1/inventory/goods-receipts', payload);
    return response.data;
  },

  // Goods Issues (GIN)
  async getGoodsIssues(): Promise<GoodsIssueItem[]> {
    const response = await api.get('/api/v1/inventory/goods-issues');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createGoodsIssue(payload: {
    warehouse_id: string;
    issue_date: string;
    issue_reason: string;
    items: Array<{ product_id: string; issued_quantity: number }>;
  }): Promise<GoodsIssueItem> {
    const response = await api.post('/api/v1/inventory/goods-issues', payload);
    return response.data;
  },

  // Stock Transfers
  async getStockTransfers(): Promise<StockTransferItem[]> {
    const response = await api.get('/api/v1/inventory/stock-transfers');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createStockTransfer(payload: {
    source_warehouse_id: string;
    target_warehouse_id: string;
    transfer_date: string;
    items: Array<{ product_id: string; quantity: number }>;
  }): Promise<StockTransferItem> {
    const response = await api.post('/api/v1/inventory/stock-transfers', payload);
    return response.data;
  },

  async completeStockTransfer(id: string): Promise<StockTransferItem> {
    const response = await api.post(`/api/v1/inventory/stock-transfers/${id}/complete`);
    return response.data;
  },
};
