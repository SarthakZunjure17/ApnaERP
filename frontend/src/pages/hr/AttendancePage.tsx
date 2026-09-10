import React, { useState, useEffect } from 'react';
import {
  CalendarCheck,
  CheckCircle2,
  Clock,
  Plus,
  Search,
  Filter,
  Users,
  Calendar,
  XCircle,
  Check,
  AlertCircle,
} from 'lucide-react';
import { hrService } from '../../services/hrService';
import { AttendanceRecord, LeaveRequestItem, LeaveTypeItem, ShiftItem, EmployeeListItem } from '../../types/hr';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { useToast } from '../../context/ToastContext';

export const AttendancePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'attendance' | 'leaves' | 'shifts'>('attendance');
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([]);
  const [leaves, setLeaves] = useState<LeaveRequestItem[]>([]);
  const [leaveTypes, setLeaveTypes] = useState<LeaveTypeItem[]>([]);
  const [shifts, setShifts] = useState<ShiftItem[]>([]);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Check in modal
  const [isCheckInModalOpen, setIsCheckInModalOpen] = useState(false);
  const [selectedEmpId, setSelectedEmpId] = useState('');
  const [checkInNotes, setCheckInNotes] = useState('');

  // Leave modal
  const [isLeaveModalOpen, setIsLeaveModalOpen] = useState(false);
  const [leaveForm, setLeaveForm] = useState({
    employee_id: '',
    leave_type_id: '',
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0],
    reason: '',
  });

  const { success, error: toastError } = useToast();

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [attRes, leaveRes, typeRes, shiftRes, empRes] = await Promise.all([
        hrService.getAttendanceRecords(),
        hrService.getLeaveRequests(),
        hrService.getLeaveTypes(),
        hrService.getShifts(),
        hrService.getEmployees(),
      ]);
      setAttendance(attRes);
      setLeaves(leaveRes);
      setLeaveTypes(typeRes);
      setShifts(shiftRes);
      setEmployees(empRes.items);
      if (empRes.items.length > 0 && !selectedEmpId) {
        setSelectedEmpId(empRes.items[0].id);
        setLeaveForm((prev) => ({
          ...prev,
          employee_id: empRes.items[0].id,
          leave_type_id: typeRes[0]?.id || '',
        }));
      }
    } catch (err: any) {
      toastError('Load Error', err.message || 'Failed to load attendance & leave records.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCheckInSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEmpId) return;
    try {
      await hrService.checkIn(selectedEmpId, checkInNotes);
      success('Checked In', 'Attendance punch recorded successfully.');
      setIsCheckInModalOpen(false);
      loadData();
    } catch (err: any) {
      toastError('Check-in Failed', err.message || 'Failed to record check-in.');
    }
  };

  const handleLeaveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!leaveForm.employee_id || !leaveForm.leave_type_id || !leaveForm.reason) {
      toastError('Validation', 'Please fill in all required leave fields.');
      return;
    }
    try {
      await hrService.createLeaveRequest(leaveForm);
      success('Leave Submitted', 'Leave application recorded.');
      setIsLeaveModalOpen(false);
      loadData();
    } catch (err: any) {
      toastError('Leave Submission Failed', err.message || 'Failed to submit leave.');
    }
  };

  const handleApproveLeave = async (id: string) => {
    try {
      await hrService.approveLeaveRequest(id, 'Approved by Manager');
      success('Approved', 'Leave request has been approved.');
      loadData();
    } catch (err: any) {
      toastError('Error', err.message || 'Failed to approve leave.');
    }
  };

  const handleRejectLeave = async (id: string) => {
    try {
      await hrService.rejectLeaveRequest(id, 'Rejected');
      success('Rejected', 'Leave request has been rejected.');
      loadData();
    } catch (err: any) {
      toastError('Error', err.message || 'Failed to reject leave.');
    }
  };

  return (
    <div className="space-y-5 animate-fade-in pb-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Attendance & Leaves
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Shift tracking, employee check-ins, and leave management workflows.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsCheckInModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <Clock className="w-3.5 h-3.5" />
            Check In Employee
          </button>
          <button
            onClick={() => setIsLeaveModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            Apply Leave
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 overflow-x-auto pb-1 border-b border-slate-200/80 dark:border-slate-800 text-xs">
        <button
          onClick={() => setActiveTab('attendance')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg font-semibold transition-all cursor-pointer ${
            activeTab === 'attendance'
              ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-blue-300 shadow-2xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <CalendarCheck className="w-3.5 h-3.5" />
          Attendance Records ({attendance.length})
        </button>

        <button
          onClick={() => setActiveTab('leaves')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg font-semibold transition-all cursor-pointer ${
            activeTab === 'leaves'
              ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-blue-300 shadow-2xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Calendar className="w-3.5 h-3.5" />
          Leave Requests ({leaves.length})
        </button>

        <button
          onClick={() => setActiveTab('shifts')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg font-semibold transition-all cursor-pointer ${
            activeTab === 'shifts'
              ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-blue-300 shadow-2xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          Work Shifts ({shifts.length})
        </button>
      </div>

      {isLoading ? (
        <LoadingState message="Loading records..." />
      ) : activeTab === 'attendance' ? (
        /* Attendance Tab */
        attendance.length === 0 ? (
          <EmptyState
            title="No attendance records logged"
            description="Punch check-ins to start recording attendance."
            actionText="Check In Employee"
            onAction={() => setIsCheckInModalOpen(true)}
          />
        ) : (
          <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800 text-[10px] font-bold text-slate-400 uppercase">
                  <tr>
                    <th className="px-4 py-3">Employee</th>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Check In</th>
                    <th className="px-4 py-3">Check Out</th>
                    <th className="px-4 py-3">Hours</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {attendance.map((rec) => {
                    const emp = employees.find((e) => e.id === rec.employee_id);
                    return (
                      <tr key={rec.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/50">
                        <td className="px-4 py-3 font-semibold text-slate-900 dark:text-white">
                          {rec.employee_name || emp?.full_name || emp?.first_name || 'Staff Member'}
                        </td>
                        <td className="px-4 py-3 font-medium text-slate-700 dark:text-slate-300">{rec.date}</td>
                        <td className="px-4 py-3 text-slate-500">{rec.check_in || '--'}</td>
                        <td className="px-4 py-3 text-slate-500">{rec.check_out || '--'}</td>
                        <td className="px-4 py-3 text-slate-500">{rec.total_hours ? `${rec.total_hours} hrs` : '--'}</td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-brand-700 dark:bg-blue-950 dark:text-blue-300">
                            {rec.status}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )
      ) : activeTab === 'leaves' ? (
        /* Leaves Tab */
        leaves.length === 0 ? (
          <EmptyState
            title="No leave applications found"
            description="Submit leave requests to route for supervisor approvals."
            actionText="Apply Leave"
            onAction={() => setIsLeaveModalOpen(true)}
          />
        ) : (
          <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800 text-[10px] font-bold text-slate-400 uppercase">
                  <tr>
                    <th className="px-4 py-3">Employee</th>
                    <th className="px-4 py-3">Leave Type</th>
                    <th className="px-4 py-3">Duration</th>
                    <th className="px-4 py-3">Days</th>
                    <th className="px-4 py-3">Reason</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {leaves.map((l) => {
                    const emp = employees.find((e) => e.id === l.employee_id);
                    const lType = leaveTypes.find((t) => t.id === l.leave_type_id);
                    return (
                      <tr key={l.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/50">
                        <td className="px-4 py-3 font-semibold text-slate-900 dark:text-white">
                          {l.employee_name || emp?.full_name || 'Employee'}
                        </td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                          {l.leave_type_name || lType?.name || 'General Leave'}
                        </td>
                        <td className="px-4 py-3 text-slate-500">
                          {l.start_date} to {l.end_date}
                        </td>
                        <td className="px-4 py-3 font-medium text-slate-700 dark:text-slate-300">
                          {l.total_days || 1} day(s)
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-400 max-w-xs truncate">
                          {l.reason}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              l.status === 'Approved'
                                ? 'bg-emerald-50 text-emerald-700'
                                : l.status === 'Rejected'
                                ? 'bg-rose-50 text-rose-700'
                                : 'bg-amber-50 text-amber-700'
                            }`}
                          >
                            {l.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {l.status === 'Pending' && (
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => handleApproveLeave(l.id)}
                                className="px-2 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded text-[11px] font-semibold transition-colors cursor-pointer"
                              >
                                Approve
                              </button>
                              <button
                                onClick={() => handleRejectLeave(l.id)}
                                className="px-2 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded text-[11px] font-semibold transition-colors cursor-pointer"
                              >
                                Reject
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )
      ) : (
        /* Shifts Tab */
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {shifts.map((s) => (
            <div key={s.id} className="p-4 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl shadow-xs">
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-slate-900 dark:text-white text-sm">{s.name}</span>
                <span className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-600 dark:text-slate-300">
                  {s.code}
                </span>
              </div>
              <div className="text-xs text-slate-500 space-y-1">
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-brand-600" />
                  <span>{s.start_time} - {s.end_time}</span>
                </div>
                {s.is_night_shift && (
                  <span className="inline-block mt-2 px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-50 text-purple-700">
                    Overnight Shift
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Check In Modal */}
      <Modal isOpen={isCheckInModalOpen} onClose={() => setIsCheckInModalOpen(false)} title="Record Employee Check-In">
        <form onSubmit={handleCheckInSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">Select Employee *</label>
            <select
              value={selectedEmpId}
              onChange={(e) => setSelectedEmpId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-800 dark:text-slate-200"
            >
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.full_name || `${e.first_name} ${e.last_name}`} ({e.employee_code})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">Notes / Location</label>
            <input
              type="text"
              placeholder="e.g. On-site Head Office"
              value={checkInNotes}
              onChange={(e) => setCheckInNotes(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-800 dark:text-slate-200"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button type="button" variant="outline" size="sm" onClick={() => setIsCheckInModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm">
              Confirm Check-In
            </Button>
          </div>
        </form>
      </Modal>

      {/* Leave Application Modal */}
      <Modal isOpen={isLeaveModalOpen} onClose={() => setIsLeaveModalOpen(false)} title="Apply Leave Request">
        <form onSubmit={handleLeaveSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">Employee *</label>
            <select
              value={leaveForm.employee_id}
              onChange={(e) => setLeaveForm({ ...leaveForm, employee_id: e.target.value })}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-800 dark:text-slate-200"
            >
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.full_name || `${e.first_name} ${e.last_name}`} ({e.employee_code})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">Leave Type *</label>
            <select
              value={leaveForm.leave_type_id}
              onChange={(e) => setLeaveForm({ ...leaveForm, leave_type_id: e.target.value })}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-800 dark:text-slate-200"
            >
              {leaveTypes.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.days_allowed} days allowed)
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">Start Date *</label>
              <input
                type="date"
                required
                value={leaveForm.start_date}
                onChange={(e) => setLeaveForm({ ...leaveForm, start_date: e.target.value })}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-800 dark:text-slate-200"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">End Date *</label>
              <input
                type="date"
                required
                value={leaveForm.end_date}
                onChange={(e) => setLeaveForm({ ...leaveForm, end_date: e.target.value })}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-800 dark:text-slate-200"
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">Reason *</label>
            <textarea
              required
              rows={2}
              value={leaveForm.reason}
              onChange={(e) => setLeaveForm({ ...leaveForm, reason: e.target.value })}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg outline-none text-slate-800 dark:text-slate-200"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button type="button" variant="outline" size="sm" onClick={() => setIsLeaveModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm">
              Submit Leave Request
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
