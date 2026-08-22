import React from 'react';
import { Routes, Route, Navigate, useParams } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { ProtectedRoute } from './ProtectedRoute';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';
import { EmployeesPage } from '../pages/hr/EmployeesPage';
import { EmployeeDetailPage } from '../pages/hr/EmployeeDetailPage';
import { ProductsPage } from '../pages/inventory/ProductsPage';
import { PurchaseOrdersPage } from '../pages/procurement/PurchaseOrdersPage';
import { PurchaseOrderDetailPage } from '../pages/procurement/PurchaseOrderDetailPage';
import { SalesOrdersPage } from '../pages/sales/SalesOrdersPage';
import { SalesOrderDetailPage } from '../pages/sales/SalesOrderDetailPage';
import { ModulePlaceholderPage } from '../pages/ModulePlaceholderPage';
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
        <Route path="workforce/employees" element={<EmployeesPage />} />
        <Route path="workforce/employees/:id" element={<EmployeeDetailPage />} />
        <Route path="workforce/attendance" element={<ModulePlaceholderPage />} />
        <Route path="workforce/payroll" element={<ModulePlaceholderPage />} />

        {/* Direct aliases for Employees */}
        <Route path="employees" element={<Navigate to="/workforce/employees" replace />} />
        <Route path="employees/:id" element={<EmployeeDetailRedirect />} />

        {/* INVENTORY */}
        <Route path="inventory/products" element={<ProductsPage />} />
        <Route path="inventory/stock" element={<ModulePlaceholderPage />} />
        <Route path="products" element={<Navigate to="/inventory/products" replace />} />

        {/* PROCUREMENT */}
        <Route path="procurement" element={<Navigate to="/procurement/orders" replace />} />
        <Route path="procurement/orders" element={<PurchaseOrdersPage />} />
        <Route path="procurement/orders/:id" element={<PurchaseOrderDetailPage />} />

        {/* SALES & CRM */}
        <Route path="sales" element={<Navigate to="/sales/orders" replace />} />
        <Route path="sales/customers" element={<ModulePlaceholderPage />} />
        <Route path="sales/orders" element={<SalesOrdersPage />} />
        <Route path="sales/orders/:id" element={<SalesOrderDetailPage />} />
        <Route path="orders" element={<Navigate to="/sales/orders" replace />} />

        {/* FINANCE */}
        <Route path="finance" element={<Navigate to="/finance/accounts" replace />} />
        <Route path="finance/accounts" element={<ModulePlaceholderPage />} />
        <Route path="finance/reports" element={<ModulePlaceholderPage />} />
        <Route path="reports" element={<Navigate to="/finance/reports" replace />} />

        {/* 404 inside layout */}
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      {/* Global fallback */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};
