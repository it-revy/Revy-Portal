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
  Package as PackageIcon,
  Plus,
  RefreshCw,
  Eye,
  GitBranch,
  Edit
} from 'lucide-react';
import catalogueService, { normalizeArrayResponse } from '../../../services/catalogueService';
import { useAuth } from '../../../context/AuthContext';

export default function PackagesPage() {
  const navigate = useNavigate();
  const { hasRole, isGlobalAdmin, hasPermission } = useAuth();

  const globalAdminActive = typeof isGlobalAdmin === 'function' ? isGlobalAdmin() : Boolean(isGlobalAdmin);
  const canManage = globalAdminActive || hasRole('CRM_ADMIN') || hasPermission('crm.catalogue.manage');

  const [loading, setLoading] = useState(true);
  const [packages, setPackages] = useState([]);
  const [categories, setCategories] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  useEffect(() => {
    async function loadCategories() {
      try {
        const res = await catalogueService.getCategories({ includeInactive: true });
        setCategories(normalizeArrayResponse(res, 'categories'));
      } catch (err) {
        console.error('Failed to load categories', err);
        setCategories([]);
      }
    }
    loadCategories();
  }, []);

  const fetchPackages = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page,
        pageSize,
        search: search.trim() || undefined,
        categoryId: selectedCategory !== 'ALL' ? selectedCategory : undefined,
        isActive: selectedStatus === 'ALL' ? undefined : (selectedStatus === 'ACTIVE')
      };
      const res = await catalogueService.getPackages(params);
      const items = normalizeArrayResponse(res, 'packages');
      setPackages(items);
      const total = res.data?.total ?? res.total ?? items.length;
      setTotalItems(total);
      setTotalPages(Math.max(1, Math.ceil(total / pageSize)));
    } catch (err) {
      console.error('Failed to fetch packages', err);
      setPackages([]);
      setTotalItems(0);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  }, [page, search, selectedCategory, selectedStatus]);

  useEffect(() => {
    fetchPackages();
  }, [fetchPackages]);

  const columns = [
    {
      key: 'packageCode',
      accessor: 'packageCode',
      label: 'Package Code',
      header: 'Package Code',
      render: (codeVal, row) => {
        const pCode = codeVal || row?.packageCode || row?.code || '—';
        return (
          <span style={{ fontWeight: 700, color: 'var(--color-primary)', fontFamily: 'monospace' }}>
            {pCode}
          </span>
        );
      }
    },
    {
      key: 'name',
      accessor: 'name',
      label: 'Package Name',
      header: 'Package Name',
      render: (nameVal, row) => {
        const pkgName = nameVal || row?.name || '—';
        const desc = row?.description;
        return (
          <div>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{pkgName}</div>
            {desc && (
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', maxWidth: '320px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {desc}
              </div>
            )}
          </div>
        );
      }
    },
    {
      key: 'categoryName',
      accessor: 'categoryName',
      label: 'Category',
      header: 'Category',
      render: (catVal, row) => (
        <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 500 }}>
          {catVal || row?.categoryName || 'General Laboratory'}
        </span>
      )
    },
    {
      key: 'currentVersion',
      accessor: 'currentVersion',
      label: 'Version',
      header: 'Version',
      align: 'center',
      render: (verVal, row) => {
        const ver = verVal !== undefined ? verVal : (row?.currentVersion || row?.activeVersion?.versionNumber || 1);
        return (
          <div style={{ textAlign: 'center' }}>
            <span className="badge badge-info" style={{ fontWeight: 700 }}>
              v{ver}
            </span>
          </div>
        );
      }
    },
    {
      key: 'components',
      accessor: 'id',
      label: 'Components',
      header: 'Components',
      align: 'center',
      render: (_, row) => {
        const comps = row?.latestVersion?.components || row?.activeVersion?.components || [];
        return (
          <div style={{ textAlign: 'center', fontWeight: 600 }}>
            {comps.length} test{comps.length === 1 ? '' : 's'}
          </div>
        );
      }
    },
    {
      key: 'fixedPackagePrice',
      accessor: 'fixedPackagePrice',
      label: 'Fixed Package Price',
      header: 'Fixed Package Price',
      align: 'right',
      render: (priceVal, row) => {
        const price = priceVal !== undefined ? priceVal : (row?.fixedPackagePrice || row?.activeVersion?.packagePrice || 0);
        return (
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.95rem' }}>
              ₹{Number(price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
              onClick={() => navigate(`/crm/catalogue/packages/${rowId}`)}
            />
            {canManage && (
              <>
                <Button
                  size="sm"
                  variant="secondary"
                  icon={Edit}
                  title="Edit Package"
                  onClick={() => navigate(`/crm/catalogue/packages/${rowId}/edit`)}
                />
                <Button
                  size="sm"
                  variant="secondary"
                  icon={GitBranch}
                  title="Create New Version"
                  onClick={() => navigate(`/crm/catalogue/packages/${rowId}/new-version`)}
                />
              </>
            )}
          </div>
        );
      }
    }
  ];

  const categoryOptions = [
    { value: 'ALL', label: 'All Categories' },
    ...(Array.isArray(categories) ? categories : []).map(c => ({ value: c.id, label: `${c.code} — ${c.name}` }))
  ];

  const statusOptions = [
    { value: 'ALL', label: 'All Statuses' },
    { value: 'ACTIVE', label: 'Active Only' },
    { value: 'INACTIVE', label: 'Inactive Only' }
  ];

  return (
    <div className="page-body">
      <PageHeader
        title="Service Packages & Commercial Bundles"
        subtitle="Predefined laboratory test bundles with unified package pricing and version control."
        icon={PackageIcon}
        breadcrumbs={[
          { label: 'Portal', to: '/portal' },
          { label: 'CRM', to: '/crm' },
          { label: 'Catalogue', to: '/crm/catalogue/services' },
          { label: 'Packages' }
        ]}
        actions={
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <Button
              variant="secondary"
              icon={RefreshCw}
              onClick={fetchPackages}
              title="Refresh package list"
            >
              Refresh
            </Button>
            {canManage && (
              <Button
                variant="primary"
                icon={Plus}
                onClick={() => navigate('/crm/catalogue/packages/new')}
              >
                Create Package
              </Button>
            )}
          </div>
        }
      />

      <FilterBar>
        <div style={{ flex: 1, minWidth: '240px', maxWidth: '440px' }}>
          <SearchInput
            placeholder="Search code, package name, description..."
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
            <LoadingState message="Loading service packages..." />
          </div>
        ) : (
          <>
            <DataTable
              columns={columns}
              data={packages}
              keyField="id"
              emptyMessage="No service packages found matching the active filters."
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

