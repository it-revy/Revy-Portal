import React from 'react';
import EmptyState from '../EmptyState';
import Pagination from './Pagination';

export default function DataTable({
  columns = null, // array of { key, label, render, align, width, style }
  data = null,    // array of items
  loading = false,
  emptyTitle = 'No data available',
  emptyMessage = 'There are no records matching your current filter criteria.',
  emptyAction = null,
  pagination = null, // { currentPage, totalPages, totalCount, pageSize, onPageChange }
  children,
  className = '',
  style = {}
}) {
  return (
    <div style={{ width: '100%', marginBottom: 'var(--space-4)', ...style }}>
      <div className={`revy-table-container ${className}`.trim()}>
        {children ? (
          children
        ) : (
          <table className="revy-table">
            {columns && (
              <thead>
                <tr>
                  {columns.map(col => (
                    <th
                      key={col.key || col.label}
                      style={{
                        textAlign: col.align || 'left',
                        width: col.width || 'auto',
                        minWidth: col.minWidth || 'auto',
                        ...col.style
                      }}
                    >
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={columns ? columns.length : 1} style={{ textAlign: 'center', padding: '3rem 1rem' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.75rem', color: 'var(--color-text-secondary)' }}>
                      <span
                        style={{
                          width: '20px',
                          height: '20px',
                          border: '2px solid var(--color-border)',
                          borderTopColor: 'var(--color-primary)',
                          borderRadius: '50%',
                          animation: 'revySpin 0.8s linear infinite'
                        }}
                      />
                      <span>Loading records...</span>
                    </div>
                  </td>
                </tr>
              ) : !data || data.length === 0 ? (
                <tr>
                  <td colSpan={columns ? columns.length : 1} style={{ padding: '2rem 1rem' }}>
                    <EmptyState title={emptyTitle} message={emptyMessage} actionButton={emptyAction} />
                  </td>
                </tr>
              ) : (
                data.map((row, idx) => (
                  <tr key={row.id || row.key || idx}>
                    {columns.map(col => (
                      <td
                        key={col.key || col.label}
                        style={{
                          textAlign: col.align || 'left',
                          ...col.cellStyle
                        }}
                      >
                        {col.render ? col.render(row[col.key], row, idx) : row[col.key]}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>

      {pagination && (
        <Pagination
          currentPage={pagination.currentPage}
          totalPages={pagination.totalPages}
          totalCount={pagination.totalCount}
          pageSize={pagination.pageSize}
          onPageChange={pagination.onPageChange}
        />
      )}
    </div>
  );
}
