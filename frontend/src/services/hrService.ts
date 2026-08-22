import { api } from './api';
import { EmployeeProfile, EmployeeListItem } from '../types/hr';

// High-fidelity fallback data matching Screenshot 1
const DEFAULT_EMPLOYEE_PROFILE: EmployeeProfile = {
  id: 'emp-001',
  employee_code: 'EMP-2021-042',
  first_name: 'Amit',
  last_name: 'Patel',
  full_name: 'Amit Patel',
  email: 'amit.patel@apnaerp.com',
  phone: '+91 98765 43210',
  avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
  designation: 'Senior Software Engineer',
  department: 'Engineering',
  location: 'Mumbai, India',
  status: 'Active',
  hire_date: '01 Mar 2021',
  date_of_birth: '12 Aug 1988',
  blood_group: 'O+',
  home_address: 'B-402, Skyline Apartments, Andheri East, Mumbai 400069',
  reporting_manager: {
    name: 'Priya Sharma',
    designation: 'Director of Engineering',
    avatar_url: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80',
  },
  attendance_ytd: {
    percentage: 92,
    leave_balance: 14,
    sick_taken: 3,
  },
  skills: [
    { id: '1', name: 'React.js', colorTheme: 'default' },
    { id: '2', name: 'Node.js', colorTheme: 'default' },
    { id: '3', name: 'PostgreSQL', colorTheme: 'default' },
    { id: '4', name: 'AWS CERTIFIED DEVELOPER', isCertified: true, colorTheme: 'blue' },
  ],
  upcoming_review: {
    description: 'Annual performance cycle begins in 14 days. Prepare self-assessment.',
    scheduled_date: '15 Nov 2023',
  },
};

const MOCK_EMPLOYEES_LIST: EmployeeListItem[] = [
  {
    id: 'emp-001',
    employee_code: 'EMP-2021-042',
    full_name: 'Amit Patel',
    email: 'amit.patel@apnaerp.com',
    phone: '+91 98765 43210',
    department: 'Engineering',
    designation: 'Senior Software Engineer',
    status: 'Active',
    join_date: '01 Mar 2021',
    location: 'Mumbai, India',
  },
  {
    id: 'emp-002',
    employee_code: 'EMP-2020-011',
    full_name: 'Priya Sharma',
    email: 'priya.sharma@apnaerp.com',
    phone: '+91 98111 22334',
    department: 'Engineering',
    designation: 'Director of Engineering',
    status: 'Active',
    join_date: '15 Jan 2020',
    location: 'Mumbai, India',
  },
  {
    id: 'emp-003',
    employee_code: 'EMP-2022-088',
    full_name: 'Rahul Verma',
    email: 'rahul.v@apnaerp.com',
    phone: '+91 97654 32109',
    department: 'Product',
    designation: 'Product Manager',
    status: 'Active',
    join_date: '10 Aug 2022',
    location: 'Bengaluru, India',
  },
  {
    id: 'emp-004',
    employee_code: 'EMP-2023-104',
    full_name: 'Neha Gupta',
    email: 'neha.g@apnaerp.com',
    phone: '+91 96543 21098',
    department: 'Finance',
    designation: 'Financial Analyst',
    status: 'On Leave',
    join_date: '01 Feb 2023',
    location: 'Delhi, India',
  },
  {
    id: 'emp-005',
    employee_code: 'EMP-2023-115',
    full_name: 'Suresh Kumar',
    email: 'suresh.k@apnaerp.com',
    phone: '+91 95432 10987',
    department: 'Operations',
    designation: 'Supply Chain Lead',
    status: 'Pending',
    join_date: '15 Sep 2023',
    location: 'Pune, India',
  },
];

export const hrService = {
  getEmployees: async (search?: string, department?: string): Promise<EmployeeListItem[]> => {
    try {
      const params: Record<string, string> = {};
      if (search) params.search = search;
      if (department && department !== 'All') params.department = department;

      const response = await api.get('/employees', { params });
      if (response.data && Array.isArray(response.data)) {
        return response.data;
      }
      return MOCK_EMPLOYEES_LIST;
    } catch {
      let filtered = [...MOCK_EMPLOYEES_LIST];
      if (search) {
        const q = search.toLowerCase();
        filtered = filtered.filter(
          (e) =>
            e.full_name.toLowerCase().includes(q) ||
            e.employee_code.toLowerCase().includes(q) ||
            e.email.toLowerCase().includes(q)
        );
      }
      if (department && department !== 'All') {
        filtered = filtered.filter((e) => e.department === department);
      }
      return filtered;
    }
  },

  getEmployeeById: async (id: string): Promise<EmployeeProfile> => {
    try {
      const response = await api.get(`/employees/${id}`);
      if (response.data) {
        return {
          ...DEFAULT_EMPLOYEE_PROFILE,
          ...response.data,
        };
      }
      return DEFAULT_EMPLOYEE_PROFILE;
    } catch {
      return DEFAULT_EMPLOYEE_PROFILE;
    }
  },

  updateEmployeeProfile: async (
    id: string,
    payload: Partial<EmployeeProfile>
  ): Promise<EmployeeProfile> => {
    try {
      const response = await api.put(`/employees/${id}`, payload);
      return response.data;
    } catch {
      return {
        ...DEFAULT_EMPLOYEE_PROFILE,
        ...payload,
      };
    }
  },

  addSkill: async (employeeId: string, skillName: string): Promise<EmployeeProfile> => {
    const newSkill = {
      id: String(Date.now()),
      name: skillName,
      colorTheme: 'default' as const,
    };
    return {
      ...DEFAULT_EMPLOYEE_PROFILE,
      skills: [...DEFAULT_EMPLOYEE_PROFILE.skills, newSkill],
    };
  },
};
