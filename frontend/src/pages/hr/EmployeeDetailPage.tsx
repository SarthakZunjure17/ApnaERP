import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  User,
  Mail,
  Copy,
  Check,
  Calendar,
  Droplet,
  Briefcase,
  Code2,
  Trophy,
  Star,
  KeyRound,
  Pencil,
  EyeOff,
  LayoutGrid,
  FileText,
  CalendarCheck,
  CreditCard,
  History,
  Plus,
  MapPin,
  CheckCircle2,
  ChevronRight,
  Shield,
} from 'lucide-react';
import { hrService } from '../../services/hrService';
import { EmployeeProfile, SkillItem } from '../../types/hr';
import { CircularProgress } from '../../components/common/CircularProgress';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { useToast } from '../../context/ToastContext';

export const EmployeeDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [profile, setProfile] = useState<EmployeeProfile | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'employment' | 'documents' | 'attendance' | 'payroll' | 'activity'>('overview');
  const [copiedEmail, setCopiedEmail] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isAddSkillModalOpen, setIsAddSkillModalOpen] = useState(false);
  const [newSkillName, setNewSkillName] = useState('');
  const [isResetAuthModalOpen, setIsResetAuthModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Edit form state
  const [editForm, setEditForm] = useState({
    phone: '',
    home_address: '',
    blood_group: '',
  });

  const { success, info } = useToast();

  useEffect(() => {
    loadEmployee();
  }, [id]);

  const loadEmployee = async () => {
    setIsLoading(true);
    const data = await hrService.getEmployeeById(id || 'emp-001');
    setProfile(data);
    setEditForm({
      phone: data.phone,
      home_address: data.home_address,
      blood_group: data.blood_group,
    });
    setIsLoading(false);
  };

  const handleCopyEmail = (email: string) => {
    navigator.clipboard.writeText(email);
    setCopiedEmail(true);
    success('Copied to Clipboard', email);
    setTimeout(() => setCopiedEmail(false), 2000);
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;
    const updated = await hrService.updateEmployeeProfile(profile.id, editForm);
    setProfile(updated);
    setIsEditModalOpen(false);
    success('Profile Updated', 'Employee details saved successfully.');
  };

  const handleAddSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile || !newSkillName.trim()) return;
    const updated = await hrService.addSkill(profile.id, newSkillName.trim());
    setProfile(updated);
    setNewSkillName('');
    setIsAddSkillModalOpen(false);
    success('Skill Added', `${newSkillName} added to certifications.`);
  };

  const handleResetAuth = () => {
    setIsResetAuthModalOpen(false);
    success('Auth Reset', 'Password reset instructions sent to employee email.');
  };

  if (isLoading || !profile) {
    return <LoadingState message="Loading employee profile..." />;
  }

  return (
    <div className="space-y-4 sm:space-y-5 animate-fade-in pb-10">
      {/* Top Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/workforce/employees" className="hover:text-brand-600 transition-colors">
          Workforce
        </Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <Link to="/workforce/employees" className="hover:text-brand-600 transition-colors">
          Employees
        </Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <span className="font-semibold text-slate-700 dark:text-slate-200">{profile.full_name}</span>
      </div>

      {/* Profile Header Hero Card (Matching Screenshot 1) */}
      <div className="bg-[#f0f4ff] dark:bg-slate-900 border border-blue-100/90 dark:border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-5">
        {/* Left: Avatar + Details */}
        <div className="flex items-center gap-4">
          {/* Avatar with blue verified badge */}
          <div className="relative shrink-0">
            <img
              src={profile.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80'}
              alt={profile.full_name}
              className="w-16 h-16 sm:w-18 sm:h-18 rounded-xl object-cover ring-2 ring-white dark:ring-slate-800 shadow-sm"
            />
            <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-brand-600 text-white rounded-full flex items-center justify-center ring-2 ring-white dark:ring-slate-900">
              <CheckCircle2 className="w-3.5 h-3.5" />
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                {profile.full_name}
              </h1>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
                ACTIVE
              </span>
            </div>

            <p className="text-xs sm:text-sm font-medium text-slate-600 dark:text-slate-300 mt-1">
              {profile.designation} <span className="text-slate-400">•</span> {profile.department} Dept
            </p>

            <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mt-1.5 flex-wrap">
              <span className="inline-flex items-center gap-1">
                <span className="text-slate-400">#</span> {profile.employee_code}
              </span>
              <span className="text-slate-300 dark:text-slate-700">•</span>
              <span className="inline-flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                {profile.location}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2 self-start md:self-center">
          <button
            onClick={() => setIsResetAuthModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200/90 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <KeyRound className="w-3.5 h-3.5 text-slate-500" />
            Reset Auth
          </button>

          <button
            onClick={() => setIsEditModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <Pencil className="w-3.5 h-3.5" />
            Edit Profile
          </button>

          <button
            onClick={() => info('Security Actions', 'Access controls and session restrictions')}
            className="p-2 bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 rounded-lg transition-colors cursor-pointer"
            title="Account Restrictions"
          >
            <EyeOff className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Tabs Navigation (Matching Screenshot 1) */}
      <div className="flex items-center gap-1 overflow-x-auto pb-1 border-b border-slate-200/80 dark:border-slate-800 text-xs">
        <button
          onClick={() => setActiveTab('overview')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg font-semibold transition-all cursor-pointer ${
            activeTab === 'overview'
              ? 'bg-blue-100/80 dark:bg-blue-900/50 text-brand-700 dark:text-blue-300 shadow-2xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <LayoutGrid className="w-3.5 h-3.5" />
          Overview
        </button>

        <button
          onClick={() => setActiveTab('employment')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg font-semibold transition-all cursor-pointer ${
            activeTab === 'employment'
              ? 'bg-blue-100/80 dark:bg-blue-900/50 text-brand-700 dark:text-blue-300 shadow-2xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Briefcase className="w-3.5 h-3.5" />
          Employment
        </button>

        <button
          onClick={() => setActiveTab('documents')}
          className={`relative inline-flex items-center gap-2 px-3.5 py-2 rounded-lg font-semibold transition-all cursor-pointer ${
            activeTab === 'documents'
              ? 'bg-blue-100/80 dark:bg-blue-900/50 text-brand-700 dark:text-blue-300 shadow-2xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          Documents
          <span className="w-1.5 h-1.5 rounded-full bg-rose-500 absolute top-1.5 right-1.5 ring-2 ring-white dark:ring-slate-900" />
        </button>

        <button
          onClick={() => setActiveTab('attendance')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg font-semibold transition-all cursor-pointer ${
            activeTab === 'attendance'
              ? 'bg-blue-100/80 dark:bg-blue-900/50 text-brand-700 dark:text-blue-300 shadow-2xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <CalendarCheck className="w-3.5 h-3.5" />
          Attendance
        </button>

        <button
          onClick={() => setActiveTab('payroll')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg font-semibold transition-all cursor-pointer ${
            activeTab === 'payroll'
              ? 'bg-blue-100/80 dark:bg-blue-900/50 text-brand-700 dark:text-blue-300 shadow-2xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <CreditCard className="w-3.5 h-3.5" />
          Payroll
        </button>

        <button
          onClick={() => setActiveTab('activity')}
          className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg font-semibold transition-all cursor-pointer ${
            activeTab === 'activity'
              ? 'bg-blue-100/80 dark:bg-blue-900/50 text-brand-700 dark:text-blue-300 shadow-2xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          Activity
        </button>
      </div>

      {/* Tab Content: Overview (Matching Screenshot 1) */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          {/* Row 1: 3 Columns Grid (Personal Details + Job Profile + Attendance YTD) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Card 1: Personal Details */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-md bg-blue-50 dark:bg-blue-950 flex items-center justify-center text-blue-600 dark:text-blue-400">
                      <User className="w-3.5 h-3.5" />
                    </div>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                      Personal Details
                    </h3>
                  </div>
                  <button
                    onClick={() => setIsEditModalOpen(true)}
                    className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded transition-colors"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="space-y-3 text-xs">
                  {/* Email */}
                  <div>
                    <span className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase block">
                      Email Address
                    </span>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="text-slate-800 dark:text-slate-200 font-medium truncate">
                        {profile.email}
                      </span>
                      <button
                        onClick={() => handleCopyEmail(profile.email)}
                        className="text-slate-400 hover:text-brand-600 transition-colors p-0.5"
                        title="Copy email"
                      >
                        {copiedEmail ? (
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Phone */}
                  <div>
                    <span className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase block">
                      Phone Number
                    </span>
                    <span className="text-slate-800 dark:text-slate-200 font-medium mt-0.5 block">
                      {profile.phone}
                    </span>
                  </div>

                  {/* Home Address */}
                  <div>
                    <span className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase block">
                      Home Address
                    </span>
                    <span className="text-slate-800 dark:text-slate-200 font-medium mt-0.5 block leading-relaxed">
                      {profile.home_address}
                    </span>
                  </div>

                  {/* DOB & Blood Group */}
                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <div>
                      <span className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase block">
                        Date of Birth
                      </span>
                      <span className="text-slate-800 dark:text-slate-200 font-medium mt-0.5 block">
                        {profile.date_of_birth}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase block">
                        Blood Group
                      </span>
                      <span className="inline-flex items-center gap-1 text-slate-800 dark:text-slate-200 font-medium mt-0.5">
                        {profile.blood_group}
                        <Droplet className="w-3 h-3 text-rose-500 fill-rose-500" />
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Card 2: Job Profile */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-6 h-6 rounded-md bg-blue-50 dark:bg-blue-950 flex items-center justify-center text-blue-600 dark:text-blue-400">
                  <Briefcase className="w-3.5 h-3.5" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Job Profile
                </h3>
              </div>

              <div className="space-y-3.5 text-xs">
                {/* Employee ID & Hire Date */}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase block">
                      Employee ID
                    </span>
                    <span className="inline-block px-2 py-0.5 mt-1 rounded bg-blue-50 dark:bg-blue-950/60 text-brand-700 dark:text-blue-300 font-mono font-semibold text-[11px]">
                      {profile.employee_code}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase block">
                      Hire Date
                    </span>
                    <span className="text-slate-800 dark:text-slate-200 font-medium mt-1 block">
                      {profile.hire_date}
                    </span>
                  </div>
                </div>

                {/* Department */}
                <div>
                  <span className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase block">
                    Department
                  </span>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-6 h-6 rounded bg-amber-600 text-white flex items-center justify-center">
                      <Code2 className="w-3.5 h-3.5" />
                    </div>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      {profile.department}
                    </span>
                  </div>
                </div>

                {/* Reporting Manager */}
                <div>
                  <span className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase block">
                    Reporting Manager
                  </span>
                  <div className="flex items-center gap-2.5 mt-1.5 p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                    <img
                      src={profile.reporting_manager.avatar_url}
                      alt={profile.reporting_manager.name}
                      className="w-7 h-7 rounded-full object-cover shrink-0 ring-1 ring-white"
                    />
                    <div>
                      <p className="font-semibold text-slate-900 dark:text-white leading-tight">
                        {profile.reporting_manager.name}
                      </p>
                      <p className="text-[10px] text-slate-400 mt-0.5 leading-tight">
                        {profile.reporting_manager.designation}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Card 3: Attendance (YTD) */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-6 h-6 rounded-md bg-blue-50 dark:bg-blue-950 flex items-center justify-center text-blue-600 dark:text-blue-400">
                    <CalendarCheck className="w-3.5 h-3.5" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Attendance (YTD)
                  </h3>
                </div>

                {/* Circular Gauge */}
                <div className="flex justify-center py-1">
                  <CircularProgress
                    percentage={profile.attendance_ytd.percentage}
                    label="PRESENT"
                    size={105}
                    strokeWidth={8}
                  />
                </div>
              </div>

              {/* Bottom stats boxes */}
              <div className="grid grid-cols-2 gap-2.5 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/50 text-center">
                  <span className="text-lg font-bold text-slate-900 dark:text-white block leading-tight">
                    {profile.attendance_ytd.leave_balance}
                  </span>
                  <span className="text-[9px] font-semibold text-slate-400 uppercase tracking-wider mt-0.5 block">
                    Leave Balance
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/50 text-center">
                  <span className="text-lg font-bold text-slate-900 dark:text-white block leading-tight">
                    {profile.attendance_ytd.sick_taken}
                  </span>
                  <span className="text-[9px] font-semibold text-slate-400 uppercase tracking-wider mt-0.5 block">
                    Sick Taken
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Row 2: 2 Columns Grid (Skills & Certifications + Upcoming Review) */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
            {/* Skills & Certifications (Col span 8) */}
            <div className="md:col-span-8 bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800/80 rounded-xl p-4 sm:p-5 shadow-xs">
              <div className="flex items-center gap-2 mb-3.5">
                <div className="w-6 h-6 rounded-md bg-blue-50 dark:bg-blue-950 flex items-center justify-center text-blue-600 dark:text-blue-400">
                  <Trophy className="w-3.5 h-3.5" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Skills & Certifications
                </h3>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {profile.skills.map((skill) => {
                  if (skill.isCertified) {
                    return (
                      <span
                        key={skill.id}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600 text-white font-bold text-[11px] uppercase tracking-wider shadow-xs"
                      >
                        <Shield className="w-3.5 h-3.5" />
                        {skill.name}
                      </span>
                    );
                  }

                  return (
                    <span
                      key={skill.id}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-semibold text-xs border border-slate-200/60 dark:border-slate-700"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-brand-600" />
                      {skill.name}
                    </span>
                  );
                })}

                <button
                  onClick={() => setIsAddSkillModalOpen(true)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-dashed border-slate-300 dark:border-slate-700 text-slate-500 hover:text-brand-600 hover:border-brand-500 font-medium text-xs transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add Skill
                </button>
              </div>
            </div>

            {/* Upcoming Review Banner (Col span 4, Solid Blue matching Screenshot 1) */}
            <div className="md:col-span-4 bg-brand-600 text-white rounded-xl p-4 sm:p-5 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2.5 mb-2">
                  <div className="w-7 h-7 rounded-lg bg-white/20 flex items-center justify-center">
                    <Star className="w-4 h-4 text-white fill-white" />
                  </div>
                  <h3 className="text-sm font-bold tracking-tight">Upcoming Review</h3>
                </div>

                <p className="text-xs text-blue-100 leading-relaxed">
                  {profile.upcoming_review.description}
                </p>
              </div>

              <div className="mt-4 p-2.5 rounded-lg bg-brand-700/60 border border-brand-500/40">
                <span className="text-[9px] font-bold text-blue-200 uppercase tracking-wider block">
                  Scheduled Date
                </span>
                <span className="text-xs font-bold text-white mt-0.5 block">
                  {profile.upcoming_review.scheduled_date}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Employment Tab */}
      {activeTab === 'employment' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">Employment History</h3>
          <div className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
            <div className="py-3 flex justify-between">
              <div>
                <p className="font-semibold text-slate-900 dark:text-white">Promoted to Senior Software Engineer</p>
                <p className="text-slate-500 mt-0.5">Engineering Department</p>
              </div>
              <span className="text-slate-400">Jan 2023</span>
            </div>
            <div className="py-3 flex justify-between">
              <div>
                <p className="font-semibold text-slate-900 dark:text-white">Joined as Software Engineer</p>
                <p className="text-slate-500 mt-0.5">Engineering Department</p>
              </div>
              <span className="text-slate-400">Mar 2021</span>
            </div>
          </div>
        </div>
      )}

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Employee Documents</h3>
            <Button size="sm" variant="outline" onClick={() => info('Upload Document', 'Select PDF or image')}>
              <Plus className="w-3.5 h-3.5 mr-1" /> Upload Doc
            </Button>
          </div>
          <div className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
            <div className="py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText className="w-4 h-4 text-blue-600" />
                <div>
                  <p className="font-semibold text-slate-900 dark:text-white">Employment_Contract_2021.pdf</p>
                  <p className="text-[11px] text-slate-400">Signed on 01 Mar 2021 • 2.4 MB</p>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700">Verified</span>
            </div>
            <div className="py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText className="w-4 h-4 text-blue-600" />
                <div>
                  <p className="font-semibold text-slate-900 dark:text-white">Government_ID_Proof.pdf</p>
                  <p className="text-[11px] text-slate-400">Uploaded on 02 Mar 2021 • 1.1 MB</p>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700">Verified</span>
            </div>
          </div>
        </div>
      )}

      {/* Attendance Tab */}
      {activeTab === 'attendance' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">Recent Attendance Logs</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Today</span>
              <p className="font-bold text-emerald-600 mt-1">Present (Checked in 09:12 AM)</p>
            </div>
            <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Yesterday</span>
              <p className="font-bold text-emerald-600 mt-1">Present (9.2 hrs)</p>
            </div>
            <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Current Month</span>
              <p className="font-bold text-slate-900 dark:text-white mt-1">21 / 22 Working Days</p>
            </div>
          </div>
        </div>
      )}

      {/* Payroll Tab */}
      {activeTab === 'payroll' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">Compensation & Payslips</h3>
          <div className="p-4 bg-slate-50 dark:bg-slate-800/60 rounded-xl flex justify-between items-center text-xs">
            <div>
              <span className="text-slate-500">Current Monthly Gross</span>
              <h4 className="text-lg font-bold text-slate-900 dark:text-white mt-0.5">$8,500.00</h4>
            </div>
            <Button size="sm" variant="primary" onClick={() => info('Payslip', 'Downloading latest payslip PDF')}>
              Download Latest Slip
            </Button>
          </div>
        </div>
      )}

      {/* Activity Tab */}
      {activeTab === 'activity' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">System Audit & Logs</h3>
          <div className="space-y-3 text-xs">
            <div className="flex gap-2.5">
              <span className="w-2 h-2 rounded-full bg-brand-600 mt-1" />
              <div>
                <p className="font-semibold text-slate-800 dark:text-slate-200">Skills updated: Added AWS Certified Developer</p>
                <span className="text-[10px] text-slate-400">2 days ago by ERP Admin</span>
              </div>
            </div>
            <div className="flex gap-2.5">
              <span className="w-2 h-2 rounded-full bg-slate-400 mt-1" />
              <div>
                <p className="font-semibold text-slate-800 dark:text-slate-200">Leave requested: 2 days Sick Leave approved</p>
                <span className="text-[10px] text-slate-400">1 week ago by Priya Sharma</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Profile Modal */}
      <Modal isOpen={isEditModalOpen} onClose={() => setIsEditModalOpen(false)} title="Edit Employee Profile">
        <form onSubmit={handleSaveProfile} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">Phone Number</label>
            <input
              type="text"
              value={editForm.phone}
              onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
              className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
            />
          </div>
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">Home Address</label>
            <textarea
              value={editForm.home_address}
              onChange={(e) => setEditForm({ ...editForm, home_address: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
            />
          </div>
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">Blood Group</label>
            <select
              value={editForm.blood_group}
              onChange={(e) => setEditForm({ ...editForm, blood_group: e.target.value })}
              className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
            >
              <option value="O+">O+</option>
              <option value="A+">A+</option>
              <option value="B+">B+</option>
              <option value="AB+">AB+</option>
              <option value="O-">O-</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button variant="outline" size="sm" type="button" onClick={() => setIsEditModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* Add Skill Modal */}
      <Modal isOpen={isAddSkillModalOpen} onClose={() => setIsAddSkillModalOpen(false)} title="Add Skill or Certification">
        <form onSubmit={handleAddSkill} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">Skill / Certification Name</label>
            <input
              type="text"
              placeholder="e.g. Docker, TypeScript, AWS Architect..."
              value={newSkillName}
              onChange={(e) => setNewSkillName(e.target.value)}
              className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-100"
              autoFocus
            />
          </div>
          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button variant="outline" size="sm" type="button" onClick={() => setIsAddSkillModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit" disabled={!newSkillName.trim()}>
              Add Skill
            </Button>
          </div>
        </form>
      </Modal>

      {/* Reset Auth Confirmation Modal */}
      <Modal isOpen={isResetAuthModalOpen} onClose={() => setIsResetAuthModalOpen(false)} title="Reset Employee Authentication">
        <div className="space-y-3 text-xs">
          <p className="text-slate-600 dark:text-slate-300">
            Are you sure you want to reset password and multi-factor credentials for{' '}
            <strong className="text-slate-900 dark:text-white">{profile.full_name}</strong>?
          </p>
          <p className="text-slate-500">A secure one-time password link will be emailed to {profile.email}.</p>
          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button variant="outline" size="sm" onClick={() => setIsResetAuthModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleResetAuth}>
              Send Reset Link
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
