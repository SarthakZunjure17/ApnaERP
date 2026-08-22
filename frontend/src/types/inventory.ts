export interface ProductItem {
  id: string;
  sku: string;
  name: string;
  category: string;
  warehouse: string;
  on_hand: number;
  committed: number;
  available: number;
  unit_price: number;
  formatted_unit_price: string;
  status: 'In Stock' | 'Low Stock' | 'Out of Stock';
  image_url?: string;
  barcode?: string;
}

export interface InventoryMetrics {
  total_skus: {
    value: string;
    trend: string;
    progress_percentage: number;
  };
  low_stock_alerts: {
    count: number;
    categories: { name: string; count: number }[];
  };
  total_stock_value: {
    value: string;
    sparkline_points: number[];
  };
}

export interface CategoryOption {
  id: string;
  name: string;
  code: string;
}

export interface WarehouseOption {
  id: string;
  name: string;
  code: string;
  location: string;
}
