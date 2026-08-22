import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  CalendarCheck,
  CreditCard,
  Package,
  Layers,
  UserCheck,
  FileText,
  Landmark,
  BarChart3,
  X,
  Boxes,
} from 'lucide-react';
import { NavItem, NavSection } from '../../types/common';

const NAV_ITEMS: NavItem[] = [
  // OVERVIEW
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: 'LayoutDashboard',
    section: 'OVERVIEW',
    isImplemented: true,
  },
  // WORKFORCE
  {
    name: 'Employees',
    href: '/workforce/employees',
    icon: 'Users',
    section: 'WORKFORCE',
    isImplemented: true,
  },
  {
    name: 'Attendance',
    href: '/workforce/attendance',
    icon: 'CalendarCheck',
    section: 'WORKFORCE',
    isImplemented: true,
  },
  {
    name: 'Payroll',
    href: '/workforce/payroll',
    icon: 'CreditCard',
    section: 'WORKFORCE',
    isImplemented: true,
  },
  // INVENTORY
  {
    name: 'Products',
    href: '/inventory/products',
    icon: 'Package',
    section: 'INVENTORY',
    isImplemented: true,
  },
  {
    name: 'Stock Control',
    href: '/inventory/stock',
    icon: 'Layers',
    section: 'INVENTORY',
    isImplemented: true,
  },
  // SALES & CRM
  {
    name: 'Customers',
    href: '/sales/customers',
    icon: 'UserCheck',
    section: 'SALES & CRM',
    isImplemented: false,
  },
  {
    name: 'Sales Orders',
    href: '/sales/orders',
    icon: 'FileText',
    section: 'SALES & CRM',
    isImplemented: false,
  },
  // FINANCE
  {
    name: 'Accounts',
    href: '/finance/accounts',
    icon: 'Landmark',
    section: 'FINANCE',
    isImplemented: false,
  },
  {
    name: 'Reports',
    href: '/finance/reports',
    icon: 'BarChart3',
    section: 'FINANCE',
    isImplemented: false,
  },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const location = useLocation();

  const renderIcon = (iconName: string, isActive: boolean) => {
    const iconClass = `w-4 h-4 shrink-0 transition-colors ${
      isActive ? 'text-white' : 'text-slate-500 group-hover:text-slate-800 dark:text-slate-400 dark:group-hover:text-slate-200'
    }`;

    switch (iconName) {
      case 'LayoutDashboard':
        return <LayoutDashboard className={iconClass} />;
      case 'Users':
        return <Users className={iconClass} />;
      case 'CalendarCheck':
        return <CalendarCheck className={iconClass} />;
      case 'CreditCard':
        return <CreditCard className={iconClass} />;
      case 'Package':
        return <Package className={iconClass} />;
      case 'Layers':
        return <Layers className={iconClass} />;
      case 'UserCheck':
        return <UserCheck className={iconClass} />;
      case 'FileText':
        return <FileText className={iconClass} />;
      case 'Landmark':
        return <Landmark className={iconClass} />;
      case 'BarChart3':
        return <BarChart3 className={iconClass} />;
      default:
        return <LayoutDashboard className={iconClass} />;
    }
  };

  const sections: NavSection[] = ['OVERVIEW', 'WORKFORCE', 'INVENTORY', 'SALES & CRM', 'FINANCE'];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-xs lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar container - 224px (w-56) compact width */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-56 bg-white dark:bg-slate-900 border-r border-slate-200/70 dark:border-slate-800 flex flex-col transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header - 56px (h-14) */}
        <div className="h-14 px-4 flex items-center justify-between border-b border-slate-100 dark:border-slate-800">
          <NavLink to="/dashboard" className="flex items-center gap-2.5 group">
            <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center text-white shadow-xs shadow-brand-500/20 group-hover:scale-105 transition-transform">
              <Boxes className="w-4 h-4" />
            </div>
            <div className="flex flex-col">
              <span className="text-[15px] font-bold text-slate-900 dark:text-white tracking-tight leading-none">
                Apna<span className="text-brand-600">ERP</span>
              </span>
              <span className="text-[9px] text-slate-400 font-semibold tracking-wider uppercase mt-0.5">
                Enterprise
              </span>
            </div>
          </NavLink>

          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation items scrollable */}
        <div className="flex-1 overflow-y-auto px-2.5 py-3 space-y-4">
          {sections.map((section) => {
            const items = NAV_ITEMS.filter((item) => item.section === section);
            return (
              <div key={section}>
                <div className="px-2.5 mb-1 text-[10px] font-bold text-slate-400/90 dark:text-slate-500 uppercase tracking-wider">
                  {section}
                </div>
                <nav className="space-y-0.5">
                  {items.map((item) => {
                    const isActive =
                      location.pathname === item.href ||
                      (item.href !== '/dashboard' && location.pathname.startsWith(item.href));

                    return (
                      <NavLink
                        key={item.href}
                        to={item.href}
                        onClick={() => {
                          if (window.innerWidth < 1024) onClose();
                        }}
                        className={`group flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-all duration-150 ${
                          isActive
                            ? 'bg-brand-600 text-white font-semibold shadow-xs'
                            : 'text-slate-600 dark:text-slate-400 font-medium hover:bg-slate-100/70 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-200'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          {renderIcon(item.icon, isActive)}
                          <span className="tracking-tight">{item.name}</span>
                        </div>

                        {item.badge && (
                          <span
                            className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                              isActive
                                ? 'bg-white/20 text-white'
                                : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                            }`}
                          >
                            {item.badge}
                          </span>
                        )}
                      </NavLink>
                    );
                  })}
                </nav>
              </div>
            );
          })}
        </div>

        {/* Bottom Footer Info */}
        <div className="p-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
          <span className="font-medium text-slate-400">v0.2.0</span>
          <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium text-[10px]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            System Live
          </span>
        </div>
      </aside>
    </>
  );
};
