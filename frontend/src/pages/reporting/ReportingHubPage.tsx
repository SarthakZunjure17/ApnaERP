import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  Download,
  Calendar,
  RefreshCw,
  TrendingUp,
  DollarSign,
  ShoppingBag,
  Boxes,
  Users,
  CreditCard,
  Target,
  FileSpreadsheet,
  Building2,
  Layers,
  ArrowDownRight,
  ArrowUpRight,
} from 'lucide-react';
import { reportingService } from '../../services/reportingService';
import {
  ProfitLossReportData,
  BalanceSheetReportData,
  TrialBalanceReportData,
  SalesReportSummaryData,
  ProcurementReportSummaryData,
  InventoryStockReportData,
  HeadcountReportData,
  PayrollReportSummaryData,
} from '../../types/reporting';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { KpiCard } from '../../components/common/KpiCard';
import { useToast } from '../../context/ToastContext';

type ReportDomain = 'finance' | 'sales' | 'procurement' | 'inventory' | 'hr' | 'payroll' | 'crm';

export const ReportingHubPage: React.FC = () => {
  const [activeDomain, setActiveDomain] = useState<ReportDomain>('finance');
  const [fromDate, setFromDate] = useState(
    new Date(new Date().getFullYear(), 0, 1).toISOString().split('T')[0]
  );
  const [toDate, setToDate] = useState(new Date().toISOString().split('T')[0]);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  // Data states
  const [pnlData, setPnlData] = useState<ProfitLossReportData | null>(null);
  const [bsData, setBsData] = useState<BalanceSheetReportData | null>(null);
  const [salesData, setSalesData] = useState<SalesReportSummaryData | null>(null);
  const [procData, setProcData] = useState<ProcurementReportSummaryData | null>(null);
  const [invData, setInvData] = useState<InventoryStockReportData | null>(null);
  const [hrData, setHrData] = useState<HeadcountReportData | null>(null);
  const [payrollData, setPayrollData] = useState<PayrollReportSummaryData | null>(null);
  const [crmData, setCrmData] = useState<any>(null);

  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadDomainReport();
  }, [activeDomain, fromDate, toDate]);

  const loadDomainReport = async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (activeDomain === 'finance') {
        const [pnl, bs] = await Promise.all([
          reportingService.getProfitLoss(fromDate, toDate),
          reportingService.getBalanceSheet(toDate),
        ]);
        setPnlData(pnl);
        setBsData(bs);
      } else if (activeDomain === 'sales') {
        const s = await reportingService.getSalesSummary(fromDate, toDate);
        setSalesData(s);
      } else if (activeDomain === 'procurement') {
        const p = await reportingService.getProcurementSummary(fromDate, toDate);
        setProcData(p);
      } else if (activeDomain === 'inventory') {
        const i = await reportingService.getStockByWarehouse();
        setInvData(i);
      } else if (activeDomain === 'hr') {
        const h = await reportingService.getHeadcountReport(toDate);
        setHrData(h);
      } else if (activeDomain === 'payroll') {
        const pr = await reportingService.getPayrollSummary(fromDate, toDate);
        setPayrollData(pr);
      } else if (activeDomain === 'crm') {
        const c = await reportingService.getCrmLeadsSummary(fromDate, toDate);
        setCrmData(c);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to compile enterprise domain report');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportCsv = async (reportType: string) => {
    setIsExporting(true);
    try {
      await reportingService.downloadReportCsv(reportType, fromDate, toDate, toDate);
      success('Export Completed', `${reportType} report CSV downloaded successfully.`);
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to download report CSV');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Enterprise Reporting Hub</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Real-time multi-dimensional financial, operational, and supply-chain intelligence
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" icon={<RefreshCw className="w-4 h-4" />} onClick={loadDomainReport}>
            Refresh
          </Button>
          <Button
            variant="primary"
            icon={<Download className="w-4 h-4" />}
            loading={isExporting}
            onClick={() => handleExportCsv(activeDomain === 'finance' ? 'profit_loss' : activeDomain)}
          >
            Export CSV
          </Button>
        </div>
      </div>

      {/* Domain Navigation Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 space-x-1 overflow-x-auto">
        <button
          onClick={() => setActiveDomain('finance')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 whitespace-nowrap ${
            activeDomain === 'finance'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <DollarSign className="w-4 h-4" /> Finance & P&L
        </button>
        <button
          onClick={() => setActiveDomain('sales')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 whitespace-nowrap ${
            activeDomain === 'sales'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <TrendingUp className="w-4 h-4" /> Sales Analysis
        </button>
        <button
          onClick={() => setActiveDomain('procurement')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 whitespace-nowrap ${
            activeDomain === 'procurement'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <ShoppingBag className="w-4 h-4" /> Procurement & Spend
        </button>
        <button
          onClick={() => setActiveDomain('inventory')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 whitespace-nowrap ${
            activeDomain === 'inventory'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Boxes className="w-4 h-4" /> Inventory & Stock
        </button>
        <button
          onClick={() => setActiveDomain('hr')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 whitespace-nowrap ${
            activeDomain === 'hr'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Users className="w-4 h-4" /> HR & Headcount
        </button>
        <button
          onClick={() => setActiveDomain('payroll')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 whitespace-nowrap ${
            activeDomain === 'payroll'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <CreditCard className="w-4 h-4" /> Payroll Disbursements
        </button>
        <button
          onClick={() => setActiveDomain('crm')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 whitespace-nowrap ${
            activeDomain === 'crm'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Target className="w-4 h-4" /> CRM Pipeline
        </button>
      </div>

      {/* Date Filter Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-wrap gap-4 items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase text-gray-500">From:</span>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white px-2 py-1"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase text-gray-500">To:</span>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white px-2 py-1"
            />
          </div>
        </div>

        <div className="text-xs text-gray-400">
          Grounded directly against backend reporting endpoints
        </div>
      </div>

      {/* Report Content View */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden p-6">
        {isLoading ? (
          <LoadingState message={`Compiling ${activeDomain.toUpperCase()} domain intelligence...`} />
        ) : error ? (
          <ErrorState title="Failed to generate report" message={error} onRetry={loadDomainReport} />
        ) : (
          <>
            {/* Domain: Finance */}
            {activeDomain === 'finance' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <KpiCard
                    title="Revenue"
                    value={`$${Number(pnlData?.total_revenue || 0).toLocaleString()}`}
                    icon={<ArrowUpRight className="w-5 h-5 text-emerald-600" />}
                    description="Gross income"
                  />
                  <KpiCard
                    title="Operating Expenses"
                    value={`$${Number(pnlData?.total_expense || 0).toLocaleString()}`}
                    icon={<ArrowDownRight className="w-5 h-5 text-red-600" />}
                    description="Operating costs"
                  />
                  <KpiCard
                    title="Net Profit"
                    value={`$${Number(pnlData?.net_income || 0).toLocaleString()}`}
                    icon={<DollarSign className="w-5 h-5 text-blue-600" />}
                    description="Bottom-line income"
                  />
                </div>

                <div className="pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
                  <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Export Available Formats:
                  </span>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      icon={<Download className="w-3.5 h-3.5" />}
                      onClick={() => handleExportCsv('profit_loss')}
                    >
                      Export P&L CSV
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      icon={<Download className="w-3.5 h-3.5" />}
                      onClick={() => handleExportCsv('balance_sheet')}
                    >
                      Export Balance Sheet CSV
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      icon={<Download className="w-3.5 h-3.5" />}
                      onClick={() => handleExportCsv('trial_balance')}
                    >
                      Export Trial Balance CSV
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Domain: Sales */}
            {activeDomain === 'sales' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <KpiCard
                    title="Total Sales Orders"
                    value={salesData?.total_orders || 0}
                    icon={<ShoppingBag className="w-5 h-5 text-blue-600" />}
                    description="Orders booked in period"
                  />
                  <KpiCard
                    title="Total Invoiced Value"
                    value={`$${Number(salesData?.total_sales_amount || 0).toLocaleString()}`}
                    icon={<DollarSign className="w-5 h-5 text-emerald-600" />}
                    description="Gross revenue volume"
                  />
                  <KpiCard
                    title="Avg Order Value"
                    value={`$${Number(salesData?.average_order_value || 0).toFixed(2)}`}
                    icon={<TrendingUp className="w-5 h-5 text-purple-600" />}
                    description="Average transaction size"
                  />
                </div>

                <div className="pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
                  <Button
                    size="sm"
                    variant="primary"
                    icon={<Download className="w-3.5 h-3.5" />}
                    onClick={() => handleExportCsv('sales')}
                  >
                    Download Full Sales CSV
                  </Button>
                </div>
              </div>
            )}

            {/* Domain: Procurement */}
            {activeDomain === 'procurement' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <KpiCard
                    title="Purchase Orders Issued"
                    value={procData?.total_po_count || 0}
                    icon={<ShoppingBag className="w-5 h-5 text-blue-600" />}
                    description="Vendor orders placed"
                  />
                  <KpiCard
                    title="Total Procurement Spend"
                    value={`$${Number(procData?.total_spend_amount || 0).toLocaleString()}`}
                    icon={<DollarSign className="w-5 h-5 text-emerald-600" />}
                    description="Total vendor disbursements"
                  />
                  <KpiCard
                    title="Active Suppliers"
                    value={procData?.active_suppliers_count || 0}
                    icon={<Building2 className="w-5 h-5 text-purple-600" />}
                    description="Supplying partners"
                  />
                </div>

                <div className="pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
                  <Button
                    size="sm"
                    variant="primary"
                    icon={<Download className="w-3.5 h-3.5" />}
                    onClick={() => handleExportCsv('procurement')}
                  >
                    Download Procurement Spend CSV
                  </Button>
                </div>
              </div>
            )}

            {/* Domain: Inventory */}
            {activeDomain === 'inventory' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <KpiCard
                    title="Warehouses Managed"
                    value={invData?.warehouse_breakdown?.length || 0}
                    icon={<Building2 className="w-5 h-5 text-blue-600" />}
                    description="Fulfillment locations"
                  />
                  <KpiCard
                    title="Total Stock Units"
                    value={Number(invData?.total_units_on_hand || 0).toLocaleString()}
                    icon={<Boxes className="w-5 h-5 text-emerald-600" />}
                    description="Physical items across sites"
                  />
                  <KpiCard
                    title="Inventory Valuation"
                    value={`$${Number(invData?.total_valuation || 0).toLocaleString()}`}
                    icon={<DollarSign className="w-5 h-5 text-purple-600" />}
                    description="Capital invested in stock"
                  />
                </div>

                <div className="pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
                  <Button
                    size="sm"
                    variant="primary"
                    icon={<Download className="w-3.5 h-3.5" />}
                    onClick={() => handleExportCsv('inventory')}
                  >
                    Download Stock Valuation CSV
                  </Button>
                </div>
              </div>
            )}

            {/* Domain: HR */}
            {activeDomain === 'hr' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <KpiCard
                    title="Total Workforce Headcount"
                    value={hrData?.total_headcount || 0}
                    icon={<Users className="w-5 h-5 text-blue-600" />}
                    description="Active employees"
                  />
                  <KpiCard
                    title="Departments Operating"
                    value={hrData?.department_breakdown?.length || 0}
                    icon={<Layers className="w-5 h-5 text-purple-600" />}
                    description="Organizational units"
                  />
                </div>

                <div className="pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
                  <Button
                    size="sm"
                    variant="primary"
                    icon={<Download className="w-3.5 h-3.5" />}
                    onClick={() => handleExportCsv('hr')}
                  >
                    Download Headcount CSV
                  </Button>
                </div>
              </div>
            )}

            {/* Domain: Payroll */}
            {activeDomain === 'payroll' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <KpiCard
                    title="Total Payroll Disbursed"
                    value={`$${Number(payrollData?.total_net_payroll || 0).toLocaleString()}`}
                    icon={<CreditCard className="w-5 h-5 text-emerald-600" />}
                    description="Net salaries paid"
                  />
                  <KpiCard
                    title="Tax & Deductions"
                    value={`$${Number(payrollData?.total_statutory_deductions || 0).toLocaleString()}`}
                    icon={<DollarSign className="w-5 h-5 text-red-600" />}
                    description="Withholding taxes"
                  />
                  <KpiCard
                    title="Employees Paid"
                    value={payrollData?.employees_processed || 0}
                    icon={<Users className="w-5 h-5 text-blue-600" />}
                    description="Disbursement count"
                  />
                </div>

                <div className="pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
                  <Button
                    size="sm"
                    variant="primary"
                    icon={<Download className="w-3.5 h-3.5" />}
                    onClick={() => handleExportCsv('payroll')}
                  >
                    Download Payroll Ledger CSV
                  </Button>
                </div>
              </div>
            )}

            {/* Domain: CRM */}
            {activeDomain === 'crm' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <KpiCard
                    title="Total Leads Ingested"
                    value={crmData?.total_leads || 0}
                    icon={<Target className="w-5 h-5 text-blue-600" />}
                    description="Prospective opportunities"
                  />
                  <KpiCard
                    title="Converted to Customers"
                    value={crmData?.converted_leads || 0}
                    icon={<TrendingUp className="w-5 h-5 text-emerald-600" />}
                    description="Won clients"
                  />
                </div>

                <div className="pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
                  <Button
                    size="sm"
                    variant="primary"
                    icon={<Download className="w-3.5 h-3.5" />}
                    onClick={() => handleExportCsv('crm')}
                  >
                    Download CRM Funnel CSV
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
