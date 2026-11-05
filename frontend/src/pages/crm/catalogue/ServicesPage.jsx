import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PageHeader,
  FilterBar,
  FilterField,
  SearchInput,
  Select,
  Button,
  Card,
  DataTable,
  Pagination,
  StatusBadge,
  LoadingState
} from '../../../components/ui';
import {
  FlaskConical,
  Plus,
  RefreshCw,
  Eye,
  Edit,
  AlertCircle
} from 'lucide-react';
import catalogueService, { normalizeArrayResponse } from '../../../services/catalogueService';
import { useAuth } from '../../../context/AuthContext';

export default function ServicesPage() {
  const navigate = useNavigate();
  const { hasRole, isGlobalAdmin, hasPermission } = useAuth();

  const globalAdminActive = typeof isGlobalAdmin === 'function' ? isGlobalAdmin() : Boolean(isGlobalAdmin);
  const canManage = globalAdminActive || hasRole('CRM_ADMIN') || hasPermission('crm.catalogue.manage');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [services, setServices] = useState([]);
  const [categories, setCategories] = useState([]);
  const [subcategories, setSubcategories] = useState([]);
  const [subcategoriesError, setSubcategoriesError] = useState(null);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [selectedSubcategory, setSelectedSubcategory] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Load Categories on mount
  useEffect(() => {
    let isMounted = true;
    async function loadMeta() {
      try {
        const catRes = await catalogueService.getCategories({ includeInactive: true });
        if (isMounted) {
          setCategories(normalizeArrayResponse(catRes, 'categories'));
        }
      } catch (err) {
        console.error('Failed to load categories', err);
        if (isMounted) {
          setCategories([]);
        }
      }
    }
    loadMeta();
    return () => { isMounted = false; };
  }, []);

  // Update subcategories dropdown when category filter changes
  useEffect(() => {
    let isMounted = true;
    async function loadSubcategories() {
      try {
        setSubcategoriesError(null);
        const params = { includeInactive: true };
        if (selectedCategory && selectedCategory !== 'ALL') {
          params.categoryId = selectedCategory;
        }
        const res = await catalogueService.getSubcategories(params);
        if (isMounted) {
          setSubcategories(normalizeArrayResponse(res, 'subcategories'));
        }
      } catch (err) {
        console.error('Failed to load subcategories', err);
        if (isMounted) {
          setSubcategories([]);
          setSubcategoriesError('Failed to load subcategories');
        }
      }
    }
    loadSubcategories();
    setSelectedSubcategory('ALL');
    return () => { isMounted = false; };
  }, [selectedCategory]);

  const fetchServices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page,
        pageSize,
        search: search.trim() || undefined,
        categoryId: selectedCategory !== 'ALL' ? selectedCategory : undefined,
        subcategoryId: selectedSubcategory !== 'ALL' ? selectedSubcategory : undefined,
        isActive: selectedStatus === 'ALL' ? undefined : (selectedStatus === 'ACTIVE')
      };
      const res = await catalogueService.getServices(params);
      const items = normalizeArrayResponse(res, 'services');
      setServices(items);
      const total = res.data?.total ?? res.total ?? items.length;
      setTotalItems(total);
      setTotalPages(Math.max(1, Math.ceil(total / pageSize)));
    } catch (err) {
      console.error('Failed to fetch services', err);
      setError(err.response?.data?.message || 'Failed to fetch services from catalogue.');
      setServices([]);
      setTotalItems(0);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  }, [page, search, selectedCategory, selectedSubcategory, selectedStatus]);

  useEffect(() => {
    fetchServices();
  }, [fetchServices]);

  const columns = [
    {
      key: 'serviceCode',
      accessor: 'serviceCode',
      label: 'Code',
      header: 'Code',
      render: (code, row) => {
        const itemCode = code || row?.serviceCode || row?.code || '—';
        return (
          <span style={{ fontWeight: 700, color: 'var(--color-primary)', fontFamily: 'monospace' }}>
            {itemCode}
          </span>
        );
      }
    },
    {
      key: 'name',
      accessor: 'name',
      label: 'Service Name',
      header: 'Service Name',
      render: (nameVal, row) => {
        const svcName = nameVal || row?.name || '—';
        const note = row?.sourceNote;
        return (
          <div>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{svcName}</div>
            {note && (
              <span style={{ fontSize: '0.72rem', color: '#f59e0b', background: '#fef3c7', padding: '1px 6px', borderRadius: '4px', fontWeight: 600 }}>
                Note: {note}
              </span>
            )}
          </div>
        );
      }
    },
    {
      key: 'categoryName',
      accessor: 'categoryName',
      label: 'Category / Subcategory',
      header: 'Category / Subcategory',
      render: (catVal, row) => (
        <div style={{ fontSize: '0.82rem' }}>
          <div style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{catVal || row?.categoryName || '—'}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>{row?.subcategoryName || '—'}</div>
        </div>
      )
    },
    {
      key: 'billingUnitCode',
      accessor: 'billingUnitCode',
      label: 'Billing Unit',
      header: 'Billing Unit',
      render: (unitVal, row) => (
        <span className="badge badge-neutral" style={{ fontSize: '0.75rem', fontWeight: 600 }}>
          {unitVal || row?.billingUnitCode || 'TEST'}
        </span>
      )
    },
    {
      key: 'standardPrice',
      accessor: 'standardPrice',
      label: 'Standard Price',
      header: 'Standard Price',
      align: 'right',
      render: (priceVal, row) => {
        const price = priceVal !== undefined ? priceVal : row?.standardPrice;
        return (
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
              ₹{Number(price || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>+ GST</span>
          </div>
        );
      }
    },
    {
      key: 'minimumBillingQuantity',
      accessor: 'minimumBillingQuantity',
      label: 'Min Qty',
      header: 'Min Qty',
      align: 'center',
      render: (qtyVal, row) => (
        <div style={{ textAlign: 'center' }}>{qtyVal || row?.minimumBillingQuantity || 1}</div>
      )
    },
    {
      key: 'isActive',
      accessor: 'isActive',
      label: 'Status',
      header: 'Status',
      align: 'center',
      render: (statusVal, row) => {
        const active = statusVal !== undefined ? statusVal : row?.isActive;
        return (
          <div style={{ textAlign: 'center' }}>
            <StatusBadge status={active ? 'ACTIVE' : 'INACTIVE'} />
          </div>
        );
      }
    },
    {
      key: 'actions',
      accessor: 'id',
      label: 'Actions',
      header: 'Actions',
      align: 'right',
      render: (idVal, row) => {
        const rowId = idVal && typeof idVal === 'string' ? idVal : row?.id;
        return (
          <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'flex-end' }}>
            <Button
              size="sm"
              variant="ghost"
              icon={Eye}
              title="View Details"
              onClick={() => navigate(`/crm/catalogue/services/${rowId}`)}
            />
            {canManage && (
              <Button
                size="sm"
                variant="secondary"
                icon={Edit}
                title="Edit Service"
                onClick={() => navigate(`/crm/catalogue/services/${rowId}/edit`)}
              />
            )}
          </div>
        );
      }
    }
  ];

  const safeCategories = Array.isArray(categories) ? categories : [];
  const safeSubcategories = Array.isArray(subcategories) ? subcategories : [];

  const categoryOptions = [
    { value: 'ALL', label: 'All Categories' },
    ...safeCategories.map(c => ({ value: c.id, label: `${c.code} — ${c.name}` }))
  ];

  let subcategoryPlaceholder = 'All Subcategories';
  if (subcategoriesError) {
    subcategoryPlaceholder = 'Error loading subcategories';
  } else if (selectedCategory !== 'ALL' && safeSubcategories.length === 0) {
    subcategoryPlaceholder = 'No subcategories found';
  }

  const subcategoryOptions = [
    { value: 'ALL', label: subcategoryPlaceholder },
    ...safeSubcategories.map(sc => ({ value: sc.id, label: `${sc.code} — ${sc.name}` }))
  ];

  const statusOptions = [
    { value: 'ALL', label: 'All Statuses' },
    { value: 'ACTIVE', label: 'Active Only' },
    { value: 'INACTIVE', label: 'Inactive Only' }
  ];

  return (
    <div className="page-body">
      <PageHeader
        title="Laboratory Services Catalogue"
        subtitle="Authoritative R&D renewable energy testing services, parameter suites, and standard pricing."
        icon={FlaskConical}
        breadcrumbs={[
          { label: 'Portal', to: '/portal' },
          { label: 'CRM', to: '/crm' },
          { label: 'Catalogue', to: '/crm/catalogue/services' },
          { label: 'Services' }
        ]}
        actions={
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <Button
              variant="secondary"
              icon={RefreshCw}
              onClick={fetchServices}
              title="Refresh catalogue list"
            >
              Refresh
            </Button>
            {canManage && (
              <Button
                variant="primary"
                icon={Plus}
                onClick={() => navigate('/crm/catalogue/services/new')}
              >
                Add Service
              </Button>
            )}
          </div>
        }
      />

      {error && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          padding: '1rem',
          marginBottom: '1rem',
          background: 'var(--color-danger-subtle, #fef2f2)',
          border: '1px solid var(--color-danger-border, #fecaca)',
          borderRadius: 'var(--radius-md, 8px)',
          color: 'var(--color-danger, #dc2626)'
        }}>
          <AlertCircle size={20} />
          <div style={{ flex: 1, fontSize: '0.875rem' }}>{error}</div>
          <Button size="sm" variant="secondary" onClick={fetchServices}>Retry</Button>
        </div>
      )}

      <FilterBar>
        <div style={{ flex: 1, minWidth: '240px', maxWidth: '400px' }}>
          <SearchInput
            placeholder="Search code, service name, description..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            onClear={() => { setSearch(''); setPage(1); }}
          />
        </div>

        <FilterField label="Category">
          <Select
            size="md"
            value={selectedCategory}
            onChange={(e) => { setSelectedCategory(e.target.value); setPage(1); }}
            options={categoryOptions}
          />
        </FilterField>

        <FilterField label="Subcategory">
          <Select
            size="md"
            value={selectedSubcategory}
            onChange={(e) => { setSelectedSubcategory(e.target.value); setPage(1); }}
            options={subcategoryOptions}
            disabled={Boolean(subcategoriesError) || (selectedCategory !== 'ALL' && safeSubcategories.length === 0)}
          />
        </FilterField>

        <FilterField label="Status">
          <Select
            size="md"
            value={selectedStatus}
            onChange={(e) => { setSelectedStatus(e.target.value); setPage(1); }}
            options={statusOptions}
          />
        </FilterField>
      </FilterBar>

      <Card noPadding>
        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center' }}>
            <LoadingState message="Loading laboratory services catalogue..." />
          </div>
        ) : (
          <>
            <DataTable
              columns={columns}
              data={services}
              keyField="id"
              emptyMessage={
                error
                  ? `Failed to load services: ${error}`
                  : (selectedCategory !== 'ALL' || selectedSubcategory !== 'ALL' || search)
                  ? 'No laboratory services found matching the active filters.'
                  : 'No laboratory services found in the catalogue.'
              }
            />
            {totalItems > 0 && (
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                totalItems={totalItems}
                pageSize={pageSize}
                onPageChange={setPage}
              />
            )}
          </>
        )}
      </Card>
    </div>
  );
}
