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
  FlaskConical,
  ArrowLeft,
  Edit,
  Calendar,
  Layers,
  History,
  CheckCircle2,
  AlertCircle,
  FileText
} from 'lucide-react';
import catalogueService from '../../../services/catalogueService';
import { useAuth } from '../../../context/AuthContext';

export default function ServiceDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasRole, isGlobalAdmin, hasPermission } = useAuth();

  const globalAdminActive = typeof isGlobalAdmin === 'function' ? isGlobalAdmin() : Boolean(isGlobalAdmin);
  const canManage = globalAdminActive || hasRole('CRM_ADMIN') || hasPermission('crm.catalogue.manage');

  const [loading, setLoading] = useState(true);
  const [service, setService] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadService() {
      setLoading(true);
      setError(null);
      try {
        const res = await catalogueService.getServiceById(id);
        setService(res.data);
      } catch (err) {
        console.error('Failed to load service', err);
        setError('Failed to load service details. The service may not exist or has been removed.');
      } finally {
        setLoading(false);
      }
    }
    loadService();
  }, [id]);

  if (loading) {
    return (
      <div className="page-body">
        <LoadingState message="Loading service details..." />
      </div>
    );
  }

  if (error || !service) {
    return (
      <div className="page-body">
        <Card>
          <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
            <AlertCircle size={48} color="var(--danger)" style={{ marginBottom: '1rem' }} />
            <h3 style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>Service Not Found</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>{error}</p>
            <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate('/crm/catalogue/services')}>
              Back to Services
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  const priceHistoryColumns = [
    {
      key: 'effectiveDate',
      accessor: 'effectiveDate',
      label: 'Effective Date',
      header: 'Effective Date',
      render: (dateVal, row) => {
        const d = dateVal || row?.effectiveDate;
        return (
          <span style={{ fontWeight: 600 }}>
            {d ? new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'}
          </span>
        );
      }
    },
    {
      key: 'price',
      accessor: 'price',
      label: 'Price',
      header: 'Price',
      align: 'right',
      render: (priceVal, row) => {
        const p = priceVal !== undefined ? priceVal : row?.price;
        return (
          <div style={{ textAlign: 'right', fontWeight: 700, color: 'var(--color-primary)' }}>
            ₹{Number(p || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        );
      }
    },
    {
      key: 'reason',
      accessor: 'reason',
      label: 'Reason / Change Note',
      header: 'Reason / Change Note',
      render: (reasonVal, row) => reasonVal || row?.reason || 'Standard update'
    },
    {
      key: 'createdAt',
      accessor: 'createdAt',
      label: 'Changed At',
      header: 'Changed At',
      render: (createdVal, row) => {
        const c = createdVal || row?.createdAt;
        return (
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
            {c ? new Date(c).toLocaleString('en-IN') : '—'}
          </span>
        );
      }
    }
  ];

  const reportingParamColumns = [
    {
      key: 'parameterName',
      accessor: 'parameterName',
      label: 'Parameter Name',
      header: 'Parameter Name',
      render: (nameVal, row) => <span style={{ fontWeight: 600 }}>{nameVal || row?.parameterName || '—'}</span>
    },
    {
      key: 'reportingUnitSymbol',
      accessor: 'reportingUnitSymbol',
      label: 'Unit',
      header: 'Unit',
      render: (unitVal, row) => (
        <span className="badge badge-neutral" style={{ fontWeight: 600 }}>
          {unitVal || row?.reportingUnitSymbol || '—'}
        </span>
      )
    },
    {
      key: 'minRange',
      accessor: 'minRange',
      label: 'Range (Min - Max)',
      header: 'Range (Min - Max)',
      render: (_, row) => {
        const min = row?.minRange;
        const max = row?.maxRange;
        if (min !== null && min !== undefined && max !== null && max !== undefined) {
          return `${min} – ${max}`;
        } else if (min !== null && min !== undefined) {
          return `≥ ${min}`;
        } else if (max !== null && max !== undefined) {
          return `≤ ${max}`;
        }
        return 'Standard Range';
      }
    },
    {
      key: 'testingMethodName',
      accessor: 'testingMethodName',
      label: 'Method Override',
      header: 'Method Override',
      render: (methodVal, row) => {
        const m = methodVal || row?.testingMethodName;
        return m ? (
          <span style={{ fontSize: '0.78rem', color: 'var(--color-primary)' }}>
            {m}
          </span>
        ) : (
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Default (All Methods)</span>
        );
      }
    }
  ];

  return (
    <div className="page-body">
      <PageHeader
        title={`${service.serviceCode} — ${service.name}`}
        subtitle={`Category: ${service.categoryName || '—'} > ${service.subcategoryName || '—'}`}
        icon={FlaskConical}
        breadcrumbs={[
          { label: 'Portal', to: '/portal' },
          { label: 'CRM', to: '/crm' },
          { label: 'Catalogue', to: '/crm/catalogue/services' },
          { label: service.serviceCode }
        ]}
        actions={
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <Button
              variant="secondary"
              icon={ArrowLeft}
              onClick={() => navigate('/crm/catalogue/services')}
            >
              Back
            </Button>
            {canManage && (
              <Button
                variant="primary"
                icon={Edit}
                onClick={() => navigate(`/crm/catalogue/services/${service.id}/edit`)}
              >
                Edit Service
              </Button>
            )}
          </div>
        }
      />

      {/* Overview Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
        {/* Commercial Details Card */}
        <Card title="Commercial & Billing Configuration">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid var(--color-border)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Standard Price:</span>
              <span style={{ fontWeight: 700, fontSize: '1.15rem', color: 'var(--color-primary)' }}>
                ₹{Number(service.standardPrice).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid var(--color-border)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Billing Unit:</span>
              <span className="badge badge-neutral" style={{ fontWeight: 700 }}>
                {service.billingUnitCode || 'TEST'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid var(--color-border)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Minimum Billing Qty:</span>
              <span style={{ fontWeight: 600 }}>{service.minimumBillingQuantity} unit(s)</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid var(--color-border)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Currency:</span>
              <span style={{ fontWeight: 600 }}>{service.currencyCode || 'INR'} ({service.currencySymbol || '₹'})</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid var(--color-border)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Effective Since:</span>
              <span style={{ fontWeight: 500 }}>
                {service.effectiveDate ? new Date(service.effectiveDate).toLocaleDateString('en-IN') : '—'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Status:</span>
              <StatusBadge status={service.isActive ? 'ACTIVE' : 'INACTIVE'} />
            </div>
          </div>
        </Card>

        {/* Technical & Categorization Card */}
        <Card title="Classification & Special Rules">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                Main Category
              </span>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {service.categoryCode} — {service.categoryName}
              </div>
            </div>

            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                Subcategory
              </span>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {service.subcategoryCode} — {service.subcategoryName}
              </div>
            </div>

            {service.sourceNote && (
              <div style={{ background: '#fef3c7', padding: '0.75rem', borderRadius: '6px', border: '1px solid #fcd34d' }}>
                <span style={{ fontSize: '0.75rem', color: '#92400e', textTransform: 'uppercase', fontWeight: 700 }}>
                  Unverified Source Note
                </span>
                <div style={{ fontWeight: 600, color: '#b45309', marginTop: '2px' }}>
                  {service.sourceNote}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <CheckCircle2 size={16} color={service.isAddonEligible ? 'var(--success)' : 'var(--text-muted)'} />
                <span style={{ fontSize: '0.85rem', color: service.isAddonEligible ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                  Add-on Eligible
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <CheckCircle2 size={16} color={service.canHaveAddons ? 'var(--success)' : 'var(--text-muted)'} />
                <span style={{ fontSize: '0.85rem', color: service.canHaveAddons ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                  Can Have Add-ons
                </span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Description */}
      {service.description && (
        <Card title="Service Description" style={{ marginBottom: '1.5rem' }}>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
            {service.description}
          </p>
        </Card>
      )}

      {/* Sample Types & Testing Methods */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
        {/* Sample Types */}
        <Card title="Supported Sample Types">
          {service.sampleTypes && service.sampleTypes.length > 0 ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {service.sampleTypes.map((st) => (
                <span key={st.id} className="badge badge-primary" style={{ padding: '0.35rem 0.65rem', fontSize: '0.82rem' }}>
                  {st.sampleTypeName || st.sampleTypeCode}
                </span>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: 0 }}>
              No sample types specifically restricted. Applicable to all valid laboratory samples.
            </p>
          )}
        </Card>

        {/* Testing Methods */}
        <Card title="Standard Testing Methods">
          {service.testingMethods && service.testingMethods.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {service.testingMethods.map((tm) => (
                <div key={tm.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem', background: 'var(--color-bg-secondary)', borderRadius: '6px' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{tm.methodName}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Ref: {tm.standardReference || 'N/A'} {tm.revision ? `(Rev ${tm.revision})` : ''}
                    </div>
                  </div>
                  {tm.isDefault && (
                    <span className="badge badge-success" style={{ fontSize: '0.72rem' }}>Default Method</span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: 0 }}>
              No testing methods assigned yet. CRM Admin may configure analytical standards.
            </p>
          )}
        </Card>
      </div>

      {/* Reporting Parameters */}
      <Card title="Reporting Parameters & Expected Ranges" style={{ marginBottom: '1.5rem' }}>
        <DataTable
          columns={reportingParamColumns}
          data={service.reportingParameters || []}
          keyField="id"
          emptyMessage="No reporting parameters defined for this service."
        />
      </Card>

      {/* Effective Price History Audit Trail */}
      <Card title="Effective Price History & Audit Log">
        <DataTable
          columns={priceHistoryColumns}
          data={service.priceHistory || []}
          keyField="id"
          emptyMessage="No historical price modifications recorded."
        />
      </Card>
    </div>
  );
}

