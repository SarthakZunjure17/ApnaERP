import React, { useState, useEffect } from 'react';
import {
  Boxes,
  ArrowDownLeft,
  ArrowUpRight,
  ArrowLeftRight,
  Warehouse,
  History,
  Plus,
  RefreshCw,
  Search,
  CheckCircle2,
  Calendar,
  Building2,
  Layers,
  FileText,
} from 'lucide-react';
import { inventoryService } from '../../services/inventoryService';
import {
  StockBalanceItem,
  StockLedgerItem,
  GoodsReceiptItem,
  GoodsIssueItem,
  StockTransferItem,
  WarehouseOption,
  ProductItem,
} from '../../types/inventory';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { KpiCard } from '../../components/common/KpiCard';
import { useToast } from '../../context/ToastContext';

type TabType = 'balances' | 'ledger' | 'grn' | 'gin' | 'transfers' | 'warehouses';

export const StockMovementsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('balances');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data
  const [balances, setBalances] = useState<StockBalanceItem[]>([]);
  const [ledger, setLedger] = useState<StockLedgerItem[]>([]);
  const [grns, setGrns] = useState<GoodsReceiptItem[]>([]);
  const [gins, setGins] = useState<GoodsIssueItem[]>([]);
  const [transfers, setTransfers] = useState<StockTransferItem[]>([]);
  const [warehouses, setWarehouses] = useState<WarehouseOption[]>([]);
  const [products, setProducts] = useState<ProductItem[]>([]);

  // Modals
  const [isGrnModalOpen, setIsGrnModalOpen] = useState(false);
  const [isGinModalOpen, setIsGinModalOpen] = useState(false);
  const [isTransferModalOpen, setIsTransferModalOpen] = useState(false);
  const [isWarehouseModalOpen, setIsWarehouseModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form States
  const [grnForm, setGrnForm] = useState({
    warehouse_id: '',
    supplier_id: '',
    receipt_date: new Date().toISOString().split('T')[0],
    product_id: '',
    received_quantity: 10,
    unit_cost: 0,
  });

  const [ginForm, setGinForm] = useState({
    warehouse_id: '',
    issue_date: new Date().toISOString().split('T')[0],
    issue_reason: 'Production',
    product_id: '',
    issued_quantity: 1,
  });

  const [transferForm, setTransferForm] = useState({
    source_warehouse_id: '',
    target_warehouse_id: '',
    transfer_date: new Date().toISOString().split('T')[0],
    product_id: '',
    quantity: 1,
  });

  const [whForm, setWhForm] = useState({
    name: '',
    code: '',
    address: '',
  });

  // Filter
  const [searchQuery, setSearchQuery] = useState('');
  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [balList, ledList, grnList, ginList, trfList, whList, prodList] = await Promise.all([
        inventoryService.getStockBalances(),
        inventoryService.getStockLedger({ limit: 50 }),
        inventoryService.getGoodsReceipts(),
        inventoryService.getGoodsIssues(),
        inventoryService.getStockTransfers(),
        inventoryService.getWarehouses(),
        inventoryService.getProducts({ limit: 100 }),
      ]);
      setBalances(balList);
      setLedger(ledList);
      setGrns(grnList);
      setGins(ginList);
      setTransfers(trfList);
      setWarehouses(whList);
      setProducts(prodList.items);

      if (whList.length > 0) {
        setGrnForm((prev) => ({ ...prev, warehouse_id: whList[0].id }));
        setGinForm((prev) => ({ ...prev, warehouse_id: whList[0].id }));
        setTransferForm((prev) => ({
          ...prev,
          source_warehouse_id: whList[0].id,
          target_warehouse_id: whList[1]?.id || whList[0].id,
        }));
      }
      if (prodList.items.length > 0) {
        setGrnForm((prev) => ({ ...prev, product_id: prodList.items[0].id, unit_cost: prodList.items[0].cost_price }));
        setGinForm((prev) => ({ ...prev, product_id: prodList.items[0].id }));
        setTransferForm((prev) => ({ ...prev, product_id: prodList.items[0].id }));
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load stock movements data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateGRN = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!grnForm.warehouse_id || !grnForm.product_id || grnForm.received_quantity <= 0) {
      toastError('Please fill in valid warehouse, product, and quantity');
      return;
    }
    setIsSubmitting(true);
    try {
      await inventoryService.createGoodsReceipt({
        warehouse_id: grnForm.warehouse_id,
        supplier_id: grnForm.supplier_id || undefined,
        receipt_date: grnForm.receipt_date,
        items: [
          {
            product_id: grnForm.product_id,
            received_quantity: Number(grnForm.received_quantity),
            unit_cost: Number(grnForm.unit_cost),
          },
        ],
      });
      success('Goods Receipt created & inventory updated');
      setIsGrnModalOpen(false);
      loadAll();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to create Goods Receipt');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateGIN = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ginForm.warehouse_id || !ginForm.product_id || ginForm.issued_quantity <= 0) {
      toastError('Please fill in valid warehouse, product, and quantity');
      return;
    }
    setIsSubmitting(true);
    try {
      await inventoryService.createGoodsIssue({
        warehouse_id: ginForm.warehouse_id,
        issue_date: ginForm.issue_date,
        issue_reason: ginForm.issue_reason,
        items: [
          {
            product_id: ginForm.product_id,
            issued_quantity: Number(ginForm.issued_quantity),
          },
        ],
      });
      success('Goods Issue recorded & stock deducted');
      setIsGinModalOpen(false);
      loadAll();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to record Goods Issue');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (transferForm.source_warehouse_id === transferForm.target_warehouse_id) {
      toastError('Source and Destination warehouse must be different');
      return;
    }
    setIsSubmitting(true);
    try {
      await inventoryService.createStockTransfer({
        source_warehouse_id: transferForm.source_warehouse_id,
        target_warehouse_id: transferForm.target_warehouse_id,
        transfer_date: transferForm.transfer_date,
        items: [
          {
            product_id: transferForm.product_id,
            quantity: Number(transferForm.quantity),
          },
        ],
      });
      success('Stock transfer initiated');
      setIsTransferModalOpen(false);
      loadAll();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to initiate stock transfer');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCompleteTransfer = async (id: string) => {
    try {
      await inventoryService.completeStockTransfer(id);
      success('Stock transfer marked completed');
      loadAll();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to complete transfer');
    }
  };

  const handleCreateWarehouse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!whForm.name || !whForm.code) {
      toastError('Warehouse name and code are required');
      return;
    }
    setIsSubmitting(true);
    try {
      await inventoryService.createWarehouse(whForm);
      success('Warehouse registered successfully');
      setIsWarehouseModalOpen(false);
      setWhForm({ name: '', code: '', address: '' });
      loadAll();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to register warehouse');
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalOnHand = balances.reduce((acc, b) => acc + (b.quantity_on_hand || 0), 0);
  const totalReserved = balances.reduce((acc, b) => acc + (b.quantity_reserved || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Stock & Inventory Movements</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Real-time stock balances, ledger audit trails, GRN receipts, issues, and transfers
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" icon={<RefreshCw className="w-4 h-4" />} onClick={loadAll}>
            Refresh
          </Button>
          {activeTab === 'grn' && (
            <Button
              variant="primary"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => setIsGrnModalOpen(true)}
            >
              New Goods Receipt (GRN)
            </Button>
          )}
          {activeTab === 'gin' && (
            <Button
              variant="primary"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => setIsGinModalOpen(true)}
            >
              New Goods Issue (GIN)
            </Button>
          )}
          {activeTab === 'transfers' && (
            <Button
              variant="primary"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => setIsTransferModalOpen(true)}
            >
              New Stock Transfer
            </Button>
          )}
          {activeTab === 'warehouses' && (
            <Button
              variant="primary"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => setIsWarehouseModalOpen(true)}
            >
              Add Warehouse
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Total Units On Hand"
          value={totalOnHand.toLocaleString()}
          icon={<Boxes className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          description="Summed across all warehouses"
        />
        <KpiCard
          title="Reserved Units"
          value={totalReserved.toLocaleString()}
          icon={<Layers className="w-5 h-5 text-amber-600 dark:text-amber-400" />}
          description="Allocated to active sales orders"
        />
        <KpiCard
          title="Active Warehouses"
          value={warehouses.length}
          icon={<Warehouse className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          description="Storage locations managed"
        />
        <KpiCard
          title="Ledger Entries"
          value={ledger.length}
          icon={<History className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
          description="Audit trail transactions"
        />
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 space-x-2">
        <button
          onClick={() => setActiveTab('balances')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'balances'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Boxes className="w-4 h-4" /> Stock Balances
        </button>
        <button
          onClick={() => setActiveTab('ledger')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'ledger'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <History className="w-4 h-4" /> Stock Ledger
        </button>
        <button
          onClick={() => setActiveTab('grn')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'grn'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <ArrowDownLeft className="w-4 h-4" /> Receipts (GRN)
        </button>
        <button
          onClick={() => setActiveTab('gin')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'gin'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <ArrowUpRight className="w-4 h-4" /> Issues (GIN)
        </button>
        <button
          onClick={() => setActiveTab('transfers')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'transfers'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <ArrowLeftRight className="w-4 h-4" /> Transfers
        </button>
        <button
          onClick={() => setActiveTab('warehouses')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'warehouses'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Warehouse className="w-4 h-4" /> Warehouses
        </button>
      </div>

      {/* Main Content Area */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <LoadingState message="Loading inventory records..." />
          </div>
        ) : error ? (
          <div className="p-8">
            <ErrorState title="Failed to load stock data" message={error} onRetry={loadAll} />
          </div>
        ) : (
          <>
            {/* Tab: Stock Balances */}
            {activeTab === 'balances' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                  <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                    <tr>
                      <th className="px-6 py-4">Product SKU</th>
                      <th className="px-6 py-4">Product Name</th>
                      <th className="px-6 py-4">Warehouse</th>
                      <th className="px-6 py-4 text-right">On Hand</th>
                      <th className="px-6 py-4 text-right">Reserved</th>
                      <th className="px-6 py-4 text-right">Available</th>
                      <th className="px-6 py-4">Last Updated</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {balances.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-6 py-8 text-center text-gray-400">
                          No stock balance records found. Perform a Goods Receipt (GRN) to populate stock.
                        </td>
                      </tr>
                    ) : (
                      balances.map((b) => (
                        <tr key={b.id || `${b.product_id}-${b.warehouse_id}`} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                          <td className="px-6 py-4 font-mono font-medium text-gray-900 dark:text-white">
                            {b.product_sku}
                          </td>
                          <td className="px-6 py-4 font-medium text-gray-900 dark:text-white">{b.product_name}</td>
                          <td className="px-6 py-4 text-gray-700 dark:text-gray-300">{b.warehouse_name}</td>
                          <td className="px-6 py-4 text-right font-mono font-bold text-gray-900 dark:text-white">
                            {b.quantity_on_hand}
                          </td>
                          <td className="px-6 py-4 text-right font-mono text-amber-600 dark:text-amber-400">
                            {b.quantity_reserved}
                          </td>
                          <td className="px-6 py-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                            {b.quantity_available}
                          </td>
                          <td className="px-6 py-4 text-xs text-gray-400">{new Date(b.updated_at).toLocaleString()}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab: Stock Ledger */}
            {activeTab === 'ledger' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                  <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                    <tr>
                      <th className="px-6 py-4">Timestamp</th>
                      <th className="px-6 py-4">SKU / Product</th>
                      <th className="px-6 py-4">Warehouse</th>
                      <th className="px-6 py-4">Type</th>
                      <th className="px-6 py-4 text-right">Quantity</th>
                      <th className="px-6 py-4 text-right">Balance After</th>
                      <th className="px-6 py-4">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {ledger.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-6 py-8 text-center text-gray-400">
                          No ledger transaction history recorded yet.
                        </td>
                      </tr>
                    ) : (
                      ledger.map((l) => (
                        <tr key={l.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                          <td className="px-6 py-4 text-xs text-gray-500">{new Date(l.created_at).toLocaleString()}</td>
                          <td className="px-6 py-4">
                            <span className="font-mono text-xs font-semibold text-gray-900 dark:text-white block">
                              {l.product_sku}
                            </span>
                            <span className="text-xs text-gray-500">{l.product_name}</span>
                          </td>
                          <td className="px-6 py-4 text-gray-700 dark:text-gray-300">{l.warehouse_name}</td>
                          <td className="px-6 py-4">
                            <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                              {l.transaction_type}
                            </span>
                          </td>
                          <td
                            className={`px-6 py-4 text-right font-mono font-bold ${
                              l.quantity >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                            }`}
                          >
                            {l.quantity > 0 ? `+${l.quantity}` : l.quantity}
                          </td>
                          <td className="px-6 py-4 text-right font-mono font-semibold text-gray-900 dark:text-white">
                            {l.balance_after}
                          </td>
                          <td className="px-6 py-4 text-xs text-gray-500">{l.notes || '-'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab: Receipts (GRN) */}
            {activeTab === 'grn' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                  <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                    <tr>
                      <th className="px-6 py-4">GRN Number</th>
                      <th className="px-6 py-4">Warehouse</th>
                      <th className="px-6 py-4">Supplier</th>
                      <th className="px-6 py-4">Receipt Date</th>
                      <th className="px-6 py-4">Status</th>
                      <th className="px-6 py-4">Items Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {grns.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-gray-400">
                          No Goods Receipts on file. Click "New Goods Receipt" to receive incoming inventory.
                        </td>
                      </tr>
                    ) : (
                      grns.map((g) => (
                        <tr key={g.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                          <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">{g.grn_number}</td>
                          <td className="px-6 py-4">{g.warehouse_name || g.warehouse_id}</td>
                          <td className="px-6 py-4">{g.supplier_name || 'Standard Inbound'}</td>
                          <td className="px-6 py-4 text-xs text-gray-500">{g.receipt_date}</td>
                          <td className="px-6 py-4">
                            <StatusBadge status={g.status || 'Received'} variant="success" />
                          </td>
                          <td className="px-6 py-4 font-mono">{g.items?.length || 1} items</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab: Issues (GIN) */}
            {activeTab === 'gin' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                  <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                    <tr>
                      <th className="px-6 py-4">GIN Number</th>
                      <th className="px-6 py-4">Warehouse</th>
                      <th className="px-6 py-4">Issue Date</th>
                      <th className="px-6 py-4">Reason</th>
                      <th className="px-6 py-4">Status</th>
                      <th className="px-6 py-4">Items Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {gins.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-gray-400">
                          No Goods Issues recorded. Click "New Goods Issue" to write-off or dispatch stock.
                        </td>
                      </tr>
                    ) : (
                      gins.map((g) => (
                        <tr key={g.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                          <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">{g.gin_number}</td>
                          <td className="px-6 py-4">{g.warehouse_name || g.warehouse_id}</td>
                          <td className="px-6 py-4 text-xs text-gray-500">{g.issue_date}</td>
                          <td className="px-6 py-4 text-gray-700 dark:text-gray-300">{g.issue_reason}</td>
                          <td className="px-6 py-4">
                            <StatusBadge status={g.status || 'Issued'} variant="warning" />
                          </td>
                          <td className="px-6 py-4 font-mono">{g.items?.length || 1} items</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab: Transfers */}
            {activeTab === 'transfers' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                  <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                    <tr>
                      <th className="px-6 py-4">Transfer Number</th>
                      <th className="px-6 py-4">Source Warehouse</th>
                      <th className="px-6 py-4">Target Warehouse</th>
                      <th className="px-6 py-4">Transfer Date</th>
                      <th className="px-6 py-4">Status</th>
                      <th className="px-6 py-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {transfers.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-gray-400">
                          No inter-warehouse transfers found. Click "New Stock Transfer" to move stock between sites.
                        </td>
                      </tr>
                    ) : (
                      transfers.map((t) => (
                        <tr key={t.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                          <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">
                            {t.transfer_number}
                          </td>
                          <td className="px-6 py-4">{t.source_warehouse_name || t.source_warehouse_id}</td>
                          <td className="px-6 py-4">{t.target_warehouse_name || t.target_warehouse_id}</td>
                          <td className="px-6 py-4 text-xs text-gray-500">{t.transfer_date}</td>
                          <td className="px-6 py-4">
                            <StatusBadge
                              status={t.status}
                              variant={t.status === 'Completed' ? 'success' : 'warning'}
                            />
                          </td>
                          <td className="px-6 py-4 text-right">
                            {t.status !== 'Completed' && (
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => handleCompleteTransfer(t.id)}
                              >
                                Complete Receipt
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Tab: Warehouses */}
            {activeTab === 'warehouses' && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                  <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                    <tr>
                      <th className="px-6 py-4">Warehouse Code</th>
                      <th className="px-6 py-4">Warehouse Name</th>
                      <th className="px-6 py-4">Address</th>
                      <th className="px-6 py-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {warehouses.map((w) => (
                      <tr key={w.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                        <td className="px-6 py-4 font-mono font-bold text-gray-900 dark:text-white">{w.code}</td>
                        <td className="px-6 py-4 font-medium text-gray-900 dark:text-white">{w.name}</td>
                        <td className="px-6 py-4 text-gray-500">{w.address || 'Standard Location'}</td>
                        <td className="px-6 py-4">
                          <StatusBadge status={w.is_active ? 'Active' : 'Inactive'} variant={w.is_active ? 'success' : 'default'} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>

      {/* Modal: New Goods Receipt (GRN) */}
      <Modal
        isOpen={isGrnModalOpen}
        onClose={() => setIsGrnModalOpen(false)}
        title="Receive Goods (GRN)"
        size="lg"
      >
        <form onSubmit={handleCreateGRN} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Destination Warehouse *
              </label>
              <select
                required
                value={grnForm.warehouse_id}
                onChange={(e) => setGrnForm({ ...grnForm, warehouse_id: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Receipt Date *
              </label>
              <input
                type="date"
                required
                value={grnForm.receipt_date}
                onChange={(e) => setGrnForm({ ...grnForm, receipt_date: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Product Item *
              </label>
              <select
                required
                value={grnForm.product_id}
                onChange={(e) => {
                  const prod = products.find((p) => p.id === e.target.value);
                  setGrnForm({
                    ...grnForm,
                    product_id: e.target.value,
                    unit_cost: prod ? prod.cost_price : 0,
                  });
                }}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} (SKU: {p.sku})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Received Quantity *
              </label>
              <input
                type="number"
                min="1"
                required
                value={grnForm.received_quantity}
                onChange={(e) => setGrnForm({ ...grnForm, received_quantity: parseInt(e.target.value, 10) || 1 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Unit Cost ($)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={grnForm.unit_cost}
                onChange={(e) => setGrnForm({ ...grnForm, unit_cost: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsGrnModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Receive & Update Stock
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: New Goods Issue (GIN) */}
      <Modal
        isOpen={isGinModalOpen}
        onClose={() => setIsGinModalOpen(false)}
        title="Issue Goods (GIN)"
        size="lg"
      >
        <form onSubmit={handleCreateGIN} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Source Warehouse *
              </label>
              <select
                required
                value={ginForm.warehouse_id}
                onChange={(e) => setGinForm({ ...ginForm, warehouse_id: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Issue Date *
              </label>
              <input
                type="date"
                required
                value={ginForm.issue_date}
                onChange={(e) => setGinForm({ ...ginForm, issue_date: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Product Item *
              </label>
              <select
                required
                value={ginForm.product_id}
                onChange={(e) => setGinForm({ ...ginForm, product_id: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} (SKU: {p.sku})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Issued Quantity *
              </label>
              <input
                type="number"
                min="1"
                required
                value={ginForm.issued_quantity}
                onChange={(e) => setGinForm({ ...ginForm, issued_quantity: parseInt(e.target.value, 10) || 1 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Issue Reason *
              </label>
              <select
                value={ginForm.issue_reason}
                onChange={(e) => setGinForm({ ...ginForm, issue_reason: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                <option value="Production">Production / Assembly</option>
                <option value="Damage">Damaged Goods</option>
                <option value="Internal Use">Internal Consumption</option>
                <option value="Sample">Customer Sample</option>
                <option value="Scrap">Scrapped / Expired</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsGinModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Issue Goods
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: New Stock Transfer */}
      <Modal
        isOpen={isTransferModalOpen}
        onClose={() => setIsTransferModalOpen(false)}
        title="Inter-Warehouse Stock Transfer"
        size="lg"
      >
        <form onSubmit={handleCreateTransfer} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Source Warehouse *
              </label>
              <select
                required
                value={transferForm.source_warehouse_id}
                onChange={(e) => setTransferForm({ ...transferForm, source_warehouse_id: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Target Warehouse *
              </label>
              <select
                required
                value={transferForm.target_warehouse_id}
                onChange={(e) => setTransferForm({ ...transferForm, target_warehouse_id: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.code})
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Product Item *
              </label>
              <select
                required
                value={transferForm.product_id}
                onChange={(e) => setTransferForm({ ...transferForm, product_id: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} (SKU: {p.sku})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Transfer Quantity *
              </label>
              <input
                type="number"
                min="1"
                required
                value={transferForm.quantity}
                onChange={(e) => setTransferForm({ ...transferForm, quantity: parseInt(e.target.value, 10) || 1 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Transfer Date *
              </label>
              <input
                type="date"
                required
                value={transferForm.transfer_date}
                onChange={(e) => setTransferForm({ ...transferForm, transfer_date: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsTransferModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Initiate Transfer
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: New Warehouse */}
      <Modal
        isOpen={isWarehouseModalOpen}
        onClose={() => setIsWarehouseModalOpen(false)}
        title="Register Warehouse"
      >
        <form onSubmit={handleCreateWarehouse} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Warehouse Code *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. WH-EAST-01"
              value={whForm.code}
              onChange={(e) => setWhForm({ ...whForm, code: e.target.value })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Warehouse Name *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Central Distribution Hub"
              value={whForm.name}
              onChange={(e) => setWhForm({ ...whForm, name: e.target.value })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Address
            </label>
            <input
              type="text"
              placeholder="e.g. 100 Logistics Blvd, Dallas, TX"
              value={whForm.address}
              onChange={(e) => setWhForm({ ...whForm, address: e.target.value })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsWarehouseModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Register Warehouse
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
