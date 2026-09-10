export interface DepartmentItem {
  id: string;
  name: string;
  code: string;
  description?: string;
  manager_id?: string;
  parent_department_id?: string;
  is_active: boolean;
}

export interface EmployeeListItem {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string;
  full_name: string;
  work_email: string;
  personal_email?: string;
  work_phone?: string;
  personal_phone?: string;
  department_id: string;
  department_name?: string;
  position_id?: string;
  position_title?: string;
  manager_id?: string;
  employment_type: string;
  employment_status: string;
  joining_date: string;
  is_active: boolean;
}

export interface EmployeeCreatePayload {
  employee_code: string;
  first_name: string;
  last_name: string;
  work_email: string;
  department_id: string;
  position_id?: string;
  joining_date: string;
  employment_type?: string;
  employment_status?: string;
  work_phone?: string;
  personal_phone?: string;
  date_of_birth?: string;
  gender?: string;
}

export interface EmployeeDocumentItem {
  id: string;
  employee_id: string;
  document_name: string;
  document_type: string;
  file_id: string;
  file_name?: string;
  file_size?: number;
  uploaded_at: string;
  is_verified: boolean;
}

export interface AttendanceRecord {
  id: string;
  employee_id: string;
  employee_name?: string;
  employee_code?: string;
  date: string;
  check_in?: string;
  check_out?: string;
  status: 'Present' | 'Absent' | 'Half Day' | 'Late' | 'On Leave';
  total_hours?: number;
  notes?: string;
}

export interface LeaveTypeItem {
  id: string;
  name: string;
  code: string;
  days_allowed: number;
  is_paid: boolean;
  is_active: boolean;
}

export interface LeaveRequestItem {
  id: string;
  employee_id: string;
  employee_name?: string;
  leave_type_id: string;
  leave_type_name?: string;
  start_date: string;
  end_date: string;
  total_days: number;
  reason: string;
  status: 'Pending' | 'Approved' | 'Rejected' | 'Cancelled';
  applied_at: string;
  approver_id?: string;
  approver_comments?: string;
}

export interface ShiftItem {
  id: string;
  name: string;
  code: string;
  start_time: string;
  end_time: string;
  is_night_shift?: boolean;
}
