export interface SkillItem {
  id: string;
  name: string;
  isCertified?: boolean;
  colorTheme?: 'default' | 'blue';
}

export interface EmployeeDocument {
  id: string;
  title: string;
  category: string;
  file_name: string;
  file_size: string;
  upload_date: string;
  verified: boolean;
}

export interface EmployeeProfile {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  phone: string;
  avatar_url?: string;
  designation: string;
  department: string;
  location: string;
  status: 'Active' | 'Pending' | 'On Leave' | 'Terminated';
  hire_date: string;
  date_of_birth: string;
  blood_group: string;
  home_address: string;
  reporting_manager: {
    name: string;
    designation: string;
    avatar_url?: string;
  };
  attendance_ytd: {
    percentage: number;
    leave_balance: number;
    sick_taken: number;
  };
  skills: SkillItem[];
  upcoming_review: {
    description: string;
    scheduled_date: string;
  };
}

export interface EmployeeListItem {
  id: string;
  employee_code: string;
  full_name: string;
  email: string;
  phone: string;
  department: string;
  designation: string;
  status: 'Active' | 'Pending' | 'On Leave' | 'Terminated';
  join_date: string;
  location: string;
  avatar_url?: string;
}
