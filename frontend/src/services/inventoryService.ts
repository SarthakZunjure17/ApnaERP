import { api } from './api';
import { ProductItem, InventoryMetrics, CategoryOption, WarehouseOption } from '../types/inventory';

const MOCK_METRICS: InventoryMetrics = {
  total_skus: {
    value: '1,240',
    trend: '2.4%',
    progress_percentage: 65,
  },
  low_stock_alerts: {
    count: 14,
    categories: [
      { name: 'Electronics', count: 5 },
      { name: 'Apparel', count: 9 },
    ],
  },
  total_stock_value: {
    value: '$2.1M',
    sparkline_points: [12, 14, 18, 16, 22, 28, 26, 32, 30, 36, 40],
  },
};

const MOCK_PRODUCTS: ProductItem[] = [
  {
    id: 'prod-001',
    sku: 'AU-WH-001',
    name: 'Aura Wireless Headphones',
    category: 'Electronics',
    warehouse: 'Main Hub (NY)',
    on_hand: 342,
    committed: 12,
    available: 330,
    unit_price: 299.0,
    formatted_unit_price: '$299.00',
    status: 'In Stock',
    image_url: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=100&auto=format&fit=crop&q=80',
    barcode: '8901234567890',
  },
  {
    id: 'prod-002',
    sku: 'FUR-OC-992',
    name: 'ErgoPro Office Chair',
    category: 'Furniture',
    warehouse: 'West Coast (CA)',
    on_hand: 8,
    committed: 6,
    available: 2,
    unit_price: 450.0,
    formatted_unit_price: '$450.00',
    status: 'Low Stock',
    image_url: 'https://images.unsplash.com/photo-1580481077197-9860b299e525?w=100&auto=format&fit=crop&q=80',
    barcode: '8901234567891',
  },
  {
    id: 'prod-003',
    sku: 'AU-KB-045',
    name: 'Nova Mechanical Keyboard',
    category: 'Electronics',
    warehouse: 'Main Hub (NY)',
    on_hand: 15,
    committed: 15,
    available: 0,
    unit_price: 129.0,
    formatted_unit_price: '$129.00',
    status: 'Out of Stock',
    image_url: 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=100&auto=format&fit=crop&q=80',
    barcode: '8901234567892',
  },
  {
    id: 'prod-004',
    sku: 'FUR-DL-112',
    name: 'Lumina Desk Lamp',
    category: 'Furniture',
    warehouse: 'Main Hub (NY)',
    on_hand: 1204,
    committed: 45,
    available: 1159,
    unit_price: 85.0,
    formatted_unit_price: '$85.00',
    status: 'In Stock',
    image_url: 'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=100&auto=format&fit=crop&q=80',
    barcode: '8901234567893',
  },
  {
    id: 'prod-005',
    sku: 'LOG-MW-500',
    name: 'Precision Wireless Mouse',
    category: 'Electronics',
    warehouse: 'West Coast (CA)',
    on_hand: 520,
    committed: 30,
    available: 490,
    unit_price: 69.0,
    formatted_unit_price: '$69.00',
    status: 'In Stock',
    image_url: 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=100&auto=format&fit=crop&q=80',
    barcode: '8901234567894',
  },
];

const MOCK_CATEGORIES: CategoryOption[] = [
  { id: 'cat-1', name: 'All Categories', code: 'ALL' },
  { id: 'cat-2', name: 'Electronics', code: 'ELEC' },
  { id: 'cat-3', name: 'Furniture', code: 'FURN' },
  { id: 'cat-4', name: 'Apparel', code: 'APP' },
  { id: 'cat-5', name: 'Office Supplies', code: 'OFF' },
];

const MOCK_WAREHOUSES: WarehouseOption[] = [
  { id: 'wh-1', name: 'All Warehouses', code: 'ALL', location: 'Global' },
  { id: 'wh-2', name: 'Main Hub (NY)', code: 'NY-01', location: 'New York, NY' },
  { id: 'wh-3', name: 'West Coast (CA)', code: 'CA-02', location: 'San Francisco, CA' },
  { id: 'wh-4', name: 'Central Logistics (TX)', code: 'TX-03', location: 'Dallas, TX' },
];

function calculateDynamicMetrics(): InventoryMetrics {
  const total = MOCK_PRODUCTS.length;
  const lowStock = MOCK_PRODUCTS.filter((p) => p.status === 'Low Stock' || p.status === 'Out of Stock');
  const catCountMap: Record<string, number> = {};
  lowStock.forEach((p) => {
    catCountMap[p.category] = (catCountMap[p.category] || 0) + 1;
  });

  const lowStockCategories = Object.entries(catCountMap).map(([name, count]) => ({
    name,
    count,
  }));

  const totalValueNum = MOCK_PRODUCTS.reduce((sum, p) => sum + p.on_hand * p.unit_price, 0);
  const formattedVal = totalValueNum >= 1000000 
    ? `$${(totalValueNum / 1000000).toFixed(1)}M`
    : `$${(totalValueNum / 1000).toFixed(1)}K`;

  return {
    total_skus: {
      value: String(total),
      trend: '+2.4%',
      progress_percentage: Math.min(100, Math.round((total / 20) * 100)),
    },
    low_stock_alerts: {
      count: lowStock.length,
      categories: lowStockCategories.length > 0 ? lowStockCategories : [{ name: 'Electronics', count: 1 }],
    },
    total_stock_value: {
      value: formattedVal,
      sparkline_points: [12, 14, 18, 16, 22, 28, 26, 32, 30, 36, 40],
    },
  };
}

