import React, { useState, useEffect } from 'react';
import API from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Coffee,
  Sun,
  Sunset,
  CheckCircle2,
  AlertCircle,
  Clock,
  History,
  Info,
  Calendar
} from 'lucide-react';
import { PageHeader, Card, Button, Select, Input, StatusBadge, DataTable } from '../components/ui';

const BeverageLogPage = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [submittingSession, setSubmittingSession] = useState(null); // 'MORNING' | 'EVENING' | null
  const [statusData, setStatusData] = useState(null);
  const [myHistory, setMyHistory] = useState([]);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Form states for Morning and Evening submissions
  const [morningBeverageId, setMorningBeverageId] = useState('');
  const [morningQuantity, setMorningQuantity] = useState(1);
  const [morningNotes, setMorningNotes] = useState('');

  const [eveningBeverageId, setEveningBeverageId] = useState('');
  const [eveningQuantity, setEveningQuantity] = useState(1);
  const [eveningNotes, setEveningNotes] = useState('');

  useEffect(() => {
    loadTodayData();
    loadHistory();
  }, []);

  const loadTodayData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await API.get('/breakfast/beverages/today-summary');
      if (res.data.success) {
        setStatusData(res.data);
        const bevs = res.data.activeBeverages || [];
        if (bevs.length > 0) {
          if (!morningBeverageId) setMorningBeverageId(bevs[0].id);
          if (!eveningBeverageId) setEveningBeverageId(bevs[0].id);
        }
      } else {
        setError(res.data.message || 'Unable to load today beverage status.');
      }
    } catch (err) {
      console.error('Failed to load beverage status:', err);
      setError(err.response?.data?.message || 'Failed to connect to beverage service.');
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const res = await API.get('/breakfast/beverages/my-entries');
      if (res.data.success) {
        setMyHistory(res.data.entries || []);
      }
    } catch (err) {
      console.error('Failed to load my beverage history:', err);
    }
  };

  const handleSessionSubmit = async (session) => {
    setError(null);
    setSuccessMessage(null);

    const beverageId = session === 'MORNING' ? morningBeverageId : eveningBeverageId;
    const quantity = parseInt(session === 'MORNING' ? morningQuantity : eveningQuantity, 10);
    const notes = session === 'MORNING' ? morningNotes : eveningNotes;

    if (!beverageId) {
      setError(`Please select a beverage for the ${session.toLowerCase()} session.`);
      return;
    }

    if (!quantity || isNaN(quantity) || quantity <= 0) {
      setError('Quantity must be a positive whole number (at least 1 cup).');
      return;
    }

    try {
      setSubmittingSession(session);
      const res = await API.post('/breakfast/beverages/entries', {
        beverageId,
        session,
        quantity,
        notes: notes.trim() || undefined
      });

      if (res.data.success) {
        setSuccessMessage(res.data.message || `Successfully logged ${quantity} cup(s) for ${session} session!`);
        await loadTodayData();
        await loadHistory();
      } else {
        setError(res.data.message || 'Failed to submit beverage entry.');
      }
    } catch (err) {
      console.error('Submit beverage error:', err);
      setError(err.response?.data?.message || 'Failed to log beverage consumption. Please check duplicate entries.');
    } finally {
      setSubmittingSession(null);
    }
  };

  const activeBeverages = statusData?.activeBeverages || [];
  const beverageSelectOptions = activeBeverages.map(b => ({
    value: b.id,
    label: `${b.name} (${b.unit || 'Cups'})`
  }));

  const morningEntry = statusData?.morningEntry;
  const eveningEntry = statusData?.eveningEntry;

  const historyColumns = [
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
      header: 'Logged At',
      accessor: 'createdAt',
      cell: (row) => (
        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          {row.createdAt ? new Date(row.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'}
        </span>
      )
    },
    {
      header: 'Notes',
      accessor: 'notes',
      cell: (row) => (
        <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          {row.notes || '-'}
        </span>
      )
    }
  ];

  return (
    <div className="page-body">
      {/* 1. Page Header */}
      <PageHeader
        title="Employee Beverage Log"
        subtitle={`Logged in as: ${user?.name || 'Employee'} (${user?.employeeId || 'ID'}) • Today's operational date: ${statusData?.businessDate || 'Today (Asia/Kolkata)'}`}
        icon={Coffee}
        breadcrumbs={[
          { label: 'BMS', to: '/bms/dashboard' },
          { label: 'Beverage Log' }
        ]}
      />

      {/* 2. Notifications & Instructions */}
      {error && (
        <div className="alert alert-danger" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <AlertCircle size={18} color="var(--danger)" />
          <span>{error}</span>
        </div>
      )}

      {successMessage && (
        <div className="alert alert-success" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <CheckCircle2 size={18} color="var(--success)" />
          <span>{successMessage}</span>
        </div>
      )}

      <div
        className="glass-card"
        style={{
          padding: '0.85rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          borderLeft: '4px solid var(--accent-primary)',
          fontSize: '0.85rem'
        }}
      >
        <Info size={18} color="var(--accent-primary)" style={{ flexShrink: 0 }} />
        <div>
          <span><strong>Operational Rules:</strong> Beverage logs are submitted strictly for today's date ({statusData?.businessDate || 'Today'}) in Asia/Kolkata timezone. Exactly one beverage per employee per session. All beverages are measured in <strong>Cups</strong>. Submission is optional. Submitted entries are immutable and cannot be edited or deleted by employees.</span>
        </div>
      </div>

      {/* 3. Session Cards Grid: Morning & Evening */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        
        {/* Morning Session Card */}
        <div className="panel-card" style={{ padding: '1.5rem', borderTop: '4px solid #f59e0b' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sun size={24} color="#f59e0b" />
              <div>
                <h3 style={{ margin: 0, fontSize: '1.15rem' }}>Morning Session</h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Tea / Coffee / Green Tea</span>
              </div>
            </div>
            {morningEntry ? (
              <StatusBadge variant="success">✓ Submitted</StatusBadge>
            ) : (
              <StatusBadge variant="neutral">Not Logged</StatusBadge>
            )}
          </div>

          {morningEntry ? (
            /* Submitted Read-Only View */
            <div style={{ background: 'rgba(16, 185, 129, 0.06)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '8px', padding: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', color: '#10b981', fontWeight: 700 }}>
                <CheckCircle2 size={18} />
                <span>Morning Beverage Logged (Read-Only)</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.9rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Beverage:</span>
                  <strong style={{ color: 'var(--text-primary)' }}>{morningEntry.beverageNameSnapshot}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Quantity:</span>
                  <strong style={{ color: 'var(--accent-primary)' }}>{morningEntry.quantity} {morningEntry.unit || 'Cups'}</strong>
                </div>
                {morningEntry.notes && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Notes:</span>
                    <span>{morningEntry.notes}</span>
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)', borderTop: '1px dashed var(--border-color)', paddingTop: '0.5rem', marginTop: '0.25rem' }}>
                  <span>Logged at:</span>
                  <span>{morningEntry.createdAt ? new Date(morningEntry.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'}</span>
                </div>
              </div>
              <div style={{ marginTop: '0.85rem', fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                🔒 Submitted records cannot be modified or deleted by employees.
              </div>
            </div>
          ) : (
            /* Submission Form */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                  Select Beverage
                </label>
                <Select
                  size="md"
                  value={morningBeverageId}
                  onChange={(e) => setMorningBeverageId(e.target.value)}
                  options={beverageSelectOptions}
                  disabled={submittingSession === 'MORNING' || loading}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                  Quantity (in Cups)
                </label>
                <Input
                  type="number"
                  min="1"
                  step="1"
                  value={morningQuantity}
                  onChange={(e) => setMorningQuantity(e.target.value)}
                  disabled={submittingSession === 'MORNING' || loading}
                  placeholder="1"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                  Notes (Optional)
                </label>
                <Input
                  type="text"
                  value={morningNotes}
                  onChange={(e) => setMorningNotes(e.target.value)}
                  disabled={submittingSession === 'MORNING' || loading}
                  placeholder="e.g. Less sugar, extra hot"
                />
              </div>

              <Button
                variant="primary"
                onClick={() => handleSessionSubmit('MORNING')}
                disabled={submittingSession === 'MORNING' || loading || activeBeverages.length === 0}
                style={{ width: '100%', marginTop: '0.5rem' }}
              >
                {submittingSession === 'MORNING' ? 'Submitting...' : 'Log Morning Beverage'}
              </Button>
            </div>
          )}
        </div>

        {/* Evening Session Card */}
        <div className="panel-card" style={{ padding: '1.5rem', borderTop: '4px solid #6366f1' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sunset size={24} color="#6366f1" />
              <div>
                <h3 style={{ margin: 0, fontSize: '1.15rem' }}>Evening Session</h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Tea / Coffee / Green Tea</span>
              </div>
            </div>
            {eveningEntry ? (
              <StatusBadge variant="success">✓ Submitted</StatusBadge>
            ) : (
              <StatusBadge variant="neutral">Not Logged</StatusBadge>
            )}
          </div>

          {eveningEntry ? (
            /* Submitted Read-Only View */
            <div style={{ background: 'rgba(16, 185, 129, 0.06)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '8px', padding: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', color: '#10b981', fontWeight: 700 }}>
                <CheckCircle2 size={18} />
                <span>Evening Beverage Logged (Read-Only)</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.9rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Beverage:</span>
                  <strong style={{ color: 'var(--text-primary)' }}>{eveningEntry.beverageNameSnapshot}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Quantity:</span>
                  <strong style={{ color: 'var(--accent-primary)' }}>{eveningEntry.quantity} {eveningEntry.unit || 'Cups'}</strong>
                </div>
                {eveningEntry.notes && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Notes:</span>
                    <span>{eveningEntry.notes}</span>
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)', borderTop: '1px dashed var(--border-color)', paddingTop: '0.5rem', marginTop: '0.25rem' }}>
                  <span>Logged at:</span>
                  <span>{eveningEntry.createdAt ? new Date(eveningEntry.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'}</span>
                </div>
              </div>
              <div style={{ marginTop: '0.85rem', fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                🔒 Submitted records cannot be modified or deleted by employees.
              </div>
            </div>
          ) : (
            /* Submission Form */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                  Select Beverage
                </label>
                <Select
                  size="md"
                  value={eveningBeverageId}
                  onChange={(e) => setEveningBeverageId(e.target.value)}
                  options={beverageSelectOptions}
                  disabled={submittingSession === 'EVENING' || loading}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                  Quantity (in Cups)
                </label>
                <Input
                  type="number"
                  min="1"
                  step="1"
                  value={eveningQuantity}
                  onChange={(e) => setEveningQuantity(e.target.value)}
                  disabled={submittingSession === 'EVENING' || loading}
                  placeholder="1"
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                  Notes (Optional)
                </label>
                <Input
                  type="text"
                  value={eveningNotes}
                  onChange={(e) => setEveningNotes(e.target.value)}
                  disabled={submittingSession === 'EVENING' || loading}
                  placeholder="e.g. Less sugar, extra hot"
                />
              </div>

              <Button
                variant="primary"
                onClick={() => handleSessionSubmit('EVENING')}
                disabled={submittingSession === 'EVENING' || loading || activeBeverages.length === 0}
                style={{ width: '100%', marginTop: '0.5rem' }}
              >
                {submittingSession === 'EVENING' ? 'Submitting...' : 'Log Evening Beverage'}
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* 4. My Consumption History Table */}
      <Card noPadding>
        <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <History size={18} color="var(--accent-primary)" />
            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>My Submitted Beverage History</h3>
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Showing {myHistory.length} recorded entries
          </span>
        </div>

        <DataTable
          columns={historyColumns}
          data={myHistory}
          emptyMessage="No beverage logs recorded yet. Use the form above to record today's consumption."
        />
      </Card>
    </div>
  );
};

export default BeverageLogPage;
