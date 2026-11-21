import React, { useState, useEffect } from 'react';
import API from '../services/api';
import {
  Coffee,
  Plus,
  RefreshCw,
  Search,
  Edit,
  Trash2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Layers,
  FileSpreadsheet,
  Users,
  Sun,
  Sunset,
  Check,
  X,
  Filter
} from 'lucide-react';
import {
  PageHeader,
  FilterBar,
  FilterField,
  SearchInput,
  Select,
  DatePicker,
  Button,
  Card,
  DataTable,
  Pagination,
  StatusBadge,
  Input,
  ConfirmationDialog
} from '../components/ui';

const BeverageManagementPage = () => {
  const [activeTab, setActiveTab] = useState('CONSUMPTION'); // 'CONSUMPTION' | 'CATALOGUE'

  // Common notification state
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // ---------------------------------------------------------------------------
  // Tab 1: Consumption Management State
  // ---------------------------------------------------------------------------
  const [entries, setEntries] = useState([]);
  const [entriesLoading, setEntriesLoading] = useState(true);
  const [metrics, setMetrics] = useState({});
  const [totalEntries, setTotalEntries] = useState(0);

  // Filters
  const [filterDate, setFilterDate] = useState('');
  const [filterFromDate, setFilterFromDate] = useState('');
  const [filterToDate, setFilterToDate] = useState('');
  const [filterEmployeeId, setFilterEmployeeId] = useState('ALL');
  const [filterBeverageId, setFilterBeverageId] = useState('ALL');
  const [filterSession, setFilterSession] = useState('ALL');
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // Employees and Beverages master lists for dropdowns
  const [employeesList, setEmployeesList] = useState([]);
  const [catalogueList, setCatalogueList] = useState([]);

  // Create On Behalf Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createData, setCreateData] = useState({
    employeeId: '',
    beverageId: '',
    businessDate: new Date().toISOString().substring(0, 10),
    session: 'MORNING',
    quantity: 1,
    notes: ''
  });
  const [submittingCreate, setSubmittingCreate] = useState(false);

  // Edit Entry Modal State
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState(null);
  const [editData, setEditData] = useState({
    beverageId: '',
    session: 'MORNING',
    quantity: 1,
    notes: ''
  });
  const [submittingEdit, setSubmittingEdit] = useState(false);

  // Delete Entry Dialog State
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletingEntry, setDeletingEntry] = useState(null);
  const [deleteReason, setDeleteReason] = useState('');
  const [submittingDelete, setSubmittingDelete] = useState(false);

  // ---------------------------------------------------------------------------
  // Tab 2: Catalogue Administration State
  // ---------------------------------------------------------------------------
  const [catalogueLoading, setCatalogueLoading] = useState(true);

  // Add Beverage Modal State
  const [showAddBevModal, setShowAddBevModal] = useState(false);
  const [addBevData, setAddBevData] = useState({
    name: '',
    description: '',
    displayOrder: 1,
    isActive: true
  });
  const [submittingAddBev, setSubmittingAddBev] = useState(false);

  // Edit Beverage Modal State
  const [showEditBevModal, setShowEditBevModal] = useState(false);
  const [editingBev, setEditingBev] = useState(null);
  const [editBevData, setEditBevData] = useState({
    name: '',
    description: '',
    displayOrder: 1,
    isActive: true
  });
  const [submittingEditBev, setSubmittingEditBev] = useState(false);

  // Initial load
  useEffect(() => {
    loadCatalogue();
    loadEmployees();
  }, []);

  useEffect(() => {
    if (activeTab === 'CONSUMPTION') {
      loadEntries();
    } else {
      loadCatalogue();
    }
  }, [activeTab, page, filterDate, filterFromDate, filterToDate, filterEmployeeId, filterBeverageId, filterSession, includeDeleted]);

  // ---------------------------------------------------------------------------
  // API Fetch Helpers
  // ---------------------------------------------------------------------------

  const loadCatalogue = async () => {
    try {
      setCatalogueLoading(true);
      const res = await API.get('/breakfast/beverages/catalogue?active_only=false');
      if (res.data.success) {
        setCatalogueList(res.data.beverages || []);
        if (res.data.beverages?.length > 0 && !createData.beverageId) {
          setCreateData(prev => ({ ...prev, beverageId: res.data.beverages[0].id }));
        }
      }
    } catch (err) {
      console.error('Failed to load catalogue:', err);
    } finally {
      setCatalogueLoading(false);
    }
  };

  const loadEmployees = async () => {
    try {
      const res = await API.get('/employees?limit=200');
      if (res.data.success) {
        const activeEmps = (res.data.employees || []).filter(e => e.status === 'active' && !e.isHardDeleted);
        setEmployeesList(activeEmps);
        if (activeEmps.length > 0 && !createData.employeeId) {
          setCreateData(prev => ({ ...prev, employeeId: activeEmps[0].employeeId }));
        }
      }
    } catch (err) {
      console.error('Failed to load employees:', err);
    }
  };

  const loadEntries = async () => {
    try {
      setEntriesLoading(true);
      let queryParams = [];

      if (filterDate) {
        queryParams.push(`date=${filterDate}`);
      } else {
        if (filterFromDate) queryParams.push(`fromDate=${filterFromDate}`);
        if (filterToDate) queryParams.push(`toDate=${filterToDate}`);
      }

      if (filterEmployeeId && filterEmployeeId !== 'ALL') queryParams.push(`employeeId=${filterEmployeeId}`);
      if (filterBeverageId && filterBeverageId !== 'ALL') queryParams.push(`beverageId=${filterBeverageId}`);
      if (filterSession && filterSession !== 'ALL') queryParams.push(`session=${filterSession}`);
      if (includeDeleted) queryParams.push(`includeDeleted=true`);

      queryParams.push(`limit=${pageSize}`);
      queryParams.push(`offset=${(page - 1) * pageSize}`);

      const url = `/breakfast/beverages/admin/entries${queryParams.length > 0 ? '?' + queryParams.join('&') : ''}`;
      const res = await API.get(url);

      if (res.data.success) {
        setEntries(res.data.records || []);
        setMetrics(res.data.metrics || {});
        setTotalEntries(res.data.total || 0);
      }
    } catch (err) {
      console.error('Failed to load entries:', err);
      setError('Unable to load beverage consumption records.');
    } finally {
      setEntriesLoading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Action Handlers: Consumption Management
  // ---------------------------------------------------------------------------

  const handleOpenCreateModal = () => {
    setError(null);
    setSuccess(null);
    setCreateData({
      employeeId: employeesList[0]?.employeeId || '',
      beverageId: catalogueList.filter(b => b.isActive)[0]?.id || '',
      businessDate: new Date().toISOString().substring(0, 10),
      session: 'MORNING',
      quantity: 1,
      notes: ''
    });
    setShowCreateModal(true);
  };

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const qty = parseInt(createData.quantity, 10);
    if (!qty || isNaN(qty) || qty <= 0) {
      setError('Quantity must be a positive whole number (at least 1 cup).');
      return;
    }

    try {
      setSubmittingCreate(true);
      const res = await API.post('/breakfast/beverages/admin/entries', {
        employeeId: createData.employeeId,
        beverageId: createData.beverageId,
        businessDate: createData.businessDate,
        session: createData.session,
        quantity: qty,
        notes: createData.notes.trim() || undefined
      });

      if (res.data.success) {
        setSuccess(res.data.message || 'Record created successfully on behalf of employee.');
        setShowCreateModal(false);
        await loadEntries();
      }
    } catch (err) {
      console.error('Admin create error:', err);
      setError(err.response?.data?.message || 'Failed to create beverage record.');
    } finally {
      setSubmittingCreate(false);
    }
  };

  const handleOpenEditModal = (entry) => {
    setError(null);
    setSuccess(null);
    setEditingEntry(entry);
    setEditData({
      beverageId: entry.beverageId,
      session: entry.session,
      quantity: entry.quantity,
      notes: entry.notes || ''
    });
    setShowEditModal(true);
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    if (!editingEntry) return;
    setError(null);
    setSuccess(null);

    const qty = parseInt(editData.quantity, 10);
    if (!qty || isNaN(qty) || qty <= 0) {
      setError('Quantity must be a positive whole number (at least 1 cup).');
      return;
    }

    try {
      setSubmittingEdit(true);
      const res = await API.put(`/breakfast/beverages/admin/entries/${editingEntry.id}`, {
        beverageId: editData.beverageId,
        session: editData.session,
        quantity: qty,
        notes: editData.notes.trim() || undefined
      });

      if (res.data.success) {
        setSuccess('Beverage entry updated successfully.');
        setShowEditModal(false);
        setEditingEntry(null);
        await loadEntries();
      }
    } catch (err) {
      console.error('Admin edit error:', err);
      setError(err.response?.data?.message || 'Failed to update beverage record.');
    } finally {
      setSubmittingEdit(false);
    }
  };

  const handleOpenDeleteModal = (entry) => {
    setError(null);
    setSuccess(null);
    setDeletingEntry(entry);
    setDeleteReason('');
    setShowDeleteModal(true);
  };

  const handleDeleteSubmit = async () => {
    if (!deletingEntry) return;
    setError(null);
    setSuccess(null);

    try {
      setSubmittingDelete(true);
      const res = await API.delete(`/breakfast/beverages/admin/entries/${deletingEntry.id}`, {
        data: { reason: deleteReason.trim() || undefined }
      });

      if (res.data.success) {
        setSuccess('Beverage record soft-deleted successfully.');
        setShowDeleteModal(false);
        setDeletingEntry(null);
        await loadEntries();
      }
    } catch (err) {
      console.error('Admin delete error:', err);
      setError(err.response?.data?.message || 'Failed to delete beverage record.');
    } finally {
      setSubmittingDelete(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Action Handlers: Catalogue Administration
  // ---------------------------------------------------------------------------

  const handleOpenAddBevModal = () => {
    setError(null);
    setSuccess(null);
    setAddBevData({
      name: '',
      description: '',
      displayOrder: catalogueList.length + 1,
      isActive: true
    });
    setShowAddBevModal(true);
  };

  const handleAddBevSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!addBevData.name.trim()) {
      setError('Beverage name is required.');
      return;
    }

    try {
      setSubmittingAddBev(true);
      const res = await API.post('/breakfast/beverages/catalogue', {
        name: addBevData.name.trim(),
        description: addBevData.description.trim() || undefined,
        displayOrder: parseInt(addBevData.displayOrder, 10) || 0,
        isActive: addBevData.isActive,
        unit: 'Cups'
      });

      if (res.data.success) {
        setSuccess(res.data.message || 'Beverage added to catalogue successfully.');
        setShowAddBevModal(false);
        await loadCatalogue();
      }
    } catch (err) {
      console.error('Add beverage error:', err);
      setError(err.response?.data?.message || 'Failed to add beverage to catalogue.');
    } finally {
      setSubmittingAddBev(false);
    }
  };

  const handleOpenEditBevModal = (bev) => {
    setError(null);
    setSuccess(null);
    setEditingBev(bev);
    setEditBevData({
      name: bev.name,
      description: bev.description || '',
      displayOrder: bev.displayOrder,
      isActive: bev.isActive
    });
    setShowEditBevModal(true);
  };

  const handleEditBevSubmit = async (e) => {
    e.preventDefault();
    if (!editingBev) return;
    setError(null);
    setSuccess(null);

    if (!editBevData.name.trim()) {
      setError('Beverage name is required.');
      return;
    }

    try {
      setSubmittingEditBev(true);
      const res = await API.put(`/breakfast/beverages/catalogue/${editingBev.id}`, {
        name: editBevData.name.trim(),
        description: editBevData.description.trim() || undefined,
        displayOrder: parseInt(editBevData.displayOrder, 10) || 0,
        isActive: editBevData.isActive,
        unit: 'Cups'
      });

      if (res.data.success) {
        setSuccess('Beverage updated successfully.');
        setShowEditBevModal(false);
        setEditingBev(null);
        await loadCatalogue();
      }
    } catch (err) {
      console.error('Edit beverage error:', err);
      setError(err.response?.data?.message || 'Failed to update beverage.');
    } finally {
      setSubmittingEditBev(false);
    }
  };

  const handleToggleBevStatus = async (bev) => {
    setError(null);
    setSuccess(null);
    try {
      const newStatus = !bev.isActive;
      const res = await API.patch(`/breakfast/beverages/catalogue/${bev.id}/status`, {
        isActive: newStatus
      });
      if (res.data.success) {
        setSuccess(`Beverage '${bev.name}' is now ${newStatus ? 'ACTIVE' : 'INACTIVE'}.`);
        await loadCatalogue();
      }
    } catch (err) {
      console.error('Toggle status error:', err);
      setError(err.response?.data?.message || 'Failed to change beverage status.');
    }
  };

  // ---------------------------------------------------------------------------
  // Columns Definition
  // ---------------------------------------------------------------------------

  const entriesColumns = [
    {
      header: 'Date (IST)',
      accessor: 'businessDate',
      cell: (row) => (
        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
          {row.businessDate}
        </span>
      )
    },
    {
      header: 'Session',
      accessor: 'session',
      cell: (row) => (
        <span
          className="badge"
          style={{
            background: row.session === 'MORNING' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(99, 102, 241, 0.15)',
            color: row.session === 'MORNING' ? '#f59e0b' : '#818cf8',
            fontWeight: 700
          }}
        >
          {row.session === 'MORNING' ? '☀ Morning' : '🌙 Evening'}
        </span>
      )
    },
    {
      header: 'Employee',
      accessor: 'employeeNameSnapshot',
      cell: (row) => (
        <div>
          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{row.employeeNameSnapshot}</div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{row.employeeId}</span>
        </div>
      )
    },
    {
      header: 'Beverage',
      accessor: 'beverageNameSnapshot',
      cell: (row) => (
        <span style={{ fontWeight: 600 }}>{row.beverageNameSnapshot}</span>
      )
    },
    {
      header: 'Quantity',
      accessor: 'quantity',
      cell: (row) => (
        <span style={{ fontWeight: 700, color: 'var(--accent-primary)' }}>
          {row.quantity} {row.unit || 'Cups'}
        </span>
      )
    },
    {
      header: 'Source',
      accessor: 'source',
      cell: (row) => (
        <span className="badge badge-secondary" style={{ fontSize: '0.75rem' }}>
          {row.source}
        </span>
      )
    },
    {
      header: 'Status',
      accessor: 'isDeleted',
      cell: (row) => (
        row.isDeleted ? (
          <StatusBadge variant="danger" title={row.deletionReason || 'Deleted'}>Soft Deleted</StatusBadge>
        ) : (
          <StatusBadge variant="success">Active</StatusBadge>
        )
      )
    },
    {
      header: 'Actions',
      accessor: 'actions',
      cell: (row) => (
        row.isDeleted ? (
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Deleted by {row.deletedBy || 'Admin'}
          </span>
        ) : (
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <Button
              variant="secondary"
              size="sm"
              icon={Edit}
              onClick={() => handleOpenEditModal(row)}
              title="Edit Record"
            />
            <Button
              variant="danger"
              size="sm"
              icon={Trash2}
              onClick={() => handleOpenDeleteModal(row)}
              title="Delete Record (Soft Delete)"
            />
          </div>
        )
      )
    }
  ];

  const catalogueColumns = [
    {
      header: 'Order',
      accessor: 'displayOrder',
      cell: (row) => (
        <span style={{ fontWeight: 700, color: 'var(--accent-primary)' }}>
          #{row.displayOrder}
        </span>
      )
    },
    {
      header: 'Beverage Name',
      accessor: 'name',
      cell: (row) => (
        <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.95rem' }}>
          {row.name}
        </span>
      )
    },
    {
      header: 'Description',
      accessor: 'description',
      cell: (row) => (
        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          {row.description || '-'}
        </span>
      )
    },
    {
      header: 'Unit',
      accessor: 'unit',
      cell: (row) => (
        <span className="badge badge-secondary" style={{ fontWeight: 600 }}>
          {row.unit || 'Cups'}
        </span>
      )
    },
    {
      header: 'Status',
      accessor: 'isActive',
      cell: (row) => (
        row.isActive ? (
          <StatusBadge variant="success">Active</StatusBadge>
        ) : (
          <StatusBadge variant="danger">Inactive</StatusBadge>
        )
      )
    },
    {
      header: 'Actions',
      accessor: 'actions',
      cell: (row) => (
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <Button
            variant="secondary"
            size="sm"
            icon={Edit}
            onClick={() => handleOpenEditBevModal(row)}
            title="Edit Beverage"
          >
            Edit
          </Button>
          <Button
            variant={row.isActive ? "danger" : "success"}
            size="sm"
            onClick={() => handleToggleBevStatus(row)}
            title={row.isActive ? "Deactivate Beverage" : "Activate Beverage"}
          >
            {row.isActive ? "Deactivate" : "Activate"}
          </Button>
        </div>
      )
    }
  ];

  return (
    <div className="page-body">
      {/* 1. Page Header */}
      <PageHeader
        title="Beverage Management Workspace"
        subtitle="Operational oversight of beverage catalogue, morning/evening consumption logs, and employee records"
        icon={Coffee}
        breadcrumbs={[
          { label: 'BMS', to: '/bms/dashboard' },
          { label: 'Beverage Management' }
        ]}
        actions={
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <Button
              variant="secondary"
              icon={RefreshCw}
              onClick={() => {
                if (activeTab === 'CONSUMPTION') loadEntries();
                else loadCatalogue();
              }}
            >
              Refresh
            </Button>
            {activeTab === 'CONSUMPTION' ? (
              <Button variant="primary" icon={Plus} onClick={handleOpenCreateModal}>
                Log on Behalf
              </Button>
            ) : (
              <Button variant="primary" icon={Plus} onClick={handleOpenAddBevModal}>
                Add Beverage
              </Button>
            )}
          </div>
        }
      />

      {/* 2. Notifications */}
      {error && (
        <div className="alert alert-danger" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <AlertCircle size={18} color="var(--danger)" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="alert alert-success" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <CheckCircle2 size={18} color="var(--success)" />
          <span>{success}</span>
        </div>
      )}

      {/* 3. Navigation Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', marginBottom: '1.5rem' }}>
        <button
          type="button"
          onClick={() => { setActiveTab('CONSUMPTION'); setPage(1); }}
          style={{
            padding: '0.65rem 1.25rem',
            border: 'none',
            background: 'none',
            cursor: 'pointer',
            fontWeight: 700,
            fontSize: '0.9rem',
            color: activeTab === 'CONSUMPTION' ? 'var(--accent-primary)' : 'var(--text-secondary)',
            borderBottom: activeTab === 'CONSUMPTION' ? '2px solid var(--accent-primary)' : '2px solid transparent',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}
        >
          <FileSpreadsheet size={16} />
          Consumption Records
        </button>

        <button
          type="button"
          onClick={() => { setActiveTab('CATALOGUE'); }}
          style={{
            padding: '0.65rem 1.25rem',
            border: 'none',
            background: 'none',
            cursor: 'pointer',
            fontWeight: 700,
            fontSize: '0.9rem',
            color: activeTab === 'CATALOGUE' ? 'var(--accent-primary)' : 'var(--text-secondary)',
            borderBottom: activeTab === 'CATALOGUE' ? '2px solid var(--accent-primary)' : '2px solid transparent',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}
        >
          <Layers size={16} />
          Beverage Catalogue Master
        </button>
      </div>

      {/* ===================================================================== */}
      {/* TAB 1: CONSUMPTION RECORDS                                            */}
      {/* ===================================================================== */}
      {activeTab === 'CONSUMPTION' && (
        <>
          {/* Summary Metric Cards */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1rem',
              marginBottom: '1.5rem'
            }}
          >
            <div className="glass-panel metric-card" style={{ padding: '1rem', borderLeft: '4px solid #3b82f6' }}>
              <div>
                <div className="metric-label" style={{ fontSize: '0.7rem' }}>TOTAL CUPS SERVED</div>
                <div className="metric-val" style={{ fontSize: '1.5rem', color: '#60a5fa' }}>
                  {metrics.totalCups || 0}
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Filtered records</span>
              </div>
              <Coffee size={28} color="#3b82f6" opacity={0.8} />
            </div>

            <div className="glass-panel metric-card" style={{ padding: '1rem', borderLeft: '4px solid #f59e0b' }}>
              <div>
                <div className="metric-label" style={{ fontSize: '0.7rem' }}>MORNING CUPS</div>
                <div className="metric-val" style={{ fontSize: '1.5rem', color: '#fbbf24' }}>
                  {metrics.morningCups || 0}
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Morning session</span>
              </div>
              <Sun size={28} color="#f59e0b" opacity={0.8} />
            </div>

            <div className="glass-panel metric-card" style={{ padding: '1rem', borderLeft: '4px solid #8b5cf6' }}>
              <div>
                <div className="metric-label" style={{ fontSize: '0.7rem' }}>EVENING CUPS</div>
                <div className="metric-val" style={{ fontSize: '1.5rem', color: '#a78bfa' }}>
                  {metrics.eveningCups || 0}
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Evening session</span>
              </div>
              <Sunset size={28} color="#8b5cf6" opacity={0.8} />
            </div>

            <div className="glass-panel metric-card" style={{ padding: '1rem', borderLeft: '4px solid #10b981' }}>
              <div>
                <div className="metric-label" style={{ fontSize: '0.7rem' }}>ACTIVE DRINKERS</div>
                <div className="metric-val" style={{ fontSize: '1.5rem', color: '#34d399' }}>
                  {metrics.uniqueEmployees || 0}
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Distinct employees</span>
              </div>
              <Users size={28} color="#10b981" opacity={0.8} />
            </div>
          </div>

          {/* FilterBar adhering strictly to Design System 38px standardization */}
          <FilterBar>
            <FilterField label="Single Date">
              <DatePicker
                id="filter-single-date"
                value={filterDate}
                onChange={(e) => { setFilterDate(e.target.value); setPage(1); }}
                style={{ width: '140px' }}
              />
            </FilterField>

            {!filterDate && (
              <>
                <FilterField label="From Date">
                  <DatePicker
                    id="filter-from-date"
                    value={filterFromDate}
                    onChange={(e) => { setFilterFromDate(e.target.value); setPage(1); }}
                    style={{ width: '140px' }}
                  />
                </FilterField>

                <FilterField label="To Date">
                  <DatePicker
                    id="filter-to-date"
                    value={filterToDate}
                    onChange={(e) => { setFilterToDate(e.target.value); setPage(1); }}
                    style={{ width: '140px' }}
                  />
                </FilterField>
              </>
            )}

            <FilterField label="Session">
              <Select
                size="md"
                value={filterSession}
                onChange={(e) => { setFilterSession(e.target.value); setPage(1); }}
                options={[
                  { value: 'ALL', label: 'All Sessions' },
                  { value: 'MORNING', label: 'Morning' },
                  { value: 'EVENING', label: 'Evening' }
                ]}
              />
            </FilterField>

            <FilterField label="Beverage">
              <Select
                size="md"
                value={filterBeverageId}
                onChange={(e) => { setFilterBeverageId(e.target.value); setPage(1); }}
                options={[
                  { value: 'ALL', label: 'All Beverages' },
                  ...catalogueList.map(b => ({ value: b.id, label: b.name }))
                ]}
              />
            </FilterField>

            <FilterField label="Employee">
              <Select
                size="md"
                value={filterEmployeeId}
                onChange={(e) => { setFilterEmployeeId(e.target.value); setPage(1); }}
                options={[
                  { value: 'ALL', label: 'All Employees' },
                  ...employeesList.map(emp => ({ value: emp.employeeId, label: `${emp.name} (${emp.employeeId})` }))
                ]}
              />
            </FilterField>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: 'auto', marginBottom: '0.2rem' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={includeDeleted}
                  onChange={(e) => { setIncludeDeleted(e.target.checked); setPage(1); }}
                />
                Show Deleted
              </label>
            </div>
          </FilterBar>

          {/* Data Table */}
          <Card noPadding>
            <DataTable
              columns={entriesColumns}
              data={entries}
              loading={entriesLoading}
              emptyMessage="No beverage consumption entries found for the selected filter criteria."
            />
            {totalEntries > pageSize && (
              <Pagination
                currentPage={page}
                totalPages={Math.ceil(totalEntries / pageSize)}
                totalItems={totalEntries}
                pageSize={pageSize}
                onPageChange={setPage}
              />
            )}
          </Card>
        </>
      )}

      {/* ===================================================================== */}
      {/* TAB 2: BEVERAGE CATALOGUE MASTER                                      */}
      {/* ===================================================================== */}
      {activeTab === 'CATALOGUE' && (
        <Card noPadding>
          <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Active Beverage Catalogue</h3>
              <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Configured beverages available for employee daily consumption. All beverages use <strong>Cups</strong> as unit of measurement.
              </p>
            </div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {catalogueList.length} total configured items
            </span>
          </div>

          <DataTable
            columns={catalogueColumns}
            data={catalogueList}
            loading={catalogueLoading}
            emptyMessage="No beverages configured in catalogue. Click 'Add Beverage' to create initial items."
          />
        </Card>
      )}

      {/* ===================================================================== */}
      {/* MODAL 1: Create on Behalf of Employee                                 */}
      {/* ===================================================================== */}
      {showCreateModal && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '500px' }}>
            <div className="modal-header">
              <h3 style={{ margin: 0, fontSize: '1.15rem' }}>Log Beverage on Behalf of Employee</h3>
              <button type="button" className="close-btn" onClick={() => setShowCreateModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                    Employee *
                  </label>
                  <Select
                    size="md"
                    value={createData.employeeId}
                    onChange={(e) => setCreateData({ ...createData, employeeId: e.target.value })}
                    options={employeesList.map(emp => ({ value: emp.employeeId, label: `${emp.name} (${emp.employeeId} - ${emp.department})` }))}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                    Business Date *
                  </label>
                  <DatePicker
                    id="create-business-date"
                    value={createData.businessDate}
                    onChange={(e) => setCreateData({ ...createData, businessDate: e.target.value })}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                      Session *
                    </label>
                    <Select
                      size="md"
                      value={createData.session}
                      onChange={(e) => setCreateData({ ...createData, session: e.target.value })}
                      options={[
                        { value: 'MORNING', label: 'Morning' },
                        { value: 'EVENING', label: 'Evening' }
                      ]}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                      Beverage *
                    </label>
                    <Select
                      size="md"
                      value={createData.beverageId}
                      onChange={(e) => setCreateData({ ...createData, beverageId: e.target.value })}
                      options={catalogueList.filter(b => b.isActive).map(b => ({ value: b.id, label: b.name }))}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                    Quantity (in Cups) *
                  </label>
                  <Input
                    type="number"
                    min="1"
                    step="1"
                    value={createData.quantity}
                    onChange={(e) => setCreateData({ ...createData, quantity: e.target.value })}
                    placeholder="1"
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                    Admin Notes (Optional)
                  </label>
                  <Input
                    type="text"
                    value={createData.notes}
                    onChange={(e) => setCreateData({ ...createData, notes: e.target.value })}
                    placeholder="e.g. Guest meeting request"
                  />
                </div>
              </div>

              <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                <Button variant="secondary" onClick={() => setShowCreateModal(false)} type="button">
                  Cancel
                </Button>
                <Button variant="primary" type="submit" disabled={submittingCreate}>
                  {submittingCreate ? 'Saving...' : 'Create Entry'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 2: Edit Entry                                                  */}
      {/* ===================================================================== */}
      {showEditModal && editingEntry && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '500px' }}>
            <div className="modal-header">
              <h3 style={{ margin: 0, fontSize: '1.15rem' }}>Edit Beverage Record</h3>
              <button type="button" className="close-btn" onClick={() => setShowEditModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleEditSubmit}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ background: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: '6px', fontSize: '0.85rem' }}>
                  <div><strong>Employee:</strong> {editingEntry.employeeNameSnapshot} ({editingEntry.employeeId})</div>
                  <div><strong>Date:</strong> {editingEntry.businessDate}</div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                      Session *
                    </label>
                    <Select
                      size="md"
                      value={editData.session}
                      onChange={(e) => setEditData({ ...editData, session: e.target.value })}
                      options={[
                        { value: 'MORNING', label: 'Morning' },
                        { value: 'EVENING', label: 'Evening' }
                      ]}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                      Beverage *
                    </label>
                    <Select
                      size="md"
                      value={editData.beverageId}
                      onChange={(e) => setEditData({ ...editData, beverageId: e.target.value })}
                      options={catalogueList.filter(b => b.isActive).map(b => ({ value: b.id, label: b.name }))}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                    Quantity (in Cups) *
                  </label>
                  <Input
                    type="number"
                    min="1"
                    step="1"
                    value={editData.quantity}
                    onChange={(e) => setEditData({ ...editData, quantity: e.target.value })}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                    Admin Notes (Optional)
                  </label>
                  <Input
                    type="text"
                    value={editData.notes}
                    onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
                  />
                </div>
              </div>

              <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                <Button variant="secondary" onClick={() => setShowEditModal(false)} type="button">
                  Cancel
                </Button>
                <Button variant="primary" type="submit" disabled={submittingEdit}>
                  {submittingEdit ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 3: Delete Confirmation Dialog                                   */}
      {/* ===================================================================== */}
      {showDeleteModal && deletingEntry && (
        <ConfirmationDialog
          isOpen={showDeleteModal}
          title="Delete Beverage Record"
          message={`Are you sure you want to delete the record for ${deletingEntry.employeeNameSnapshot} on ${deletingEntry.businessDate} (${deletingEntry.session} session)? This will be soft-deleted and excluded from reports.`}
          confirmLabel={submittingDelete ? 'Deleting...' : 'Delete Record'}
          cancelLabel="Cancel"
          variant="danger"
          onConfirm={handleDeleteSubmit}
          onCancel={() => setShowDeleteModal(false)}
        >
          <div style={{ marginTop: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
              Reason for Deletion (Optional)
            </label>
            <Input
              type="text"
              value={deleteReason}
              onChange={(e) => setDeleteReason(e.target.value)}
              placeholder="e.g. Incorrect quantity recorded"
            />
          </div>
        </ConfirmationDialog>
      )}

      {/* ===================================================================== */}
      {/* MODAL 4: Add Beverage                                                 */}
      {/* ===================================================================== */}
      {showAddBevModal && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <h3 style={{ margin: 0, fontSize: '1.15rem' }}>Add New Beverage to Catalogue</h3>
              <button type="button" className="close-btn" onClick={() => setShowAddBevModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleAddBevSubmit}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                    Beverage Name *
                  </label>
                  <Input
                    type="text"
                    value={addBevData.name}
                    onChange={(e) => setAddBevData({ ...addBevData, name: e.target.value })}
                    placeholder="e.g. Lemon Tea"
                    required
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                    Description
                  </label>
                  <Input
                    type="text"
                    value={addBevData.description}
                    onChange={(e) => setAddBevData({ ...addBevData, description: e.target.value })}
                    placeholder="e.g. Fresh lemon infused tea"
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                      Display Order
                    </label>
                    <Input
                      type="number"
                      min="0"
                      value={addBevData.displayOrder}
                      onChange={(e) => setAddBevData({ ...addBevData, displayOrder: e.target.value })}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                      Unit
                    </label>
                    <Input
                      type="text"
                      value="Cups"
                      disabled
                      title="All beverages strictly use Cups as unit of measurement"
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <input
                    type="checkbox"
                    id="add-bev-active"
                    checked={addBevData.isActive}
                    onChange={(e) => setAddBevData({ ...addBevData, isActive: e.target.checked })}
                  />
                  <label htmlFor="add-bev-active" style={{ fontSize: '0.85rem', cursor: 'pointer' }}>
                    Active (Available for employee orders)
                  </label>
                </div>
              </div>

              <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                <Button variant="secondary" onClick={() => setShowAddBevModal(false)} type="button">
                  Cancel
                </Button>
                <Button variant="primary" type="submit" disabled={submittingAddBev}>
                  {submittingAddBev ? 'Adding...' : 'Add Beverage'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 5: Edit Beverage                                                */}
      {/* ===================================================================== */}
      {showEditBevModal && editingBev && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <h3 style={{ margin: 0, fontSize: '1.15rem' }}>Edit Beverage: {editingBev.name}</h3>
              <button type="button" className="close-btn" onClick={() => setShowEditBevModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleEditBevSubmit}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                    Beverage Name *
                  </label>
                  <Input
                    type="text"
                    value={editBevData.name}
                    onChange={(e) => setEditBevData({ ...editBevData, name: e.target.value })}
                    required
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                    Description
                  </label>
                  <Input
                    type="text"
                    value={editBevData.description}
                    onChange={(e) => setEditBevData({ ...editBevData, description: e.target.value })}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                      Display Order
                    </label>
                    <Input
                      type="number"
                      min="0"
                      value={editBevData.displayOrder}
                      onChange={(e) => setEditBevData({ ...editBevData, displayOrder: e.target.value })}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                      Unit
                    </label>
                    <Input
                      type="text"
                      value="Cups"
                      disabled
                      title="All beverages strictly use Cups as unit of measurement"
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <input
                    type="checkbox"
                    id="edit-bev-active"
                    checked={editBevData.isActive}
                    onChange={(e) => setEditBevData({ ...editBevData, isActive: e.target.checked })}
                  />
                  <label htmlFor="edit-bev-active" style={{ fontSize: '0.85rem', cursor: 'pointer' }}>
                    Active (Available for employee orders)
                  </label>
                </div>
              </div>

              <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                <Button variant="secondary" onClick={() => setShowEditBevModal(false)} type="button">
                  Cancel
                </Button>
                <Button variant="primary" type="submit" disabled={submittingEditBev}>
                  {submittingEditBev ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default BeverageManagementPage;
