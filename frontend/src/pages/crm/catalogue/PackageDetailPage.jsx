import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  PageHeader,
  Card,
  Button,
  StatusBadge,
  DataTable,
  LoadingState
} from '../../../components/ui';
import {
  Package as PackageIcon,
  ArrowLeft,
  GitBranch,
  Edit,
  Layers,
  Sparkles,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import catalogueService from '../../../services/catalogueService';
import { useAuth } from '../../../context/AuthContext';

export default function PackageDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasRole, isGlobalAdmin, hasPermission } = useAuth();

  const globalAdminActive = typeof isGlobalAdmin === 'function' ? isGlobalAdmin() : Boolean(isGlobalAdmin);
  const canManage = globalAdminActive || hasRole('CRM_ADMIN') || hasPermission('crm.catalogue.manage');

  const [loading, setLoading] = useState(true);
  const [pkg, setPkg] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadPackage() {
      setLoading(true);
      setError(null);
      try {
        const res = await catalogueService.getPackageById(id);
        setPkg(res.data);
      } catch (err) {
        console.error('Failed to load package', err);
        setError('Failed to load package details.');
      } finally {
        setLoading(false);
      }
    }
    loadPackage();
  }, [id]);

  if (loading) {
    return (
      <div className="page-body">
        <LoadingState message="Loading package details and version breakdown..." />
      </div>
    );
  }

  if (error || !pkg) {
    return (
      <div className="page-body">
        <Card>
          <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
            <AlertCircle size={48} color="var(--danger)" style={{ marginBottom: '1rem' }} />
            <h3 style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>Package Not Found</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>{error}</p>
            <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate('/crm/catalogue/packages')}>
              Back to Packages
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  const latestVer = pkg.latestVersion || (pkg.versions && pkg.versions[0]) || null;
  const components = latestVer?.components || [];
  const addons = latestVer?.addonConfigurations || [];

  // Calculate sum of individual reference prices
  const totalReferencePrice = components.reduce((sum, comp) => {
    return sum + (Number(comp.referencePrice || 0) * Number(comp.quantity || 1));
  }, 0);

  const packagePrice = Number(pkg.fixedPackagePrice || 0);
  const commercialSavings = totalReferencePrice > packagePrice ? (totalReferencePrice - packagePrice) : 0;
  const savingsPct = totalReferencePrice > 0 && commercialSavings > 0 ? ((commercialSavings / totalReferencePrice) * 100).toFixed(1) : 0;

  const componentColumns = [
    {
      key: 'serviceCode',
      accessor: 'serviceCode',
      label: 'Service Code',
      header: 'Service Code',
      render: (codeVal, row) => {
        const sc = codeVal || row?.serviceCode || row?.code || '—';
        return (
          <span style={{ fontWeight: 700, color: 'var(--color-primary)', fontFamily: 'monospace' }}>
            {sc}
          </span>
        );
      }
    },
    {
      key: 'serviceName',
      accessor: 'serviceName',
      label: 'Component Service',
      header: 'Component Service',
      render: (nameVal, row) => {
        const sn = nameVal || row?.serviceName || row?.name || '—';
        return (
          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
            {sn}
          </span>
        );
      }
    },
    {
      key: 'quantity',
      accessor: 'quantity',
      label: 'Quantity in Package',
      header: 'Quantity in Package',
      align: 'center',
      render: (qtyVal, row) => {
        const qty = qtyVal !== undefined ? qtyVal : (row?.quantity || 1);
        return (
          <div style={{ textAlign: 'center', fontWeight: 600 }}>
            {qty} unit{qty === 1 ? '' : 's'}
          </div>
        );
      }
    },
    {
      key: 'referencePrice',
      accessor: 'referencePrice',
      label: 'Individual Ref Price',
      header: 'Individual Ref Price',
      align: 'right',
      render: (priceVal, row) => {
        const p = priceVal !== undefined ? priceVal : (row?.referencePrice || 0);
        return (
          <div style={{ textAlign: 'right', color: 'var(--text-secondary)' }}>
            ₹{Number(p).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        );
      }
    },
    {
      key: 'totalRefValue',
      accessor: 'id',
      label: 'Total Ref Value',
      header: 'Total Ref Value',
      align: 'right',
      render: (_, row) => {
        const lineTotal = Number(row?.referencePrice || 0) * Number(row?.quantity || 1);
        return (
          <div style={{ textAlign: 'right', fontWeight: 600 }}>
            ₹{lineTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        );
      }
    }
  ];

  const versionColumns = [
    {
      key: 'versionNumber',
      accessor: 'versionNumber',
      label: 'Version',
      header: 'Version',
      align: 'center',
      render: (verVal, row) => {
        const vn = verVal !== undefined ? verVal : (row?.versionNumber || 1);
        return (
          <span className="badge badge-info" style={{ fontWeight: 700 }}>
            v{vn}
          </span>
        );
      }
    },
    {
      key: 'fixedPrice',
      accessor: 'fixedPrice',
      label: 'Fixed Price',
      header: 'Fixed Price',
      align: 'right',
      render: (priceVal, row) => {
        const fp = priceVal !== undefined ? priceVal : (row?.fixedPrice || row?.packagePrice || 0);
        return (
          <div style={{ textAlign: 'right', fontWeight: 700, color: 'var(--color-primary)' }}>
            ₹{Number(fp).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        );
      }
    },
    {
      key: 'effectiveDate',
      accessor: 'effectiveDate',
      label: 'Effective Date',
      header: 'Effective Date',
      render: (dateVal, row) => {
        const ed = dateVal || row?.effectiveDate;
        return (
          <span>
            {ed ? new Date(ed).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'}
          </span>
        );
      }
    },
    {
      key: 'changeSummary',
      accessor: 'changeSummary',
      label: 'Change Summary',
      header: 'Change Summary',
      render: (summaryVal, row) => summaryVal || row?.changeSummary || row?.changeReason || 'Version created'
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
    }
  ];

  return (
    <div className="page-body">
      <PageHeader
        title={`${pkg.packageCode} — ${pkg.name}`}
        subtitle={`Current Active Version: v${pkg.currentVersion} | Category: ${pkg.categoryName || 'General Laboratory'}`}
        icon={PackageIcon}
        breadcrumbs={[
          { label: 'Portal', to: '/portal' },
          { label: 'CRM', to: '/crm' },
          { label: 'Catalogue', to: '/crm/catalogue/services' },
          { label: 'Packages', to: '/crm/catalogue/packages' },
          { label: pkg.packageCode }
        ]}
        actions={
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <Button
              variant="secondary"
              icon={ArrowLeft}
              onClick={() => navigate('/crm/catalogue/packages')}
            >
              Back
            </Button>
            {canManage && (
              <Button
                variant="primary"
                icon={GitBranch}
                onClick={() => navigate(`/crm/catalogue/packages/${pkg.id}/new-version`)}
              >
                Create New Version
              </Button>
            )}
          </div>
        }
      />

      {/* Commercial Summary Banner */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
        {/* Fixed Package Price Card */}
        <Card title="Commercial Package Price">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Fixed Package Price:</span>
              <span style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--color-primary)' }}>
                ₹{packagePrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
              <span>Sum of Individual Components:</span>
              <span style={{ textDecoration: 'line-through' }}>
                ₹{totalReferencePrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
            {commercialSavings > 0 && (
              <div style={{ background: '#dcfce7', border: '1px solid #86efac', padding: '0.5rem 0.75rem', borderRadius: '6px', color: '#166534', fontSize: '0.85rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Sparkles size={16} />
                <span>Commercial Bundle Savings: ₹{commercialSavings.toLocaleString('en-IN')} ({savingsPct}% discount)</span>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.25rem', paddingTop: '0.5rem', borderTop: '1px solid var(--color-border)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Status:</span>
              <StatusBadge status={pkg.isActive ? 'ACTIVE' : 'INACTIVE'} />
            </div>
          </div>
        </Card>

        {/* Classification Card */}
        <Card title="Classification & Metadata">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                Category
              </span>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                {pkg.categoryName || 'General Laboratory'}
              </div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                Currency
              </span>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                {pkg.currencyCode || 'INR'} ({pkg.currencySymbol || '₹'})
              </div>
            </div>
          </div>
        </Card>
      </div>

      {pkg.description && (
        <Card title="Package Description" style={{ marginBottom: '1.5rem' }}>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
            {pkg.description}
          </p>
        </Card>
      )}

      {/* Included Component Services */}
      <Card title={`Included Component Services (Active Version v${latestVer?.versionNumber || 1})`} style={{ marginBottom: '1.5rem' }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
          When added to a quotation, the customer is billed the fixed package price. Individual component reference prices are preserved for transparent client comparison:
        </p>
        <DataTable
          columns={componentColumns}
          data={components}
          keyField="id"
          emptyMessage="No component services configured in this package version."
        />
      </Card>

      {/* Configured Add-ons */}
      <Card title="Applicable Add-on Services" style={{ marginBottom: '1.5rem' }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
          Special supplementary tests (e.g. C/N Ratio) available to attach to this package at configured add-on pricing:
        </p>
        {addons.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
            {addons.map(addon => (
              <div
                key={addon.id}
                style={{
                  padding: '1rem',
                  borderRadius: '6px',
                  background: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.4rem'
                }}
              >
                <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{addon.addonServiceName}</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--color-primary)', fontFamily: 'monospace' }}>
                  {addon.addonServiceCode}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginTop: '0.4rem', paddingTop: '0.4rem', borderTop: '1px solid var(--color-border)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Add-on Price:</span>
                  <span style={{ fontWeight: 700 }}>
                    ₹{Number(addon.overridePrice !== null ? addon.overridePrice : (addon.standardPrice || 300)).toLocaleString('en-IN')}
                    {addon.overridePrice !== null && (
                      <span style={{ fontSize: '0.7rem', color: '#16a34a', marginLeft: '4px' }}>(Package Override)</span>
                    )}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Default Qty:</span>
                  <span>{addon.defaultQuantity} unit(s)</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: 0 }}>
            No add-on services configured for this package version.
          </p>
        )}
      </Card>

      {/* Package Version History */}
      <Card title="Package Version History">
        <DataTable
          columns={versionColumns}
          data={pkg.versions || []}
          keyField="id"
          emptyMessage="No version history available."
        />
      </Card>
    </div>
  );
}

