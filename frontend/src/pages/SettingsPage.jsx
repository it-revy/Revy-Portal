import React, { useState, useEffect } from 'react';
import API from '../services/api';
import { Settings, Clock, Plus, Save, CheckCircle2 } from 'lucide-react';

const TIME_REGEX = /^([01]\d|2[0-3]):([0-5]\d)$/;

const format12Hour = (timeStr) => {
  if (!timeStr || !timeStr.includes(':')) return timeStr || '';
  const [hStr, mStr] = timeStr.split(':');
  const h = parseInt(hStr, 10);
  const m = parseInt(mStr, 10);
  if (isNaN(h) || isNaN(m)) return timeStr;
  const ampm = h >= 12 ? 'PM' : 'AM';
  const hour12 = h % 12 || 12;
  const minuteFormatted = String(m).padStart(2, '0');
  return `${hour12}:${minuteFormatted} ${ampm}`;
};

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    requestOpenTime: '17:30',
    requestCloseTime: '08:20',
    cutoffTime: '08:20',
    timezone: 'Asia/Kolkata'
  });
  const [reasons, setReasons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  // New Reason modal state
  const [newReason, setNewReason] = useState({ code: '', label: '', isCustomAllowed: false, displayOrder: 10 });
  const [showReasonModal, setShowReasonModal] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await API.get('/settings');
      if (res.data.success) {
        setSettings({
          requestOpenTime: res.data.settings.requestOpenTime || '17:30',
          requestCloseTime: res.data.settings.requestCloseTime || res.data.settings.cutoffTime || '08:20',
          cutoffTime: res.data.settings.requestCloseTime || res.data.settings.cutoffTime || '08:20',
          timezone: res.data.settings.timezone || 'Asia/Kolkata'
        });
        setReasons(res.data.reasons);
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setMessage(null);

    const openTrim = (settings.requestOpenTime || '').trim();
    const closeTrim = (settings.requestCloseTime || '').trim();

    if (!TIME_REGEX.test(openTrim)) {
      setMessage({ type: 'error', text: 'Request opening time must be a valid 24-hour time in format HH:mm (e.g. 17:30)' });
      return;
    }
    if (!TIME_REGEX.test(closeTrim)) {
      setMessage({ type: 'error', text: 'Request closing time must be a valid 24-hour time in format HH:mm (e.g. 08:20)' });
      return;
    }
    if (openTrim === closeTrim) {
      setMessage({ type: 'error', text: 'Request opening time and closing time cannot be identical.' });
      return;
    }

    setSaving(true);
    try {
      const payload = {
        requestOpenTime: openTrim,
        requestCloseTime: closeTrim,
        cutoffTime: closeTrim,
        timezone: 'Asia/Kolkata'
      };
      const res = await API.put('/settings', payload);
      if (res.data.success) {
        setMessage({
          type: 'success',
          text: 'Daily breakfast request cycle settings saved successfully. Takes effect immediately.'
        });
        setSettings({
          requestOpenTime: res.data.settings.requestOpenTime || openTrim,
          requestCloseTime: res.data.settings.requestCloseTime || closeTrim,
          cutoffTime: res.data.settings.requestCloseTime || closeTrim,
          timezone: res.data.settings.timezone || 'Asia/Kolkata'
        });
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.message || 'Failed to update settings' });
    } finally {
      setSaving(false);
    }
  };

  const handleAddReason = async (e) => {
    e.preventDefault();
    try {
      const res = await API.post('/settings/reasons', newReason);
      if (res.data.success) {
        setShowReasonModal(false);
        setNewReason({ code: '', label: '', isCustomAllowed: false, displayOrder: 10 });
        setMessage({ type: 'success', text: 'Opt-out reason added successfully.' });
        fetchSettings();
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.message || 'Failed to add reason' });
    }
  };

  if (loading) {
    return <div className="page-body">Loading settings...</div>;
  }

  const isOvernight = (settings.requestOpenTime || '17:30') > (settings.requestCloseTime || '08:20');
  const previewOpenDisp = format12Hour(settings.requestOpenTime || '17:30');
  const previewCloseDisp = format12Hour(settings.requestCloseTime || '08:20');

  return (
    <div className="page-body">
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Settings color="var(--accent-primary)" /> System Settings & Breakfast Cycle Configuration
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
          Configure daily breakfast request cycle opening & closing window and opt-out reason types
        </p>
      </div>

      {message && (
        <div style={{
          background: message.type === 'error' ? 'var(--danger-bg)' : 'var(--success-bg)',
          border: `1px solid ${message.type === 'error' ? '#fca5a5' : 'var(--success)'}`,
          color: message.type === 'error' ? 'var(--danger-text)' : 'var(--success)',
          padding: '0.75rem 1.25rem',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <CheckCircle2 size={18} />
          {message.text || message}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))', gap: '1.5rem' }}>
        {/* Breakfast Request Cycle Configuration */}
        <div className="glass-panel" style={{ padding: '1.75rem' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem', fontSize: '1.2rem' }}>
            <Clock color="var(--warning)" /> Daily Breakfast Request Cycle
          </h2>

          <form onSubmit={handleSaveSettings}>
            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label className="form-label">Request Opens (24h Format HH:mm) *</label>
              <input
                type="text"
                className="form-input"
                placeholder="17:30"
                value={settings.requestOpenTime}
                onChange={(e) => setSettings({ ...settings, requestOpenTime: e.target.value })}
                required
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Default: 17:30 (Requests open at 5:30 PM IST on the day before the breakfast business date)
              </span>
            </div>

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label className="form-label">Request Closes (24h Format HH:mm) *</label>
              <input
                type="text"
                className="form-input"
                placeholder="08:20"
                value={settings.requestCloseTime}
                onChange={(e) => setSettings({ ...settings, requestCloseTime: e.target.value })}
                required
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Default: 08:20 (Requests close at 8:20 AM IST on the breakfast business date)
              </span>
            </div>

            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
              <label className="form-label">Business Timezone</label>
              <input
                type="text"
                className="form-input"
                value="Asia/Kolkata (IST, UTC+05:30)"
                disabled
              />
            </div>

            {/* Live Request-Window Preview */}
            <div style={{
              background: 'rgba(59, 130, 246, 0.08)',
              border: '1px solid rgba(59, 130, 246, 0.25)',
              borderRadius: 'var(--radius-sm)',
              padding: '1rem',
              marginBottom: '1.25rem'
            }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#3b82f6', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.35rem' }}>
                Live Request-Window Preview
              </div>
              <div style={{ fontSize: '0.88rem', color: 'var(--text-primary)', lineHeight: 1.45 }}>
                {isOvernight ? (
                  <>
                    For breakfast on <strong>7 October 2026</strong>, requests open on <strong>6 October 2026 at {previewOpenDisp} IST</strong> and close on <strong>7 October 2026 at {previewCloseDisp} IST</strong>.
                  </>
                ) : (
                  <>
                    For breakfast on <strong>7 October 2026</strong>, requests open on <strong>7 October 2026 at {previewOpenDisp} IST</strong> and close on <strong>7 October 2026 at {previewCloseDisp} IST</strong>.
                  </>
                )}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
                Takes effect immediately for all upcoming and active breakfast cycles.
              </div>
            </div>

            <button type="submit" className="btn btn-primary" disabled={saving}>
              <Save size={16} /> {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </form>
        </div>

        {/* Reasons Management */}
        <div className="glass-panel" style={{ padding: '1.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
            <h2 style={{ fontSize: '1.2rem' }}>Configured Opt-Out Reasons</h2>
            <button className="btn btn-primary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }} onClick={() => setShowReasonModal(true)}>
              <Plus size={14} /> Add Reason
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {reasons.map(r => (
              <div key={r.code} className="glass-card" style={{ padding: '0.85rem 1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <strong style={{ color: 'var(--text-primary)', display: 'block' }}>{r.label}</strong>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Code: {r.code}</span>
                </div>
                {r.isCustomAllowed && (
                  <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>Mandatory Text Required</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Add Reason Modal */}
      {showReasonModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h2>Add Custom Rejection Reason</h2>
            <form onSubmit={handleAddReason} style={{ marginTop: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Reason Code (Uppercase) *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. WORK_TRIP"
                  value={newReason.code}
                  onChange={(e) => setNewReason({ ...newReason, code: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Reason Label *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Official Work Trip"
                  value={newReason.label}
                  onChange={(e) => setNewReason({ ...newReason, label: e.target.value })}
                  required
                />
              </div>

              <div className="form-group" style={{ flexDirection: 'row', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  id="customTextCheck"
                  checked={newReason.isCustomAllowed}
                  onChange={(e) => setNewReason({ ...newReason, isCustomAllowed: e.target.checked })}
                />
                <label htmlFor="customTextCheck" style={{ fontSize: '0.85rem', cursor: 'pointer' }}>
                  Require mandatory text description field when selected
                </label>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowReasonModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Add Reason</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SettingsPage;
