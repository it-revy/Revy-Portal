import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  PageHeader,
  Card,
  Button,
  FormField,
  Input,
  Select,
  DatePicker,
  LoadingState
} from '../../../components/ui';
import {
  Package as PackageIcon,
  ArrowLeft,
  Save,
  Plus,
  Trash2,
  AlertCircle,
  GitBranch
} from 'lucide-react';
import catalogueService, { normalizeArrayResponse } from '../../../services/catalogueService';

export default function PackageFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNewVersionMode = Boolean(id);

  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(isNewVersionMode);
  const [error, setError] = useState(null);

  // Masters
  const [availableServices, setAvailableServices] = useState([]);
  const [categories, setCategories] = useState([]);
  const [currencies, setCurrencies] = useState([]);

  // Base Package fields
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [currencyId, setCurrencyId] = useState('');
  const [fixedPackagePrice, setFixedPackagePrice] = useState('');
  const [isActive, setIsActive] = useState(true);

  // Version-specific fields
  const [changeSummary, setChangeSummary] = useState('');
  const [effectiveDate, setEffectiveDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [currentVersionNumber, setCurrentVersionNumber] = useState(1);

  // Components: [{ serviceId, quantity }]
  const [components, setComponents] = useState([]);

  // Add-ons: [{ addonServiceId, defaultQuantity, overridePrice, isMandatory }]
  const [addons, setAddons] = useState([]);

  // Validation errors
  const [validationErrors, setValidationErrors] = useState({});

  useEffect(() => {
    async function loadMasters() {
      try {
        const [svcRes, catRes, currRes] = await Promise.all([
          catalogueService.getServices({ pageSize: 100, isActive: true }),
          catalogueService.getCategories({ includeInactive: true }),
          catalogueService.getCurrencies({ includeInactive: false })
        ]);

        setAvailableServices(normalizeArrayResponse(svcRes, 'services'));
        setCategories(normalizeArrayResponse(catRes, 'categories'));
        setCurrencies(normalizeArrayResponse(currRes, 'currencies'));

        const inr = normalizeArrayResponse(currRes, 'currencies').find(c => c.code === 'INR' || c.isDefault);
        if (inr && !isNewVersionMode) {
          setCurrencyId(inr.id);
        }
      } catch (err) {
        console.error('Failed to load masters', err);
        setError('Failed to load service catalogue metadata.');
      }
    }
    loadMasters();
  }, [isNewVersionMode]);

  // Load existing package for new-version mode
  useEffect(() => {
    if (isNewVersionMode) {
      async function loadPackage() {
        setInitialLoading(true);
        try {
          const res = await catalogueService.getPackageById(id);
          const p = res.data;
          setName(p.name);
          setDescription(p.description || '');
          setCategoryId(p.categoryId || '');
          setCurrencyId(p.currencyId);
          setFixedPackagePrice(p.fixedPackagePrice);
          setCurrentVersionNumber(p.currentVersion || 1);

          const latest = p.latestVersion;
          if (latest) {
            setComponents((latest.components || []).map(c => ({
              serviceId: c.serviceId,
              quantity: c.quantity || 1
            })));
            setAddons((latest.addonConfigurations || []).map(a => ({
              addonServiceId: a.addonServiceId,
              defaultQuantity: a.defaultQuantity || 1,
              overridePrice: a.overridePrice !== null ? String(a.overridePrice) : '',
              isMandatory: a.isMandatory || false
            })));
          }
        } catch (err) {
          console.error('Failed to load package', err);
          setError('Failed to load existing package.');
        } finally {
          setInitialLoading(false);
        }
      }
      loadPackage();
    }
  }, [id, isNewVersionMode]);

  // Component manipulation
  const addComponentRow = () => {
    const defaultSvc = availableServices.length > 0 ? availableServices[0].id : '';
    setComponents(prev => [...prev, { serviceId: defaultSvc, quantity: 1 }]);
  };

  const removeComponentRow = (index) => {
    setComponents(prev => prev.filter((_, i) => i !== index));
  };

  const updateComponentRow = (index, field, value) => {
    setComponents(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  // Add-on manipulation
  const addAddonRow = () => {
    const addonEligibleServices = availableServices.filter(s => s.isAddonEligible);
    const defaultSvc = addonEligibleServices.length > 0 ? addonEligibleServices[0].id : '';
    setAddons(prev => [...prev, { addonServiceId: defaultSvc, defaultQuantity: 1, overridePrice: '', isMandatory: false }]);
  };

  const removeAddonRow = (index) => {
    setAddons(prev => prev.filter((_, i) => i !== index));
  };

  const updateAddonRow = (index, field, value) => {
    setAddons(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const validateForm = () => {
    const errors = {};
    if (!name.trim()) errors.name = 'Package name is mandatory.';
    if (!currencyId) errors.currencyId = 'Currency is required.';

    const price = parseFloat(fixedPackagePrice);
    if (isNaN(price) || price < 0) {
      errors.fixedPackagePrice = 'Fixed package price must be a valid non-negative number.';
    }

    if (components.length === 0) {
      errors.components = 'At least one component service must be included in the package.';
    }

    // Component validations
    const selectedServiceIds = new Set();
    for (let i = 0; i < components.length; i++) {
      const c = components[i];
      if (!c.serviceId) {
        errors[`comp_${i}`] = 'Please select a service.';
      } else if (selectedServiceIds.has(c.serviceId)) {
        errors[`comp_${i}`] = 'Duplicate service in package components.';
      } else {
        selectedServiceIds.add(c.serviceId);
      }

      const q = parseInt(c.quantity, 10);
      if (isNaN(q) || q < 1) {
        errors[`comp_qty_${i}`] = 'Qty must be ≥ 1.';
      }
    }

    if (isNewVersionMode && !changeSummary.trim()) {
      errors.changeSummary = 'Please enter a summary of changes for this new package version.';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    setError(null);

    try {
      if (isNewVersionMode) {
        // Create new version
        const payload = {
          fixedPackagePrice: parseFloat(fixedPackagePrice),
          changeSummary: changeSummary.trim(),
          effectiveDate,
          components: components.map(c => ({
            serviceId: c.serviceId,
            quantity: parseInt(c.quantity, 10)
          })),
          addonConfigurations: addons.map(a => ({
            addonServiceId: a.addonServiceId,
            defaultQuantity: parseInt(a.defaultQuantity, 10),
            overridePrice: a.overridePrice !== '' ? parseFloat(a.overridePrice) : undefined,
            isMandatory: a.isMandatory
          }))
        };
        await catalogueService.createPackageVersion(id, payload);
        navigate(`/crm/catalogue/packages/${id}`);
      } else {
        // Create new package
        const payload = {
          name: name.trim(),
          description: description.trim() || undefined,
          categoryId: categoryId || undefined,
          currencyId,
          fixedPackagePrice: parseFloat(fixedPackagePrice),
          isActive,
          components: components.map(c => ({
            serviceId: c.serviceId,
            quantity: parseInt(c.quantity, 10)
          })),
          addonConfigurations: addons.map(a => ({
            addonServiceId: a.addonServiceId,
            defaultQuantity: parseInt(a.defaultQuantity, 10),
            overridePrice: a.overridePrice !== '' ? parseFloat(a.overridePrice) : undefined,
            isMandatory: a.isMandatory
          }))
        };
        const res = await catalogueService.createPackage(payload);
        navigate(`/crm/catalogue/packages/${res.data.id}`);
      }
    } catch (err) {
      console.error('Failed to save package', err);
      const msg = err.response?.data?.message || err.message || 'Failed to save package.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  if (initialLoading) {
    return (
      <div className="page-body">
        <LoadingState message="Loading package configuration..." />
      </div>
    );
  }

  const addonEligibleServices = availableServices.filter(s => s.isAddonEligible);

  // Calculate reference total for comparison
  const totalRefPrice = components.reduce((sum, c) => {
    const svc = availableServices.find(s => s.id === c.serviceId);
    return sum + (Number(svc?.standardPrice || 0) * Number(c.quantity || 1));
  }, 0);

  return (
    <div className="page-body">
      <PageHeader
        title={isNewVersionMode ? `Create New Version — ${name} (v${currentVersionNumber + 1})` : 'Create Service Package'}
        subtitle={isNewVersionMode
          ? 'Modify component services or package pricing. Historical quotations will preserve previous versions.'
          : 'Define a predefined commercial bundle of laboratory services at a unified fixed price.'}
        icon={PackageIcon}
        breadcrumbs={[
          { label: 'Portal', to: '/portal' },
          { label: 'CRM', to: '/crm' },
          { label: 'Catalogue', to: '/crm/catalogue/services' },
          { label: 'Packages', to: '/crm/catalogue/packages' },
          { label: isNewVersionMode ? `New Version v${currentVersionNumber + 1}` : 'New Package' }
        ]}
        actions={
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <Button
              variant="secondary"
              icon={ArrowLeft}
              onClick={() => navigate(isNewVersionMode ? `/crm/catalogue/packages/${id}` : '/crm/catalogue/packages')}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              icon={Save}
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? 'Saving...' : (isNewVersionMode ? 'Publish New Version' : 'Create Package')}
            </Button>
          </div>
        }
      />

      {error && (
        <div style={{ padding: '1rem', background: 'var(--danger-bg)', border: '1px solid var(--danger)', borderRadius: '6px', color: 'var(--danger)', marginBottom: '1.5rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* 1. Basic Package Information */}
        <Card title={isNewVersionMode ? '1. Package Identity (Read-only metadata)' : '1. Package Classification & Identity'}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
            <FormField label="Package Name" required error={validationErrors.name}>
              <Input
                placeholder="e.g. Sludge Analysis Package"
                value={name}
                disabled={isNewVersionMode}
                onChange={e => setName(e.target.value)}
              />
            </FormField>

            <FormField label="Category">
              <Select
                value={categoryId}
                disabled={isNewVersionMode}
                onChange={e => setCategoryId(e.target.value)}
                options={[
                  { value: '', label: 'General Laboratory (Optional)' },
                  ...categories.map(c => ({ value: c.id, label: `${c.code} — ${c.name}` }))
                ]}
              />
            </FormField>

            <FormField label="Currency" required error={validationErrors.currencyId}>
              <Select
                value={currencyId}
                disabled={isNewVersionMode}
                onChange={e => setCurrencyId(e.target.value)}
                options={[
                  { value: '', label: 'Select Currency' },
                  ...currencies.map(c => ({ value: c.id, label: `${c.code} (${c.symbol})` }))
                ]}
              />
            </FormField>
          </div>

          {!isNewVersionMode && (
            <div style={{ marginTop: '1.25rem' }}>
              <FormField label="Package Description">
                <textarea
                  className="revy-textarea crm-textarea"
                  style={{ width: '100%', minHeight: '80px', padding: '0.65rem 0.85rem', backgroundColor: '#ffffff', border: '1px solid var(--color-border)' }}
                  placeholder="Comprehensive bundle description and analytical purpose..."
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                />
              </FormField>
            </div>
          )}
        </Card>

        {/* 2. Commercial Pricing & Version Details */}
        <Card title={isNewVersionMode ? `2. New Version v${currentVersionNumber + 1} Pricing & Release` : '2. Fixed Commercial Pricing'}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem' }}>
            <FormField label="Fixed Package Price (₹, GST extra)" required error={validationErrors.fixedPackagePrice}>
              <Input
                type="number"
                step="0.01"
                min="0"
                placeholder="2200.00"
                value={fixedPackagePrice}
                onChange={e => setFixedPackagePrice(e.target.value)}
              />
            </FormField>

            <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                Sum of Components (Reference)
              </span>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
                ₹{totalRefPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>

            <FormField label="Version Effective Date">
              <DatePicker
                value={effectiveDate}
                onChange={e => setEffectiveDate(e.target.value)}
              />
            </FormField>
          </div>

          {isNewVersionMode && (
            <div style={{ marginTop: '1.25rem' }}>
              <FormField label="Change Summary for New Version" required error={validationErrors.changeSummary}>
                <Input
                  placeholder="e.g. Updated standard fixed price and adjusted component test parameters."
                  value={changeSummary}
                  onChange={e => setChangeSummary(e.target.value)}
                />
              </FormField>
            </div>
          )}
        </Card>

        {/* 3. Included Component Services */}
        <Card
          title="3. Included Component Services"
          actions={
            <Button
              size="sm"
              variant="secondary"
              icon={Plus}
              type="button"
              onClick={addComponentRow}
            >
              Add Component Service
            </Button>
          }
        >
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
            Select individual laboratory tests included in this bundle. When ordered in a quotation, the customer is billed the fixed package price:
          </p>

          {validationErrors.components && (
            <div style={{ color: 'var(--danger)', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
              {validationErrors.components}
            </div>
          )}

          {components.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {components.map((c, idx) => {
                const svc = availableServices.find(s => s.id === c.serviceId);
                const refPrice = svc ? Number(svc.standardPrice) : 0;
                const lineTotal = refPrice * Number(c.quantity || 1);

                return (
                  <div
                    key={idx}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '3fr 1fr 1.5fr auto',
                      gap: '0.75rem',
                      alignItems: 'center',
                      padding: '0.75rem',
                      background: '#ffffff',
                      border: '1px solid var(--color-border)',
                      borderRadius: '6px',
                      boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'
                    }}
                  >
                    <div>
                      <Select
                        value={c.serviceId}
                        onChange={e => updateComponentRow(idx, 'serviceId', e.target.value)}
                        options={availableServices.map(s => ({
                          value: s.id,
                          label: `${s.serviceCode} — ${s.name} (Ref: ₹${Number(s.standardPrice).toLocaleString('en-IN')})`
                        }))}
                      />
                      {validationErrors[`comp_${idx}`] && (
                        <span style={{ color: 'var(--danger)', fontSize: '0.75rem' }}>
                          {validationErrors[`comp_${idx}`]}
                        </span>
                      )}
                    </div>

                    <div>
                      <Input
                        type="number"
                        min="1"
                        step="1"
                        placeholder="Qty"
                        value={c.quantity}
                        onChange={e => updateComponentRow(idx, 'quantity', e.target.value)}
                      />
                      {validationErrors[`comp_qty_${idx}`] && (
                        <span style={{ color: 'var(--danger)', fontSize: '0.75rem' }}>
                          {validationErrors[`comp_qty_${idx}`]}
                        </span>
                      )}
                    </div>

                    <div style={{ textAlign: 'right', fontSize: '0.88rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Ref Subtotal: </span>
                      <span style={{ fontWeight: 600 }}>₹{lineTotal.toLocaleString('en-IN')}</span>
                    </div>

                    <Button
                      size="sm"
                      variant="danger"
                      icon={Trash2}
                      type="button"
                      onClick={() => removeComponentRow(idx)}
                    />
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '2rem', border: '1px dashed var(--color-border)', borderRadius: '6px' }}>
              <p style={{ color: 'var(--text-muted)', margin: '0 0 1rem 0' }}>
                No component services added yet. Click below to add laboratory tests to this package.
              </p>
              <Button size="sm" variant="secondary" icon={Plus} type="button" onClick={addComponentRow}>
                Add First Service
              </Button>
            </div>
          )}
        </Card>

        {/* 4. Add-on Configurations */}
        <Card
          title="4. Special Add-on Configurations (e.g. C/N Ratio)"
          actions={
            <Button
              size="sm"
              variant="secondary"
              icon={Plus}
              type="button"
              disabled={addonEligibleServices.length === 0}
              onClick={addAddonRow}
            >
              Add Add-on Rule
            </Button>
          }
        >
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
            Configure supplementary services (like C/N Ratio) available to attach to this package with optional package-specific price overrides:
          </p>

          {addons.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {addons.map((a, idx) => {
                const svc = availableServices.find(s => s.id === a.addonServiceId);
                const stdPrice = svc ? Number(svc.standardPrice) : 300;

                return (
                  <div
                    key={idx}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '2.5fr 1fr 1.5fr 1fr auto',
                      gap: '0.75rem',
                      alignItems: 'center',
                      padding: '0.75rem',
                      background: '#ffffff',
                      border: '1px solid var(--color-border)',
                      borderRadius: '6px',
                      boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'
                    }}
                  >
                    <Select
                      value={a.addonServiceId}
                      onChange={e => updateAddonRow(idx, 'addonServiceId', e.target.value)}
                      options={addonEligibleServices.map(s => ({
                        value: s.id,
                        label: `${s.serviceCode} — ${s.name} (Std: ₹${Number(s.standardPrice).toLocaleString('en-IN')})`
                      }))}
                    />

                    <Input
                      type="number"
                      min="1"
                      step="1"
                      placeholder="Default Qty"
                      value={a.defaultQuantity}
                      onChange={e => updateAddonRow(idx, 'defaultQuantity', e.target.value)}
                    />

                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder={`Override Price (Default: ₹${stdPrice})`}
                      value={a.overridePrice}
                      onChange={e => updateAddonRow(idx, 'overridePrice', e.target.value)}
                    />

                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.82rem' }}>
                      <input
                        type="checkbox"
                        checked={a.isMandatory}
                        onChange={e => updateAddonRow(idx, 'isMandatory', e.target.checked)}
                      />
                      <span>Mandatory</span>
                    </label>

                    <Button
                      size="sm"
                      variant="danger"
                      icon={Trash2}
                      type="button"
                      onClick={() => removeAddonRow(idx)}
                    />
                  </div>
                );
              })}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: 0 }}>
              No special add-on configurations defined. Click "Add Add-on Rule" to configure add-on services.
            </p>
          )}
        </Card>

        {/* Submit Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
          <Button
            variant="secondary"
            type="button"
            onClick={() => navigate(isNewVersionMode ? `/crm/catalogue/packages/${id}` : '/crm/catalogue/packages')}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            icon={Save}
            type="submit"
            disabled={loading}
          >
            {loading ? 'Saving...' : (isNewVersionMode ? 'Publish New Version' : 'Create Package')}
          </Button>
        </div>
      </form>
    </div>
  );
}