export const inventoryService = {
  getMetrics: async (): Promise<InventoryMetrics> => {
    try {
      const response = await api.get('/api/v1/inventory/analytics/kpis');
      if (response.data && typeof response.data === 'object' && response.data.total_skus) {
        return response.data;
      }
      return calculateDynamicMetrics();
    } catch {
      return calculateDynamicMetrics();
    }
  },

  getProducts: async (filters?: {
    search?: string;
    category?: string;
    warehouse?: string;
    stockLevel?: string;
  }): Promise<{ items: ProductItem[]; total: number }> => {
    try {
      const params: Record<string, string> = {};
      if (filters?.search) params.search = filters.search;
      if (filters?.category && filters.category !== 'All Categories') params.category = filters.category;
      if (filters?.warehouse && filters.warehouse !== 'All Warehouses') params.warehouse = filters.warehouse;

      const response = await api.get('/api/v1/inventory/products', { params });
      if (response.data && typeof response.data === 'object' && Array.isArray(response.data.items)) {
        return response.data;
      }
      if (response.data && Array.isArray(response.data)) {
        return { items: response.data, total: response.data.length };
      }
      return filterMockProducts(filters);
    } catch {
      return filterMockProducts(filters);
    }
  },

  getProductById: async (id: string): Promise<ProductItem | null> => {
    if (!id) return null;
    const cleanId = id.trim().toLowerCase();
    const found = MOCK_PRODUCTS.find(
      (p) => p.id.toLowerCase() === cleanId || p.sku.toLowerCase() === cleanId
    );
    return found || null;
  },

  getCategories: async (): Promise<CategoryOption[]> => {
    try {
      const response = await api.get('/api/v1/inventory/categories');
      if (response.data && Array.isArray(response.data)) return response.data;
      return MOCK_CATEGORIES;
    } catch {
      return MOCK_CATEGORIES;
    }
  },

  getWarehouses: async (): Promise<WarehouseOption[]> => {
    try {
      const response = await api.get('/api/v1/inventory/warehouses');
      if (response.data && Array.isArray(response.data)) return response.data;
      return MOCK_WAREHOUSES;
    } catch {
      return MOCK_WAREHOUSES;
    }
  },

  createProduct: async (productData: Partial<ProductItem>): Promise<ProductItem> => {
    const onHand = Number(productData.on_hand) || 0;
    const committed = Number(productData.committed) || 0;
    const available = Math.max(0, onHand - committed);
    const unitPrice = Number(productData.unit_price) || 0;

    let status: ProductItem['status'] = 'In Stock';
    if (available === 0) {
      status = 'Out of Stock';
    } else if (available <= 10) {
      status = 'Low Stock';
    }

    const newProduct: ProductItem = {
      id: `prod-${Date.now()}`,
      sku: productData.sku || `SKU-${Date.now().toString().slice(-6)}`,
      name: productData.name || 'New Product Item',
      category: productData.category || 'Electronics',
      warehouse: productData.warehouse || 'Main Hub (NY)',
      on_hand: onHand,
      committed: committed,
      available: available,
      unit_price: unitPrice,
      formatted_unit_price: `$${unitPrice.toFixed(2)}`,
      status: status,
      image_url:
        productData.image_url ||
        'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=100&auto=format&fit=crop&q=80',
      barcode: productData.barcode || `89012345${Math.floor(10000 + Math.random() * 90000)}`,
    };

    try {
      const response = await api.post('/api/v1/inventory/products', newProduct);
      if (response.data && typeof response.data === 'object' && response.data.id) {
        MOCK_PRODUCTS.unshift(response.data);
        return response.data;
      }
    } catch {
      // Fallback
    }

    MOCK_PRODUCTS.unshift(newProduct);
    return newProduct;
  },

  deleteProduct: async (id: string): Promise<boolean> => {
    const cleanId = id.trim().toLowerCase();
    const idx = MOCK_PRODUCTS.findIndex((p) => p.id.toLowerCase() === cleanId || p.sku.toLowerCase() === cleanId);
    if (idx !== -1) {
      MOCK_PRODUCTS.splice(idx, 1);
      return true;
    }
    return false;
  },
};

function filterMockProducts(filters?: {
  search?: string;
  category?: string;
  warehouse?: string;
  stockLevel?: string;
}) {
  let items = [...MOCK_PRODUCTS];
  if (filters?.search) {
    const q = filters.search.toLowerCase();
    items = items.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.sku.toLowerCase().includes(q) ||
        p.barcode?.includes(q)
    );
  }
  if (filters?.category && filters.category !== 'All Categories' && filters.category !== 'All') {
    items = items.filter((p) => p.category.toLowerCase() === filters.category!.toLowerCase());
  }
  if (filters?.warehouse && filters.warehouse !== 'All Warehouses' && filters.warehouse !== 'All') {
    items = items.filter((p) => p.warehouse.toLowerCase() === filters.warehouse!.toLowerCase());
  }
  if (filters?.stockLevel && filters.stockLevel !== 'Stock Level: All' && filters.stockLevel !== 'All') {
    items = items.filter((p) => p.status.toLowerCase() === filters.stockLevel!.toLowerCase());
  }
  return { items, total: items.length };
}
