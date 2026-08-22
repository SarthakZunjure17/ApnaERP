import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

export const AppShell: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#f8fafc] dark:bg-slate-950 flex flex-col font-sans transition-colors">
      {/* Reusable Collapsible Navigation Sidebar (224px compact width) */}
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

      {/* Main Content Area with Desktop Sidebar Offset */}
      <div className="lg:pl-56 flex flex-col min-h-screen">
        {/* Reusable Enterprise Topbar (56px compact height) */}
        <Topbar onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)} />

        {/* Page Content Outlet with compact padding */}
        <main className="flex-1 p-4 sm:p-5 md:p-6 max-w-[1400px] w-full mx-auto animate-fade-in">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
