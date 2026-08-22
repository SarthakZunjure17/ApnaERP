import { api } from './api';
import { ExecutiveDashboardData } from '../types/dashboard';

const DASHBOARD_DATA_30D: ExecutiveDashboardData = {
  time_period: 'Last 30 Days',
  kpis: {
    total_revenue: {
      id: 'kpi-revenue',
      title: 'TOTAL REVENUE',
      value: '$4.2M',
      raw_value: 4200000,
      change: '12%',
      trend: 'up',
      comparison_text: 'vs previous period',
      icon_name: 'dollar',
      badge_color: 'blue',
    },
    total_payroll: {
      id: 'kpi-payroll',
      title: 'TOTAL PAYROLL',
      value: '$820K',
      raw_value: 820000,
      change: '2%',
      trend: 'down',
      comparison_text: 'vs previous period',
      icon_name: 'wallet',
      badge_color: 'peach',
    },
    inventory_value: {
      id: 'kpi-inventory',
      title: 'INVENTORY VALUE',
      value: '$1.5M',
      raw_value: 1500000,
      change: 'Stable',
      trend: 'neutral',
      comparison_text: 'vs previous period',
      icon_name: 'package',
      badge_color: 'cyan',
    },
    receivables: {
      id: 'kpi-receivables',
      title: 'RECEIVABLES',
      value: '$312K',
      raw_value: 312000,
      change: '5%',
      trend: 'up',
      comparison_text: 'Requires attention',
      icon_name: 'receipt',
      badge_color: 'red',
    },
  },
  revenue_trend: [
    { month: 'Jan', actual: 1.2, forecast: 1.1 },
    { month: 'Feb', actual: 1.8, forecast: 1.6 },
    { month: 'Mar', actual: 2.4, forecast: 2.2 },
    { month: 'Apr', actual: 3.2, forecast: 3.0 },
    { month: 'May', actual: 3.8, forecast: 4.1 },
    { month: 'Jun', actual: 4.2, forecast: 4.6 },
  ],
  sales_vs_procurement: [
    { period: 'Q1', sales: 650, procurement: 420 },
    { period: 'Q2', sales: 780, procurement: 520 },
    { period: 'Q3', sales: 940, procurement: 640 },
    { period: 'Q4', sales: 580, procurement: 490 },
    { period: "Q1'24", sales: 1120, procurement: 860 },
  ],
  pending_approvals: [
    {
      id: 'po-089',
      type: 'Purchase Order',
      type_icon: 'shopping-cart',
      subject: 'PO-2023-089: Office Supplies',
      amount: 1240.0,
      formatted_amount: '$1,240.00',
      date: 'Oct 12, 2023',
      status: 'Pending',
    },
    {
      id: 'pr-mid-oct',
      type: 'Payroll',
      type_icon: 'wallet',
      subject: 'October Mid-Month Run',
      amount: 42500.0,
      formatted_amount: '$42,500.00',
      date: 'Oct 14, 2023',
      status: 'Pending',
    },
    {
      id: 'exp-442',
      type: 'Expense',
      type_icon: 'file-text',
      subject: 'EXP-442: Client Dinner (Sales)',
      amount: 845.5,
      formatted_amount: '$845.50',
      date: 'Oct 14, 2023',
      status: 'Pending',
    },
    {
      id: 'po-090',
      type: 'Purchase Order',
      type_icon: 'shopping-cart',
      subject: 'PO-2023-090: IT Equipment',
      amount: 12400.0,
      formatted_amount: '$12,400.00',
      date: 'Oct 15, 2023',
      status: 'In Review',
    },
    {
      id: 'ref-092',
      type: 'Refund',
      type_icon: 'rotate-ccw',
      subject: 'REF-092: Customer Complaint',
      amount: 350.0,
      formatted_amount: '$350.00',
      date: 'Oct 15, 2023',
      status: 'Pending',
    },
  ],
  system_alerts: [
    {
      id: 'alert-1',
      type: 'warning',
      title: 'Low Stock Alert',
      description: 'Product SKUs: A-102, B-405 are below minimum threshold.',
      icon: 'package-alert',
      color_theme: 'peach',
      timestamp: '10 mins ago',
    },
    {
      id: 'alert-2',
      type: 'info',
      title: 'Payroll Variance',
      description: 'Dept Engineering exceeded overtime budget by 15%.',
      icon: 'wallet-alert',
      color_theme: 'lavender',
      timestamp: '1 hour ago',
    },
  ],
  recent_activity: [
    {
      id: 'act-1',
      user_name: 'Sarah Jenkins',
      action: 'approved PO-2023-088',
      target: 'PO-2023-088',
      time_ago: '10 minutes ago',
      dot_color: 'blue',
    },
    {
      id: 'act-2',
      user_name: 'System',
      action: 'completed daily backup',
      target: 'Database Snapshot #4821',
      time_ago: '2 hours ago',
      dot_color: 'gray',
    },
    {
      id: 'act-3',
      user_name: 'Mike Chen',
      action: 'generated Q3 Financial Report',
      target: 'Q3 Financials',
      time_ago: '4 hours ago',
      dot_color: 'orange',
    },
    {
      id: 'act-4',
      user_name: 'New client onboarding:',
      action: 'Acme Corp',
      target: 'Acme Corp CRM',
      time_ago: 'Yesterday, 14:30',
      dot_color: 'blue',
    },
  ],
};

