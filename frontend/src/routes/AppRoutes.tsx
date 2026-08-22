import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { ProtectedRoute } from './ProtectedRoute';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';
import { EmployeesPage } from '../pages/hr/EmployeesPage';
import { EmployeeDetailPage } from '../pages/hr/EmployeeDetailPage';
import { ProductsPage } from '../pages/inventory/ProductsPage';
import { PurchaseOrdersPage } from '../pages/procurement/PurchaseOrdersPage';
import { PurchaseOrderDetailPage } from '../pages/procurement/PurchaseOrderDetailPage';
import { ModulePlaceholderPage } from '../pages/ModulePlaceholderPage';
import { NotFoundPage } from '../pages/NotFoundPage';

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

        {/* WORKFORCE (FE-2) */}
        <Route path="workforce/employees" element={<EmployeesPage />} />
        <Route path="workforce/employees/:id" element={<EmployeeDetailPage />} />
        <Route path="workforce/attendance" element={<EmployeeDetailPage />} />
        <Route path="workforce/payroll" element={<EmployeeDetailPage />} />

        {/* INVENTORY (FE-4) */}
        <Route path="inventory/products" element={<ProductsPage />} />
        <Route path="inventory/stock" element={<PurchaseOrdersPage />} />

        {/* PROCUREMENT (FE-5) */}
        <Route path="procurement/orders" element={<PurchaseOrdersPage />} />
        <Route path="procurement/orders/:id" element={<PurchaseOrderDetailPage />} />

        {/* SALES & CRM */}
        <Route path="sales/customers" element={<ModulePlaceholderPage />} />
        <Route path="sales/orders" element={<ModulePlaceholderPage />} />

        {/* FINANCE */}
        <Route path="finance/accounts" element={<ModulePlaceholderPage />} />
        <Route path="finance/reports" element={<ModulePlaceholderPage />} />

        {/* 404 inside layout */}
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      {/* Global fallback */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};
