export interface ProfitLossReportData {
  from_date?: string;
  to_date?: string;
  total_revenue: number;
  total_expenses: number;
  total_expense?: number;
  net_profit: number;
  net_income?: number;
  revenue_lines?: Array<{
    account_id: string;
    account_code: string;
    account_name: string;
    account_group_name?: string;
    amount: number;
  }>;
  expense_lines?: Array<{
    account_id: string;
    account_code: string;
    account_name: string;
    account_group_name?: string;
    amount: number;
  }>;
}

export type ProfitAndLossReport = ProfitLossReportData;

export interface BalanceSheetReportData {
  as_of_date: string;
  total_assets: number;
  total_liabilities: number;
  total_equity: number;
  total_liabilities_and_equity?: number;
  is_balanced?: boolean;
  asset_lines?: Array<{
    account_id: string;
    account_code: string;
    account_name: string;
    balance: number;
  }>;
  liability_lines?: Array<{
    account_id: string;
    account_code: string;
    account_name: string;
    balance: number;
  }>;
  equity_lines?: Array<{
    account_id: string;
    account_code: string;
    account_name: string;
    balance: number;
  }>;
}

export type BalanceSheetReport = BalanceSheetReportData;

export interface TrialBalanceItem {
  account_id: string;
  account_code: string;
  account_name: string;
  account_type: string;
  opening_balance?: number;
  period_debit?: number;
  period_credit?: number;
  debit_balance: number;
  credit_balance: number;
}

export interface TrialBalanceReportData {
  as_of_date: string;
  total_debit: number;
  total_credit: number;
  is_balanced: boolean;
  accounts_count?: number;
  lines?: TrialBalanceItem[];
  items?: TrialBalanceItem[];
}

export type TrialBalanceReport = TrialBalanceReportData;

export interface SalesReportSummaryData {
  from_date?: string;
  to_date?: string;
  total_orders: number;
  total_revenue?: number;
  total_sales_amount?: number;
  average_order_value: number;
  status_breakdown?: Record<string, number>;
}

export interface ProcurementReportSummaryData {
  from_date?: string;
  to_date?: string;
  total_pos?: number;
  total_po_count?: number;
  total_spend?: number;
  total_spend_amount?: number;
  average_po_value?: number;
  active_suppliers_count?: number;
  status_breakdown?: Record<string, number>;
}

export interface InventoryStockReportData {
  total_warehouses?: number;
  total_products?: number;
  total_quantity?: number;
  total_units_on_hand?: number;
  total_valuation: number;
  warehouse_breakdown?: any[];
  items?: Array<{
    product_sku: string;
    product_name: string;
    quantity_on_hand: number;
    valuation: number;
  }>;
}

export interface HeadcountReportData {
  as_of_date: string;
  total_employees?: number;
  total_headcount?: number;
  active_employees?: number;
  inactive_employees?: number;
  by_employment_type?: Record<string, number>;
  by_department?: Record<string, number>;
  department_breakdown?: any[];
}

export interface PayrollReportSummaryData {
  from_date?: string;
  to_date?: string;
  total_payroll_runs?: number;
  total_gross_pay?: number;
  total_deductions?: number;
  total_statutory_deductions?: number;
  total_net_disbursed?: number;
  total_net_payroll?: number;
  employees_processed?: number;
}
