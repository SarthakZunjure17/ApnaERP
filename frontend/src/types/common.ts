export type NavSection =
  | 'OVERVIEW'
  | 'WORKFORCE'
  | 'INVENTORY'
  | 'PROCUREMENT'
  | 'SALES'
  | 'CRM'
  | 'FINANCE'
  | 'REPORTS'
  | 'PLATFORM';

export interface NavItem {
  name: string;
  href: string;
  icon: string;
  badge?: string | number;
  section: NavSection;
  isImplemented?: boolean;
}

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastMessage {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}
