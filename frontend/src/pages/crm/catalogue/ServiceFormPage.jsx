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
  FlaskConical,
  ArrowLeft,
  Save,
  Plus,
  Trash2,
  AlertCircle
} from 'lucide-react';
import catalogueService, { normalizeArrayResponse } from '../../../services/catalogueService';

export default function ServiceFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditMode = Boolean(id);

  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(isEditMode);
  const [error, setError] = useState(null);

  // Master Data Options
  const [categories, setCategories] = useState([]);
  const [billingUnits, setBillingUnits] = useState([]);
  const [reportingUnits, setReportingUnits] = useState([]);
  const [sampleTypes, setSampleTypes] = useState([]);
  const [testingMethods, setTestingMethods] = useState([]);
  const [currencies, setCurrencies] = useState([]);

  // Form State
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [billingUnitId, setBillingUnitId] = useState('');
  const [currencyId, setCurrencyId] = useState('');
  const [minimumBillingQuantity, setMinimumBillingQuantity] = useState(1);
  const [standardPrice, setStandardPrice] = useState('');
  const [originalPrice, setOriginalPrice] = useState(null);
  const [priceChangeReason, setPriceChangeReason] = useState('');
  const [effectiveDate, setEffectiveDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [isActive, setIsActive] = useState(true);
  const [isAddonEligible, setIsAddonEligible] = useState(false);
  const [canHaveAddons, setCanHaveAddons] = useState(true);
  const [sourceNote, setSourceNote] = useState('');

  // Multi-selects & sub-tables
  const [selectedSampleTypeIds, setSelectedSampleTypeIds] = useState([]);
  const [selectedMethods, setSelectedMethods] = useState([]); // [{ testingMethodId, isDefault }]
  const [reportingParams, setReportingParams] = useState([]); // [{ parameterName, reportingUnitId, testingMethodId, minRange, maxRange, isActive }]

  // Validation Errors
  const [validationErrors, setValidationErrors] = useState({});

  // 1. Fetch Masters on Mount
  useEffect(() => {
    async function loadMasters() {
      try {
        const [catRes, buRes, ruRes, stRes, tmRes, currRes] = await Promise.all([
          catalogueService.getCategories({ includeInactive: true }),
          catalogueService.getBillingUnits({ includeInactive: false }),
          catalogueService.getReportingUnits({ includeInactive: false }),
          catalogueService.getSampleTypes({ includeInactive: false }),
          catalogueService.getTestingMethods({ includeInactive: false }),
          catalogueService.getCurrencies({ includeInactive: false })
        ]);

        setCategories(normalizeArrayResponse(catRes, 'categories'));
        setBillingUnits(normalizeArrayResponse(buRes, 'billingUnits'));
        setReportingUnits(normalizeArrayResponse(ruRes, 'reportingUnits'));
        setSampleTypes(normalizeArrayResponse(stRes, 'sampleTypes'));
        setTestingMethods(normalizeArrayResponse(tmRes, 'testingMethods'));
        setCurrencies(normalizeArrayResponse(currRes, 'currencies'));

        // Default currency selection
        const inr = (currRes.data || []).find(c => c.code === 'INR' || c.isDefault);
        if (inr && !isEditMode) {
          setCurrencyId(inr.id);
        }

        // Default billing unit selection
        const testBu = (buRes.data || []).find(b => b.code === 'TEST');
        if (testBu && !isEditMode) {
          setBillingUnitId(testBu.id);
        }
      } catch (err) {
        console.error('Failed to load masters', err);
        setError('Failed to load master metadata required for service configuration.');
      }
    }
    loadMasters();
  }, [isEditMode]);

  // 2. Load existing service for edit
  useEffect(() => {
    if (isEditMode) {
      async function loadService() {
        setInitialLoading(true);
        try {
          const res = await catalogueService.getServiceById(id);
          const s = res.data;
          setName(s.name);
          setDescription(s.description || '');
          setCategoryId(s.categoryId);
          setBillingUnitId(s.billingUnitId);
          setCurrencyId(s.currencyId);
          setMinimumBillingQuantity(s.minimumBillingQuantity || 1);
          setStandardPrice(s.standardPrice);
          setOriginalPrice(s.standardPrice);
          setEffectiveDate(s.effectiveDate || new Date().toISOString().split('T')[0]);
          setIsActive(s.isActive);
          setIsAddonEligible(s.isAddonEligible);
          setCanHaveAddons(s.canHaveAddons);
          setSourceNote(s.sourceNote || '');

          setSelectedSampleTypeIds((s.sampleTypes || []).map(st => st.sampleTypeId));
          setSelectedMethods((s.testingMethods || []).map(tm => ({
            testingMethodId: tm.testingMethodId,
            isDefault: tm.isDefault
          })));
          setReportingParams((s.reportingParameters || []).map(rp => ({
            id: rp.id,
            parameterName: rp.parameterName,
            reportingUnitId: rp.reportingUnitId,
            testingMethodId: rp.testingMethodId || '',
            minRange: rp.minRange !== null ? String(rp.minRange) : '',
            maxRange: rp.maxRange !== null ? String(rp.maxRange) : '',
            isActive: rp.isActive
          })));
        } catch (err) {
          console.error('Failed to load service', err);
          setError('Failed to load service data.');
        } finally {
          setInitialLoading(false);
        }
      }
      loadService();
    }
  }, [id, isEditMode]);

  // Handle reporting parameter row manipulation
  const addReportingParamRow = () => {
    const defaultUnit = reportingUnits.length > 0 ? reportingUnits[0].id : '';
    setReportingParams(prev => [
      ...prev,
      {
        parameterName: '',
        reportingUnitId: defaultUnit,
        testingMethodId: '',
        minRange: '',
        maxRange: '',
        isActive: true
      }
    ]);
  };

  const removeReportingParamRow = (index) => {
    setReportingParams(prev => prev.filter((_, i) => i !== index));
  };

  const updateReportingParamRow = (index, field, value) => {
    setReportingParams(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  // Handle testing method toggle & default designation
  const toggleTestingMethod = (methodId) => {
    setSelectedMethods(prev => {
      const exists = prev.find(m => m.testingMethodId === methodId);
      if (exists) {
        return prev.filter(m => m.testingMethodId !== methodId);
      } else {
        const isFirst = prev.length === 0;
        return [...prev, { testingMethodId: methodId, isDefault: isFirst }];
      }
    });
  };

  const setDefaultMethod = (methodId) => {
    setSelectedMethods(prev =>
      prev.map(m => ({
        ...m,
        isDefault: m.testingMethodId === methodId
      }))
    );
  };

  // Form Validation
  const validateForm = () => {
    const errors = {};
    if (!name.trim()) errors.name = 'Service name is mandatory.';
    if (!categoryId) errors.categoryId = 'Category is required.';
    if (!billingUnitId) errors.billingUnitId = 'Billing unit is required.';
    if (!currencyId) errors.currencyId = 'Currency is required.';

    const qty = parseInt(minimumBillingQuantity, 10);
    if (isNaN(qty) || qty < 1) {
      errors.minimumBillingQuantity = 'Minimum billing quantity must be a positive whole number (≥ 1).';
    }

    const price = parseFloat(standardPrice);
    if (isNaN(price) || price < 0) {
      errors.standardPrice = 'Standard price must be a valid non-negative number.';
    }

    if (isEditMode && originalPrice !== null && parseFloat(standardPrice) !== parseFloat(originalPrice) && !priceChangeReason.trim()) {
      errors.priceChangeReason = 'A reason is mandatory when modifying the standard price.';
    }

    // Check reporting parameter names
    for (let i = 0; i < reportingParams.length; i++) {
      if (!reportingParams[i].parameterName.trim()) {
        errors[`param_${i}`] = 'Parameter name cannot be blank.';
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    setError(null);

    const payload = {
      name: name.trim(),
      description: description.trim() || undefined,
      categoryId,
      billingUnitId,
      currencyId,
      minimumBillingQuantity: parseInt(minimumBillingQuantity, 10),
      standardPrice: parseFloat(standardPrice),
      effectiveDate,
      isActive,
      isAddonEligible,
      canHaveAddons,
      sourceNote: sourceNote.trim() || undefined,
      sampleTypeIds: selectedSampleTypeIds,
      testingMethods: selectedMethods,
      reportingParameters: reportingParams.map(rp => ({
        parameterName: rp.parameterName.trim(),
        reportingUnitId: rp.reportingUnitId,
        testingMethodId: rp.testingMethodId || undefined,
        minRange: rp.minRange !== '' ? parseFloat(rp.minRange) : undefined,
        maxRange: rp.maxRange !== '' ? parseFloat(rp.maxRange) : undefined,
        isActive: rp.isActive
      }))
    };

    if (isEditMode) {
      payload.priceChangeReason = priceChangeReason.trim() || undefined;
    }

    try {
      if (isEditMode) {
        await catalogueService.updateService(id, payload);
      } else {
        await catalogueService.createService(payload);
      }
      navigate('/crm/catalogue/services');
    } catch (err) {
      console.error('Failed to save service', err);
      const msg = err.response?.data?.message || err.message || 'Failed to save service.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  if (initialLoading) {
    return (
      <div className="page-body">
        <LoadingState message="Loading service configuration..." />
      </div>
    );
  }

  return (
    <div className="page-body">
      <PageHeader
        title={isEditMode ? `Edit Service — ${name}` : 'Create Laboratory Service'}
        subtitle="Define commercial, analytical parameter, and scientific testing method attributes."
        icon={FlaskConical}
        breadcrumbs={[
          { label: 'Portal', to: '/portal' },
          { label: 'CRM', to: '/crm' },
          { label: 'Catalogue', to: '/crm/catalogue/services' },
          { label: isEditMode ? 'Edit' : 'New Service' }
        ]}
        actions={
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <Button
              variant="secondary"
              icon={ArrowLeft}
              onClick={() => navigate('/crm/catalogue/services')}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              icon={Save}
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? 'Saving...' : 'Save Service'}
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
        {/* 1. Core Identification & Categorization */}
        <Card title="1. Service Classification & Identification">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
            <FormField label="Service Name" required error={validationErrors.name}>
              <Input
                placeholder="e.g. Biochemical Oxygen Demand (BOD)"
                value={name}
                onChange={e => setName(e.target.value)}
              />
            </FormField>

            <FormField label="Category" required error={validationErrors.categoryId}>
              <Select
                value={categoryId}
                onChange={e => setCategoryId(e.target.value)}
                options={[
                  { value: '', label: 'Select Category' },
                  ...categories
                    .filter(c => isEditMode ? (!c.isDeleted || c.id === categoryId) : (c.isActive && !c.isDeleted))
                    .map(c => ({ value: c.id, label: `${c.code} — ${c.name}` }))
                ]}
              />
            </FormField>

            <FormField label="Source / Reference Note (Optional)">
              <Input
                placeholder="e.g. SR 50/51"
                value={sourceNote}
                onChange={e => setSourceNote(e.target.value)}
              />
            </FormField>
          </div>

          <div style={{ marginTop: '1.25rem' }}>
            <FormField label="Service Description">
              <textarea
                className="revy-textarea crm-textarea"
                style={{ width: '100%', minHeight: '80px', padding: '0.65rem 0.85rem', backgroundColor: '#ffffff', border: '1px solid var(--color-border)' }}
                placeholder="Detailed laboratory testing description, analytical scope, and notes..."
                value={description}
                onChange={e => setDescription(e.target.value)}
              />
            </FormField>
          </div>
        </Card>

        {/* 2. Commercial & Pricing Configuration */}
        <Card title="2. Commercial, Billing & Effective Pricing">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem' }}>
            <FormField label="Standard Price (₹, GST extra)" required error={validationErrors.standardPrice}>
              <Input
                type="number"
                step="0.01"
                min="0"
                placeholder="1000.00"
                value={standardPrice}
                onChange={e => setStandardPrice(e.target.value)}
              />
            </FormField>

            <FormField label="Billing Unit" required error={validationErrors.billingUnitId}>
              <Select
                value={billingUnitId}
                onChange={e => setBillingUnitId(e.target.value)}
                options={[
                  { value: '', label: 'Select Billing Unit' },
                  ...billingUnits.map(b => ({ value: b.id, label: `${b.code} — ${b.name}` }))
                ]}
              />
            </FormField>

            <FormField label="Minimum Billing Qty" required error={validationErrors.minimumBillingQuantity}>
              <Input
                type="number"
                min="1"
                step="1"
                value={minimumBillingQuantity}
                onChange={e => setMinimumBillingQuantity(e.target.value)}
              />
            </FormField>

            <FormField label="Currency" required error={validationErrors.currencyId}>
              <Select
                value={currencyId}
                onChange={e => setCurrencyId(e.target.value)}
                options={[
                  { value: '', label: 'Select Currency' },
                  ...currencies.map(c => ({ value: c.id, label: `${c.code} (${c.symbol})` }))
                ]}
              />
            </FormField>

            <FormField label="Price Effective Date">
              <DatePicker
                value={effectiveDate}
                onChange={e => setEffectiveDate(e.target.value)}
              />
            </FormField>
          </div>

          {isEditMode && originalPrice !== null && parseFloat(standardPrice) !== parseFloat(originalPrice) && (
            <div style={{ marginTop: '1.25rem', padding: '1rem', background: '#eff6ff', borderRadius: '6px', border: '1px solid #bfdbfe' }}>
              <FormField label="Reason for Standard Price Change" required error={validationErrors.priceChangeReason}>
                <Input
                  placeholder="e.g. Annual chemical reagent cost adjustment, equipment upgrade"
                  value={priceChangeReason}
                  onChange={e => setPriceChangeReason(e.target.value)}
                />
              </FormField>
            </div>
          )}

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2rem', marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--color-border)' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.9rem' }}>
              <input
                type="checkbox"
                checked={isActive}
                onChange={e => setIsActive(e.target.checked)}
              />
              <span style={{ fontWeight: 600 }}>Active in Catalogue</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.9rem' }}>
              <input
                type="checkbox"
                checked={isAddonEligible}
                onChange={e => setIsAddonEligible(e.target.checked)}
              />
              <span style={{ fontWeight: 600 }}>Eligible as Add-on to other services/packages</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.9rem' }}>
              <input
                type="checkbox"
                checked={canHaveAddons}
                onChange={e => setCanHaveAddons(e.target.checked)}
              />
              <span style={{ fontWeight: 600 }}>Allows Add-ons (e.g. C/N Ratio) to attach</span>
            </label>
          </div>
        </Card>

        {/* 3. Supported Sample Types */}
        <Card title="3. Supported Sample Types">
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
            Select all sample matrices verified for this analytical test:
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.75rem' }}>
            {sampleTypes.map(st => {
              const isChecked = selectedSampleTypeIds.includes(st.id);
              return (
                <label
                  key={st.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.5rem 0.75rem',
                    borderRadius: '6px',
                    background: isChecked ? '#fef3c7' : '#ffffff',
                    border: `1px solid ${isChecked ? '#d97706' : 'var(--color-border)'}`,
                    cursor: 'pointer'
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => {
                      setSelectedSampleTypeIds(prev =>
                        prev.includes(st.id) ? prev.filter(x => x !== st.id) : [...prev, st.id]
                      );
                    }}
                  />
                  <span style={{ fontSize: '0.85rem', fontWeight: isChecked ? 600 : 400 }}>{st.name}</span>
                </label>
              );
            })}
          </div>
        </Card>

        {/* 4. Testing Methods */}
        <Card title="4. Standard Testing Methods & Default Designation">
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
            Choose applicable methods. Exactly one active default method may be designated:
          </p>
          {testingMethods.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              {testingMethods.map(tm => {
                const assigned = selectedMethods.find(m => m.testingMethodId === tm.id);
                const isSelected = Boolean(assigned);
                const isDefault = assigned?.isDefault || false;

                return (
                  <div
                    key={tm.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.75rem 1rem',
                      borderRadius: '6px',
                      background: isSelected ? '#fef3c7' : '#ffffff',
                      border: `1px solid ${isSelected ? '#d97706' : 'var(--color-border)'}`
                    }}
                  >
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer', flex: 1 }}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleTestingMethod(tm.id)}
                      />
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{tm.methodName}</div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                          Reference: {tm.standardReference || 'N/A'} {tm.revision ? `(${tm.revision})` : ''}
                        </div>
                      </div>
                    </label>

                    {isSelected && (
                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.82rem' }}>
                        <input
                          type="radio"
                          name="default_method"
                          checked={isDefault}
                          onChange={() => setDefaultMethod(tm.id)}
                        />
                        <span style={{ fontWeight: isDefault ? 700 : 400, color: isDefault ? 'var(--color-primary)' : 'var(--text-secondary)' }}>
                          Default Method
                        </span>
                      </label>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              No testing methods configured in Master Data yet. CRM Admin may add methods in Master Data.
            </p>
          )}
        </Card>

        {/* 5. Reporting Parameters & Expected Ranges */}
        <Card
          title="5. Analytical Reporting Parameters & Range Limits"
          actions={
            <Button
              size="sm"
              variant="secondary"
              icon={Plus}
              type="button"
              onClick={addReportingParamRow}
            >
              Add Parameter
            </Button>
          }
        >
          {reportingParams.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {reportingParams.map((rp, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '2fr 1.2fr 1fr 1fr 1.5fr auto',
                    gap: '0.75rem',
                    alignItems: 'center',
                    padding: '0.65rem',
                    background: '#ffffff',
                    border: '1px solid var(--color-border)',
                    borderRadius: '6px',
                    boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'
                  }}
                >
                  <Input
                    placeholder="Parameter Name"
                    value={rp.parameterName}
                    onChange={e => updateReportingParamRow(idx, 'parameterName', e.target.value)}
                  />

                  <Select
                    value={rp.reportingUnitId}
                    onChange={e => updateReportingParamRow(idx, 'reportingUnitId', e.target.value)}
                    options={reportingUnits.map(ru => ({ value: ru.id, label: `${ru.symbol} (${ru.name})` }))}
                  />

                  <Input
                    type="number"
                    step="any"
                    placeholder="Min"
                    value={rp.minRange}
                    onChange={e => updateReportingParamRow(idx, 'minRange', e.target.value)}
                  />

                  <Input
                    type="number"
                    step="any"
                    placeholder="Max"
                    value={rp.maxRange}
                    onChange={e => updateReportingParamRow(idx, 'maxRange', e.target.value)}
                  />

                  <Select
                    value={rp.testingMethodId}
                    onChange={e => updateReportingParamRow(idx, 'testingMethodId', e.target.value)}
                    options={[
                      { value: '', label: 'Default (All Methods)' },
                      ...testingMethods.map(tm => ({ value: tm.id, label: tm.methodName }))
                    ]}
                  />

                  <Button
                    size="sm"
                    variant="danger"
                    icon={Trash2}
                    type="button"
                    onClick={() => removeReportingParamRow(idx)}
                  />
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: 0 }}>
              No parameters configured. Click "Add Parameter" to configure output parameters and ranges.
            </p>
          )}
        </Card>

        {/* Submit Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
          <Button
            variant="secondary"
            type="button"
            onClick={() => navigate('/crm/catalogue/services')}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            icon={Save}
            type="submit"
            disabled={loading}
          >
            {loading ? 'Saving Service...' : 'Save Service'}
          </Button>
        </div>
      </form>
    </div>
  );
}

