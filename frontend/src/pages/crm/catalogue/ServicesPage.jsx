import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
  AlertCircle,
  X
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
  const [billingUnits, setBillingUnits] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [selectedBillingUnit, setSelectedBillingUnit] = useState('ALL');
  const [minPrice, setMinPrice] = useState('');
  const [maxPrice, setMaxPrice] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Load Metadata (Categories & Billing Units)
  useEffect(() => {
    let isMounted = true;
    async function loadMeta() {
      try {
        const [catRes, unitRes] = await Promise.all([
          catalogueService.getCategories({ includeInactive: true }),
          catalogueService.getBillingUnits({ includeInactive: true })
        ]);
        if (isMounted) {
          setCategories(normalizeArrayResponse(catRes, 'categories'));
          setBillingUnits(normalizeArrayResponse(unitRes, 'billingUnits'));
        }
      } catch (err) {
        console.error('Failed to load catalogue metadata:', err);
      }
    }
    loadMeta();
    return () => { isMounted = false; };
  }, []);

  // Fetch Services from backend with filter cohesion
  const fetchServices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page,
        pageSize,
        search: search.trim() || undefined,
        categoryId: selectedCategory !== 'ALL' ? selectedCategory : undefined,
        billingUnitId: selectedBillingUnit !== 'ALL' ? selectedBillingUnit : undefined,
        minPrice: minPrice !== '' ? Number(minPrice) : undefined,
        maxPrice: maxPrice !== '' ? Number(maxPrice) : undefined,
        isActive: selectedStatus === 'ALL' ? undefined : (selectedStatus === 'ACTIVE')
      };
      const res = await catalogueService.getServices(params);
      const items = normalizeArrayResponse(res, 'services');
      setServices(items);
      const total = res.data?.total ?? res.total ?? items.length;
      setTotalItems(total);
      setTotalPages(Math.max(1, Math.ceil(total / pageSize)));
    } catch (err) {
      console.error('Failed to fetch services:', err);
      setError(err.response?.data?.message || 'Failed to fetch services from catalogue.');
      setServices([]);
      setTotalItems(0);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  }, [page, search, selectedCategory, selectedBillingUnit, minPrice, maxPrice, selectedStatus]);

  useEffect(() => {
    fetchServices();
  }, [fetchServices]);

  const handleClearFilters = () => {
    setSearch('');
    setSelectedCategory('ALL');
    setSelectedStatus('ALL');
    setSelectedBillingUnit('ALL');
    setMinPrice('');
    setMaxPrice('');
    setPage(1);
  };

  const hasActiveFilters = Boolean(
    search.trim() ||
    selectedCategory !== 'ALL' ||
    selectedStatus !== 'ALL' ||
    selectedBillingUnit !== 'ALL' ||
    minPrice !== '' ||
    maxPrice !== ''
  );

  const columns = [
    {
      key: 'serviceCode',
      accessor: 'serviceCode',
      label: 'Service Code',
      header: 'Service Code',
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
              <span style={{ fontSize: '0.72rem', color: '#b45309', background: '#fef3c7', padding: '1px 6px', borderRadius: '4px', fontWeight: 600, display: 'inline-block', marginTop: '2px' }}>
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
      label: 'Main Category',
      header: 'Main Category',
      render: (catVal, row) => (
        <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 500 }}>
          {catVal || row?.categoryName || '—'}
        </span>
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

  // Options for dropdowns (shows only the four active categories)
  const safeCategories = Array.isArray(categories) ? categories.filter(c => c.isActive && !c.isDeleted) : [];
  const categoryOptions = useMemo(() => [
    { value: 'ALL', label: 'All Categories' },
    ...safeCategories.map(c => ({ value: c.id, label: `${c.code} — ${c.name}` }))
  ], [safeCategories]);

  const safeBillingUnits = Array.isArray(billingUnits) ? billingUnits : [];
  const billingUnitOptions = useMemo(() => [
    { value: 'ALL', label: 'All Units' },
    ...safeBillingUnits.map(u => ({ value: u.id, label: `${u.code} (${u.name})` }))
  ], [safeBillingUnits]);

  const statusOptions = [
    { value: 'ALL', label: 'All Status' },
    { value: 'ACTIVE', label: 'Active' },
    { value: 'INACTIVE', label: 'Inactive' }
  ];

  return (
    <div className="page-body">
      <PageHeader
        title="Laboratory Services Catalogue"
        subtitle="Manage laboratory services, test parameters, and commercial rates."
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

      {/* Practical Compact Filter Toolbar (Search | Category | Status | Billing Unit | Min Price | Max Price | Clear) */}
      <FilterBar onReset={hasActiveFilters ? handleClearFilters : null} resetLabel="Clear Filters">
        <div style={{ width: '240px', minWidth: '180px' }}>
          <SearchInput
            placeholder="Search code, name, description..."
            value={search}
            onChange={(e) => {
              const val = typeof e === 'string' ? e : (e?.target?.value ?? '');
              setSearch(val);
              setPage(1);
            }}
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

        <FilterField label="Status">
          <Select
            size="md"
            value={selectedStatus}
            onChange={(e) => { setSelectedStatus(e.target.value); setPage(1); }}
            options={statusOptions}
          />
        </FilterField>

        <FilterField label="Billing Unit">
          <Select
            size="md"
            value={selectedBillingUnit}
            onChange={(e) => { setSelectedBillingUnit(e.target.value); setPage(1); }}
            options={billingUnitOptions}
          />
        </FilterField>

        <FilterField label="Min Price">
          <input
            type="number"
            className="revy-input"
            style={{ width: '90px', height: '36px', fontSize: '0.85rem' }}
            placeholder="₹ Min"
            value={minPrice}
            onChange={(e) => { setMinPrice(e.target.value); setPage(1); }}
            min="0"
          />
        </FilterField>

        <FilterField label="Max Price">
          <input
            type="number"
            className="revy-input"
            style={{ width: '90px', height: '36px', fontSize: '0.85rem' }}
            placeholder="₹ Max"
            value={maxPrice}
            onChange={(e) => { setMaxPrice(e.target.value); setPage(1); }}
            min="0"
          />
        </FilterField>
      </FilterBar>

      {/* Services Data Table Card */}
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
                  : hasActiveFilters
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
