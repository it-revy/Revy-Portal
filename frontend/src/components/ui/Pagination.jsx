import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import Button from './Button';

export default function Pagination({
  currentPage = 1,
  totalPages = 1,
  totalCount = null,
  pageSize = 20,
  onPageChange,
  className = '',
  style = {}
}) {
  const startItem = totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endItem = totalCount !== null ? Math.min(currentPage * pageSize, totalCount) : currentPage * pageSize;

  return (
    <div className={`revy-pagination ${className}`.trim()} style={style}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        {totalCount !== null ? (
          <span>
            Showing <strong>{startItem}</strong>–<strong>{endItem}</strong> of <strong>{totalCount}</strong> records
          </span>
        ) : (
          <span>
            Page <strong>{currentPage}</strong> of <strong>{Math.max(1, totalPages)}</strong>
          </span>
        )}
      </div>

      <div className="revy-pagination-actions">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          icon={ChevronLeft}
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
          aria-label="Previous page"
        >
          Previous
        </Button>

        <span style={{ padding: '0 8px', fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>
          {currentPage} / {Math.max(1, totalPages)}
        </span>

        <Button
          type="button"
          variant="secondary"
          size="sm"
          icon={ChevronRight}
          iconPosition="right"
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(currentPage + 1)}
          aria-label="Next page"
        >
          Next
        </Button>
      </div>
    </div>
  );
}
