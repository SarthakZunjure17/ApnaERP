import { api } from './api';
import { EmployeeProfile, EmployeeListItem } from '../types/hr';

const MOCK_PROFILES_MAP: Record<string, EmployeeProfile> = {
  'emp-001': {
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
  },
  'emp-002': {
    id: 'emp-002',
    employee_code: 'EMP-2020-011',
    first_name: 'Priya',
    last_name: 'Sharma',
    full_name: 'Priya Sharma',
    email: 'priya.sharma@apnaerp.com',
    phone: '+91 98111 22334',
    avatar_url: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80',
    designation: 'Director of Engineering',
    department: 'Engineering',
    location: 'Mumbai, India',
    status: 'Active',
    hire_date: '15 Jan 2020',
    date_of_birth: '24 May 1982',
    blood_group: 'A+',
    home_address: '1202 Sea Breeze Towers, Worli, Mumbai 400018',
    reporting_manager: {
      name: 'Vikram Mehta',
      designation: 'Chief Technology Officer',
      avatar_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
    },
    attendance_ytd: {
      percentage: 96,
      leave_balance: 18,
      sick_taken: 1,
    },
    skills: [
      { id: '1', name: 'System Architecture', colorTheme: 'default' },
      { id: '2', name: 'Kubernetes', colorTheme: 'default' },
      { id: '3', name: 'Team Leadership', colorTheme: 'default' },
      { id: '4', name: 'TOGAF CERTIFIED ARCHITECT', isCertified: true, colorTheme: 'blue' },
    ],
    upcoming_review: {
      description: 'Executive leadership evaluation scheduled with the board.',
      scheduled_date: '01 Dec 2023',
    },
  },
  'emp-003': {
    id: 'emp-003',
    employee_code: 'EMP-2022-088',
    first_name: 'Rahul',
    last_name: 'Verma',
    full_name: 'Rahul Verma',
    email: 'rahul.v@apnaerp.com',
    phone: '+91 97654 32109',
    avatar_url: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80',
    designation: 'Product Manager',
    department: 'Product',
    location: 'Bengaluru, India',
    status: 'Active',
    hire_date: '10 Aug 2022',
    date_of_birth: '19 Sep 1991',
    blood_group: 'B+',
    home_address: 'Plot 45, Green Glen Layout, Bellandur, Bengaluru 560103',
    reporting_manager: {
      name: 'Ananya Rao',
      designation: 'VP of Product',
      avatar_url: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80',
    },
    attendance_ytd: {
      percentage: 89,
      leave_balance: 10,
      sick_taken: 4,
    },
    skills: [
      { id: '1', name: 'Product Roadmapping', colorTheme: 'default' },
      { id: '2', name: 'Data Analytics', colorTheme: 'default' },
      { id: '3', name: 'Agile / Scrum', colorTheme: 'default' },
      { id: '4', name: 'CERTIFIED SCRUM PRODUCT OWNER', isCertified: true, colorTheme: 'blue' },
    ],
    upcoming_review: {
      description: 'Q4 Product roadmap review and KPI sign-off.',
      scheduled_date: '20 Nov 2023',
    },
  },
  'emp-004': {
    id: 'emp-004',
    employee_code: 'EMP-2023-104',
    first_name: 'Neha',
    last_name: 'Gupta',
    full_name: 'Neha Gupta',
    email: 'neha.g@apnaerp.com',
    phone: '+91 96543 21098',
    avatar_url: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80',
    designation: 'Financial Analyst',
    department: 'Finance',
    location: 'Delhi, India',
    status: 'On Leave',
    hire_date: '01 Feb 2023',
    date_of_birth: '05 Nov 1993',
    blood_group: 'AB+',
    home_address: 'C-14, Hauz Khas Enclave, New Delhi 110016',
    reporting_manager: {
      name: 'Rohan Deshmukh',
      designation: 'Chief Financial Officer',
      avatar_url: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&auto=format&fit=crop&q=80',
    },
    attendance_ytd: {
      percentage: 84,
      leave_balance: 5,
      sick_taken: 8,
    },
    skills: [
      { id: '1', name: 'Financial Modeling', colorTheme: 'default' },
      { id: '2', name: 'ERP GL Accounting', colorTheme: 'default' },
      { id: '3', name: 'Budget Forecasting', colorTheme: 'default' },
      { id: '4', name: 'CFA CHARTERHOLDER', isCertified: true, colorTheme: 'blue' },
    ],
    upcoming_review: {
      description: 'Mid-year performance checkpoint upon return from leave.',
      scheduled_date: '10 Jan 2024',
    },
  },
  'emp-005': {
    id: 'emp-005',
    employee_code: 'EMP-2023-115',
    first_name: 'Suresh',
    last_name: 'Kumar',
    full_name: 'Suresh Kumar',
    email: 'suresh.k@apnaerp.com',
    phone: '+91 95432 10987',
    avatar_url: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=150&auto=format&fit=crop&q=80',
    designation: 'Supply Chain Lead',
    department: 'Operations',
    location: 'Pune, India',
    status: 'Pending',
    hire_date: '15 Sep 2023',
    date_of_birth: '30 Mar 1989',
    blood_group: 'O-',
    home_address: 'Flat 301, Silver Crest, Viman Nagar, Pune 411014',
    reporting_manager: {
      name: 'Kavita Menon',
      designation: 'VP of Global Operations',
      avatar_url: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150&auto=format&fit=crop&q=80',
    },
    attendance_ytd: {
      percentage: 95,
      leave_balance: 20,
      sick_taken: 0,
    },
    skills: [
      { id: '1', name: 'Inventory Forecasting', colorTheme: 'default' },
      { id: '2', name: 'Procurement Logistics', colorTheme: 'default' },
      { id: '3', name: 'Warehouse Automation', colorTheme: 'default' },
      { id: '4', name: 'CSCP CERTIFIED', isCertified: true, colorTheme: 'blue' },
    ],
    upcoming_review: {
      description: 'Probation completion and 90-day onboarding assessment.',
      scheduled_date: '15 Dec 2023',
    },
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

function normalizeBackendEmployeeItem(backendEmp: any, index: number = 0): EmployeeListItem {
  const fullName = backendEmp.full_name || `${backendEmp.first_name || 'Staff'} ${backendEmp.last_name || 'Member'}`.trim();
  const defaultAvatars = [
    'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80',
    'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
  ];

  return {
    id: String(backendEmp.id),
    employee_code: backendEmp.employee_code || `EMP-2024-${String(index + 1).padStart(3, '0')}`,
    full_name: fullName,
    email: backendEmp.email || backendEmp.work_email || `${fullName.toLowerCase().replace(/\s+/g, '.')}@apnaerp.com`,
    phone: backendEmp.phone || backendEmp.work_phone || '+91 98765 43210',
    department: backendEmp.department_name || backendEmp.department || 'Engineering',
    designation: backendEmp.designation_name || backendEmp.designation || 'Specialist',
    status: (backendEmp.employment_status || backendEmp.status || 'Active') as EmployeeListItem['status'],
    join_date: backendEmp.join_date || backendEmp.joining_date || '01 Mar 2023',
    location: backendEmp.location || 'Mumbai, India',
    avatar_url: backendEmp.avatar_url || defaultAvatars[index % defaultAvatars.length],
  };
}

export const hrService = {
  getEmployees: async (search?: string, department?: string): Promise<EmployeeListItem[]> => {
    try {
      const params: Record<string, string> = {};
      if (search) params.search = search;
      if (department && department !== 'All') params.department = department;

      const response = await api.get('/api/v1/employees', { params });
      if (response.data && Array.isArray(response.data) && response.data.length > 0) {
        return response.data.map((e: any, idx: number) => normalizeBackendEmployeeItem(e, idx));
      }
      if (response.data && Array.isArray(response.data.items) && response.data.items.length > 0) {
        return response.data.items.map((e: any, idx: number) => normalizeBackendEmployeeItem(e, idx));
      }
      return filterMockList(search, department);
    } catch {
      return filterMockList(search, department);
    }
  },

  getEmployeeById: async (id: string): Promise<EmployeeProfile | null> => {
    if (!id) return null;
    const cleanId = id.trim().toLowerCase();

    // 1. Check if it's one of the canonical mock profiles first
    for (const [key, profile] of Object.entries(MOCK_PROFILES_MAP)) {
      if (key.toLowerCase() === cleanId || profile.employee_code.toLowerCase() === cleanId) {
        return profile;
      }
    }

    try {
      const response = await api.get(`/api/v1/employees/${id}`);
      if (response.data && typeof response.data === 'object' && response.data.id) {
        const emp = response.data;
        const fullName = emp.full_name || `${emp.first_name || 'Staff'} ${emp.last_name || 'Member'}`.trim();
        const names = fullName.split(' ');
        return {
          id: String(emp.id),
          employee_code: emp.employee_code || 'EMP-2024-001',
          first_name: names[0] || 'Employee',
          last_name: names.slice(1).join(' ') || '',
          full_name: fullName,
          email: emp.email || emp.work_email || 'employee@apnaerp.com',
          phone: emp.phone || emp.work_phone || '+91 98765 43210',
          avatar_url: emp.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
          designation: emp.designation_name || emp.designation || 'Senior Specialist',
          department: emp.department_name || emp.department || 'Engineering',
          location: emp.location || 'Mumbai, India',
          status: (emp.employment_status || emp.status || 'Active') as EmployeeProfile['status'],
          hire_date: emp.join_date || emp.joining_date || '01 Mar 2021',
          date_of_birth: emp.date_of_birth || '15 Jan 1990',
          blood_group: emp.blood_group || 'O+',
          home_address: emp.home_address || 'B-402, Skyline Apartments, Andheri East, Mumbai',
          reporting_manager: emp.reporting_manager || {
            name: 'Priya Sharma',
            designation: 'Director of Engineering',
            avatar_url: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80',
          },
          attendance_ytd: emp.attendance_ytd || {
            percentage: 94,
            leave_balance: 16,
            sick_taken: 2,
          },
          skills: Array.isArray(emp.skills) && emp.skills.length > 0 ? emp.skills : [
            { id: '1', name: emp.department || 'Engineering', colorTheme: 'default' },
            { id: '2', name: emp.designation || 'Specialist', colorTheme: 'default' },
            { id: '3', name: 'ERP System Ops', isCertified: true, colorTheme: 'blue' },
          ],
          upcoming_review: emp.upcoming_review || {
            description: 'Annual performance review scheduled.',
            scheduled_date: '15 Dec 2024',
          },
        };
      }
      return getMockProfileById(id);
    } catch {
      return getMockProfileById(id);
    }
  },

  updateEmployeeProfile: async (
    id: string,
    payload: Partial<EmployeeProfile>
  ): Promise<EmployeeProfile | null> => {
    try {
      const response = await api.put(`/api/v1/employees/${id}`, payload);
      if (response.data && typeof response.data === 'object' && response.data.id) {
        return response.data;
      }
      const existing = getMockProfileById(id);
      if (!existing) return null;
      const updated = { ...existing, ...payload };
      MOCK_PROFILES_MAP[id] = updated;
      return updated;
    } catch {
      const existing = getMockProfileById(id);
      if (!existing) return null;
      const updated = { ...existing, ...payload };
      MOCK_PROFILES_MAP[id] = updated;
      return updated;
    }
  },

  addSkill: async (employeeId: string, skillName: string): Promise<EmployeeProfile | null> => {
    const existing = getMockProfileById(employeeId);
    if (!existing) return null;
    const newSkill = {
      id: String(Date.now()),
      name: skillName,
      colorTheme: 'default' as const,
    };
    const updated = {
      ...existing,
      skills: [...existing.skills, newSkill],
    };
    MOCK_PROFILES_MAP[employeeId] = updated;
    return updated;
  },

  createEmployee: async (employee: Partial<EmployeeListItem>): Promise<EmployeeListItem> => {
    const newId = employee.id || `emp-${Date.now()}`;
    const newEmp: EmployeeListItem = {
      id: newId,
      employee_code: employee.employee_code || `EMP-2024-${String(MOCK_EMPLOYEES_LIST.length + 1).padStart(3, '0')}`,
      full_name: employee.full_name || 'New Employee',
      email: employee.email || 'employee@apnaerp.com',
      phone: employee.phone || '+91 90000 00000',
      department: employee.department || 'Engineering',
      designation: employee.designation || 'Staff Member',
      status: 'Active',
      join_date: 'Today',
      location: employee.location || 'Mumbai, India',
    };

    MOCK_EMPLOYEES_LIST.unshift(newEmp);

    const names = newEmp.full_name.split(' ');
    const newProfile: EmployeeProfile = {
      id: newId,
      employee_code: newEmp.employee_code,
      first_name: names[0] || 'Employee',
      last_name: names.slice(1).join(' ') || '',
      full_name: newEmp.full_name,
      email: newEmp.email,
      phone: newEmp.phone,
      avatar_url: `https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80`,
      designation: newEmp.designation,
      department: newEmp.department,
      location: newEmp.location,
      status: newEmp.status,
      hire_date: newEmp.join_date,
      date_of_birth: '15 Jan 1992',
      blood_group: 'O+',
      home_address: `Building 12, Cyber City, ${newEmp.location}`,
      reporting_manager: {
        name: 'Priya Sharma',
        designation: 'Director of Engineering',
        avatar_url: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80',
      },
      attendance_ytd: {
        percentage: 100,
        leave_balance: 18,
        sick_taken: 0,
      },
      skills: [
        { id: '1', name: newEmp.department, colorTheme: 'default' },
        { id: '2', name: newEmp.designation, colorTheme: 'default' },
        { id: '3', name: 'Workforce Onboarding', colorTheme: 'default' },
      ],
      upcoming_review: {
        description: 'New hire 90-day onboarding review.',
        scheduled_date: '15 Dec 2024',
      },
    };

    MOCK_PROFILES_MAP[newId] = newProfile;
    return newEmp;
  },
};

function filterMockList(search?: string, department?: string): EmployeeListItem[] {
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

function getMockProfileById(id: string): EmployeeProfile | null {
  if (!id) return null;
  const cleanId = id.trim().toLowerCase();

  // Direct match in profiles map
  for (const [key, profile] of Object.entries(MOCK_PROFILES_MAP)) {
    if (key.toLowerCase() === cleanId || profile.employee_code.toLowerCase() === cleanId) {
      return profile;
    }
  }

  // If ID matches an item from employee list, generate matching profile
  const foundInList = MOCK_EMPLOYEES_LIST.find(
    (e) => e.id.toLowerCase() === cleanId || e.employee_code.toLowerCase() === cleanId
  );
  if (foundInList) {
    const names = foundInList.full_name.split(' ');
    const profile: EmployeeProfile = {
      id: foundInList.id,
      employee_code: foundInList.employee_code,
      first_name: names[0] || 'Employee',
      last_name: names.slice(1).join(' ') || '',
      full_name: foundInList.full_name,
      email: foundInList.email,
      phone: foundInList.phone,
      avatar_url: `https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80`,
      designation: foundInList.designation,
      department: foundInList.department,
      location: foundInList.location,
      status: foundInList.status,
      hire_date: foundInList.join_date,
      date_of_birth: '15 Jan 1990',
      blood_group: 'B+',
      home_address: `Building 10, Technology City, ${foundInList.location}`,
      reporting_manager: {
        name: 'Priya Sharma',
        designation: 'Director of Engineering',
        avatar_url: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80',
      },
      attendance_ytd: {
        percentage: 94,
        leave_balance: 15,
        sick_taken: 2,
      },
      skills: [
        { id: '1', name: foundInList.department, colorTheme: 'default' },
        { id: '2', name: foundInList.designation, colorTheme: 'default' },
        { id: '3', name: 'Enterprise ERP', colorTheme: 'default' },
      ],
      upcoming_review: {
        description: 'Quarterly milestone review.',
        scheduled_date: '15 Dec 2023',
      },
    };
    MOCK_PROFILES_MAP[foundInList.id] = profile;
    return profile;
  }

  // Return null if employee ID does not exist
  return null;
}
