import { api } from './api';
import {
  ProfitLossReportData,
  BalanceSheetReportData,
  TrialBalanceReportData,
  SalesReportSummaryData,
  ProcurementReportSummaryData,
  InventoryStockReportData,
  HeadcountReportData,
  PayrollReportSummaryData,
} from '../types/reporting';

export const reportingService = {
  // Finance Reports
  async getProfitLoss(
    fromDateOrOptions?: string | { from_date?: string; to_date?: string; start_date?: string; end_date?: string },
    toDate?: string
  ): Promise<ProfitLossReportData> {
    const params: Record<string, string> = {};
    if (typeof fromDateOrOptions === 'object') {
      if (fromDateOrOptions.from_date || fromDateOrOptions.start_date) {
        params.from_date = (fromDateOrOptions.from_date || fromDateOrOptions.start_date)!;
      }
      if (fromDateOrOptions.to_date || fromDateOrOptions.end_date) {
        params.to_date = (fromDateOrOptions.to_date || fromDateOrOptions.end_date)!;
      }
    } else {
      if (fromDateOrOptions) params.from_date = fromDateOrOptions;
      if (toDate) params.to_date = toDate;
    }
    const response = await api.get('/api/v1/reports/finance/profit-loss', { params });
    return response.data;
  },

  async getBalanceSheet(asOfDateOrOptions?: string | { as_of_date?: string; to_date?: string }): Promise<BalanceSheetReportData> {
    const params: Record<string, string> = {};
    if (typeof asOfDateOrOptions === 'object') {
      if (asOfDateOrOptions.as_of_date || asOfDateOrOptions.to_date) {
        params.as_of_date = (asOfDateOrOptions.as_of_date || asOfDateOrOptions.to_date)!;
      }
    } else if (asOfDateOrOptions) {
      params.as_of_date = asOfDateOrOptions;
    }
    const response = await api.get('/api/v1/reports/finance/balance-sheet', { params });
    return response.data;
  },

  async getTrialBalance(asOfDateOrOptions?: string | { as_of_date?: string; to_date?: string; start_date?: string; end_date?: string }): Promise<TrialBalanceReportData> {
    const params: Record<string, string> = {};
    if (typeof asOfDateOrOptions === 'object') {
      if (asOfDateOrOptions.as_of_date || asOfDateOrOptions.end_date || asOfDateOrOptions.to_date) {
        params.as_of_date = (asOfDateOrOptions.as_of_date || asOfDateOrOptions.end_date || asOfDateOrOptions.to_date)!;
      }
    } else if (asOfDateOrOptions) {
      params.as_of_date = asOfDateOrOptions;
    }
    const response = await api.get('/api/v1/reports/finance/trial-balance', { params });
    return response.data;
  },

  // Sales Reports
  async getSalesSummary(fromDate?: string, toDate?: string): Promise<SalesReportSummaryData> {
    const params: Record<string, string> = {};
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    const response = await api.get('/api/v1/reports/sales/summary', { params });
    return response.data;
  },

  // Procurement Reports
  async getProcurementSummary(fromDate?: string, toDate?: string): Promise<ProcurementReportSummaryData> {
    const params: Record<string, string> = {};
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    const response = await api.get('/api/v1/reports/procurement/summary', { params });
    return response.data;
  },

  // Inventory Reports
  async getStockByWarehouse(): Promise<InventoryStockReportData> {
    const response = await api.get('/api/v1/reports/inventory/stock-by-warehouse');
    return response.data;
  },

  async getLowStockSummary(): Promise<any> {
    const response = await api.get('/api/v1/reports/inventory/low-stock');
    return response.data;
  },

  // HR & Payroll Reports
  async getHeadcountReport(asOfDate?: string): Promise<HeadcountReportData> {
    const params: Record<string, string> = {};
    if (asOfDate) params.as_of_date = asOfDate;
    const response = await api.get('/api/v1/reports/hr/headcount', { params });
    return response.data;
  },

  async getPayrollSummary(fromDate?: string, toDate?: string): Promise<PayrollReportSummaryData> {
    const params: Record<string, string> = {};
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    const response = await api.get('/api/v1/reports/payroll/summary', { params });
    return response.data;
  },

  // CRM Reports
  async getCrmLeadsSummary(fromDate?: string, toDate?: string): Promise<any> {
    const params: Record<string, string> = {};
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    const response = await api.get('/api/v1/reports/crm/leads', { params });
    return response.data;
  },

  async getCrmPipelineReport(fromDate?: string, toDate?: string): Promise<any> {
    const params: Record<string, string> = {};
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    const response = await api.get('/api/v1/reports/crm/pipeline', { params });
    return response.data;
  },

  // Export CSV
  async downloadReportCsv(reportType: string, fromDate?: string, toDate?: string, asOfDate?: string): Promise<void> {
    const params: Record<string, string> = { report_type: reportType };
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    if (asOfDate) params.as_of_date = asOfDate;

    const response = await api.get('/api/v1/reports/export', {
      params,
      responseType: 'blob',
    });

    const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${reportType}_report_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};
