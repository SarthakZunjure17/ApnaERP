import { api } from './api';
import {
  CompanyItem,
  ChartOfAccountItem,
  FiscalYearItem,
  FiscalPeriodItem,
  JournalEntryItem,
  GeneralLedgerTransaction,
} from '../types/finance';

export const financeService = {
  // Company
  async getCompany(): Promise<CompanyItem | null> {
    try {
      const response = await api.get('/api/v1/finance/company');
      if (Array.isArray(response.data) && response.data.length > 0) return response.data[0];
      if (response.data && typeof response.data === 'object') return response.data;
      return null;
    } catch {
      return null;
    }
  },

  // Chart of Accounts
  async getChartOfAccounts(): Promise<ChartOfAccountItem[]> {
    const response = await api.get('/api/v1/finance/accounts');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createAccount(data: {
    code: string;
    name: string;
    account_type: string;
    account_group?: string;
    parent_id?: string;
    is_reconciliation?: boolean;
  }): Promise<ChartOfAccountItem> {
    const response = await api.post('/api/v1/finance/accounts', data);
    return response.data;
  },

  async updateAccount(id: string, data: Partial<ChartOfAccountItem>): Promise<ChartOfAccountItem> {
    const response = await api.put(`/api/v1/finance/accounts/${id}`, data);
    return response.data;
  },

  // Fiscal Years & Periods
  async getFiscalYears(): Promise<FiscalYearItem[]> {
    const response = await api.get('/api/v1/finance/fiscal/years');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async getFiscalPeriods(yearId?: string): Promise<FiscalPeriodItem[]> {
    const response = await api.get('/api/v1/finance/fiscal/periods', {
      params: yearId ? { fiscal_year_id: yearId } : {},
    });
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  // Journals
  async getJournals(params?: { status?: string }): Promise<JournalEntryItem[]> {
    const response = await api.get('/api/v1/finance/journals', { params });
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async getJournalById(id: string): Promise<JournalEntryItem | null> {
    const response = await api.get(`/api/v1/finance/journals/${id}`);
    return response.data;
  },

  async createJournal(data: {
    journal_type: string;
    posting_date: string;
    description: string;
    reference_number?: string;
    lines: Array<{
      account_id: string;
      description?: string;
      debit_amount: number;
      credit_amount: number;
    }>;
  }): Promise<JournalEntryItem> {
    const response = await api.post('/api/v1/finance/journals', data);
    return response.data;
  },

  async postJournal(id: string): Promise<JournalEntryItem> {
    const response = await api.post(`/api/v1/finance/journals/${id}/post`);
    return response.data;
  },

  async cancelJournal(id: string): Promise<JournalEntryItem> {
    const response = await api.post(`/api/v1/finance/journals/${id}/cancel`);
    return response.data;
  },

  async reverseJournal(id: string, reason?: string): Promise<JournalEntryItem> {
    const response = await api.post(`/api/v1/finance/journals/${id}/reverse`, {
      reversal_date: new Date().toISOString().split('T')[0],
      reason: reason || 'Manual reversal',
    });
    return response.data;
  },

  // General Ledger
  async getGeneralLedgerTransactions(params?: {
    account_id?: string;
    from_date?: string;
    to_date?: string;
  }): Promise<GeneralLedgerTransaction[]> {
    const response = await api.get('/api/v1/finance/ledger/transactions', { params });
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async getGeneralLedger(params?: {
    account_id?: string;
    start_date?: string;
    end_date?: string;
    from_date?: string;
    to_date?: string;
  }): Promise<GeneralLedgerTransaction[]> {
    return this.getGeneralLedgerTransactions({
      account_id: params?.account_id,
      from_date: params?.from_date || params?.start_date,
      to_date: params?.to_date || params?.end_date,
    });
  },
};
