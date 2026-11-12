import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '../../../context/AuthContext';
import {
  Folder,
  Plus,
  Edit2,
  Trash2,
  Power,
  CheckCircle2,
  XCircle,
  Filter,
  X
} from 'lucide-react';
import catalogueService from '../../../services/catalogueService';
import {
  PageHeader,
  Card,
  Button,
  StatusBadge,
  FormField,
  SearchInput,
  LoadingState,
  Modal,
  ConfirmationDialog
} from '../../../components/ui';

export default function CategoriesPage() {
  const { hasRole } = useAuth();
  const isAdmin = hasRole('CRM_ADMIN') || hasRole('IT_ADMIN') || hasRole('DIRECTOR');

  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Filters (strictly separated state to prevent type errors)
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Main Category Modal State
  const [categoryModalOpen, setCategoryModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [categoryFormData, setCategoryFormData] = useState({
    code: '',
    name: '',
    description: '',
    isActive: true
  });

  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState(null);

  // Confirmation dialog
  const [confirmDialog, setConfirmDialog] = useState({
    isOpen: false,
    title: '',
    message: '',
    confirmVariant: 'danger',
    confirmText: 'Confirm',
    onConfirm: null
  });

  // Load Main Categories
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await catalogueService.getCategories({ includeInactive: true });
      if (res.data?.success) {
        setCategories(res.data.categories || []);
      } else if (Array.isArray(res.data)) {
        setCategories(res.data);
      }
    } catch (err) {
      console.error('Failed to load categories:', err);
      setError(err.response?.data?.message || 'Failed to load catalogue categories.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const flashSuccess = (msg) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 4000);
  };

  // Safe handler for search input change
  const handleSearchChange = (e) => {
    const value = typeof e === 'string' ? e : (e?.target?.value ?? '');
    setSearchTerm(value);
  };

  const handleClearFilters = () => {
    setSearchTerm('');
    setStatusFilter('ALL');
  };

  // Defensive filtering logic
  const filteredCategories = useMemo(() => {
    const normalizedSearch = String(searchTerm ?? '').trim().toLowerCase();

    return categories.filter(cat => {
      // Status filter
      if (statusFilter === 'ACTIVE' && !cat.isActive) return false;
      if (statusFilter === 'INACTIVE' && cat.isActive) return false;

      // Search filter
      if (normalizedSearch) {
        const code = String(cat.code ?? '').toLowerCase();
        const name = String(cat.name ?? '').toLowerCase();
        const desc = String(cat.description ?? '').toLowerCase();
        const matches = code.includes(normalizedSearch) ||
                        name.includes(normalizedSearch) ||
                        desc.includes(normalizedSearch);
        if (!matches) return false;
      }

      return true;
    });
  }, [categories, searchTerm, statusFilter]);

  // Modal Handlers
  const handleOpenCategoryModal = (cat = null) => {
    setEditingCategory(cat);
    if (cat) {
      setCategoryFormData({
        code: cat.code || '',
        name: cat.name || '',
        description: cat.description || '',
        isActive: cat.isActive !== false
      });
    } else {
      setCategoryFormData({
        code: '',
        name: '',
        description: '',
        isActive: true
      });
    }
    setModalError(null);
    setCategoryModalOpen(true);
  };

  const handleSaveCategory = async (e) => {
    if (e && e.preventDefault) e.preventDefault();

    if (!categoryFormData.code.trim() || !categoryFormData.name.trim()) {
      setModalError('Category code and name are required.');
      return;
    }

    setSubmitting(true);
    setModalError(null);

    try {
      if (editingCategory) {
        await catalogueService.updateCategory(editingCategory.id, {
          name: categoryFormData.name.trim(),
          description: categoryFormData.description.trim() || null,
          isActive: categoryFormData.isActive
        });
        flashSuccess(`Category "${categoryFormData.name}" updated successfully.`);
      } else {
        await catalogueService.createCategory({
          code: categoryFormData.code.trim().toUpperCase(),
          name: categoryFormData.name.trim(),
          description: categoryFormData.description.trim() || null,
          isActive: categoryFormData.isActive
        });
        flashSuccess(`Category "${categoryFormData.name}" created successfully.`);
      }
      setCategoryModalOpen(false);
      fetchData();
    } catch (err) {
      setModalError(err.response?.data?.message || err.response?.data?.detail || 'Failed to save category.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleCategoryActive = (cat) => {
    const nextStatus = !cat.isActive;
    const actionName = nextStatus ? 'activate' : 'deactivate';
    setConfirmDialog({
      isOpen: true,
      title: `${nextStatus ? 'Activate' : 'Deactivate'} Category`,
      message: `Are you sure you want to ${actionName} "${cat.name}" (${cat.code})? Inactive categories cannot be selected when creating new laboratory services.`,
      confirmVariant: nextStatus ? 'primary' : 'warning',
      confirmText: nextStatus ? 'Activate' : 'Deactivate',
      onConfirm: async () => {
        setConfirmDialog(prev => ({ ...prev, isOpen: false }));
        try {
          await catalogueService.updateCategory(cat.id, { isActive: nextStatus });
          flashSuccess(`Category "${cat.name}" is now ${nextStatus ? 'Active' : 'Inactive'}.`);
          fetchData();
        } catch (err) {
          alert(err.response?.data?.message || err.response?.data?.detail || 'Failed to update category status.');
        }
      }
    });
  };

  const handleDeleteCategory = (cat) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Soft-Delete Category',
      message: `Are you sure you want to soft-delete Category "${cat.name}" (${cat.code})? Note: Categories with active laboratory services cannot be deleted.`,
      confirmVariant: 'danger',
      confirmText: 'Delete Category',
      onConfirm: async () => {
        setConfirmDialog(prev => ({ ...prev, isOpen: false }));
        try {
          await catalogueService.deleteCategory(cat.id);
          flashSuccess(`Category "${cat.name}" soft-deleted.`);
          fetchData();
        } catch (err) {
          alert(err.response?.data?.message || err.response?.data?.detail || 'Failed to delete category.');
        }
      }
    });
  };

  const hasActiveFilters = searchTerm !== '' || statusFilter !== 'ALL';

  return (
    <div className="page-body">
      <PageHeader
        title="Service Categories"
        subtitle="Manage laboratory service categories. Direct hierarchy: Main Category → Services."
        breadcrumbs={[
          { label: 'CRM', to: '/crm/dashboard' },
          { label: 'Catalogue', to: '/crm/catalogue/services' },
          { label: 'Categories' }
        ]}
        actions={
          isAdmin && (
            <Button
              variant="primary"
              icon={Plus}
              onClick={() => handleOpenCategoryModal(null)}
            >
              Add Category
            </Button>
          )
        }
      />

      {successMsg && (
        <div style={{
          padding: '0.75rem 1rem',
          background: '#ecfdf5',
          border: '1px solid #a7f3d0',
          color: '#065f46',
          borderRadius: 'var(--radius-md)',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.9rem'
        }}>
          <CheckCircle2 size={18} />
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div style={{
          padding: '0.75rem 1rem',
          background: '#fef2f2',
          border: '1px solid #fecaca',
          color: '#991b1b',
          borderRadius: 'var(--radius-md)',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.9rem'
        }}>
          <XCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Main Categories Standard Data Table Card */}
      <Card>
        {/* Compact Filter Toolbar */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
          marginBottom: '1rem',
          paddingBottom: '0.75rem',
          borderBottom: '1px solid var(--border-color)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <div style={{ width: '260px' }}>
              <SearchInput
                value={searchTerm}
                onChange={handleSearchChange}
                onClear={() => setSearchTerm('')}
                placeholder="Search category code or name..."
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Status:</span>
              <select
                className="crm-select"
                style={{ height: '36px', minWidth: '130px', fontSize: '0.85rem' }}
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
              >
                <option value="ALL">All Status</option>
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
              </select>
            </div>

            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                icon={X}
                onClick={handleClearFilters}
              >
                Clear
              </Button>
            )}
          </div>

          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Showing <strong>{filteredCategories.length}</strong> of {categories.length} categories
          </div>
        </div>

        {loading ? (
          <LoadingState message="Loading categories..." />
        ) : filteredCategories.length === 0 ? (
          <div style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Folder size={36} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
            <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>No Categories Found</div>
            <div style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
              {hasActiveFilters ? 'Try adjusting your search or status filter.' : 'Click "Add Category" above to create your first category.'}
            </div>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="crm-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left', background: 'var(--bg-secondary)' }}>
                  <th style={{ padding: '10px 12px', width: '120px' }}>Code</th>
                  <th style={{ padding: '10px 12px', width: '280px' }}>Category Name</th>
                  <th style={{ padding: '10px 12px', width: '120px', textAlign: 'center' }}>Service Count</th>
                  <th style={{ padding: '10px 12px' }}>Description</th>
                  <th style={{ padding: '10px 12px', width: '100px', textAlign: 'center' }}>Status</th>
                  {isAdmin && <th style={{ padding: '10px 12px', width: '120px', textAlign: 'right' }}>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {filteredCategories.map(cat => (
                  <tr key={cat.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {cat.code}
                    </td>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {cat.name}
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                      <span className="badge badge-neutral" style={{ fontSize: '0.8rem', fontWeight: 700, padding: '2px 8px' }}>
                        {cat.serviceCount ?? cat.activeServicesCount ?? 0}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontSize: '0.825rem' }}>
                      {cat.description || '—'}
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                      <StatusBadge status={cat.isActive ? 'Active' : 'Inactive'} />
                    </td>
                    {isAdmin && (
                      <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '0.35rem' }}>
                          <button
                            type="button"
                            className="btn-icon"
                            title="Edit Category"
                            onClick={() => handleOpenCategoryModal(cat)}
                            style={{ padding: '4px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}
                          >
                            <Edit2 size={15} />
                          </button>
                          <button
                            type="button"
                            className="btn-icon"
                            title={cat.isActive ? 'Deactivate Category' : 'Activate Category'}
                            onClick={() => handleToggleCategoryActive(cat)}
                            style={{ padding: '4px', background: 'none', border: 'none', cursor: 'pointer', color: cat.isActive ? '#059669' : '#dc2626' }}
                          >
                            <Power size={15} />
                          </button>
                          <button
                            type="button"
                            className="btn-icon"
                            title="Delete Category"
                            onClick={() => handleDeleteCategory(cat)}
                            style={{ padding: '4px', background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626' }}
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Main Category Create / Edit Modal */}
      <Modal
        isOpen={categoryModalOpen}
        onClose={() => setCategoryModalOpen(false)}
        title={editingCategory ? `Edit Category (${editingCategory.code})` : 'Add Category'}
        subtitle={editingCategory ? 'Update category details and status' : 'Create a new laboratory service category'}
        maxWidth="500px"
        footer={
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', width: '100%' }}>
            <Button variant="secondary" type="button" onClick={() => setCategoryModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="button" disabled={submitting} onClick={handleSaveCategory}>
              {submitting ? 'Saving...' : (editingCategory ? 'Save Changes' : 'Create Category')}
            </Button>
          </div>
        }
      >
        <form onSubmit={handleSaveCategory} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {modalError && (
            <div style={{ padding: '0.65rem 0.85rem', background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', borderRadius: '4px', fontSize: '0.85rem' }}>
              {modalError}
            </div>
          )}

          <FormField label="Category Code" required hint="Unique category identifier (e.g. LAB-01)">
            <input
              type="text"
              className="crm-input"
              value={categoryFormData.code}
              onChange={e => setCategoryFormData(prev => ({ ...prev, code: e.target.value.toUpperCase() }))}
              disabled={!!editingCategory}
              placeholder="e.g. LAB-06"
              required
            />
          </FormField>

          <FormField label="Category Name" required>
            <input
              type="text"
              className="crm-input"
              value={categoryFormData.name}
              onChange={e => setCategoryFormData(prev => ({ ...prev, name: e.target.value }))}
              placeholder="e.g. Advanced Membrane Technology"
              required
            />
          </FormField>

          <FormField label="Description">
            <textarea
              className="crm-textarea"
              rows={3}
              value={categoryFormData.description}
              onChange={e => setCategoryFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Brief description of laboratory analysis category..."
            />
          </FormField>

          {editingCategory && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
              <input
                type="checkbox"
                id="catIsActive"
                checked={categoryFormData.isActive}
                onChange={e => setCategoryFormData(prev => ({ ...prev, isActive: e.target.checked }))}
                style={{ width: '16px', height: '16px', cursor: 'pointer' }}
              />
              <label htmlFor="catIsActive" style={{ fontSize: '0.9rem', color: 'var(--text-primary)', cursor: 'pointer' }}>
                Category is Active (available for new service creation)
              </label>
            </div>
          )}
        </form>
      </Modal>

      {/* Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={confirmDialog.isOpen}
        onClose={() => setConfirmDialog(prev => ({ ...prev, isOpen: false }))}
        onConfirm={confirmDialog.onConfirm}
        title={confirmDialog.title}
        message={confirmDialog.message}
        confirmVariant={confirmDialog.confirmVariant}
        confirmText={confirmDialog.confirmText}
      />
    </div>
  );
}
