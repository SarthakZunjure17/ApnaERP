export interface KpiMetric {
  id: string;
  title: string;
  value: string;
  raw_value?: number;
  change: string;
  trend: 'up' | 'down' | 'neutral';
  comparison_text: string;
  icon_name: 'dollar' | 'wallet' | 'package' | 'receipt' | 'trending-up' | 'users';
  badge_color?: 'blue' | 'peach' | 'cyan' | 'red' | 'green';
}

export interface RevenueDataPoint {
  month: string;
  actual: number;
  forecast?: number;
}

export interface SalesProcurementDataPoint {
  period: string;
  sales: number;
  procurement: number;
}

export interface ApprovalItem {
  id: string;
  type: 'Purchase Order' | 'Payroll' | 'Expense' | 'Refund';
  type_icon: 'shopping-cart' | 'wallet' | 'file-text' | 'rotate-ccw';
  subject: string;
  amount: number;
  formatted_amount: string;
  date: string;
  status: 'Pending' | 'In Review' | 'Approved' | 'Rejected';
}

export interface SystemAlert {
  id: string;
  type: 'warning' | 'info' | 'error';
  title: string;
  description: string;
  icon: 'package-alert' | 'wallet-alert' | 'bell';
  color_theme: 'peach' | 'lavender' | 'blue' | 'red';
  timestamp?: string;
}

export interface ActivityItem {
  id: string;
  user_name: string;
  action: string;
  target: string;
  time_ago: string;
  dot_color: 'blue' | 'gray' | 'orange' | 'green';
}

export interface ExecutiveDashboardData {
  time_period: string;
  kpis: {
    total_revenue: KpiMetric;
    total_payroll: KpiMetric;
    inventory_value: KpiMetric;
    receivables: KpiMetric;
  };
  revenue_trend: RevenueDataPoint[];
  sales_vs_procurement: SalesProcurementDataPoint[];
  pending_approvals: ApprovalItem[];
  system_alerts: SystemAlert[];
  recent_activity: ActivityItem[];
}
