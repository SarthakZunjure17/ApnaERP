import React, { useState, useEffect } from 'react';
import {
  Package,
  Plus,
  Search,
  Layers,
  Building2,
  Filter,
  DollarSign,
  Trash2,
  RefreshCw,
  Tag,
  CheckCircle2,
  XCircle,
  Eye,
} from 'lucide-react';
import { inventoryService } from '../../services/inventoryService';
import { ProductItem, CategoryOption, UnitOfMeasureOption, WarehouseOption, ProductCreatePayload } from '../../types/inventory';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Pagination } from '../../components/common/Pagination';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { KpiCard } from '../../components/common/KpiCard';
import { useToast } from '../../context/ToastContext';

export const ProductsPage: React.FC = () => {
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const [uoms, setUoms] = useState<UnitOfMeasureOption[]>([]);
  const [warehouses, setWarehouses] = useState<WarehouseOption[]>([]);
  const [totalProducts, setTotalProducts] = useState(0);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isNewProductModalOpen, setIsNewProductModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<ProductItem | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [formData, setFormData] = useState<ProductCreatePayload>({
    sku: '',
    name: '',
    category_id: '',
    uom_id: '',
    cost_price: 0,
    selling_price: 0,
    min_stock_level: 10,
    max_stock_level: 1000,
    barcode: '',
    description: '',
  });

  const pageSize = 10;
  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadMetadata();
  }, []);

  useEffect(() => {
    loadProducts();
  }, [searchQuery, selectedCategory, currentPage]);

  const loadMetadata = async () => {
    try {
      const [cats, uomList, whList] = await Promise.all([
        inventoryService.getCategories(),
        inventoryService.getUOMs(),
        inventoryService.getWarehouses(),
      ]);
      setCategories(cats);
      setUoms(uomList);
      setWarehouses(whList);
      if (cats.length > 0 && !formData.category_id) {
        setFormData((prev) => ({ ...prev, category_id: cats[0].id }));
      }
      if (uomList.length > 0 && !formData.uom_id) {
        setFormData((prev) => ({ ...prev, uom_id: uomList[0].id }));
      }
    } catch (err: any) {
      console.error('Failed to load inventory metadata', err);
    }
  };

  const loadProducts = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await inventoryService.getProducts({
        search: searchQuery || undefined,
        category_id: selectedCategory !== 'All' ? selectedCategory : undefined,
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
      });
      setProducts(res.items);
      setTotalProducts(res.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load products from server');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.sku || !formData.name || !formData.category_id || !formData.uom_id) {
      toastError('Please fill in all required fields (SKU, Name, Category, UOM)');
      return;
    }

    setIsSubmitting(true);
    try {
      await inventoryService.createProduct(formData);
      success('Product created successfully');
      setIsNewProductModalOpen(false);
      setFormData({
        sku: '',
        name: '',
        category_id: categories[0]?.id || '',
        uom_id: uoms[0]?.id || '',
        cost_price: 0,
        selling_price: 0,
        min_stock_level: 10,
        max_stock_level: 1000,
        barcode: '',
        description: '',
      });
      loadProducts();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to create product');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteProduct = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to deactivate or remove this product?')) return;
    try {
      await inventoryService.deleteProduct(id);
      success('Product deleted / deactivated successfully');
      loadProducts();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to delete product');
    }
  };

  // Quick stats computed from current view
  const activeProducts = products.filter((p) => p.is_active).length;
  const avgMargin = products.length > 0
    ? (products.reduce((acc, p) => acc + ((p.selling_price - p.cost_price) / (p.selling_price || 1)) * 100, 0) / products.length).toFixed(1)
    : '0';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Product Catalog</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Master repository of items, pricing, SKUs, and stock tracking parameters
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            icon={<RefreshCw className="w-4 h-4" />}
            onClick={() => {
              loadMetadata();
              loadProducts();
            }}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            icon={<Plus className="w-4 h-4" />}
            onClick={() => {
              if (categories.length > 0 && !formData.category_id) {
                setFormData((prev) => ({ ...prev, category_id: categories[0].id }));
              }
              if (uoms.length > 0 && !formData.uom_id) {
                setFormData((prev) => ({ ...prev, uom_id: uoms[0].id }));
              }
              setIsNewProductModalOpen(true);
            }}
          >
            Add Product
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Total Products"
          value={totalProducts}
          icon={<Package className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          description="Registered SKUs in system"
        />
        <KpiCard
          title="Active SKUs"
          value={activeProducts}
          icon={<CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          description="Ready for sales & purchase"
        />
        <KpiCard
          title="Categories"
          value={categories.length}
          icon={<Layers className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
          description="Configured product classes"
        />
        <KpiCard
          title="Avg Gross Margin"
          value={`${avgMargin}%`}
          icon={<DollarSign className="w-5 h-5 text-amber-600 dark:text-amber-400" />}
          description="Catalog markup average"
        />
      </div>

      {/* Filters & Search */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by SKU, Name, or Description..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="All">All Categories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.code})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Products Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <LoadingState message="Loading products from inventory..." />
          </div>
        ) : error ? (
          <div className="p-8">
            <ErrorState title="Failed to load products" message={error} onRetry={loadProducts} />
          </div>
        ) : products.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No products found"
              description="Create your first inventory product or adjust your filters."
              action={
                <Button
                  variant="primary"
                  icon={<Plus className="w-4 h-4" />}
                  onClick={() => setIsNewProductModalOpen(true)}
                >
                  Create Product
                </Button>
              }
            />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                  <tr>
                    <th className="px-6 py-4">SKU / Code</th>
                    <th className="px-6 py-4">Product Name</th>
                    <th className="px-6 py-4">Category</th>
                    <th className="px-6 py-4">UOM</th>
                    <th className="px-6 py-4">Cost Price</th>
                    <th className="px-6 py-4">Selling Price</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {products.map((p) => (
                    <tr
                      key={p.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors cursor-pointer"
                      onClick={() => {
                        setSelectedProduct(p);
                        setIsDetailModalOpen(true);
                      }}
                    >
                      <td className="px-6 py-4 font-mono font-medium text-gray-900 dark:text-white">
                        {p.sku}
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-medium text-gray-900 dark:text-white">{p.name}</div>
                        {p.description && (
                          <div className="text-xs text-gray-400 truncate max-w-xs">{p.description}</div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300">
                          <Tag className="w-3 h-3" />
                          {p.category_name || categories.find((c) => c.id === p.category_id)?.name || 'General'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-700 dark:text-gray-300">
                        {p.uom_name || uoms.find((u) => u.id === p.uom_id)?.symbol || 'Units'}
                      </td>
                      <td className="px-6 py-4 font-mono text-gray-900 dark:text-white">
                        ${Number(p.cost_price || 0).toFixed(2)}
                      </td>
                      <td className="px-6 py-4 font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                        ${Number(p.selling_price || 0).toFixed(2)}
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge
                          status={p.is_active ? 'Active' : 'Inactive'}
                          variant={p.is_active ? 'success' : 'default'}
                        />
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            title="View Details"
                            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedProduct(p);
                              setIsDetailModalOpen(true);
                            }}
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            title="Delete / Deactivate"
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                            onClick={(e) => handleDeleteProduct(p.id, e)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-4 border-t border-gray-200 dark:border-gray-700">
              <Pagination
                currentPage={currentPage}
                totalItems={totalProducts}
                pageSize={pageSize}
                onPageChange={(page) => setCurrentPage(page)}
              />
            </div>
          </>
        )}
      </div>

      {/* Product Detail Modal */}
      {selectedProduct && (
        <Modal
          isOpen={isDetailModalOpen}
          onClose={() => setIsDetailModalOpen(false)}
          title={`Product: ${selectedProduct.name}`}
          size="lg"
        >
          <div className="space-y-6">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 bg-gray-50 dark:bg-gray-700/50 p-4 rounded-xl border border-gray-200 dark:border-gray-600">
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">SKU</span>
                <p className="font-mono font-medium text-gray-900 dark:text-white mt-0.5">{selectedProduct.sku}</p>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Barcode</span>
                <p className="font-mono text-gray-900 dark:text-white mt-0.5">{selectedProduct.barcode || 'N/A'}</p>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Status</span>
                <div className="mt-0.5">
                  <StatusBadge
                    status={selectedProduct.is_active ? 'Active' : 'Inactive'}
                    variant={selectedProduct.is_active ? 'success' : 'default'}
                  />
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Cost Price</span>
                <p className="font-mono font-medium text-gray-900 dark:text-white mt-0.5">
                  ${Number(selectedProduct.cost_price || 0).toFixed(2)}
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Selling Price</span>
                <p className="font-mono font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                  ${Number(selectedProduct.selling_price || 0).toFixed(2)}
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-400 uppercase font-semibold">Gross Margin</span>
                <p className="font-medium text-blue-600 dark:text-blue-400 mt-0.5">
                  {(
                    ((selectedProduct.selling_price - selectedProduct.cost_price) /
                      (selectedProduct.selling_price || 1)) *
                    100
                  ).toFixed(1)}
                  %
                </p>
              </div>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Description & Notes</h4>
              <p className="text-sm text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-700/30 p-3 rounded-lg">
                {selectedProduct.description || 'No description entered for this product.'}
              </p>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button variant="secondary" onClick={() => setIsDetailModalOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Create Product Modal */}
      <Modal
        isOpen={isNewProductModalOpen}
        onClose={() => setIsNewProductModalOpen(false)}
        title="Add New Inventory Product"
        size="lg"
      >
        <form onSubmit={handleCreateProduct} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                SKU / Code *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. ELEC-001"
                value={formData.sku}
                onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Product Name *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Premium Laser Scanner"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Category *
              </label>
              <select
                required
                value={formData.category_id}
                onChange={(e) => setFormData({ ...formData, category_id: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Unit of Measure *
              </label>
              <select
                required
                value={formData.uom_id}
                onChange={(e) => setFormData({ ...formData, uom_id: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                {uoms.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name} ({u.symbol})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Cost Price ($) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                required
                value={formData.cost_price}
                onChange={(e) => setFormData({ ...formData, cost_price: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Selling Price ($) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                required
                value={formData.selling_price}
                onChange={(e) => setFormData({ ...formData, selling_price: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Min Stock Level
              </label>
              <input
                type="number"
                min="0"
                value={formData.min_stock_level}
                onChange={(e) => setFormData({ ...formData, min_stock_level: parseInt(e.target.value, 10) || 0 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Barcode / UPC
              </label>
              <input
                type="text"
                placeholder="Optional barcode"
                value={formData.barcode}
                onChange={(e) => setFormData({ ...formData, barcode: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              rows={3}
              placeholder="Product details, specifications, or notes"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsNewProductModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Create Product
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
