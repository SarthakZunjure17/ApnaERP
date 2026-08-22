import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  Search,
  Filter,
  Plus,
  Mail,
  Phone,
  MapPin,
  ChevronRight,
  UserCheck,
  Building,
} from 'lucide-react';
import { hrService } from '../../services/hrService';
import { EmployeeListItem } from '../../types/hr';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Pagination } from '../../components/common/Pagination';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { useToast } from '../../context/ToastContext';

export const EmployeesPage: React.FC = () => {
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDept, setSelectedDept] = useState('All');
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [isAddEmployeeModalOpen, setIsAddEmployeeModalOpen] = useState(false);

  // New employee form
  const [newEmployee, setNewEmployee] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    department: 'Engineering',
    designation: 'Software Engineer',
    location: 'Mumbai, India',
  });

  const navigate = useNavigate();
  const { success } = useToast();

  useEffect(() => {
    loadEmployees();
  }, [searchQuery, selectedDept]);

  const loadEmployees = async () => {
    setIsLoading(true);
    const data = await hrService.getEmployees(searchQuery, selectedDept);
    setEmployees(data);
    setIsLoading(false);
  };

  const handleAddEmployee = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmployee.first_name || !newEmployee.email) return;

    const created: EmployeeListItem = {
      id: `emp-${Date.now()}`,
      employee_code: `EMP-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`,
      full_name: `${newEmployee.first_name} ${newEmployee.last_name}`,
      email: newEmployee.email,
      phone: newEmployee.phone || '+91 98765 00000',
      department: newEmployee.department,
      designation: newEmployee.designation,
      status: 'Active',
      join_date: 'Today',
      location: newEmployee.location,
    };

    setEmployees([created, ...employees]);
    setIsAddEmployeeModalOpen(false);
    success('Employee Created', `${created.full_name} has been added to workforce.`);
    navigate(`/workforce/employees/${created.id}`);
  };

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

        <button
          onClick={() => setIsAddEmployeeModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          Add Employee
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800 rounded-xl p-3.5 shadow-xs flex flex-col sm:flex-row items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 w-full">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by name, ID or email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-100/70 dark:bg-slate-800/80 border border-slate-200/60 dark:border-slate-700/60 rounded-lg text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-brand-500"
          />
        </div>

        {/* Department Filter */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={selectedDept}
            onChange={(e) => setSelectedDept(e.target.value)}
            className="px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs text-slate-700 dark:text-slate-200 focus:outline-none focus:border-brand-500 w-full sm:w-44"
          >
            <option value="All">All Departments</option>
            <option value="Engineering">Engineering</option>
            <option value="Product">Product</option>
            <option value="Finance">Finance</option>
            <option value="Operations">Operations</option>
          </select>
        </div>
      </div>

      {/* Employees Table */}
      {isLoading ? (
        <LoadingState message="Fetching employees list..." />
      ) : (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                  <th className="py-2 px-3">Employee</th>
                  <th className="py-2 px-3">Department</th>
                  <th className="py-2 px-3">Contact</th>
                  <th className="py-2 px-3">Location</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100/80 dark:divide-slate-800/60 text-xs">
                {employees.map((emp) => (
                  <tr
                    key={emp.id}
                    onClick={() => navigate(`/workforce/employees/${emp.id}`)}
                    className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors group cursor-pointer"
                  >
                    {/* Employee info */}
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950 flex items-center justify-center text-blue-700 dark:text-blue-300 font-bold text-xs shrink-0">
                          {emp.full_name
                            .split(' ')
                            .map((n) => n[0])
                            .join('')}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-900 dark:text-white group-hover:text-brand-600 transition-colors">
                            {emp.full_name}
                          </p>
                          <span className="text-[11px] text-slate-400 font-mono">
                            {emp.employee_code}
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Department & Designation */}
                    <td className="py-3 px-3">
                      <p className="font-medium text-slate-800 dark:text-slate-200">{emp.designation}</p>
                      <span className="text-[11px] text-slate-400">{emp.department}</span>
                    </td>

                    {/* Contact */}
                    <td className="py-3 px-3 text-slate-600 dark:text-slate-300">
                      <p className="text-xs">{emp.email}</p>
                      <span className="text-[11px] text-slate-400">{emp.phone}</span>
                    </td>

                    {/* Location */}
                    <td className="py-3 px-3 text-slate-500 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1 text-[11px]">
                        <MapPin className="w-3 h-3 text-slate-400" />
                        {emp.location}
                      </span>
                    </td>

                    {/* Status Badge */}
                    <td className="py-3 px-3 whitespace-nowrap">
                      <StatusBadge status={emp.status} />
                    </td>

                    {/* Action */}
                    <td className="py-3 px-3 text-right whitespace-nowrap">
                      <span className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-brand-600 group-hover:text-brand-700">
                        View Profile
                        <ChevronRight className="w-3.5 h-3.5" />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Pagination
            currentPage={currentPage}
            totalPages={3}
            totalEntries={employees.length}
            pageSize={10}
            onPageChange={(p) => setCurrentPage(p)}
          />
        </div>
      )}

      {/* Add Employee Modal */}
      <Modal
        isOpen={isAddEmployeeModalOpen}
        onClose={() => setIsAddEmployeeModalOpen(false)}
        title="Add New Employee"
      >
        <form onSubmit={handleAddEmployee} className="space-y-3.5 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                First Name
              </label>
              <input
                type="text"
                required
                value={newEmployee.first_name}
                onChange={(e) => setNewEmployee({ ...newEmployee, first_name: e.target.value })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Last Name
              </label>
              <input
                type="text"
                required
                value={newEmployee.last_name}
                onChange={(e) => setNewEmployee({ ...newEmployee, last_name: e.target.value })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
              Email Address
            </label>
            <input
              type="email"
              required
              value={newEmployee.email}
              onChange={(e) => setNewEmployee({ ...newEmployee, email: e.target.value })}
              className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Department
              </label>
              <select
                value={newEmployee.department}
                onChange={(e) => setNewEmployee({ ...newEmployee, department: e.target.value })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
              >
                <option value="Engineering">Engineering</option>
                <option value="Product">Product</option>
                <option value="Finance">Finance</option>
                <option value="Operations">Operations</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Designation
              </label>
              <input
                type="text"
                value={newEmployee.designation}
                onChange={(e) => setNewEmployee({ ...newEmployee, designation: e.target.value })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button variant="outline" size="sm" type="button" onClick={() => setIsAddEmployeeModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Create Employee
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
