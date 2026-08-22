import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalEntries: number;
  pageSize?: number;
  onPageChange: (page: number) => void;
  className?: string;
}

export const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  totalEntries,
  pageSize = 10,
  onPageChange,
  className = '',
}) => {
  const startItem = totalEntries === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalEntries);

  const renderPageNumbers = () => {
    const pages: (number | string)[] = [];

    if (totalPages <= 5) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      if (currentPage <= 3) {
        pages.push(1, 2, 3, '...', totalPages);
      } else if (currentPage >= totalPages - 2) {
        pages.push(1, '...', totalPages - 2, totalPages - 1, totalPages);
      } else {
        pages.push(1, '...', currentPage, '...', totalPages);
      }
    }

    return pages.map((page, index) => {
      if (typeof page === 'string') {
        return (
          <span
            key={`ellipsis-${index}`}
            className="px-2 py-1 text-xs text-slate-400 select-none"
          >
            ...
          </span>
        );
      }

      const isActive = page === currentPage;

      return (
        <button
          key={page}
          onClick={() => onPageChange(page)}
          className={`min-w-[28px] h-7 px-2 flex items-center justify-center rounded-md text-xs font-semibold transition-colors cursor-pointer ${
            isActive
              ? 'bg-brand-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
          aria-current={isActive ? 'page' : undefined}
        >
          {page}
        </button>
      );
    });
  };

  return (
    <div
      className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 text-xs text-slate-500 dark:text-slate-400 ${className}`}
    >
      <div>
        Showing{' '}
        <span className="font-semibold text-slate-900 dark:text-white">
          {startItem} to {endItem}
        </span>{' '}
        of{' '}
        <span className="font-semibold text-slate-900 dark:text-white">
          {totalEntries.toLocaleString()}
        </span>{' '}
        entries
      </div>

      <div className="flex items-center gap-1 self-end sm:self-auto">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className="p-1 rounded-md text-slate-500 hover:text-slate-900 dark:hover:text-white disabled:opacity-40 disabled:pointer-events-none hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          aria-label="Previous Page"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-1">{renderPageNumbers()}</div>

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className="p-1 rounded-md text-slate-500 hover:text-slate-900 dark:hover:text-white disabled:opacity-40 disabled:pointer-events-none hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          aria-label="Next Page"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