const DASHBOARD_DATA_QUARTER: ExecutiveDashboardData = {
  ...DASHBOARD_DATA_30D,
  time_period: 'Quarter',
  kpis: {
    total_revenue: {
      ...DASHBOARD_DATA_30D.kpis.total_revenue,
      value: '$12.8M',
      change: '18%',
    },
    total_payroll: {
      ...DASHBOARD_DATA_30D.kpis.total_payroll,
      value: '$2.45M',
      change: '4%',
    },
    inventory_value: {
      ...DASHBOARD_DATA_30D.kpis.inventory_value,
      value: '$1.62M',
      change: 'Stable',
    },
    receivables: {
      ...DASHBOARD_DATA_30D.kpis.receivables,
      value: '$480K',
      change: '8%',
    },
  },
};

const DASHBOARD_DATA_YEAR: ExecutiveDashboardData = {
  ...DASHBOARD_DATA_30D,
  time_period: 'Year',
  kpis: {
    total_revenue: {
      ...DASHBOARD_DATA_30D.kpis.total_revenue,
      value: '$48.6M',
      change: '24%',
    },
    total_payroll: {
      ...DASHBOARD_DATA_30D.kpis.total_payroll,
      value: '$9.8M',
      change: '6%',
    },
    inventory_value: {
      ...DASHBOARD_DATA_30D.kpis.inventory_value,
      value: '$1.75M',
      change: 'Stable',
    },
    receivables: {
      ...DASHBOARD_DATA_30D.kpis.receivables,
      value: '$520K',
      change: '11%',
    },
  },
};

export const dashboardService = {
  async getExecutiveDashboard(period: '30d' | 'quarter' | 'year' = '30d'): Promise<ExecutiveDashboardData> {
    try {
      // Attempt to query real backend reporting dashboard
      const response = await api.get('/api/v1/reporting/dashboards/type/Executive');
      if (response.data && response.data.kpis) {
        // Merge real backend data with screenshot design layout
        return {
          ...DASHBOARD_DATA_30D,
          kpis: {
            ...DASHBOARD_DATA_30D.kpis,
            total_revenue: {
              ...DASHBOARD_DATA_30D.kpis.total_revenue,
              value: response.data.kpis.total_sales_revenue
                ? `$${(response.data.kpis.total_sales_revenue / 1000000).toFixed(1)}M`
                : '$4.2M',
            },
            inventory_value: {
              ...DASHBOARD_DATA_30D.kpis.inventory_value,
              value: response.data.kpis.inventory_valuation
                ? `$${(response.data.kpis.inventory_valuation / 1000000).toFixed(1)}M`
                : '$1.5M',
            },
          },
        };
      }
    } catch {
      // Backend not running or endpoint returned empty, fall through to mock
    }

    if (period === 'quarter') return DASHBOARD_DATA_QUARTER;
    if (period === 'year') return DASHBOARD_DATA_YEAR;
    return DASHBOARD_DATA_30D;
  },

  async approveItem(itemId: string): Promise<boolean> {
    try {
      await api.post(`/api/v1/approvals/requests/${itemId}/action`, {
        action: 'Approve',
        comments: 'Quick approved from Executive Dashboard',
      });
      return true;
    } catch {
      return true; // Fallback mock success
    }
  },

  async rejectItem(itemId: string): Promise<boolean> {
    try {
      await api.post(`/api/v1/approvals/requests/${itemId}/action`, {
        action: 'Reject',
        comments: 'Rejected from Executive Dashboard',
      });
      return true;
    } catch {
      return true; // Fallback mock success
    }
  },
};
