import { api } from './api';
import {
  DepartmentItem,
  EmployeeListItem,
  EmployeeCreatePayload,
  EmployeeDocumentItem,
  AttendanceRecord,
  LeaveTypeItem,
  LeaveRequestItem,
  ShiftItem,
} from '../types/hr';

export const hrService = {
  // Departments
  async getDepartments(): Promise<DepartmentItem[]> {
    const response = await api.get('/api/v1/departments');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createDepartment(data: { name: string; code: string; description?: string }): Promise<DepartmentItem> {
    const response = await api.post('/api/v1/departments', data);
    return response.data;
  },

  // Employees
  async getEmployees(params?: { search?: string; department_id?: string; skip?: number; limit?: number }): Promise<{ items: EmployeeListItem[]; total: number }> {
    const queryParams: Record<string, any> = {
      skip: params?.skip ?? 0,
      limit: params?.limit ?? 100,
    };
    if (params?.search) queryParams.search = params.search;
    if (params?.department_id && params.department_id !== 'All') queryParams.department_id = params.department_id;

    const response = await api.get('/api/v1/employees', { params: queryParams });
    if (response.data && Array.isArray(response.data.items)) {
      return { items: response.data.items, total: response.data.total ?? response.data.items.length };
    }
    if (Array.isArray(response.data)) {
      return { items: response.data, total: response.data.length };
    }
    return { items: [], total: 0 };
  },

  async getEmployeeById(id: string): Promise<EmployeeListItem | null> {
    const response = await api.get(`/api/v1/employees/${id}`);
    return response.data;
  },

  async createEmployee(payload: EmployeeCreatePayload): Promise<EmployeeListItem> {
    const response = await api.post('/api/v1/employees', payload);
    return response.data;
  },

  async updateEmployee(id: string, payload: Partial<EmployeeCreatePayload>): Promise<EmployeeListItem> {
    const response = await api.put(`/api/v1/employees/${id}`, payload);
    return response.data;
  },

  async deleteEmployee(id: string): Promise<boolean> {
    await api.delete(`/api/v1/employees/${id}`);
    return true;
  },

  // Employee Documents
  async getEmployeeDocuments(employeeId: string): Promise<EmployeeDocumentItem[]> {
    const response = await api.get(`/api/v1/employee-documents/employee/${employeeId}`);
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  // Attendance
  async getAttendanceRecords(params?: { employee_id?: string; from_date?: string; to_date?: string }): Promise<AttendanceRecord[]> {
    const response = await api.get('/api/v1/attendance', { params });
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async checkIn(employeeId: string, notes?: string): Promise<AttendanceRecord> {
    const response = await api.post('/api/v1/attendance/check-in', {
      employee_id: employeeId,
      notes,
    });
    return response.data;
  },

  async checkOut(attendanceId: string, notes?: string): Promise<AttendanceRecord> {
    const response = await api.post('/api/v1/attendance/check-out', {
      attendance_id: attendanceId,
      notes,
    });
    return response.data;
  },

  // Shifts
  async getShifts(): Promise<ShiftItem[]> {
    const response = await api.get('/api/v1/shifts');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  // Leave Management
  async getLeaveTypes(): Promise<LeaveTypeItem[]> {
    const response = await api.get('/api/v1/leave-types');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async getLeaveRequests(params?: { employee_id?: string; status?: string }): Promise<LeaveRequestItem[]> {
    const response = await api.get('/api/v1/leave-requests', { params });
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createLeaveRequest(payload: {
    employee_id: string;
    leave_type_id: string;
    start_date: string;
    end_date: string;
    reason: string;
  }): Promise<LeaveRequestItem> {
    const response = await api.post('/api/v1/leave-requests', payload);
    return response.data;
  },

  async approveLeaveRequest(id: string, comments?: string): Promise<LeaveRequestItem> {
    const response = await api.post(`/api/v1/leave-requests/${id}/approve`, { comments });
    return response.data;
  },

  async rejectLeaveRequest(id: string, comments?: string): Promise<LeaveRequestItem> {
    const response = await api.post(`/api/v1/leave-requests/${id}/reject`, { comments });
    return response.data;
  },
};
