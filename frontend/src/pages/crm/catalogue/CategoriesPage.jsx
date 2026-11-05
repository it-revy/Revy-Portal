import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../../context/AuthContext';
import {
  FolderTree,
  Plus,
  Edit2,
  Trash2,
  Power,
  ChevronRight,
  Folder,
  Layers,
  AlertTriangle,
  Info,
  CheckCircle2,
  XCircle,
  HelpCircle
} from 'lucide-react';
import catalogueService from '../../../services/catalogueService';
import {
  PageHeader,
  Card,
  Button,
  DataTable,
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
  const [subcategories, setSubcategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Selected Category filter
  const [selectedCategoryId, setSelectedCategoryId] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  // Modals
  const [categoryModalOpen, setCategoryModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [categoryFormData, setCategoryFormData] = useState({
    code: '',
    name: '',
    description: '',
    displayOrder: 0
  });

  const [subcategoryModalOpen, setSubcategoryModalOpen] = useState(false);
  const [editingSubcategory, setEditingSubcategory] = useState(null);
  const [subcategoryFormData, setSubcategoryFormData] = useState({
    categoryId: '',
    code: '',
    name: '',
    description: '',
    displayOrder: 0
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

  // Load Data
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [catsRes, subcatsRes] = await Promise.all([
        catalogueService.getCategories({ includeInactive: true }),
        catalogueService.getSubcategories({ includeInactive: true })
      ]);

      if (catsRes.data?.success) {
        setCategories(catsRes.data.categories || []);
      }
      if (subcatsRes.data?.success) {
        setSubcategories(subcatsRes.data.subcategories || []);
      }
    } catch (err) {
      console.error('Failed to load categories:', err);
      setError(err.response?.data?.message || 'Failed to load category hierarchy.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Flash messages helper
  const flashSuccess = (msg) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 4000);
  };

  // Main Category Handlers
  const handleOpenCategoryModal = (cat = null) => {
    setEditingCategory(cat);
    if (cat) {
      setCategoryFormData({
        code: cat.code || '',
        name: cat.name || '',
        description: cat.description || '',
        displayOrder: cat.displayOrder || 0
      });
    } else {
      setCategoryFormData({
        code: '',
        name: '',
        description: '',
        displayOrder: categories.length + 1
      });
    }
    setModalError(null);
    setCategoryModalOpen(true);
  };

  const handleSaveCategory = async (e) => {
    e.preventDefault();
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
          displayOrder: Number(categoryFormData.displayOrder) || 0
        });
        flashSuccess(`Main Category "${categoryFormData.name}" updated successfully.`);
      } else {
        await catalogueService.createCategory({
          code: categoryFormData.code.trim().toUpperCase(),
          name: categoryFormData.name.trim(),
          description: categoryFormData.description.trim() || null,
          displayOrder: Number(categoryFormData.displayOrder) || 0
        });
        flashSuccess(`Main Category "${categoryFormData.name}" created successfully.`);
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
      title: `${nextStatus ? 'Activate' : 'Deactivate'} Main Category`,
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
    const subCount = subcategories.filter(s => s.categoryId === cat.id && !s.isDeleted).length;
    if (subCount > 0) {
      setConfirmDialog({
        isOpen: true,
        title: 'Cannot Delete Main Category',
        message: `Cannot delete Main Category "${cat.name}". It contains ${subCount} associated subcategories. Delete or reassign all subcategories before removing this category.`,
        confirmVariant: 'primary',
        confirmText: 'Understood',
        onConfirm: () => setConfirmDialog(prev => ({ ...prev, isOpen: false }))
      });
      return;
    }

    setConfirmDialog({
      isOpen: true,
      title: 'Soft-Delete Main Category',
      message: `Are you sure you want to soft-delete Main Category "${cat.name}" (${cat.code})? This action preserves historical laboratory service records.`,
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

  // Subcategory Handlers
  const handleOpenSubcategoryModal = (subcat = null, defaultCatId = null) => {
    setEditingSubcategory(subcat);
    if (subcat) {
      setSubcategoryFormData({
        categoryId: subcat.categoryId || '',
        code: subcat.code || '',
        name: subcat.name || '',
        description: subcat.description || '',
        displayOrder: subcat.displayOrder || 0
      });
    } else {
      setSubcategoryFormData({
        categoryId: defaultCatId || (selectedCategoryId !== 'ALL' ? selectedCategoryId : (categories[0]?.id || '')),
        code: '',
        name: '',
        description: '',
        displayOrder: 1
      });
    }
    setModalError(null);
    setSubcategoryModalOpen(true);
  };

  const handleSaveSubcategory = async (e) => {
    e.preventDefault();
    if (!subcategoryFormData.categoryId) {
      setModalError('Parent Main Category is required.');
      return;
    }
    if (!subcategoryFormData.code.trim() || !subcategoryFormData.name.trim()) {
      setModalError('Subcategory code and name are required.');
      return;
    }

    setSubmitting(true);
    setModalError(null);

    try {
      if (editingSubcategory) {
        await catalogueService.updateSubcategory(editingSubcategory.id, {
          name: subcategoryFormData.name.trim(),
          description: subcategoryFormData.description.trim() || null,
          displayOrder: Number(subcategoryFormData.displayOrder) || 0
        });
        flashSuccess(`Subcategory "${subcategoryFormData.name}" updated successfully.`);
      } else {
        await catalogueService.createSubcategory({
          categoryId: subcategoryFormData.categoryId,
          code: subcategoryFormData.code.trim().toUpperCase(),
          name: subcategoryFormData.name.trim(),
          description: subcategoryFormData.description.trim() || null,
          displayOrder: Number(subcategoryFormData.displayOrder) || 0
        });
        flashSuccess(`Subcategory "${subcategoryFormData.name}" created successfully.`);
      }
      setSubcategoryModalOpen(false);
      fetchData();
    } catch (err) {
      setModalError(err.response?.data?.message || err.response?.data?.detail || 'Failed to save subcategory.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleSubcategoryActive = (subcat) => {
    const nextStatus = !subcat.isActive;
    const actionName = nextStatus ? 'activate' : 'deactivate';
    setConfirmDialog({
      isOpen: true,
      title: `${nextStatus ? 'Activate' : 'Deactivate'} Subcategory`,
      message: `Are you sure you want to ${actionName} "${subcat.name}" (${subcat.code})? Inactive subcategories cannot be selected for new laboratory services.`,
      confirmVariant: nextStatus ? 'primary' : 'warning',
      confirmText: nextStatus ? 'Activate' : 'Deactivate',
      onConfirm: async () => {
        setConfirmDialog(prev => ({ ...prev, isOpen: false }));
        try {
          await catalogueService.updateSubcategory(subcat.id, { isActive: nextStatus });
          flashSuccess(`Subcategory "${subcat.name}" is now ${nextStatus ? 'Active' : 'Inactive'}.`);
          fetchData();
        } catch (err) {
          alert(err.response?.data?.message || err.response?.data?.detail || 'Failed to update subcategory status.');
        }
      }
    });
  };

  const handleDeleteSubcategory = (subcat) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Soft-Delete Subcategory',
      message: `Are you sure you want to soft-delete Subcategory "${subcat.name}" (${subcat.code})?\n\nNote: If this subcategory has active laboratory services, deletion will be blocked by system governance rules.`,
      confirmVariant: 'danger',
      confirmText: 'Delete Subcategory',
      onConfirm: async () => {
        setConfirmDialog(prev => ({ ...prev, isOpen: false }));
        try {
          await catalogueService.deleteSubcategory(subcat.id);
          flashSuccess(`Subcategory "${subcat.name}" soft-deleted.`);
          fetchData();
        } catch (err) {
          alert(err.response?.data?.message || err.response?.data?.detail || 'Failed to delete subcategory.');
        }
      }
    });
  };

  // Filtered subcategories
  const filteredSubcategories = subcategories.filter(sub => {
    if (selectedCategoryId !== 'ALL' && sub.categoryId !== selectedCategoryId) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      const matchName = sub.name?.toLowerCase().includes(q);
      const matchCode = sub.code?.toLowerCase().includes(q);
      const matchDesc = sub.description?.toLowerCase().includes(q);
      return matchName || matchCode || matchDesc;
    }
    return true;
  });

  return (
    <div className="page-body">
      <PageHeader
        title="Category Architecture"
        subtitle="Manage the 2-level laboratory taxonomy: Main Category → Subcategory. Preserves historical references and audit compliance."
        breadcrumbs={[
          { label: 'CRM', to: '/crm/dashboard' },
          { label: 'Catalogue', to: '/crm/catalogue/services' },
          { label: 'Categories' }
        ]}
        actions={
          isAdmin && (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <Button
                variant="secondary"
                icon={Plus}
                onClick={() => handleOpenSubcategoryModal(null, selectedCategoryId !== 'ALL' ? selectedCategoryId : null)}
              >
                New Subcategory
              </Button>
              <Button
                variant="primary"
                icon={Plus}
                onClick={() => handleOpenCategoryModal(null)}
              >
                New Main Category
              </Button>
            </div>
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

      {/* Main Categories Overview Cards */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Folder size={18} />
          <span>Main Categories ({categories.length})</span>
        </h3>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
          gap: '1rem'
        }}>
          {categories.map(cat => {
            const count = subcategories.filter(s => s.categoryId === cat.id && !s.isDeleted).length;
            const isSelected = selectedCategoryId === cat.id;

            return (
              <Card
                key={cat.id}
                style={{
                  cursor: 'pointer',
                  border: isSelected ? '2px solid var(--accent-primary)' : '1px solid var(--border-color)',
                  background: isSelected ? '#f8fafc' : 'var(--bg-card)',
                  transition: 'all 0.15s ease'
                }}
                onClick={() => setSelectedCategoryId(isSelected ? 'ALL' : cat.id)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{
                      fontWeight: 700,
                      fontSize: '0.8rem',
                      background: 'var(--bg-secondary)',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      color: 'var(--text-primary)'
                    }}>
                      {cat.code}
                    </span>
                    <StatusBadge status={cat.isActive ? 'Active' : 'Inactive'} />
                  </div>

                  {isAdmin && (
                    <div style={{ display: 'flex', gap: '0.25rem' }} onClick={e => e.stopPropagation()}>
                      <button
                        type="button"
                        className="btn-icon"
                        title="Edit Main Category"
                        onClick={() => handleOpenCategoryModal(cat)}
                        style={{ padding: '4px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}
                      >
                        <Edit2 size={15} />
                      </button>
                      <button
                        type="button"
                        className="btn-icon"
                        title={cat.isActive ? 'Deactivate' : 'Activate'}
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
                  )}
                </div>

                <div style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                  {cat.name}
                </div>
                {cat.description && (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem', lineHeight: '1.3' }}>
                    {cat.description}
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem', marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span>{count} Subcategories</span>
                  <span style={{ color: isSelected ? 'var(--accent-primary)' : 'inherit', fontWeight: isSelected ? 600 : 400 }}>
                    {isSelected ? '✓ Filtered' : 'Click to filter'}
                  </span>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Subcategories Table Section */}
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Layers size={18} />
              <span>
                Subcategories {selectedCategoryId !== 'ALL' ? `(${categories.find(c => c.id === selectedCategoryId)?.name})` : ''}
              </span>
            </h3>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Showing {filteredSubcategories.length} of {subcategories.length} subcategories
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            {selectedCategoryId !== 'ALL' && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setSelectedCategoryId('ALL')}
              >
                Clear Category Filter
              </Button>
            )}
            <div style={{ width: '240px' }}>
              <SearchInput
                value={searchTerm}
                onChange={setSearchTerm}
                placeholder="Search subcategory..."
              />
            </div>
          </div>
        </div>

        {loading ? (
          <LoadingState message="Loading subcategories..." />
        ) : filteredSubcategories.length === 0 ? (
          <div style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Layers size={36} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
            <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>No Subcategories Found</div>
            <div style={{ fontSize: '0.8rem' }}>Create subcategories under main categories to organize laboratory services.</div>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="crm-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left', background: 'var(--bg-secondary)' }}>
                  <th style={{ padding: '10px 12px' }}>Subcategory Code</th>
                  <th style={{ padding: '10px 12px' }}>Subcategory Name</th>
                  <th style={{ padding: '10px 12px' }}>Parent Main Category</th>
                  <th style={{ padding: '10px 12px' }}>Description</th>
                  <th style={{ padding: '10px 12px', textAlign: 'center' }}>Status</th>
                  {isAdmin && <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {filteredSubcategories.map(sub => {
                  const parentCat = categories.find(c => c.id === sub.categoryId);
                  return (
                    <tr key={sub.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {sub.code}
                      </td>
                      <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {sub.name}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{ fontSize: '0.8rem', background: '#e0f2fe', color: '#0369a1', padding: '2px 8px', borderRadius: '4px', fontWeight: 500 }}>
                          {parentCat ? `${parentCat.code} — ${parentCat.name}` : sub.categoryId}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontSize: '0.8rem', maxWidth: '300px' }}>
                        {sub.description || '—'}
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                        <StatusBadge status={sub.isActive ? 'Active' : 'Inactive'} />
                      </td>
                      {isAdmin && (
                        <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '0.35rem' }}>
                            <button
                              type="button"
                              className="btn-icon"
                              title="Edit Subcategory"
                              onClick={() => handleOpenSubcategoryModal(sub)}
                              style={{ padding: '4px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}
                            >
                              <Edit2 size={15} />
                            </button>
                            <button
                              type="button"
                              className="btn-icon"
                              title={sub.isActive ? 'Deactivate Subcategory' : 'Activate Subcategory'}
                              onClick={() => handleToggleSubcategoryActive(sub)}
                              style={{ padding: '4px', background: 'none', border: 'none', cursor: 'pointer', color: sub.isActive ? '#059669' : '#dc2626' }}
                            >
                              <Power size={15} />
                            </button>
                            <button
                              type="button"
                              className="btn-icon"
                              title="Delete Subcategory"
                              onClick={() => handleDeleteSubcategory(sub)}
                              style={{ padding: '4px', background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626' }}
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Main Category Modal */}
      <Modal
        isOpen={categoryModalOpen}
        onClose={() => setCategoryModalOpen(false)}
        title={editingCategory ? `Edit Main Category (${editingCategory.code})` : 'Create Main Category'}
        subtitle="Configure laboratory service main category details and display hierarchy"
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

          <FormField label="Category Code" required hint="Stable prefix for service codes (e.g. LAB-01, WWT)">
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

          <FormField label="Display Order">
            <input
              type="number"
              className="crm-input"
              value={categoryFormData.displayOrder}
              onChange={e => setCategoryFormData(prev => ({ ...prev, displayOrder: e.target.value }))}
              min="0"
            />
          </FormField>
        </form>
      </Modal>

      {/* Subcategory Modal */}
      <Modal
        isOpen={subcategoryModalOpen}
        onClose={() => setSubcategoryModalOpen(false)}
        title={editingSubcategory ? `Edit Subcategory (${editingSubcategory.code})` : 'Create Subcategory'}
        subtitle="Configure subcategory parameters and parent category mapping"
        maxWidth="520px"
        footer={
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', width: '100%' }}>
            <Button variant="secondary" type="button" onClick={() => setSubcategoryModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="button" disabled={submitting} onClick={handleSaveSubcategory}>
              {submitting ? 'Saving...' : (editingSubcategory ? 'Save Changes' : 'Create Subcategory')}
            </Button>
          </div>
        }
      >
        <form onSubmit={handleSaveSubcategory} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {modalError && (
            <div style={{ padding: '0.65rem 0.85rem', background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', borderRadius: '4px', fontSize: '0.85rem' }}>
              {modalError}
            </div>
          )}

          <FormField label="Parent Main Category" required>
            <select
              className="crm-select"
              value={subcategoryFormData.categoryId}
              onChange={e => setSubcategoryFormData(prev => ({ ...prev, categoryId: e.target.value }))}
              disabled={!!editingSubcategory}
              required
            >
              <option value="">Select Main Category...</option>
              {categories.filter(c => c.isActive || (editingSubcategory && c.id === editingSubcategory.categoryId)).map(c => (
                <option key={c.id} value={c.id}>
                  {c.code} — {c.name} {!c.isActive ? '(Inactive)' : ''}
                </option>
              ))}
            </select>
          </FormField>

          <FormField label="Subcategory Code" required hint="Unique subcategory code (e.g. PHY-01, BIO-02)">
            <input
              type="text"
              className="crm-input"
              value={subcategoryFormData.code}
              onChange={e => setSubcategoryFormData(prev => ({ ...prev, code: e.target.value.toUpperCase() }))}
              disabled={!!editingSubcategory}
              placeholder="e.g. PHY-01"
              required
            />
          </FormField>

          <FormField label="Subcategory Name" required>
            <input
              type="text"
              className="crm-input"
              value={subcategoryFormData.name}
              onChange={e => setSubcategoryFormData(prev => ({ ...prev, name: e.target.value }))}
              placeholder="e.g. Physical Parameters"
              required
            />
          </FormField>

          <FormField label="Description">
            <textarea
              className="crm-textarea"
              rows={3}
              value={subcategoryFormData.description}
              onChange={e => setSubcategoryFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Brief description of subcategory scope..."
            />
          </FormField>

          <FormField label="Display Order">
            <input
              type="number"
              className="crm-input"
              value={subcategoryFormData.displayOrder}
              onChange={e => setSubcategoryFormData(prev => ({ ...prev, displayOrder: e.target.value }))}
              min="0"
            />
          </FormField>
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
