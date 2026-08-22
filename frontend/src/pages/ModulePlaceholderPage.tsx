import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  Boxes,
  ArrowLeft,
  Users,
  CalendarCheck,
  CreditCard,
  Package,
  Layers,
  UserCheck,
  FileText,
  Landmark,
  BarChart3,
  Sparkles,
} from 'lucide-react';
import { Button } from '../components/common/Button';

interface ModuleMeta {
  title: string;
  category: string;
  phase: string;
  description: string;
  plannedFeatures: string[];
  icon: React.ReactNode;
}

const MODULE_DATA: Record<string, ModuleMeta> = {
  '/workforce/employees': {
    title: 'Employees & Workforce Directory',
    category: 'Workforce',
    phase: 'Phase FE-2 (HR Frontend)',
    description: 'Comprehensive staff directory, department hierarchy, role assignments, and detailed employee records.',
    plannedFeatures: [
      'Interactive Employee Directory & Search (Screenshot 11)',
      'Employee Detail & Performance Profiles (Screenshot 7)',
      'Departmental Filtering & Headcount Analytics',
      'Document & Statutory Profile Management',
    ],
    icon: <Users className="w-8 h-8 text-blue-600" />,
  },
  '/workforce/attendance': {
    title: 'Attendance & Leave Management',
    category: 'Workforce',
    phase: 'Phase FE-2 (HR Frontend)',
    description: 'Real-time shift clock-ins, leave balance tracking, and attendance variance analytics.',
    plannedFeatures: [
      'Shift Assignment & Rosters',
      'Leave Balances & Request Approvals',
      'Attendance YTD Ring Gauges & Metrics',
      'Holiday Calendars & Exceptions',
    ],
    icon: <CalendarCheck className="w-8 h-8 text-emerald-600" />,
  },
  '/workforce/payroll': {
    title: 'Payroll & Compensation',
    category: 'Workforce',
    phase: 'Phase FE-3 (Payroll Frontend)',
    description: 'Automated payroll processing, salary structures, statutory tax deductions, and bank disbursement exports.',
    plannedFeatures: [
      'Monthly & Mid-Month Payroll Runs',
      'Salary Slip Generation & PDF Export',
      'Tax & Statutory Deductions Engine',
      'Direct Bank Transfer File Integration',
    ],
    icon: <CreditCard className="w-8 h-8 text-amber-600" />,
  },
  '/inventory/products': {
    title: 'Product Master & Catalog',
    category: 'Inventory',
    phase: 'Phase FE-4 (Inventory Frontend)',
    description: 'SKU management, unit of measure conversions, categories, and barcode/serial tracking.',
    plannedFeatures: [
      'Master Product Catalog & Variants',
      'Barcode & Lot/Serial Number Tracking',
      'Categories & Brand Hierarchy',
      'Minimum Threshold Alerts',
    ],
    icon: <Package className="w-8 h-8 text-indigo-600" />,
  },
  '/inventory/stock': {
    title: 'Stock Control & Warehouse Operations',
    category: 'Inventory',
    phase: 'Phase FE-4 (Inventory Frontend)',
    description: 'Multi-warehouse stock balances, goods receipts (GRN), goods issues (GIN), and inter-warehouse transfers.',
    plannedFeatures: [
      'Real-time Multi-Warehouse Stock Ledger',
      'Goods Receipt (GRN) & Issue (GIN) Vouchers',
      'Cycle Counting & Stock Reconciliations',
      'Inter-Warehouse Stock Transfers',
    ],
    icon: <Layers className="w-8 h-8 text-sky-600" />,
  },
  '/sales/customers': {
    title: 'Customer Directory & CRM',
    category: 'Sales & CRM',
    phase: 'Phase FE-7 (CRM Frontend)',
    description: 'Customer master directory, lead pipelines, interaction timelines, and credit term profiles.',
    plannedFeatures: [
      'Customer 360° Profile & Accounts',
      'Lead & Opportunity Pipeline Stages',
      'Activity & Meeting Logs',
      'Credit Limit & Payment Term Setup',
    ],
    icon: <UserCheck className="w-8 h-8 text-purple-600" />,
  },
  '/sales/orders': {
    title: 'Sales Orders & Quotations',
    category: 'Sales & CRM',
    phase: 'Phase FE-6 (Sales Frontend)',
    description: 'Sales quotation workflows, order confirmations, fulfillment dispatch, and customer invoicing.',
    plannedFeatures: [
      'Quotation Builder & Versioning',
      'Sales Order Management & Approvals',
      'Delivery Order Dispatches',
      'Pricing & Volume Discount Engine',
    ],
    icon: <FileText className="w-8 h-8 text-blue-600" />,
  },
  '/finance/accounts': {
    title: 'Chart of Accounts & General Ledger',
    category: 'Finance',
    phase: 'Phase FE-8 (Finance Frontend)',
    description: 'Double-entry journal entries, multi-currency fiscal periods, accounts payable, and receivables.',
    plannedFeatures: [
      'Hierarchical Chart of Accounts (CoA)',
      'Double-entry Journal Vouchers',
      'Accounts Receivable & Payable Invoices',
      'Bank Reconciliation & Cost Centers',
    ],
    icon: <Landmark className="w-8 h-8 text-emerald-600" />,
  },
  '/finance/reports': {
    title: 'Financial Statements & Analytics',
    category: 'Finance',
    phase: 'Phase FE-9 (Reporting + Analytics)',
    description: 'Automated Balance Sheets, Profit & Loss statements, Trial Balances, and Cash Flow projections.',
    plannedFeatures: [
      'Balance Sheet & Income Statement',
      'Trial Balance & Cash Flow Forecasts',
      'Cost Center Profitability Reports',
      'Excel & PDF Report Export Engine',
    ],
    icon: <BarChart3 className="w-8 h-8 text-brand-600" />,
  },
};

