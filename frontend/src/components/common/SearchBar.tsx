import React, { useEffect, useRef } from 'react';
import { Search } from 'lucide-react';

interface SearchBarProps {
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  onSearch?: (query: string) => void;
  className?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChange,
  placeholder = 'Search anything (Cmd+K)',
  onSearch,
  className = '',
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && onSearch && inputRef.current) {
      onSearch(inputRef.current.value);
    }
  };

  return (
    <div className={`relative flex items-center w-full max-w-sm ${className}`}>
      <Search className="absolute left-3 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={onChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="w-full pl-8 pr-9 py-1.5 text-xs sm:text-[13px] bg-slate-100/70 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800/90 text-slate-900 dark:text-white placeholder-slate-400 rounded-lg border border-slate-200/60 dark:border-slate-700/60 focus:border-brand-500 focus:bg-white dark:focus:bg-slate-900 focus:outline-none transition-all"
      />
      <div className="absolute right-2.5 hidden sm:flex items-center pointer-events-none">
        <kbd className="px-1.5 py-0.5 text-[10px] font-medium font-mono text-slate-400 bg-white dark:bg-slate-700/80 border border-slate-200/80 dark:border-slate-600 rounded">
          ⌘K
        </kbd>
      </div>
    </div>
  );
};
