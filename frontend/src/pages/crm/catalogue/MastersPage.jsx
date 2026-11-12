import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../../context/AuthContext';
import {
  Settings,
  Plus,
  Edit2,
  Power,
  Layers,
  FlaskConical,
  TestTube,
  DollarSign,
  Receipt,
  Scale,
  CheckCircle2,
  XCircle,
  Percent
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

const TABS = [
  { id: 'billing_units', label: 'Billing Units', icon: Scale },
  { id: 'reporting_units', label: 'Reporting Units', icon: Layers },
  { id: 'sample_types', label: 'Sample Types', icon: TestTube },
  { id: 'testing_methods', label: 'Testing Methods', icon: FlaskConical },
  { id: 'currencies', label: 'Currencies', icon: DollarSign },
  { id: 'tax_configs', label: 'Tax Configurations', icon: Receipt },
];

export default function MastersPage() {
  const { hasRole } = useAuth();
  const isAdmin = hasRole('CRM_ADMIN') || hasRole('IT_ADMIN') || hasRole('DIRECTOR');

  const [activeTab, setActiveTab] = useState('billing_units');
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [successMsg, setSuccessMsg] = useState(null);
  const [error, setError] = useState(null);

  // Tab Data States
  const [billingUnits, setBillingUnits] = useState([]);
  const [reportingUnits, setReportingUnits] = useState([]);
  const [sampleTypes, setSampleTypes] = useState([]);
  const [testingMethods, setTestingMethods] = useState([]);
  const [currencies, setCurrencies] = useState([]);
  const [taxConfigs, setTaxConfigs] = useState([]);

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState(null);

  // Confirmation dialog
  const [confirmDialog, setConfirmDialog] = useState({
    isOpen: false,
    title: '',
    message: '',
    confirmVariant: 'warning',
    confirmText: 'Confirm',
    onConfirm: null
  });

  const flashSuccess = (msg) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 4000);
  };

  const loadTabData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === 'billing_units') {
        const res = await catalogueService.getBillingUnits({ includeInactive: true });
        if (res.data?.success) setBillingUnits(res.data.billingUnits || []);
      } else if (activeTab === 'reporting_units') {
        const res = await catalogueService.getReportingUnits({ includeInactive: true });
        if (res.data?.success) setReportingUnits(res.data.reportingUnits || []);
      } else if (activeTab === 'sample_types') {
        const res = await catalogueService.getSampleTypes({ includeInactive: true });
        if (res.data?.success) setSampleTypes(res.data.sampleTypes || []);
      } else if (activeTab === 'testing_methods') {
        const res = await catalogueService.getTestingMethods({ includeInactive: true });
        if (res.data?.success) setTestingMethods(res.data.testingMethods || []);
      } else if (activeTab === 'currencies') {
        const res = await catalogueService.getCurrencies({ includeInactive: true });
        if (res.data?.success) setCurrencies(res.data.currencies || []);
      } else if (activeTab === 'tax_configs') {
        const res = await catalogueService.getTaxConfigurations({ includeInactive: true });
        if (res.data?.success) setTaxConfigs(res.data.taxConfigurations || []);
      }
    } catch (err) {
      console.error('Failed to load master data:', err);
      setError(err.response?.data?.message || 'Failed to load master records.');
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    loadTabData();
    setSearchTerm('');
  }, [activeTab, loadTabData]);

  // Open Modal for Create or Edit
  const handleOpenModal = (item = null) => {
    setEditingItem(item);
    setModalError(null);

    if (activeTab === 'billing_units') {
      setFormData({
        code: item?.code || '',
        name: item?.name || '',
        description: item?.description || ''
      });
    } else if (activeTab === 'reporting_units') {
      setFormData({
        code: item?.code || '',
        name: item?.name || '',
        symbol: item?.symbol || '',
        description: item?.description || ''
      });
    } else if (activeTab === 'sample_types') {
      setFormData({
        code: item?.code || '',
        name: item?.name || '',
        description: item?.description || ''
      });
    } else if (activeTab === 'testing_methods') {
      setFormData({
        code: item?.code || '',
        name: item?.name || '',
        standardAgency: item?.standardAgency || '',
        referenceStandard: item?.referenceStandard || '',
        description: item?.description || ''
      });
    } else if (activeTab === 'currencies') {
      setFormData({
        code: item?.code || '',
        name: item?.name || '',
        symbol: item?.symbol || '',
        isDefault: item?.isDefault || false
      });
    } else if (activeTab === 'tax_configs') {
      setFormData({
        code: item?.code || '',
        name: item?.name || '',
        taxType: item?.taxType || 'GST',
        description: item?.description || '',
        isDefault: item?.isDefault || false,
        rates: item?.rates ? item.rates.map(r => ({ rateName: r.rateName, percentage: r.percentage })) : [
          { rateName: 'CGST', percentage: 9 },
          { rateName: 'SGST', percentage: 9 }
        ]
      });
    }

    setModalOpen(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setModalError(null);

    try {
      if (activeTab === 'billing_units') {
        if (editingItem) {
          await catalogueService.updateBillingUnit(editingItem.id, {
            name: formData.name.trim(),
            description: formData.description.trim() || null
          });
        } else {
          await catalogueService.createBillingUnit({
            code: formData.code.trim().toUpperCase(),
            name: formData.name.trim(),
            description: formData.description.trim() || null
          });
        }
      } else if (activeTab === 'reporting_units') {
        if (editingItem) {
          await catalogueService.updateReportingUnit(editingItem.id, {
            name: formData.name.trim(),
            symbol: formData.symbol.trim() || null,
            description: formData.description.trim() || null
          });
        } else {
          await catalogueService.createReportingUnit({
            code: formData.code.trim().toUpperCase(),
            name: formData.name.trim(),
            symbol: formData.symbol.trim() || null,
            description: formData.description.trim() || null
          });
        }
      } else if (activeTab === 'sample_types') {
        if (editingItem) {
          await catalogueService.updateSampleType(editingItem.id, {
            name: formData.name.trim(),
            description: formData.description.trim() || null
          });
        } else {
          await catalogueService.createSampleType({
            code: formData.code.trim().toUpperCase(),
            name: formData.name.trim(),
            description: formData.description.trim() || null
          });
        }
      } else if (activeTab === 'testing_methods') {
        if (editingItem) {
          await catalogueService.updateTestingMethod(editingItem.id, {
            name: formData.name.trim(),
            standardAgency: formData.standardAgency.trim() || null,
            referenceStandard: formData.referenceStandard.trim() || null,
            description: formData.description.trim() || null
          });
        } else {
          await catalogueService.createTestingMethod({
            code: formData.code.trim().toUpperCase(),
            name: formData.name.trim(),
            standardAgency: formData.standardAgency.trim() || null,
            referenceStandard: formData.referenceStandard.trim() || null,
            description: formData.description.trim() || null
          });
        }
      } else if (activeTab === 'currencies') {
        if (editingItem) {
          await catalogueService.updateCurrency(editingItem.id, {
            name: formData.name.trim(),
            symbol: formData.symbol.trim() || null,
            isDefault: Boolean(formData.isDefault)
          });
        } else {
          await catalogueService.createCurrency({
            code: formData.code.trim().toUpperCase(),
            name: formData.name.trim(),
            symbol: formData.symbol.trim() || null,
            isDefault: Boolean(formData.isDefault)
          });
        }
      } else if (activeTab === 'tax_configs') {
        if (editingItem) {
          await catalogueService.updateTaxConfiguration(editingItem.id, {
            name: formData.name.trim(),
            taxType: formData.taxType.trim(),
            description: formData.description.trim() || null,
            isDefault: Boolean(formData.isDefault)
          });
        } else {
          await catalogueService.createTaxConfiguration({
            code: formData.code.trim().toUpperCase(),
            name: formData.name.trim(),
            taxType: formData.taxType.trim(),
            description: formData.description.trim() || null,
            isDefault: Boolean(formData.isDefault),
            rates: formData.rates.map(r => ({
              rateName: r.rateName.trim(),
              percentage: Number(r.percentage) || 0
            }))
          });
        }
      }

      flashSuccess('Record saved successfully.');
      setModalOpen(false);
      loadTabData();
    } catch (err) {
      setModalError(err.response?.data?.message || err.response?.data?.detail || 'Failed to save record.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActive = (item) => {
    const nextStatus = !item.isActive;
    const actionName = nextStatus ? 'activate' : 'deactivate';
    setConfirmDialog({
      isOpen: true,
      title: `${nextStatus ? 'Activate' : 'Deactivate'} Master Record`,
      message: `Are you sure you want to ${actionName} "${item.name}" (${item.code})? Inactive master records cannot be attached to newly created catalogue services or packages.`,
      confirmVariant: nextStatus ? 'primary' : 'warning',
      confirmText: nextStatus ? 'Activate' : 'Deactivate',
      onConfirm: async () => {
        setConfirmDialog(prev => ({ ...prev, isOpen: false }));
        try {
          if (activeTab === 'billing_units') {
            await catalogueService.updateBillingUnit(item.id, { isActive: nextStatus });
          } else if (activeTab === 'reporting_units') {
            await catalogueService.updateReportingUnit(item.id, { isActive: nextStatus });
          } else if (activeTab === 'sample_types') {
            await catalogueService.updateSampleType(item.id, { isActive: nextStatus });
          } else if (activeTab === 'testing_methods') {
            await catalogueService.updateTestingMethod(item.id, { isActive: nextStatus });
          } else if (activeTab === 'currencies') {
            await catalogueService.updateCurrency(item.id, { isActive: nextStatus });
          } else if (activeTab === 'tax_configs') {
            await catalogueService.updateTaxConfiguration(item.id, { isActive: nextStatus });
          }
          flashSuccess(`Status updated to ${nextStatus ? 'Active' : 'Inactive'}.`);
          loadTabData();
        } catch (err) {
          setError(err.response?.data?.message || err.response?.data?.detail || 'Failed to update status.');
        }
      }
    });
  };

  // Filter current data by search term defensively
  const getCurrentData = () => {
    let data = [];
    if (activeTab === 'billing_units') data = billingUnits;
    if (activeTab === 'reporting_units') data = reportingUnits;
    if (activeTab === 'sample_types') data = sampleTypes;
    if (activeTab === 'testing_methods') data = testingMethods;
    if (activeTab === 'currencies') data = currencies;
    if (activeTab === 'tax_configs') data = taxConfigs;

    const normalized = String(searchTerm ?? '').trim().toLowerCase();
    if (!normalized) return data;
    return data.filter(d =>
      String(d.code ?? '').toLowerCase().includes(normalized) ||
      String(d.name ?? '').toLowerCase().includes(normalized) ||
      String(d.description ?? '').toLowerCase().includes(normalized) ||
      String(d.symbol ?? '').toLowerCase().includes(normalized)
    );
  };

  const currentList = getCurrentData();

  return (
    <div className="page-body">
      <PageHeader
        title="Catalogue Master Data"
        subtitle="Manage billing units, reporting units, supported sample types, laboratory testing methods, currencies, and tax configurations."
        breadcrumbs={[
          { label: 'CRM', to: '/crm/dashboard' },
          { label: 'Catalogue', to: '/crm/catalogue/services' },
          { label: 'Master Data' }
        ]}
        actions={
          isAdmin && (
            <Button
              variant="primary"
              icon={Plus}
              onClick={() => handleOpenModal(null)}
            >
              Add {TABS.find(t => t.id === activeTab)?.label.slice(0, -1) || 'Record'}
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

      {/* Tabs Bar */}
      <div style={{
        display: 'flex',
        gap: '0.5rem',
        borderBottom: '2px solid var(--border-color)',
        marginBottom: '1.5rem',
        overflowX: 'auto',
        paddingBottom: '2px'
      }}>
        {TABS.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.65rem 1rem',
                border: 'none',
                background: 'none',
                cursor: 'pointer',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.875rem',
                color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                borderBottom: isActive ? '2px solid var(--accent-primary)' : '2px solid transparent',
                marginBottom: '-2px',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease'
              }}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Search and Table Card */}
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            Total {currentList.length} records in {TABS.find(t => t.id === activeTab)?.label}
          </div>
          <div style={{ width: '260px' }}>
            <SearchInput
              value={searchTerm}
              onChange={(e) => setSearchTerm(typeof e === 'string' ? e : (e?.target?.value ?? ''))}
              onClear={() => setSearchTerm('')}
              placeholder={`Search ${TABS.find(t => t.id === activeTab)?.label.toLowerCase()}...`}
            />
          </div>
        </div>

        {loading ? (
          <LoadingState message="Loading records..." />
        ) : currentList.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Settings size={36} style={{ margin: '0 auto 0.75rem', opacity: 0.3 }} />
            <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>No Records Found</div>
            <div style={{ fontSize: '0.8rem' }}>Click &quot;Add Record&quot; to configure master values.</div>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="crm-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left', background: 'var(--bg-secondary)' }}>
                  <th style={{ padding: '10px 12px' }}>Code</th>
                  <th style={{ padding: '10px 12px' }}>Name</th>
                  {activeTab === 'reporting_units' && <th style={{ padding: '10px 12px' }}>Symbol</th>}
                  {activeTab === 'testing_methods' && <th style={{ padding: '10px 12px' }}>Standard / Agency</th>}
                  {activeTab === 'currencies' && <th style={{ padding: '10px 12px' }}>Symbol</th>}
                  {activeTab === 'tax_configs' && <th style={{ padding: '10px 12px' }}>Tax Rates (Breakdown)</th>}
                  {activeTab === 'currencies' || activeTab === 'tax_configs' ? <th style={{ padding: '10px 12px', textAlign: 'center' }}>Default</th> : null}
                  <th style={{ padding: '10px 12px' }}>Description</th>
                  <th style={{ padding: '10px 12px', textAlign: 'center' }}>Status</th>
                  {isAdmin && <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {currentList.map(item => (
                  <tr key={item.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {item.code}
                    </td>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {item.name}
                    </td>

                    {activeTab === 'reporting_units' && (
                      <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--accent-primary)' }}>
                        {item.symbol || '—'}
                      </td>
                    )}

                    {activeTab === 'testing_methods' && (
                      <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>
                        {item.standardAgency ? `${item.standardAgency} (${item.referenceStandard || ''})` : (item.referenceStandard || '—')}
                      </td>
                    )}

                    {activeTab === 'currencies' && (
                      <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--accent-primary)' }}>
                        {item.symbol || '—'}
                      </td>
                    )}

                    {activeTab === 'tax_configs' && (
                      <td style={{ padding: '10px 12px' }}>
                        {item.rates && item.rates.length > 0 ? (
                          <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                            {item.rates.map((r, i) => (
                              <span key={i} style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600 }}>
                                {r.rateName}: {r.percentage}%
                              </span>
                            ))}
                            <span style={{ fontWeight: 700, color: 'var(--accent-primary)', fontSize: '0.8rem', marginLeft: '4px' }}>
                              (Total: {item.totalPercentage || item.rates.reduce((s, r) => s + Number(r.percentage), 0)}%)
                            </span>
                          </div>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>0% (Exempt)</span>
                        )}
                      </td>
                    )}

                    {(activeTab === 'currencies' || activeTab === 'tax_configs') && (
                      <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                        {item.isDefault ? (
                          <span style={{ background: '#dbeafe', color: '#1d4ed8', fontSize: '0.75rem', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                            Default
                          </span>
                        ) : '—'}
                      </td>
                    )}

                    <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontSize: '0.8rem', maxWidth: '300px' }}>
                      {item.description || '—'}
                    </td>

                    <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                      <StatusBadge status={item.isActive ? 'Active' : 'Inactive'} />
                    </td>

                    {isAdmin && (
                      <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '0.35rem' }}>
                          <button
                            type="button"
                            className="btn-icon"
                            title="Edit Record"
                            onClick={() => handleOpenModal(item)}
                            style={{ padding: '4px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}
                          >
                            <Edit2 size={15} />
                          </button>
                          <button
                            type="button"
                            className="btn-icon"
                            title={item.isActive ? 'Deactivate Record' : 'Activate Record'}
                            onClick={() => handleToggleActive(item)}
                            style={{ padding: '4px', background: 'none', border: 'none', cursor: 'pointer', color: item.isActive ? '#059669' : '#dc2626' }}
                          >
                            <Power size={15} />
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

      {/* Master Data Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingItem ? `Edit ${TABS.find(t => t.id === activeTab)?.label.slice(0, -1)} (${editingItem.code})` : `New ${TABS.find(t => t.id === activeTab)?.label.slice(0, -1)}`}
        subtitle={`Configure ${TABS.find(t => t.id === activeTab)?.label.toLowerCase()} definition and parameters`}
        maxWidth="540px"
        footer={
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', width: '100%' }}>
            <Button variant="secondary" type="button" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="button" disabled={submitting} onClick={handleSave}>
              {submitting ? 'Saving...' : 'Save Master Record'}
            </Button>
          </div>
        }
      >
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {modalError && (
            <div style={{ padding: '0.65rem 0.85rem', background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', borderRadius: '4px', fontSize: '0.85rem' }}>
              {modalError}
            </div>
          )}

          <FormField label="Code" required hint="Unique alphanumeric identifier">
            <input
              type="text"
              className="crm-input"
              value={formData.code || ''}
              onChange={e => setFormData(prev => ({ ...prev, code: e.target.value.toUpperCase() }))}
              disabled={!!editingItem}
              placeholder="e.g. SAMPLE, PPM, APHA-4500"
              required
            />
          </FormField>

          <FormField label="Name" required>
            <input
              type="text"
              className="crm-input"
              value={formData.name || ''}
              onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
              placeholder="Full descriptive name"
              required
            />
          </FormField>

          {activeTab === 'reporting_units' && (
            <FormField label="Unit Symbol" hint="Displayed alongside reported parameter numbers (e.g. mg/L, ppm, %)">
              <input
                type="text"
                className="crm-input"
                value={formData.symbol || ''}
                onChange={e => setFormData(prev => ({ ...prev, symbol: e.target.value }))}
                placeholder="e.g. mg/L"
              />
            </FormField>
          )}

          {activeTab === 'testing_methods' && (
            <>
              <FormField label="Standard Agency" hint="APHA, IS, ASTM, USEPA, In-House">
                <input
                  type="text"
                  className="crm-input"
                  value={formData.standardAgency || ''}
                  onChange={e => setFormData(prev => ({ ...prev, standardAgency: e.target.value }))}
                  placeholder="e.g. APHA"
                />
              </FormField>
              <FormField label="Reference Standard" hint="Standard method code/section number">
                <input
                  type="text"
                  className="crm-input"
                  value={formData.referenceStandard || ''}
                  onChange={e => setFormData(prev => ({ ...prev, referenceStandard: e.target.value }))}
                  placeholder="e.g. 5220 B. Open Reflux Method"
                />
              </FormField>
            </>
          )}

          {activeTab === 'currencies' && (
            <>
              <FormField label="Currency Symbol" hint="₹, $, €">
                <input
                  type="text"
                  className="crm-input"
                  value={formData.symbol || ''}
                  onChange={e => setFormData(prev => ({ ...prev, symbol: e.target.value }))}
                  placeholder="₹"
                />
              </FormField>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem' }}>
                <input
                  type="checkbox"
                  checked={formData.isDefault || false}
                  onChange={e => setFormData(prev => ({ ...prev, isDefault: e.target.checked }))}
                />
                <span style={{ fontWeight: 600 }}>Set as Default Currency</span>
              </label>
            </>
          )}

          {activeTab === 'tax_configs' && (
            <>
              <FormField label="Tax Type" required>
                <input
                  type="text"
                  className="crm-input"
                  value={formData.taxType || 'GST'}
                  onChange={e => setFormData(prev => ({ ...prev, taxType: e.target.value }))}
                  required
                />
              </FormField>

              {!editingItem && (
                <div style={{ padding: '0.75rem', background: '#f8fafc', border: '1px solid var(--color-border)', borderRadius: '6px' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                    Tax Component Rates
                  </label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {formData.rates && formData.rates.map((rate, idx) => (
                      <div key={idx} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', background: '#ffffff', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--color-border)' }}>
                        <input
                          type="text"
                          className="crm-input"
                          placeholder="Component Name (e.g. CGST)"
                          value={rate.rateName}
                          onChange={e => {
                            const updated = [...formData.rates];
                            updated[idx].rateName = e.target.value;
                            setFormData(prev => ({ ...prev, rates: updated }));
                          }}
                          style={{ flex: 2 }}
                        />
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', flex: 1 }}>
                          <input
                            type="number"
                            step="0.01"
                            className="crm-input"
                            placeholder="%"
                            value={rate.percentage}
                            onChange={e => {
                              const updated = [...formData.rates];
                              updated[idx].percentage = e.target.value;
                              setFormData(prev => ({ ...prev, rates: updated }));
                            }}
                          />
                          <span style={{ fontWeight: 600 }}>%</span>
                        </div>
                        {formData.rates.length > 1 && (
                          <button
                            type="button"
                            onClick={() => {
                              setFormData(prev => ({ ...prev, rates: prev.rates.filter((_, i) => i !== idx) }));
                            }}
                            style={{ background: 'none', border: 'none', color: '#dc2626', cursor: 'pointer', padding: '4px' }}
                            title="Remove Component"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    ))}
                    <Button
                      size="sm"
                      variant="secondary"
                      type="button"
                      onClick={() => {
                        setFormData(prev => ({
                          ...prev,
                          rates: [...(prev.rates || []), { rateName: '', percentage: 0 }]
                        }));
                      }}
                      style={{ alignSelf: 'flex-start', marginTop: '0.25rem' }}
                    >
                      + Add Tax Component
                    </Button>
                  </div>
                </div>
              )}

              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem' }}>
                <input
                  type="checkbox"
                  checked={formData.isDefault || false}
                  onChange={e => setFormData(prev => ({ ...prev, isDefault: e.target.checked }))}
                />
                <span style={{ fontWeight: 600 }}>Set as Default Tax Configuration</span>
              </label>
            </>
          )}

          <FormField label="Description">
            <textarea
              className="crm-textarea"
              rows={2}
              value={formData.description || ''}
              onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Optional notes or description..."
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
