import React from 'react';
import EmptyState from '../EmptyState';
import Pagination from './Pagination';

export default function DataTable({
  columns = null, // array of { key, accessor, label, header, render, align, width, minWidth, style, cellStyle }
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
            {Array.isArray(columns) && columns.length > 0 && (
              <thead>
                <tr>
                  {columns.map((col, cIdx) => {
                    const colKey = col.key || col.accessor || col.id || col.label || col.header || cIdx;
                    const colHeader = col.label ?? col.header ?? col.title ?? '';
                    return (
                      <th
                        key={colKey}
                        style={{
                          textAlign: col.align || 'left',
                          width: col.width || 'auto',
                          minWidth: col.minWidth || 'auto',
                          ...col.style
                        }}
                      >
                        {colHeader}
                      </th>
                    );
                  })}
                </tr>
              </thead>
            )}
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={Array.isArray(columns) && columns.length > 0 ? columns.length : 1} style={{ textAlign: 'center', padding: '3rem 1rem' }}>
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
              ) : !Array.isArray(data) || data.length === 0 ? (
                <tr>
                  <td colSpan={Array.isArray(columns) && columns.length > 0 ? columns.length : 1} style={{ padding: '2rem 1rem' }}>
                    <EmptyState title={emptyTitle} message={emptyMessage} actionButton={emptyAction} />
                  </td>
                </tr>
              ) : (
                data.map((row, idx) => {
                  if (!row || typeof row !== 'object') {
                    return null;
                  }
                  const rowKey = row.id || row.key || row.code || row.serviceCode || row.packageCode || idx;

                  return (
                    <tr key={rowKey}>
                      {columns.map((col, cIdx) => {
                        const key = col.key || col.accessor;
                        const colKey = key || col.id || col.label || col.header || cIdx;
                        const cellValue = key ? row[key] : undefined;

                        let cellContent;
                        if (typeof col.render === 'function') {
                          // Standard contract: col.render(cellValue, row, idx)
                          // Also resilient to legacy columns where render expects (row, idx)
                          try {
                            if (!key || key === 'actions' || (key === 'id' && (col.header === 'Actions' || col.label === 'Actions'))) {
                              cellContent = col.render(cellValue, row, idx);
                              // If render returned undefined because it accessed properties on cellValue instead of row
                              if (cellContent === undefined) {
                                cellContent = col.render(row, row, idx);
                              }
                            } else {
                              cellContent = col.render(cellValue, row, idx);
                              if (cellContent === undefined && row && typeof cellValue !== 'object') {
                                // If render expected full row object instead of cellValue
                                const retryContent = col.render(row, row, idx);
                                if (retryContent !== undefined) {
                                  cellContent = retryContent;
                                }
                              }
                            }
                          } catch (renderError) {
                            try {
                              cellContent = col.render(row, row, idx);
                            } catch {
                              cellContent = cellValue ?? '—';
                            }
                          }
                        } else {
                          cellContent = cellValue ?? '—';
                        }

                        return (
                          <td
                            key={colKey}
                            style={{
                              textAlign: col.align || 'left',
                              ...col.cellStyle
                            }}
                          >
                            {cellContent ?? '—'}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })
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
