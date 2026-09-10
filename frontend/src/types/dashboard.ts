import { NavSection } from './common';

export interface DashboardHRMetrics {
  total_employees: number;
  active_employees: number;
  total_departments: number;
}

export interface DashboardCRMMetrics {
  open_leads: number;
  total_leads: number;
  active_opportunities: number;
  pipeline_value: number;
  weighted_forecast_value: number;
}

export interface DashboardSalesMetrics {
  total_orders_count: number;
  total_sales_revenue: number;
  pending_orders_count: number;
  average_order_value: number;
}

export interface DashboardProcurementMetrics {
  total_pos_count: number;
  total_spend: number;
  pending_pos_count: number;
}

export interface DashboardInventoryMetrics {
  total_products_count: number;
  total_warehouses_count: number;
  total_on_hand_quantity: number;
  total_inventory_valuation: number;
  low_stock_items_count: number;
}

export interface DashboardFinanceMetrics {
  total_revenue: number;
  total_expenses: number;
  net_operating_income: number;
  posted_journals_count: number;
}

export interface DashboardPayrollMetrics {
  total_payroll_runs_count: number;
  total_payroll_cost: number;
  total_net_disbursed: number;
}

export interface ExecutiveDashboardResponse {
  as_of_date: string;
  hr: DashboardHRMetrics;
  crm: DashboardCRMMetrics;
  sales: DashboardSalesMetrics;
  procurement: DashboardProcurementMetrics;
  inventory: DashboardInventoryMetrics;
  finance: DashboardFinanceMetrics;
  payroll: DashboardPayrollMetrics;
}

// Legacy / Component types
export interface KpiMetric {
  id: string;
  title: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'neutral';
  timeframe: string;
  icon_name: 'dollar' | 'wallet' | 'package' | 'receipt' | string;
  badge_color: 'blue' | 'peach' | 'cyan' | 'red' | string;
  comparison_text: string;
}

export interface ApprovalItem {
  id: string;
  type: string;
  title: string;
  subject: string;
  reference_number: string;
  requested_by: string;
  department: string;
  amount?: string;
  formatted_amount?: string;
  date?: string;
  created_at: string;
  status: string;
}

export interface ActivityItem {
  id: string;
  user_name: string;
  avatar_url?: string;
  action: string;
  target: string;
  timestamp: string;
  time_ago?: string;
  category: string;
  dot_color?: string;
}

export interface RevenueDataPoint {
  date: string;
  revenue: number;
  target?: number;
}

export interface SalesProcurementDataPoint {
  month: string;
  sales: number;
  procurement: number;
}

export interface SystemAlert {
  id: string;
  title: string;
  message: string;
  description?: string;
  severity: 'low' | 'medium' | 'high' | 'critical' | string;
  color_theme?: string;
  icon: string;
  timestamp: string;
}
