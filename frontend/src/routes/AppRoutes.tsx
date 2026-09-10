import React from 'react';
import { Routes, Route, Navigate, useParams } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { ProtectedRoute } from './ProtectedRoute';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';

// HR & Payroll
import { EmployeesPage } from '../pages/hr/EmployeesPage';
import { EmployeeDetailPage } from '../pages/hr/EmployeeDetailPage';
import { AttendancePage } from '../pages/hr/AttendancePage';
import { PayrollPage } from '../pages/payroll/PayrollPage';

// Inventory
import { ProductsPage } from '../pages/inventory/ProductsPage';
import { StockMovementsPage } from '../pages/inventory/StockMovementsPage';

// Procurement
import { PurchaseOrdersPage } from '../pages/procurement/PurchaseOrdersPage';
import { PurchaseOrderDetailPage } from '../pages/procurement/PurchaseOrderDetailPage';
import { SuppliersPage } from '../pages/procurement/SuppliersPage';

// Sales
import { CustomersPage } from '../pages/sales/CustomersPage';
import { SalesOrdersPage } from '../pages/sales/SalesOrdersPage';
import { SalesOrderDetailPage } from '../pages/sales/SalesOrderDetailPage';
import { QuotationsPage } from '../pages/sales/QuotationsPage';

// CRM
import { CrmLeadsPage } from '../pages/crm/CrmLeadsPage';
import { CrmOpportunitiesPage } from '../pages/crm/CrmOpportunitiesPage';

// Finance
import { ChartOfAccountsPage } from '../pages/finance/ChartOfAccountsPage';
import { JournalsPage } from '../pages/finance/JournalsPage';
import { GeneralLedgerPage } from '../pages/finance/GeneralLedgerPage';

// Reports & Platform
import { ReportingHubPage } from '../pages/reporting/ReportingHubPage';
import { PlatformAdminPage } from '../pages/platform/PlatformAdminPage';
import { NotFoundPage } from '../pages/NotFoundPage';

// Helper component for /employees/:id redirect
const EmployeeDetailRedirect: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/workforce/employees/${id}`} replace />;
};

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected Routes inside AppShell */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />

        {/* WORKFORCE */}
        <Route path="workforce" element={<Navigate to="/workforce/employees" replace />} />
        <Route path="workforce/employees" element={<EmployeesPage />} />
        <Route path="workforce/employees/:id" element={<EmployeeDetailPage />} />
        <Route path="workforce/attendance" element={<AttendancePage />} />
        <Route path="workforce/payroll" element={<PayrollPage />} />

        {/* Aliases for Employees */}
        <Route path="employees" element={<Navigate to="/workforce/employees" replace />} />
        <Route path="employees/:id" element={<EmployeeDetailRedirect />} />

        {/* INVENTORY */}
        <Route path="inventory" element={<Navigate to="/inventory/products" replace />} />
        <Route path="inventory/products" element={<ProductsPage />} />
        <Route path="inventory/stock" element={<StockMovementsPage />} />
        <Route path="products" element={<Navigate to="/inventory/products" replace />} />

        {/* PROCUREMENT */}
        <Route path="procurement" element={<Navigate to="/procurement/orders" replace />} />
        <Route path="procurement/orders" element={<PurchaseOrdersPage />} />
        <Route path="procurement/orders/:id" element={<PurchaseOrderDetailPage />} />
        <Route path="procurement/suppliers" element={<SuppliersPage />} />

        {/* SALES */}
        <Route path="sales" element={<Navigate to="/sales/orders" replace />} />
        <Route path="sales/customers" element={<CustomersPage />} />
        <Route path="sales/orders" element={<SalesOrdersPage />} />
        <Route path="sales/orders/:id" element={<SalesOrderDetailPage />} />
        <Route path="sales/quotations" element={<QuotationsPage />} />
        <Route path="orders" element={<Navigate to="/sales/orders" replace />} />

        {/* CRM */}
        <Route path="crm" element={<Navigate to="/crm/leads" replace />} />
        <Route path="crm/leads" element={<CrmLeadsPage />} />
        <Route path="crm/opportunities" element={<CrmOpportunitiesPage />} />

        {/* FINANCE */}
        <Route path="finance" element={<Navigate to="/finance/accounts" replace />} />
        <Route path="finance/accounts" element={<ChartOfAccountsPage />} />
        <Route path="finance/journals" element={<JournalsPage />} />
        <Route path="finance/ledger" element={<GeneralLedgerPage />} />
        <Route path="finance/reports" element={<ReportingHubPage />} />

        {/* REPORTING */}
        <Route path="reports" element={<ReportingHubPage />} />

        {/* PLATFORM ADMIN */}
        <Route path="admin" element={<PlatformAdminPage />} />
        <Route path="platform/admin" element={<PlatformAdminPage />} />

        {/* 404 inside layout */}
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      {/* Global fallback */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};
