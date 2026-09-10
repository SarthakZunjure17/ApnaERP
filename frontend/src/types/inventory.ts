export interface CategoryOption {
  id: string;
  name: string;
  code: string;
  description?: string;
}

export interface UnitOfMeasureOption {
  id: string;
  name: string;
  code: string;
  symbol: string;
}

export interface WarehouseOption {
  id: string;
  name: string;
  code: string;
  address?: string;
  is_active: boolean;
}

export interface StorageLocationOption {
  id: string;
  warehouse_id: string;
  name: string;
  code: string;
}

export interface ProductItem {
  id: string;
  sku: string;
  name: string;
  category_id?: string;
  category_name?: string;
  uom_id?: string;
  uom_name?: string;
  brand_name?: string;
  cost_price: number;
  selling_price: number;
  min_stock_level?: number;
  max_stock_level?: number;
  total_on_hand?: number;
  total_available?: number;
  total_reserved?: number;
  is_active: boolean;
  barcode?: string;
  description?: string;
}

export interface ProductCreatePayload {
  sku: string;
  name: string;
  category_id: string;
  uom_id: string;
  brand_id?: string;
  cost_price: number;
  selling_price: number;
  min_stock_level?: number;
  max_stock_level?: number;
  barcode?: string;
  description?: string;
}

export interface StockBalanceItem {
  id: string;
  product_id: string;
  product_sku: string;
  product_name: string;
  warehouse_id: string;
  warehouse_name: string;
  location_id?: string;
  location_name?: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
  updated_at: string;
}

export interface StockLedgerItem {
  id: string;
  product_id: string;
  product_sku: string;
  product_name: string;
  warehouse_id: string;
  warehouse_name: string;
  transaction_type: string;
  reference_type?: string;
  reference_id?: string;
  quantity: number;
  balance_after: number;
  unit_cost?: number;
  created_at: string;
  notes?: string;
}

export interface GoodsReceiptItem {
  id: string;
  grn_number: string;
  warehouse_id: string;
  warehouse_name?: string;
  supplier_id?: string;
  supplier_name?: string;
  po_id?: string;
  po_number?: string;
  receipt_date: string;
  status: 'Draft' | 'Inspected' | 'Completed' | 'Cancelled' | string;
  created_at: string;
  items_count?: number;
  items?: any[];
}

export interface GoodsIssueItem {
  id: string;
  gin_number: string;
  warehouse_id: string;
  warehouse_name?: string;
  issue_date: string;
  issue_reason: string;
  status: 'Draft' | 'Completed' | 'Cancelled' | string;
  created_at: string;
  items_count?: number;
  items?: any[];
}

export interface StockTransferItem {
  id: string;
  transfer_number: string;
  source_warehouse_id: string;
  source_warehouse_name?: string;
  target_warehouse_id: string;
  target_warehouse_name?: string;
  transfer_date: string;
  status: 'Draft' | 'In Transit' | 'Completed' | 'Cancelled';
  created_at: string;
  items?: any[];
}
