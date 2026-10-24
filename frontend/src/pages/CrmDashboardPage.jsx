import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Layers,
  CheckCircle2,
  XCircle,
  UserCheck,
  Clock,
  AlertTriangle,
  Plus,
  RefreshCw,
  Building,
  ArrowRight,
  TrendingUp,
  Briefcase
} from 'lucide-react';
import crmService from '../services/crmService';

export default function CrmDashboardPage() {
  const navigate = useNavigate();
  const { user, hasPermission } = useAuth();

  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const canCreateLead = hasPermission('crm.lead.create');

  const fetchMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await crmService.getDashboardMetrics();
      if (res.data.success) {
        setMetrics(res.data);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load live CRM dashboard metrics. Please refresh.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const handleCardClick = (destination) => {
    navigate(destination);
  };

  return (
    <div className="page-body">
      {/* Top Banner & Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #f59e0b, #d97706)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              boxShadow: '0 4px 10px rgba(245, 158, 11, 0.25)'
            }}>
              <Briefcase size={20} />
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>
                CRM Dashboard
              </h1>
              <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Real-time pipeline overview, lead statuses, and scheduled client interactions
              </p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={fetchMetrics}
            className="btn btn-secondary"
            title="Refresh metrics"
            disabled={loading}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>

          {canCreateLead && (
            <button
              onClick={() => navigate('/crm/leads/new')}
              className="btn btn-primary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <Plus size={16} />
              <span>New Lead</span>
            </button>
          )}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div style={{
          padding: '1.25rem',
          background: 'var(--danger-bg)',
          border: '1px solid var(--danger-border)',
          borderRadius: '10px',
          color: 'var(--danger-text)',
          marginBottom: '1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <AlertTriangle size={20} />
            <span>{error}</span>
          </div>
          <button onClick={fetchMetrics} className="btn btn-secondary" style={{ fontSize: '0.8rem' }}>
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !metrics && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
          {[...Array(7)].map((_, i) => (
            <div key={i} className="glass-panel" style={{ height: '120px', padding: '1.25rem', background: '#f8fafc', opacity: 0.6 }}>
              <div style={{ width: '40%', height: '14px', background: '#e2e8f0', borderRadius: '4px', marginBottom: '1rem' }} />
              <div style={{ width: '60%', height: '28px', background: '#e2e8f0', borderRadius: '4px' }} />
            </div>
          ))}
        </div>
      )}

      {/* Live Metrics Grid */}
      {metrics && (
        <>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '1.1rem',
            marginBottom: '2rem'
          }}>
            {/* 1. Total Leads */}
            <div
              className="glass-panel card-hover"
              onClick={() => handleCardClick('/crm/leads?view=all')}
              style={{
                padding: '1.25rem',
                cursor: 'pointer',
                borderLeft: '4px solid #3b82f6',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between'
              }}
              title="Click to view all leads"
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                  Total Leads
                </span>
                <div style={{ padding: '6px', borderRadius: '8px', background: '#eff6ff', color: '#2563eb' }}>
                  <Layers size={18} />
                </div>
              </div>
              <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {metrics.totalLeads}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#2563eb', display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 600 }}>
                  View All <ArrowRight size={12} />
                </span>
              </div>
            </div>

            {/* 2. Open Leads */}
            <div
              className="glass-panel card-hover"
              onClick={() => handleCardClick('/crm/leads?view=open')}
              style={{
                padding: '1.25rem',
                cursor: 'pointer',
                borderLeft: '4px solid #f59e0b',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between'
              }}
              title="Click to view open leads"
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                  Open Leads
                </span>
                <div style={{ padding: '6px', borderRadius: '8px', background: '#fffbeb', color: '#d97706' }}>
                  <TrendingUp size={18} />
                </div>
              </div>
              <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '2rem', fontWeight: 700, color: '#d97706' }}>
                  {metrics.openLeads}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#d97706', display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 600 }}>
                  Active Pool <ArrowRight size={12} />
                </span>
              </div>
            </div>

            {/* 3. Qualified Leads */}
            <div
              className="glass-panel card-hover"
              onClick={() => handleCardClick('/crm/leads?view=all&lifecycleStatus=Qualified')}
              style={{
                padding: '1.25rem',
                cursor: 'pointer',
                borderLeft: '4px solid #10b981',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between'
              }}
              title="Click to view qualified leads"
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                  Qualified Leads
                </span>
                <div style={{ padding: '6px', borderRadius: '8px', background: '#ecfdf5', color: '#059669' }}>
                  <CheckCircle2 size={18} />
                </div>
              </div>
              <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '2rem', fontWeight: 700, color: '#059669' }}>
                  {metrics.qualifiedLeads}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#059669', display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 600 }}>
                  Verified <ArrowRight size={12} />
                </span>
              </div>
            </div>

            {/* 4. Disqualified Leads */}
            <div
              className="glass-panel card-hover"
              onClick={() => handleCardClick('/crm/leads?view=unqualified')}
              style={{
                padding: '1.25rem',
                cursor: 'pointer',
                borderLeft: '4px solid #ef4444',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between'
              }}
              title="Click to view unqualified / disqualified leads"
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                  Disqualified Leads
                </span>
                <div style={{ padding: '6px', borderRadius: '8px', background: '#fef2f2', color: '#dc2626' }}>
                  <XCircle size={18} />
                </div>
              </div>
              <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '2rem', fontWeight: 700, color: '#dc2626' }}>
                  {metrics.disqualifiedLeads}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#dc2626', display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 600 }}>
                  Archive <ArrowRight size={12} />
                </span>
              </div>
            </div>

            {/* 5. My Leads */}
            <div
              className="glass-panel card-hover"
              onClick={() => handleCardClick('/crm/leads?view=my_leads')}
              style={{
                padding: '1.25rem',
                cursor: 'pointer',
                borderLeft: '4px solid #8b5cf6',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between'
              }}
              title="Click to view leads assigned to you"
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                  My Assigned Leads
                </span>
                <div style={{ padding: '6px', borderRadius: '8px', background: '#f5f3ff', color: '#7c3aed' }}>
                  <UserCheck size={18} />
                </div>
              </div>
              <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '2rem', fontWeight: 700, color: '#7c3aed' }}>
                  {metrics.myLeads}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#7c3aed', display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 600 }}>
                  Mine <ArrowRight size={12} />
                </span>
              </div>
            </div>

            {/* 6. Follow-ups Due */}
            <div
              className="glass-panel card-hover"
              onClick={() => handleCardClick('/crm/leads?view=follow_ups_due')}
              style={{
                padding: '1.25rem',
                cursor: 'pointer',
                borderLeft: '4px solid #06b6d4',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between'
              }}
              title="Click to view follow-ups due"
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                  Follow-ups Due (24h)
                </span>
                <div style={{ padding: '6px', borderRadius: '8px', background: '#ecfeff', color: '#0891b2' }}>
                  <Clock size={18} />
                </div>
              </div>
              <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '2rem', fontWeight: 700, color: '#0891b2' }}>
                  {metrics.followUpsDue}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#0891b2', display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 600 }}>
                  Due Soon <ArrowRight size={12} />
                </span>
              </div>
            </div>

            {/* 7. Overdue Follow-ups */}
            <div
              className="glass-panel card-hover"
              onClick={() => handleCardClick('/crm/leads?view=follow_ups_due')}
              style={{
                padding: '1.25rem',
                cursor: 'pointer',
                borderLeft: '4px solid #f97316',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between'
              }}
              title="Click to view overdue follow-ups"
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                  Overdue Follow-ups
                </span>
                <div style={{ padding: '6px', borderRadius: '8px', background: '#fff7ed', color: '#ea580c' }}>
                  <AlertTriangle size={18} />
                </div>
              </div>
              <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '2rem', fontWeight: 700, color: '#ea580c' }}>
                  {metrics.overdueFollowUps}
                </span>
                <span style={{ fontSize: '0.75rem', color: '#ea580c', display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 600 }}>
                  Attention Required <ArrowRight size={12} />
                </span>
              </div>
            </div>
          </div>

          {/* Quick Action Navigation Panels */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
            <div className="glass-panel" style={{ padding: '1.75rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <h3 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Layers size={18} color="var(--accent-primary)" />
                  <span>Leads Workspace</span>
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.5 }}>
                  Access the primary leads pipeline with saved views (Open, All, Unqualified, My Leads, Follow-ups Due), faceted filters, and complete search.
                </p>
              </div>
              <div style={{ marginTop: '1.5rem' }}>
                <button
                  onClick={() => navigate('/crm/leads')}
                  className="btn btn-primary"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
                >
                  <span>Go to Leads Workspace</span>
                  <ArrowRight size={16} />
                </button>
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '1.75rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <h3 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Building size={18} color="#d97706" />
                  <span>Client & Requirement Pipeline</span>
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.5 }}>
                  Every lead captures client identity, Business Area (Biogas or WWT), Requirement Type, and chronological communication history independently.
                </p>
              </div>
              <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem' }}>
                {canCreateLead ? (
                  <button
                    onClick={() => navigate('/crm/leads/new')}
                    className="btn btn-secondary"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
                  >
                    <Plus size={16} />
                    <span>Create Lead Directly</span>
                  </button>
                ) : (
                  <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>
                    Read-only pipeline analytics. Lead creation restricted by CRM role.
                  </span>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
