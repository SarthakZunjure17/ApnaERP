export interface CompanyItem {
  id: string;
  name: string;
  code: string;
  legal_name?: string;
  tax_identifier?: string;
  currency_code: string;
  fiscal_year_start_month: number;
}

export interface ChartOfAccountItem {
  id: string;
  code: string;
  name: string;
  account_type: 'Asset' | 'Liability' | 'Equity' | 'Revenue' | 'Expense';
  account_group?: string;
  parent_id?: string;
  parent_account_id?: string;
  is_reconciliation: boolean;
  is_active: boolean;
  current_balance?: number;
  children?: ChartOfAccountItem[];
}

export interface FiscalYearItem {
  id: string;
  year_name: string;
  start_date: string;
  end_date: string;
  is_closed: boolean;
}

export interface FiscalPeriodItem {
  id: string;
  fiscal_year_id: string;
  period_number: number;
  period_name: string;
  start_date: string;
  end_date: string;
  is_locked: boolean;
  is_closed: boolean;
}

export interface JournalLineItem {
  id?: string;
  account_id: string;
  account_code?: string;
  account_name?: string;
  description?: string;
  debit_amount: number;
  credit_amount: number;
}

export interface JournalEntryItem {
  id: string;
  entry_number: string;
  journal_type: string;
  posting_date: string;
  description: string;
  reference_number?: string;
  status: 'Draft' | 'Posted' | 'Reversed' | 'Cancelled';
  total_debit: number;
  total_credit: number;
  lines: JournalLineItem[];
  created_at: string;
}

export interface GeneralLedgerTransaction {
  id: string;
  posting_date: string;
  entry_number: string;
  account_code: string;
  account_name: string;
  description?: string;
  debit: number;
  credit: number;
  running_balance: number;
}
