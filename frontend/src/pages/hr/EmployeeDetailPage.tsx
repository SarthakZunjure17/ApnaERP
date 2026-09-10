import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  User,
  Mail,
  Copy,
  Check,
  Calendar,
  Briefcase,
  ChevronRight,
  MapPin,
  CheckCircle2,
  FileText,
  CalendarCheck,
  CreditCard,
  Building,
  Phone,
  ArrowLeft,
} from 'lucide-react';
import { hrService } from '../../services/hrService';
import { payrollService } from '../../services/payrollService';
import { EmployeeListItem, EmployeeDocumentItem, AttendanceRecord } from '../../types/hr';
import { EmployeeCompensationItem } from '../../types/payroll';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { useToast } from '../../context/ToastContext';

export const EmployeeDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [employee, setEmployee] = useState<EmployeeListItem | null>(null);
  const [documents, setDocuments] = useState<EmployeeDocumentItem[]>([]);
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([]);
  const [compensation, setCompensation] = useState<EmployeeCompensationItem | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'documents' | 'attendance' | 'compensation'>('overview');
  const [copiedEmail, setCopiedEmail] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { success } = useToast();
  const navigate = useNavigate();

  const loadData = async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const emp = await hrService.getEmployeeById(id);
      if (!emp) {
        setError('Employee record not found.');
        setIsLoading(false);
        return;
      }
      setEmployee(emp);

      // Load supporting sub-resources
      const [docRes, attRes, compRes] = await Promise.all([
        hrService.getEmployeeDocuments(id).catch(() => []),
        hrService.getAttendanceRecords({ employee_id: id }).catch(() => []),
        payrollService.getEmployeeCompensation(id).catch(() => null),
      ]);
      setDocuments(docRes);
      setAttendance(attRes);
      setCompensation(compRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load employee details.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const handleCopyEmail = (email: string) => {
    navigator.clipboard.writeText(email);
    setCopiedEmail(true);
    success('Copied', email);
    setTimeout(() => setCopiedEmail(false), 2000);
  };

  if (isLoading) {
    return <LoadingState message="Loading employee profile..." height="h-96" />;
  }

  if (error || !employee) {
    return (
      <ErrorState
        message={error || 'Employee record could not be loaded.'}
        onRetry={loadData}
      />
    );
  }

  const fullName = employee.full_name || `${employee.first_name} ${employee.last_name}`;

  return (
    <div className="space-y-5 animate-fade-in pb-10">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/workforce/employees" className="hover:text-brand-600 transition-colors">
          Workforce
        </Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <Link to="/workforce/employees" className="hover:text-brand-600 transition-colors">
          Employees
        </Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <span className="font-semibold text-slate-700 dark:text-slate-200">{fullName}</span>
      </div>

      {/* Profile Header Hero Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-xl bg-brand-600 text-white flex items-center justify-center font-bold text-xl uppercase shadow-md shadow-brand-500/20 shrink-0">
            {employee.first_name?.[0]}
            {employee.last_name?.[0]}
          </div>

          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                {fullName}
              </h1>
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                  employee.is_active
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400'
                    : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${employee.is_active ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                {employee.employment_status || (employee.is_active ? 'Active' : 'Inactive')}
              </span>
            </div>

            <p className="text-xs sm:text-sm font-medium text-slate-600 dark:text-slate-300 mt-1">
              {employee.position_title || 'Staff Member'} <span className="text-slate-400">•</span>{' '}
              {employee.department_name || 'Department'}
            </p>

            <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mt-1.5 flex-wrap">
              <span className="font-mono bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-[11px]">
                {employee.employee_code}
              </span>
              <span>•</span>
              <span>Joined: {employee.joining_date || 'N/A'}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/workforce/employees"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-xs font-semibold shadow-xs transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Directory
          </Link>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 overflow-x-auto pb-1 border-b border-slate-200/80 dark:border-slate-800 text-xs">
        <button
          onClick={() => setActiveTab('overview')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg font-semibold transition-all cursor-pointer ${
            activeTab === 'overview'
              ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-blue-300 shadow-2xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <User className="w-3.5 h-3.5" />
          Overview
        </button>

        <button
          onClick={() => setActiveTab('documents')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg font-semibold transition-all cursor-pointer ${
            activeTab === 'documents'
              ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-blue-300 shadow-2xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          Documents ({documents.length})
        </button>

        <button
          onClick={() => setActiveTab('attendance')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg font-semibold transition-all cursor-pointer ${
            activeTab === 'attendance'
              ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-blue-300 shadow-2xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <CalendarCheck className="w-3.5 h-3.5" />
          Attendance ({attendance.length})
        </button>

        <button
          onClick={() => setActiveTab('compensation')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg font-semibold transition-all cursor-pointer ${
            activeTab === 'compensation'
              ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-blue-300 shadow-2xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <CreditCard className="w-3.5 h-3.5" />
          Compensation
        </button>
      </div>

      {/* Tab: Overview */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Contact Details */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-3 text-xs">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <Mail className="w-4 h-4 text-brand-600" />
              Contact Information
            </h3>

            <div>
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                Work Email
              </span>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="text-slate-800 dark:text-slate-200 font-medium">{employee.work_email}</span>
                <button
                  onClick={() => handleCopyEmail(employee.work_email)}
                  className="p-0.5 text-slate-400 hover:text-brand-600"
                >
                  {copiedEmail ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            {employee.work_phone && (
              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Work Phone
                </span>
                <span className="text-slate-800 dark:text-slate-200 font-medium mt-0.5 block">
                  {employee.work_phone}
                </span>
              </div>
            )}

            {employee.personal_email && (
              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Personal Email
                </span>
                <span className="text-slate-800 dark:text-slate-200 font-medium mt-0.5 block">
                  {employee.personal_email}
                </span>
              </div>
            )}
          </div>

          {/* Employment Details */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-3 text-xs">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <Briefcase className="w-4 h-4 text-brand-600" />
              Employment Details
            </h3>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Employee Code
                </span>
                <span className="text-slate-800 dark:text-slate-200 font-mono font-medium mt-0.5 block">
                  {employee.employee_code}
                </span>
              </div>
              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Employment Type
                </span>
                <span className="text-slate-800 dark:text-slate-200 font-medium mt-0.5 block">
                  {employee.employment_type || 'Full Time'}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Joining Date
                </span>
                <span className="text-slate-800 dark:text-slate-200 font-medium mt-0.5 block">
                  {employee.joining_date}
                </span>
              </div>
              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Department
                </span>
                <span className="text-slate-800 dark:text-slate-200 font-medium mt-0.5 block">
                  {employee.department_name || 'Assigned'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Documents */}
      {activeTab === 'documents' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-4">
            Uploaded Documents
          </h3>
          {documents.length === 0 ? (
            <p className="text-xs text-slate-400 py-6 text-center">No employee documents uploaded yet.</p>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
              {documents.map((doc) => (
                <div key={doc.id} className="py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="w-4 h-4 text-brand-600" />
                    <div>
                      <p className="font-semibold text-slate-800 dark:text-slate-200">{doc.document_name}</p>
                      <span className="text-[11px] text-slate-400">{doc.document_type}</span>
                    </div>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700">
                    {doc.is_verified ? 'Verified' : 'Pending Verification'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab: Attendance */}
      {activeTab === 'attendance' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-4">
            Recent Attendance Records
          </h3>
          {attendance.length === 0 ? (
            <p className="text-xs text-slate-400 py-6 text-center">No attendance records logged for this employee.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800 text-[10px] font-bold text-slate-400 uppercase">
                  <tr>
                    <th className="px-3 py-2">Date</th>
                    <th className="px-3 py-2">Check In</th>
                    <th className="px-3 py-2">Check Out</th>
                    <th className="px-3 py-2">Hours</th>
                    <th className="px-3 py-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {attendance.map((rec) => (
                    <tr key={rec.id}>
                      <td className="px-3 py-2 font-medium">{rec.date}</td>
                      <td className="px-3 py-2 text-slate-500">{rec.check_in || '--'}</td>
                      <td className="px-3 py-2 text-slate-500">{rec.check_out || '--'}</td>
                      <td className="px-3 py-2 text-slate-500">{rec.total_hours ? `${rec.total_hours} hrs` : '--'}</td>
                      <td className="px-3 py-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-brand-700">
                          {rec.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Compensation */}
      {activeTab === 'compensation' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Salary & Compensation Profile
          </h3>
          {compensation ? (
            <div className="p-4 bg-slate-50 dark:bg-slate-800/60 rounded-xl flex justify-between items-center text-xs">
              <div>
                <span className="text-slate-500">Gross Monthly CTC</span>
                <h4 className="text-xl font-bold text-slate-900 dark:text-white mt-0.5">
                  ${Number(compensation.gross_salary).toLocaleString()}
                </h4>
                <span className="text-[11px] text-slate-400 mt-1 block">
                  Structure: {compensation.salary_structure_name || 'Standard Salary Grade'}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-400 py-6 text-center">
              No compensation profile currently assigned.
            </p>
          )}
        </div>
      )}
    </div>
  );
};
