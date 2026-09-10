export interface SalaryComponentItem {
  id: string;
  name: string;
  code: string;
  component_type: 'Earning' | 'Deduction';
  calculation_type: 'Flat' | 'Percentage of Basic';
  is_statutory: boolean;
  is_active: boolean;
}

export interface SalaryStructureItem {
  id: string;
  name: string;
  code: string;
  description?: string;
  is_active: boolean;
}

export interface EmployeeCompensationItem {
  id: string;
  employee_id: string;
  employee_name?: string;
  salary_structure_id: string;
  salary_structure_name?: string;
  base_salary: number;
  gross_salary: number;
  effective_from: string;
}

export interface PayrollRunItem {
  id: string;
  run_number: string;
  period_start: string;
  period_end: string;
  payment_date: string;
  status: 'Draft' | 'Processing' | 'Completed' | 'Approved' | 'Cancelled';
  total_gross_pay: number;
  total_deductions: number;
  total_net_pay: number;
  total_employees_processed: number;
  created_at: string;
}

export interface PayslipItem {
  id: string;
  payslip_number: string;
  payroll_run_id: string;
  employee_id: string;
  employee_name: string;
  employee_code: string;
  department_name?: string;
  designation?: string;
  period_start: string;
  period_end: string;
  gross_pay: number;
  total_deductions: number;
  net_pay: number;
  payment_status: 'Unpaid' | 'Paid' | 'Processing';
  generated_at: string;
}
