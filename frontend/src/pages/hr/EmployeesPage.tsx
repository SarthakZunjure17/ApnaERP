import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Users,
  Search,
  Plus,
  Mail,
  Phone,
  Building,
  ChevronRight,
  Trash2,
  CalendarCheck,
} from 'lucide-react';
import { hrService } from '../../services/hrService';
import { EmployeeListItem, DepartmentItem, EmployeeCreatePayload } from '../../types/hr';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Pagination } from '../../components/common/Pagination';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { useToast } from '../../context/ToastContext';

export const EmployeesPage: React.FC = () => {
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [departments, setDepartments] = useState<DepartmentItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDeptId, setSelectedDeptId] = useState('All');
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [isAddEmployeeModalOpen, setIsAddEmployeeModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const pageSize = 10;

  // New employee form state
  const [newEmployee, setNewEmployee] = useState<Partial<EmployeeCreatePayload>>({
    employee_code: `EMP-${Math.floor(1000 + Math.random() * 9000)}`,
    first_name: '',
    last_name: '',
    work_email: '',
    work_phone: '',
    department_id: '',
    joining_date: new Date().toISOString().split('T')[0],
    employment_type: 'Full Time',
    employment_status: 'Active',
  });

  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [empRes, deptRes] = await Promise.all([
        hrService.getEmployees({
          search: searchQuery,
          department_id: selectedDeptId !== 'All' ? selectedDeptId : undefined,
        }),
        hrService.getDepartments(),
      ]);
      setEmployees(empRes.items);
      setDepartments(deptRes);
      if (deptRes.length > 0 && !newEmployee.department_id) {
        setNewEmployee((prev) => ({ ...prev, department_id: deptRes[0].id }));
      }
    } catch (err: any) {
      toastError('Load Error', err.message || 'Failed to fetch employee records.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    setCurrentPage(1);
    loadData();
  }, [searchQuery, selectedDeptId]);

  const handleAddEmployee = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmployee.first_name || !newEmployee.last_name || !newEmployee.work_email || !newEmployee.department_id) {
      toastError('Validation', 'Please fill in all required fields.');
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await hrService.createEmployee({
        employee_code: newEmployee.employee_code || `EMP-${Date.now().toString().slice(-4)}`,
        first_name: newEmployee.first_name!,
        last_name: newEmployee.last_name!,
        work_email: newEmployee.work_email!,
        work_phone: newEmployee.work_phone || '+91 98765 00000',
        department_id: newEmployee.department_id!,
        joining_date: newEmployee.joining_date || new Date().toISOString().split('T')[0],
        employment_type: newEmployee.employment_type || 'Full Time',
        employment_status: newEmployee.employment_status || 'Active',
      });

      success('Employee Created', `${created.first_name} ${created.last_name} has been enrolled.`);
      setIsAddEmployeeModalOpen(false);
      loadData();
      navigate(`/workforce/employees/${created.id}`);
    } catch (err: any) {
      toastError('Creation Failed', err.message || 'Failed to create employee.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteEmployee = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to deactivate ${name}?`)) return;
    try {
      await hrService.deleteEmployee(id);
      success('Deactivated', `${name} deactivated.`);
      loadData();
    } catch (err: any) {
      toastError('Error', err.message || 'Failed to deactivate employee.');
    }
  };

  const totalPages = Math.max(1, Math.ceil(employees.length / pageSize));
  const paginatedEmployees = employees.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  return (
    <div className="space-y-4 sm:space-y-5 animate-fade-in pb-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Employees Directory
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Manage organization workforce, profiles, departments and roles.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/workforce/attendance"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700 hover:bg-slate-50 text-slate-700 dark:text-slate-200 rounded-lg text-xs font-semibold shadow-xs transition-colors"
          >
            <CalendarCheck className="w-3.5 h-3.5 text-slate-500" />
            Attendance
          </Link>
          <button
            onClick={() => setIsAddEmployeeModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Employee
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-3 shadow-xs flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by name, email, code..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs focus:ring-2 focus:ring-brand-500 outline-none text-slate-800 dark:text-slate-200"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={selectedDeptId}
            onChange={(e) => setSelectedDeptId(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-200 outline-none"
          >
            <option value="All">All Departments</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Employees Table */}
      {isLoading ? (
        <LoadingState message="Loading workforce directory..." />
      ) : employees.length === 0 ? (
        <EmptyState
          title="No employees found"
          description="Get started by adding employees to your organization."
          actionText="Add Employee"
          onAction={() => setIsAddEmployeeModalOpen(true)}
        />
      ) : (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200/70 dark:border-slate-800 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Employee</th>
                  <th className="px-4 py-3">Code</th>
                  <th className="px-4 py-3">Department</th>
                  <th className="px-4 py-3">Contact</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {paginatedEmployees.map((emp) => {
                  const dept = departments.find((d) => d.id === emp.department_id);
                  const fullName = emp.full_name || `${emp.first_name} ${emp.last_name}`;
                  return (
                    <tr key={emp.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="px-4 py-3">
                        <Link
                          to={`/workforce/employees/${emp.id}`}
                          className="font-semibold text-slate-900 dark:text-white hover:text-brand-600 dark:hover:text-brand-400 block"
                        >
                          {fullName}
                        </Link>
                        <span className="text-[11px] text-slate-400">{emp.position_title || 'Staff Member'}</span>
                      </td>
                      <td className="px-4 py-3 font-mono font-medium text-slate-600 dark:text-slate-300">
                        {emp.employee_code}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                        {emp.department_name || dept?.name || 'General'}
                      </td>
                      <td className="px-4 py-3 space-y-0.5">
                        <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
                          <Mail className="w-3 h-3 text-slate-400" />
                          <span>{emp.work_email}</span>
                        </div>
                        {emp.work_phone && (
                          <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
                            <Phone className="w-3 h-3" />
                            <span>{emp.work_phone}</span>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                        {emp.employment_type || 'Full Time'}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={emp.is_active ? 'Active' : 'Inactive'} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Link
                            to={`/workforce/employees/${emp.id}`}
                            className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-slate-100 dark:hover:bg-slate-800 rounded transition-colors"
                            title="View Profile"
                          >
                            <ChevronRight className="w-4 h-4" />
                          </Link>
                          <button
                            onClick={() => handleDeleteEmployee(emp.id, fullName)}
                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded transition-colors cursor-pointer"
                            title="Deactivate"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="p-3 border-t border-slate-100 dark:border-slate-800">
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={setCurrentPage}
              totalItems={employees.length}
              pageSize={pageSize}
            />
          </div>
        </div>
      )}

      {/* Add Employee Modal */}
      <Modal
        isOpen={isAddEmployeeModalOpen}
        onClose={() => setIsAddEmployeeModalOpen(false)}
        title="Add New Employee"
      >
        <form onSubmit={handleAddEmployee} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                First Name *
              </label>
              <input
                type="text"
                required
                value={newEmployee.first_name || ''}
                onChange={(e) => setNewEmployee({ ...newEmployee, first_name: e.target.value })}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-800 dark:text-slate-200"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Last Name *
              </label>
              <input
                type="text"
                required
                value={newEmployee.last_name || ''}
                onChange={(e) => setNewEmployee({ ...newEmployee, last_name: e.target.value })}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-800 dark:text-slate-200"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Work Email *
              </label>
              <input
                type="email"
                required
                value={newEmployee.work_email || ''}
                onChange={(e) => setNewEmployee({ ...newEmployee, work_email: e.target.value })}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-800 dark:text-slate-200"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Work Phone
              </label>
              <input
                type="text"
                value={newEmployee.work_phone || ''}
                onChange={(e) => setNewEmployee({ ...newEmployee, work_phone: e.target.value })}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-800 dark:text-slate-200"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Department *
              </label>
              <select
                required
                value={newEmployee.department_id || ''}
                onChange={(e) => setNewEmployee({ ...newEmployee, department_id: e.target.value })}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-800 dark:text-slate-200"
              >
                <option value="" disabled>Select Department</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.code})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Employment Type
              </label>
              <select
                value={newEmployee.employment_type || 'Full Time'}
                onChange={(e) => setNewEmployee({ ...newEmployee, employment_type: e.target.value })}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-800 dark:text-slate-200"
              >
                <option value="Full Time">Full Time</option>
                <option value="Part Time">Part Time</option>
                <option value="Contract">Contract</option>
                <option value="Intern">Intern</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsAddEmployeeModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
            >
              Save Employee
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
