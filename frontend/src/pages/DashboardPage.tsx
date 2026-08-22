import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, Filter, Calendar, Check, SlidersHorizontal } from 'lucide-react';
import { dashboardService } from '../services/dashboardService';
import { ExecutiveDashboardData } from '../types/dashboard';
import { KpiCard } from '../components/common/KpiCard';
import { RevenueTrendChart } from '../components/dashboard/RevenueTrendChart';
import { SalesProcurementChart } from '../components/dashboard/SalesProcurementChart';
import { PendingApprovalsTable } from '../components/dashboard/PendingApprovalsTable';
import { SystemAlertsCard } from '../components/dashboard/SystemAlertsCard';
import { RecentActivityTimeline } from '../components/dashboard/RecentActivityTimeline';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { Modal } from '../components/common/Modal';
import { Button } from '../components/common/Button';
import { useToast } from '../context/ToastContext';

type PeriodOption = '30d' | 'quarter' | 'year';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [period, setPeriod] = useState<PeriodOption>('30d');
  const [data, setData] = useState<ExecutiveDashboardData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isFilterModalOpen, setIsFilterModalOpen] = useState<boolean>(false);
  const [selectedCurrency, setSelectedCurrency] = useState<'USD' | 'INR' | 'EUR'>('USD');
  const { info, success } = useToast();

  const fetchDashboardData = async (selectedPeriod: PeriodOption, isRefresh = false) => {
    if (isRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const result = await dashboardService.getExecutiveDashboard(selectedPeriod);
      setData(result);
      if (isRefresh) {
        success('Refreshed', 'Executive metrics and activities updated.');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load executive dashboard data.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData(period);
  }, [period]);

  const handlePeriodChange = (newPeriod: PeriodOption) => {
    setPeriod(newPeriod);
  };

  const handleManualRefresh = () => {
    fetchDashboardData(period, true);
  };

  if (isLoading && !data) {
    return <LoadingState message="Loading Executive Dashboard..." height="h-96" />;
  }

  if (error && !data) {
    return <ErrorState message={error} onRetry={() => fetchDashboardData(period)} />;
  }

  if (!data) return null;

  return (
    <div className="space-y-4 sm:space-y-5 animate-fade-in pb-8">
      {/* Top Page Header (Matching Screenshot 10) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Executive Dashboard
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            High-level financial and operational overview.
          </p>
        </div>

        {/* Right Controls: Period Selector, Refresh, Filter */}
        <div className="flex items-center gap-1.5 self-start sm:self-auto">
          {/* Segmented Period Buttons */}
          <div className="inline-flex items-center p-0.5 bg-slate-100/90 dark:bg-slate-800/80 rounded-lg border border-slate-200/60 dark:border-slate-700/60 text-xs font-medium">
            <button
              onClick={() => handlePeriodChange('30d')}
              className={`px-2.5 py-1 rounded-md text-xs transition-all cursor-pointer ${
                period === '30d'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                  : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              Last 30 Days
            </button>
            <button
              onClick={() => handlePeriodChange('quarter')}
              className={`px-2.5 py-1 rounded-md text-xs transition-all cursor-pointer ${
                period === 'quarter'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                  : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              Quarter
            </button>
            <button
              onClick={() => handlePeriodChange('year')}
              className={`px-2.5 py-1 rounded-md text-xs transition-all cursor-pointer ${
                period === 'year'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                  : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              Year
            </button>
          </div>

          {/* Refresh Button */}
          <button
            onClick={handleManualRefresh}
            disabled={isRefreshing}
            className="p-1.5 bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700/80 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-500 hover:text-slate-700 dark:text-slate-300 rounded-lg shadow-xs transition-colors cursor-pointer"
            title="Refresh Metrics"
            aria-label="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-brand-600' : ''}`} />
          </button>

          {/* Filter Button (Solid Blue matching Screenshot 10) */}
          <button
            onClick={() => setIsFilterModalOpen(true)}
            className="p-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg shadow-xs transition-colors cursor-pointer flex items-center justify-center"
            title="Dashboard Filters"
            aria-label="Filter"
          >
            <Filter className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Row 1: KPI Cards Grid (4 Cards Matching Screenshot 10) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-4">
        <KpiCard metric={data.kpis.total_revenue} />
        <KpiCard metric={data.kpis.total_payroll} />
        <KpiCard metric={data.kpis.inventory_value} />
        <KpiCard metric={data.kpis.receivables} />
      </div>

      {/* Row 2: Visual Charts Grid (Revenue Trend + Sales vs Procurement) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <RevenueTrendChart data={data.revenue_trend} />
        <SalesProcurementChart data={data.sales_vs_procurement} />
      </div>

      {/* Row 3: Operations & Stream Grid (Pending Approvals 7 cols / System Alerts & Activity 5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Pending Approvals Table (Col span 7 on lg) */}
        <div className="lg:col-span-7">
          <PendingApprovalsTable
            items={data.pending_approvals}
            onViewAll={() => navigate('/procurement/orders')}
          />
        </div>

        {/* Right Column: Alerts & Recent Activity (Col span 5 on lg) */}
        <div className="lg:col-span-5 space-y-4">
          <SystemAlertsCard alerts={data.system_alerts} />
          <RecentActivityTimeline items={data.recent_activity} />
        </div>
      </div>

      {/* Filter Modal */}
      <Modal
        isOpen={isFilterModalOpen}
        onClose={() => setIsFilterModalOpen(false)}
        title="Dashboard View Settings"
      >
        <div className="space-y-4 text-xs sm:text-sm">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1.5">
              Display Currency
            </label>
            <div className="grid grid-cols-3 gap-2">
              {(['USD', 'INR', 'EUR'] as const).map((curr) => (
                <button
                  key={curr}
                  type="button"
                  onClick={() => setSelectedCurrency(curr)}
                  className={`p-2 rounded-lg border text-center font-semibold transition-colors cursor-pointer ${
                    selectedCurrency === curr
                      ? 'bg-brand-50 border-brand-500 text-brand-700 dark:bg-brand-950/60 dark:text-brand-300'
                      : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50'
                  }`}
                >
                  {curr}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1.5">
              Cost Center Scope
            </label>
            <select className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200 focus:outline-none focus:border-brand-500">
              <option>All Business Units (Global Consolidation)</option>
              <option>Corporate Headquarters (HQ)</option>
              <option>Engineering & Technology</option>
              <option>Supply Chain & Logistics</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsFilterModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setIsFilterModalOpen(false);
                info('Filter Applied', `Viewing Executive metrics in ${selectedCurrency}`);
              }}
            >
              Apply Filter
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