export const ModulePlaceholderPage: React.FC = () => {
  const location = useLocation();
  const currentMeta = MODULE_DATA[location.pathname] || {
    title: 'ERP Business Module',
    category: 'Module',
    phase: 'Upcoming Phase',
    description: 'This business module is part of the ApnaERP roadmap.',
    plannedFeatures: ['Enterprise Workflow Automation', 'Real-time Reporting', 'Role-Based Permissions'],
    icon: <Boxes className="w-8 h-8 text-brand-600" />,
  };

  return (
    <div className="max-w-4xl mx-auto py-8 animate-fade-in space-y-6">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <Link to="/dashboard" className="hover:text-brand-600 transition-colors">
          Overview
        </Link>
        <span>/</span>
        <span>{currentMeta.category}</span>
        <span>/</span>
        <span className="font-semibold text-slate-800 dark:text-slate-200">
          {currentMeta.title}
        </span>
      </div>

      {/* Main Module Banner Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-start gap-5">
          <div className="w-14 h-14 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center shrink-0 shadow-xs">
            {currentMeta.icon}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-brand-600 bg-brand-50 dark:bg-brand-950/60 px-2.5 py-0.5 rounded-md">
                {currentMeta.phase}
              </span>
              <span className="text-xs text-slate-400 font-medium flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-amber-500" /> Planned for rollout
              </span>
            </div>

            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
              {currentMeta.title}
            </h1>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 mt-2 leading-relaxed">
              {currentMeta.description}
            </p>
          </div>
        </div>

        {/* Planned Features List */}
        <div className="mt-8 pt-6 border-t border-slate-100 dark:border-slate-800">
          <h3 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-4">
            Architecture & Key Capabilities in Next Phase
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {currentMeta.plannedFeatures.map((feat, index) => (
              <div
                key={index}
                className="flex items-center gap-2.5 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60 text-xs font-medium text-slate-700 dark:text-slate-200"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-brand-600 shrink-0" />
                <span>{feat}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Back action */}
        <div className="mt-8 pt-6 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            Backend API endpoints are implemented and ready in FastAPI router.
          </span>
          <Link to="/dashboard">
            <Button
              variant="primary"
              size="sm"
              leftIcon={<ArrowLeft className="w-4 h-4" />}
            >
              Return to Dashboard
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};
