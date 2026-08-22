import React, { useState, useRef, useEffect } from 'react';
import {
  Menu,
  HelpCircle,
  Bell,
  Sun,
  Moon,
  LogOut,
  User as UserIcon,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';
import { SearchBar } from '../common/SearchBar';
import { Avatar } from '../common/Avatar';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { useToast } from '../../context/ToastContext';
import { Modal } from '../common/Modal';

interface TopbarProps {
  onToggleSidebar: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ onToggleSidebar }) => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { info, success } = useToast();

  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const profileRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setIsProfileOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setIsNotificationsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = (query: string) => {
    if (!query.trim()) return;
    info('Global Search', `Searching for "${query}" across modules...`);
  };

  const handleLogout = async () => {
    await logout();
    success('Logged Out', 'You have been safely signed out.');
  };

  return (
    <>
      <header className="sticky top-0 z-30 h-14 bg-white/95 dark:bg-slate-900/95 backdrop-blur-xs border-b border-slate-200/70 dark:border-slate-800 px-4 sm:px-6 flex items-center justify-between gap-4">
        {/* Left side: Hamburger on mobile + Global Search */}
        <div className="flex items-center gap-2.5 flex-1 max-w-md">
          <button
            onClick={onToggleSidebar}
            className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden transition-colors"
            aria-label="Toggle Navigation"
          >
            <Menu className="w-4 h-4" />
          </button>

          <SearchBar
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onSearch={handleSearch}
            placeholder="Search anything (Cmd+K)"
          />
        </div>

        {/* Right side: Actions & User Info */}
        <div className="flex items-center gap-1 sm:gap-1.5">
          {/* Help Button */}
          <button
            onClick={() => setIsHelpModalOpen(true)}
            className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title="Help & Documentation"
            aria-label="Help"
          >
            <HelpCircle className="w-4 h-4" />
          </button>

          {/* Notifications Dropdown */}
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => setIsNotificationsOpen((prev) => !prev)}
              className="relative p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Notifications"
              aria-label="Notifications"
            >
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-brand-600 ring-2 ring-white dark:ring-slate-900" />
            </button>

            {isNotificationsOpen && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-slate-900 rounded-xl shadow-lg border border-slate-200 dark:border-slate-800 p-4 z-50 animate-fade-in">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                    Notifications
                  </h4>
                  <span className="text-[11px] font-semibold text-brand-600 cursor-pointer hover:underline">
                    Mark all read
                  </span>
                </div>
                <div className="divide-y divide-slate-100 dark:divide-slate-800 max-h-72 overflow-y-auto mt-2">
                  <div className="py-2.5 flex items-start gap-3">
                    <div className="w-2 h-2 mt-1.5 rounded-full bg-brand-600 shrink-0" />
                    <div>
                      <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                        Purchase Order PO-2023-089 Pending
                      </p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        Office Supplies order ($1,240) requires your approval.
                      </p>
                      <span className="text-[10px] text-slate-400 mt-1 block">10m ago</span>
                    </div>
                  </div>
                  <div className="py-2.5 flex items-start gap-3">
                    <div className="w-2 h-2 mt-1.5 rounded-full bg-amber-500 shrink-0" />
                    <div>
                      <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                        Low Stock Alert: SKU A-102
                      </p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        Inventory balance below safety threshold.
                      </p>
                      <span className="text-[10px] text-slate-400 mt-1 block">1h ago</span>
                    </div>
                  </div>
                  <div className="py-2.5 flex items-start gap-3">
                    <div className="w-2 h-2 mt-1.5 rounded-full bg-slate-300 dark:bg-slate-600 shrink-0" />
                    <div>
                      <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                        Automated Daily Backup Complete
                      </p>
                      <span className="text-[10px] text-slate-400 mt-1 block">2h ago</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
            aria-label="Toggle Theme"
          >
            {theme === 'light' ? (
              <Moon className="w-4 h-4" />
            ) : (
              <Sun className="w-4 h-4" />
            )}
          </button>

          {/* Subtle Vertical Divider */}
          <div className="h-5 w-px bg-slate-200/80 dark:bg-slate-800 mx-1 hidden sm:block" />

          {/* User Profile Pill & Dropdown */}
          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setIsProfileOpen((prev) => !prev)}
              className="flex items-center gap-2.5 p-1 rounded-lg hover:bg-slate-100/70 dark:hover:bg-slate-800 transition-colors group cursor-pointer"
            >
              {/* Text Info */}
              <div className="text-right hidden sm:flex flex-col">
                <span className="text-xs font-semibold text-slate-900 dark:text-white leading-tight">
                  {user?.full_name || 'ERP Admin'}
                </span>
                <span className="text-[10px] text-slate-400 dark:text-slate-500 leading-tight mt-0.5">
                  {user?.designation || 'System Overlord'}
                </span>
              </div>

              {/* Blue Avatar circle */}
              <Avatar name={user?.full_name || 'ERP Admin'} size="sm" />
            </button>

            {/* Profile Dropdown */}
            {isProfileOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-900 rounded-xl shadow-lg border border-slate-200 dark:border-slate-800 p-2 z-50 animate-fade-in">
                <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-800 mb-1">
                  <p className="text-xs font-bold text-slate-900 dark:text-white truncate">
                    {user?.full_name || 'ERP Admin'}
                  </p>
                  <p className="text-[11px] text-slate-500 truncate">
                    {user?.email || 'admin@apnaerp.com'}
                  </p>
                  <span className="mt-1 inline-block text-[10px] font-semibold text-brand-600 bg-brand-50 dark:bg-brand-950/60 px-2 py-0.5 rounded">
                    {user?.roles?.[0] || 'SuperAdmin'}
                  </span>
                </div>

                <div className="space-y-0.5">
                  <div className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer">
                    <UserIcon className="w-4 h-4 text-slate-400" />
                    <span>My Profile</span>
                  </div>
                  <div className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer">
                    <CheckCircle2 className="w-4 h-4 text-slate-400" />
                    <span>Account Security</span>
                  </div>
                </div>

                <div className="pt-1 mt-1 border-t border-slate-100 dark:border-slate-800">
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold text-rose-600 dark:text-rose-400 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors text-left cursor-pointer"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Help Modal */}
      <Modal
        isOpen={isHelpModalOpen}
        onClose={() => setIsHelpModalOpen(false)}
        title="ApnaERP Help & Reference"
      >
        <div className="space-y-4 text-sm text-slate-600 dark:text-slate-300">
          <div>
            <h5 className="font-semibold text-slate-900 dark:text-white mb-1">
              Global Shortcuts
            </h5>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span>Focus Global Search</span>
                <kbd className="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 rounded font-mono text-[11px]">
                  Cmd + K / Ctrl + K
                </kbd>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span>Close Modals / Popups</span>
                <kbd className="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 rounded font-mono text-[11px]">
                  ESC
                </kbd>
              </div>
            </div>
          </div>

          <div>
            <h5 className="font-semibold text-slate-900 dark:text-white mb-1">
              Architecture & API Status
            </h5>
            <p className="text-xs text-slate-500">
              ApnaERP v0.2.0 is connected to the production FastAPI backend. All modules use standardized JWT Bearer token authentication and structured REST APIs.
            </p>
          </div>

          <div className="pt-2 flex justify-end">
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-600 hover:text-brand-700"
            >
              Open Backend API Docs (Swagger)
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </Modal>
    </>
  );
};
