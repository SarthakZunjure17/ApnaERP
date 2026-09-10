import { api } from './api';
import {
  PayrollRunItem,
  PayslipItem,
  SalaryStructureItem,
  SalaryComponentItem,
  EmployeeCompensationItem,
} from '../types/payroll';

export const payrollService = {
  // Payroll Runs
  async getPayrollRuns(): Promise<PayrollRunItem[]> {
    const response = await api.get('/api/v1/payroll-runs');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createPayrollRun(payload: {
    run_number: string;
    period_start: string;
    period_end: string;
    payment_date: string;
  }): Promise<PayrollRunItem> {
    const response = await api.post('/api/v1/payroll-runs', payload);
    return response.data;
  },

  async executePayrollRun(id: string): Promise<PayrollRunItem> {
    const response = await api.post(`/api/v1/payroll-runs/${id}/execute`);
    return response.data;
  },

  async approvePayrollRun(id: string): Promise<PayrollRunItem> {
    const response = await api.post(`/api/v1/payroll-runs/${id}/approve`);
    return response.data;
  },

  // Payslips
  async getPayslips(params?: { payroll_run_id?: string; employee_id?: string }): Promise<PayslipItem[]> {
    const response = await api.get('/api/v1/payslips', { params });
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  // Salary Structures & Components
  async getSalaryStructures(): Promise<SalaryStructureItem[]> {
    const response = await api.get('/api/v1/salary-structures');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async getSalaryComponents(): Promise<SalaryComponentItem[]> {
    const response = await api.get('/api/v1/salary-components');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async getEmployeeCompensation(employeeId: string): Promise<EmployeeCompensationItem | null> {
    try {
      const response = await api.get(`/api/v1/employee-compensation/employee/${employeeId}`);
      return response.data;
    } catch {
      return null;
    }
  },
};
