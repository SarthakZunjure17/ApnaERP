import React, { useState, useEffect } from 'react';
import {
  Package,
  AlertTriangle,
  Wallet,
  Download,
  Plus,
  Search,
  Layers,
  Building2,
  SlidersHorizontal,
  Filter,
  MapPin,
  TrendingUp,
  X,
  Barcode,
  DollarSign,
  Boxes,
  CheckCircle2,
  Trash2,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  ResponsiveContainer,
} from 'recharts';
import { inventoryService } from '../../services/inventoryService';
import { ProductItem, InventoryMetrics, CategoryOption, WarehouseOption } from '../../types/inventory';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Pagination } from '../../components/common/Pagination';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { useToast } from '../../context/ToastContext';

export const ProductsPage: React.FC = () => {
  const [metrics, setMetrics] = useState<InventoryMetrics | null>(null);
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const [warehouses, setWarehouses] = useState<WarehouseOption[]>([]);

  // Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All Categories');
  const [selectedWarehouse, setSelectedWarehouse] = useState('All Warehouses');
  const [selectedStockLevel, setSelectedStockLevel] = useState('Stock Level: All');
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Modal states
  const [isNewProductModalOpen, setIsNewProductModalOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<ProductItem | null>(null);
  const [newProductForm, setNewProductForm] = useState({
    sku: '',
    name: '',
    category: 'Electronics',
    warehouse: 'Main Hub (NY)',
    on_hand: 100,
    unit_price: 150,
  });

  const pageSize = 6;
  const { success, info } = useToast();

  useEffect(() => {
    setCurrentPage(1);
    loadData();
  }, [searchQuery, selectedCategory, selectedWarehouse, selectedStockLevel]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [metricData, prodData, catData, whData] = await Promise.all([
        inventoryService.getMetrics(),
        inventoryService.getProducts({
          search: searchQuery,
          category: selectedCategory,
          warehouse: selectedWarehouse,
          stockLevel: selectedStockLevel,
        }),
        inventoryService.getCategories(),
        inventoryService.getWarehouses(),
      ]);

      setMetrics(metricData);
      setProducts(prodData.items);
      setCategories(catData);
      setWarehouses(whData);
    } catch (err) {
      console.error('Failed to load inventory data', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedRows(products.map((p) => p.id));
    } else {
      setSelectedRows([]);
    }
  };

  const handleSelectRow = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedRows((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]
    );
  };

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProductForm.name || !newProductForm.sku) return;

    const created = await inventoryService.createProduct({
      ...newProductForm,
      committed: 0,
      available: newProductForm.on_hand,
      formatted_unit_price: `$${newProductForm.unit_price.toFixed(2)}`,
    });

    setProducts((prev) => [created, ...prev]);
    setIsNewProductModalOpen(false);
    setNewProductForm({
      sku: '',
      name: '',
      category: 'Electronics',
      warehouse: 'Main Hub (NY)',
      on_hand: 100,
      unit_price: 150,
    });
    success('Product Created', `${created.name} added to catalog.`);
  };

  const handleDeleteProduct = async (id: string) => {
    await inventoryService.deleteProduct(id);
    setProducts((prev) => prev.filter((p) => p.id !== id));
    setSelectedProduct(null);
    success('Product Removed', 'Product has been deleted from the catalog.');
  };

  const handleExport = () => {
    if (products.length === 0) {
      info('No Products', 'There are no products to export.');
      return;
    }
    const headers = ['SKU', 'Name', 'Category', 'Warehouse', 'On Hand', 'Committed', 'Available', 'Unit Price', 'Status'];
    const rows = products.map((p) => [
      `"${p.sku}"`,
      `"${p.name}"`,
      `"${p.category}"`,
      `"${p.warehouse}"`,
      p.on_hand,
      p.committed,
      p.available,
      p.unit_price,
      `"${p.status}"`,
    ]);
    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `inventory_products_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    success('Export Completed', `Exported ${products.length} products to CSV.`);
  };

  const totalPages = Math.max(1, Math.ceil(products.length / pageSize));
  const paginatedProducts = products.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  // Sparkline data for stock value card
  const sparklineData = [
    { value: 10 },
    { value: 12 },
    { value: 18 },
    { value: 15 },
    { value: 24 },
    { value: 20 },
    { value: 28 },
    { value: 35 },
  ];

  return (
    <div className="space-y-4 sm:space-y-5 animate-fade-in pb-8">
      {/* Top Header (Matching Screenshot 2) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Inventory Products
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Manage and track all physical goods, variations, and stock levels across multiple warehouse locations.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            onClick={handleExport}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            Export
          </button>

          <button
            onClick={() => setIsNewProductModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            New Product
          </button>
        </div>
      </div>

      {/* 3 Metric Cards (Matching Screenshot 2) */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Card 1: Total SKUs */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center shadow-xs">
                <Package className="w-4 h-4" />
              </div>
              <span className="inline-flex items-center gap-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-1.5 py-0.5 rounded">
                <TrendingUp className="w-3 h-3" />
                {metrics.total_skus.trend}
              </span>
            </div>

            <div className="mt-3">
              <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                Total SKUs
              </span>
              <h3 className="text-2xl sm:text-[28px] font-bold text-slate-900 dark:text-white mt-1 leading-none">
                {products.length > 0 ? products.length : metrics.total_skus.value}
              </h3>
            </div>

            {/* Blue Progress Bar */}
            <div className="mt-4 w-full bg-slate-100 dark:bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-brand-600 h-1.5 rounded-full"
                style={{ width: `${metrics.total_skus.progress_percentage}%` }}
              />
            </div>
          </div>

          {/* Card 2: Low Stock Alerts */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <div className="w-8 h-8 rounded-lg bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 flex items-center justify-center border border-rose-100 dark:border-rose-900/40">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <button
                onClick={() => setSelectedStockLevel('Low Stock')}
                className="text-xs font-semibold text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 underline cursor-pointer"
              >
                View List
              </button>
            </div>

            <div className="mt-3">
              <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                Low Stock Alerts
              </span>
              <h3 className="text-2xl sm:text-[28px] font-bold text-rose-600 dark:text-rose-400 mt-1 leading-none">
                {products.filter((p) => p.status === 'Low Stock' || p.status === 'Out of Stock').length}
              </h3>
            </div>

            {/* Category tags */}
            <div className="mt-3 flex items-center gap-1.5 flex-wrap">
              {metrics.low_stock_alerts.categories.map((c) => (
                <span
                  key={c.name}
                  className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-[10px] font-semibold"
                >
                  {c.name} ({c.count})
                </span>
              ))}
            </div>
          </div>

          {/* Card 3: Total Stock Value with Sparkline */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs flex flex-col justify-between relative overflow-hidden">
            <div className="flex items-center justify-between z-10">
              <div className="w-8 h-8 rounded-lg bg-amber-600 text-white flex items-center justify-center shadow-xs">
                <Wallet className="w-4 h-4" />
              </div>
            </div>

            <div className="mt-3 z-10">
              <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                Total Stock Value
              </span>
              <h3 className="text-2xl sm:text-[28px] font-bold text-slate-900 dark:text-white mt-1 leading-none">
                {metrics.total_stock_value.value}
              </h3>
            </div>

            {/* Bottom mini area curve */}
            <div className="h-10 w-full mt-2 -mb-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={sparklineData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="stockCurve" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#d97706" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#d97706" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#d97706"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#stockCurve)"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Filter Bar (Matching Screenshot 2) */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 text-xs">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by SKU, Name or Barcode..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-blue-50/50 dark:bg-slate-800/80 border border-blue-100 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-brand-500"
          />
        </div>

        {/* Categories Dropdown */}
        <div className="relative">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full sm:w-auto pl-8 pr-6 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-200 focus:outline-none focus:border-brand-500 font-medium"
          >
            {categories.map((c) => (
              <option key={c.id} value={c.name}>
                {c.name}
              </option>
            ))}
          </select>
          <Layers className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>

        {/* Warehouses Dropdown */}
        <div className="relative">
          <select
            value={selectedWarehouse}
            onChange={(e) => setSelectedWarehouse(e.target.value)}
            className="w-full sm:w-auto pl-8 pr-6 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-200 focus:outline-none focus:border-brand-500 font-medium"
          >
            {warehouses.map((w) => (
              <option key={w.id} value={w.name}>
                {w.name}
              </option>
            ))}
          </select>
          <Building2 className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>

        {/* Stock Level Dropdown */}
        <div className="relative">
          <select
            value={selectedStockLevel}
            onChange={(e) => setSelectedStockLevel(e.target.value)}
            className="w-full sm:w-auto pl-8 pr-6 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-200 focus:outline-none focus:border-brand-500 font-medium"
          >
            <option value="Stock Level: All">Stock Level: All</option>
            <option value="In Stock">In Stock</option>
            <option value="Low Stock">Low Stock</option>
            <option value="Out of Stock">Out of Stock</option>
          </select>
          <SlidersHorizontal className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>

        {/* Reset Filter button */}
        <button
          onClick={() => {
            setSelectedCategory('All Categories');
            setSelectedWarehouse('All Warehouses');
            setSelectedStockLevel('Stock Level: All');
            setSearchQuery('');
          }}
          className="p-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-500 rounded-lg transition-colors flex items-center justify-center cursor-pointer"
          title="Reset All Filters"
        >
          <Filter className="w-4 h-4" />
        </button>
      </div>

      {/* Products Table (Matching Screenshot 2) */}
      {isLoading ? (
        <LoadingState message="Loading inventory products..." />
      ) : products.length === 0 ? (
        <EmptyState
          title="No products found"
          description={`No catalog items match "${searchQuery || selectedCategory}".`}
          actionLabel="Reset Filters"
          onAction={() => {
            setSelectedCategory('All Categories');
            setSelectedWarehouse('All Warehouses');
            setSelectedStockLevel('Stock Level: All');
            setSearchQuery('');
          }}
        />
      ) : (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                  <th className="py-2 px-3 w-8">
                    <input
                      type="checkbox"
                      checked={selectedRows.length === products.length && products.length > 0}
                      onChange={handleSelectAll}
                      className="rounded border-slate-300 dark:border-slate-700 text-brand-600 focus:ring-brand-500"
                    />
                  </th>
                  <th className="py-2 px-3">Image</th>
                  <th className="py-2 px-3">Product Info</th>
                  <th className="py-2 px-3">Warehouse</th>
                  <th className="py-2 px-3 text-center">On Hand</th>
                  <th className="py-2 px-3 text-center">Committed</th>
                  <th className="py-2 px-3 text-center">Available</th>
                  <th className="py-2 px-3 text-right">Unit Price</th>
                  <th className="py-2 px-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100/80 dark:divide-slate-800/60 text-xs">
                {paginatedProducts.map((item) => {
                  const isChecked = selectedRows.includes(item.id);
                  const isAvailableLow = item.available <= 5 && item.available > 0;
                  const isAvailableZero = item.available === 0;

                  return (
                    <tr
                      key={item.id}
                      onClick={() => setSelectedProduct(item)}
                      className={`hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors group cursor-pointer ${
                        isChecked ? 'bg-blue-50/40 dark:bg-blue-950/20' : ''
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-3 px-3" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {}}
                          onClick={(e) => handleSelectRow(item.id, e)}
                          className="rounded border-slate-300 dark:border-slate-700 text-brand-600 focus:ring-brand-500"
                        />
                      </td>

                      {/* Image Thumbnail */}
                      <td className="py-3 px-3">
                        <img
                          src={item.image_url}
                          alt={item.name}
                          className="w-9 h-9 rounded-lg object-cover bg-slate-100 dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700/60 shrink-0"
                        />
                      </td>

                      {/* Product Info (Title + SKU & Category badge) */}
                      <td className="py-3 px-3">
                        <p className="font-semibold text-slate-900 dark:text-white group-hover:text-brand-600 transition-colors">
                          {item.name}
                        </p>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="inline-block px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800 text-[10px] font-mono font-medium text-slate-600 dark:text-slate-400">
                            SKU: {item.sku}
                          </span>
                          <span className="text-slate-300 dark:text-slate-700">•</span>
                          <span className="text-[11px] text-slate-500 dark:text-slate-400">
                            {item.category}
                          </span>
                        </div>
                      </td>

                      {/* Warehouse with MapPin */}
                      <td className="py-3 px-3 whitespace-nowrap text-slate-600 dark:text-slate-300">
                        <span className="inline-flex items-center gap-1 text-xs">
                          <MapPin className="w-3.5 h-3.5 text-slate-400" />
                          {item.warehouse}
                        </span>
                      </td>

                      {/* On Hand */}
                      <td className="py-3 px-3 text-center font-medium text-slate-800 dark:text-slate-200">
                        {item.on_hand.toLocaleString()}
                      </td>

                      {/* Committed */}
                      <td className="py-3 px-3 text-center text-slate-500 dark:text-slate-400">
                        {item.committed.toLocaleString()}
                      </td>

                      {/* Available with dynamic color coding */}
                      <td className="py-3 px-3 text-center font-bold">
                        <span
                          className={
                            isAvailableZero
                              ? 'text-slate-400 dark:text-slate-500'
                              : isAvailableLow
                              ? 'text-rose-600 dark:text-rose-400'
                              : 'text-brand-600 dark:text-blue-400'
                          }
                        >
                          {item.available.toLocaleString()}
                        </span>
                      </td>

                      {/* Unit Price */}
                      <td className="py-3 px-3 text-right font-medium text-slate-900 dark:text-white">
                        {item.formatted_unit_price}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-3 text-right whitespace-nowrap">
                        <StatusBadge status={item.status} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            totalEntries={products.length}
            pageSize={pageSize}
            onPageChange={(p) => setCurrentPage(p)}
          />
        </div>
      )}

      {/* Product Detail Modal */}
      <Modal
        isOpen={!!selectedProduct}
        onClose={() => setSelectedProduct(null)}
        title={selectedProduct ? selectedProduct.name : 'Product Details'}
      >
        {selectedProduct && (
          <div className="space-y-4 text-xs">
            <div className="flex items-start gap-4 p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-100 dark:border-slate-800">
              <img
                src={selectedProduct.image_url}
                alt={selectedProduct.name}
                className="w-16 h-16 rounded-lg object-cover bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px] font-bold text-brand-600 bg-brand-50 dark:bg-brand-950 px-2 py-0.5 rounded">
                    {selectedProduct.sku}
                  </span>
                  <StatusBadge status={selectedProduct.status} />
                </div>
                <h4 className="font-bold text-sm text-slate-900 dark:text-white mt-1">
                  {selectedProduct.name}
                </h4>
                <p className="text-slate-500 mt-0.5">
                  Category: {selectedProduct.category} • Warehouse: {selectedProduct.warehouse}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2.5 text-center">
              <div className="p-2.5 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
                <span className="text-[10px] text-slate-400 font-semibold uppercase block">On Hand</span>
                <span className="text-base font-bold text-slate-900 dark:text-white mt-0.5 block">
                  {selectedProduct.on_hand}
                </span>
              </div>
              <div className="p-2.5 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
                <span className="text-[10px] text-slate-400 font-semibold uppercase block">Committed</span>
                <span className="text-base font-bold text-slate-500 mt-0.5 block">
                  {selectedProduct.committed}
                </span>
              </div>
              <div className="p-2.5 bg-brand-50 dark:bg-brand-950/40 rounded-lg border border-brand-100 dark:border-brand-900/40">
                <span className="text-[10px] text-brand-600 dark:text-brand-400 font-semibold uppercase block">Available</span>
                <span className="text-base font-bold text-brand-700 dark:text-brand-300 mt-0.5 block">
                  {selectedProduct.available}
                </span>
              </div>
            </div>

            <div className="space-y-2 border-t border-slate-100 dark:border-slate-800 pt-3">
              <div className="flex justify-between">
                <span className="text-slate-500">Unit Price</span>
                <span className="font-semibold text-slate-900 dark:text-white">
                  {selectedProduct.formatted_unit_price}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Barcode Identifier</span>
                <span className="font-mono text-slate-700 dark:text-slate-300">
                  {selectedProduct.barcode || 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Primary Warehouse</span>
                <span className="font-medium text-slate-700 dark:text-slate-300">
                  {selectedProduct.warehouse}
                </span>
              </div>
            </div>

            <div className="flex justify-between items-center pt-3 border-t border-slate-100 dark:border-slate-800">
              <Button
                variant="danger"
                size="sm"
                onClick={() => handleDeleteProduct(selectedProduct.id)}
                leftIcon={<Trash2 className="w-3.5 h-3.5" />}
              >
                Delete Product
              </Button>

              <Button
                variant="primary"
                size="sm"
                onClick={() => setSelectedProduct(null)}
              >
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* New Product Modal */}
      <Modal
        isOpen={isNewProductModalOpen}
        onClose={() => setIsNewProductModalOpen(false)}
        title="Add New Inventory Product"
      >
        <form onSubmit={handleCreateProduct} className="space-y-3.5 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Product SKU
              </label>
              <input
                type="text"
                required
                placeholder="e.g. AU-WH-005"
                value={newProductForm.sku}
                onChange={(e) => setNewProductForm({ ...newProductForm, sku: e.target.value })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Category
              </label>
              <select
                value={newProductForm.category}
                onChange={(e) => setNewProductForm({ ...newProductForm, category: e.target.value })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
              >
                <option value="Electronics">Electronics</option>
                <option value="Furniture">Furniture</option>
                <option value="Apparel">Apparel</option>
                <option value="Office Supplies">Office Supplies</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
              Product Name
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Studio Pro Studio Monitor"
              value={newProductForm.name}
              onChange={(e) => setNewProductForm({ ...newProductForm, name: e.target.value })}
              className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Initial Stock
              </label>
              <input
                type="number"
                min="0"
                value={newProductForm.on_hand}
                onChange={(e) =>
                  setNewProductForm({ ...newProductForm, on_hand: Number(e.target.value) })
                }
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Unit Price ($)
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={newProductForm.unit_price}
                onChange={(e) =>
                  setNewProductForm({ ...newProductForm, unit_price: Number(e.target.value) })
                }
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
              Assigned Warehouse
            </label>
            <select
              value={newProductForm.warehouse}
              onChange={(e) => setNewProductForm({ ...newProductForm, warehouse: e.target.value })}
              className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
            >
              <option value="Main Hub (NY)">Main Hub (NY)</option>
              <option value="West Coast (CA)">West Coast (CA)</option>
              <option value="Central Logistics (TX)">Central Logistics (TX)</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button variant="outline" size="sm" type="button" onClick={() => setIsNewProductModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Save Product
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
