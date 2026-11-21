import React, { useState, useEffect } from 'react';
import API from '../services/api';
import {
  PieChart,
  TrendingUp,
  Users,
  CheckCircle2,
  XCircle,
  Coffee,
  Wallet,
  Calendar,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Sparkles,
  Building,
  HelpCircle,
  FileSpreadsheet,
  AlertCircle,
  Sun,
  Sunset
} from 'lucide-react';
import { PageHeader, Button, DatePicker, StatusBadge } from '../components/ui';

const CEOViewPage = () => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDate, setSelectedDate] = useState('');
  const [activePeriod, setActivePeriod] = useState('ALL'); // ALL, DAILY, WEEKLY, MONTHLY

  useEffect(() => {
    fetchCeoData();
  }, []);

  const fetchCeoData = async (targetDate) => {
    setLoading(true);
    setError(null);
    try {
      const url = targetDate ? `/reports/ceo?date=${targetDate}` : '/reports/ceo';
      const res = await API.get(url);
      if (res.data.success) {
        setReport(res.data);
        if (!selectedDate && (res.data.selectedDate || res.data.todayDate)) {
          setSelectedDate(res.data.selectedDate || res.data.todayDate);
        }
      } else {
        setError(res.data.message || 'Unable to load Directors executive management insights.');
      }
    } catch (err) {
      console.error('Failed to fetch CEO report:', err);
      setError(err.response?.data?.message || 'Unable to load Directors management insights. Please check server connection.');
    } finally {
      setLoading(false);
    }
  };

  const handleDateChange = (newDate) => {
    setSelectedDate(newDate);
    fetchCeoData(newDate);
  };

  const handleResetToday = () => {
    const today = report?.todayDate || new Date().toISOString().split('T')[0];
    setSelectedDate(today);
    fetchCeoData(today);
  };

  if (loading && !report) {
    return (
      <div className="page-body" style={{ textAlign: 'center', padding: '3.5rem' }}>
        <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', color: 'var(--text-secondary)' }}>
          <div className="spinner" style={{ width: '28px', height: '28px', border: '3px solid rgba(255,255,255,0.2)', borderTopColor: 'var(--accent-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
          <span>Loading executive management insights...</span>
        </div>
      </div>
    );
  }

  if (error && !report) {
    return (
      <div className="page-body" style={{ textAlign: 'center', padding: '3.5rem' }}>
        <div style={{ maxWidth: '460px', margin: '0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
          <AlertCircle size={40} color="var(--danger)" />
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Unable to Load Directors Dashboard</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>{error}</p>
          <button className="btn btn-primary" onClick={() => fetchCeoData(selectedDate)}>
            Retry Loading Dashboard
          </button>
        </div>
      </div>
    );
  }

  const summary = report?.executiveSummary || {};
  const summaries = report?.summaries || {};
  const dailySummary = summaries.daily || {};
  const weeklySummary = summaries.weekly || {};
  const monthlySummary = summaries.monthly || {};
  const comparisons = report?.requestVsActualComparison || [];
  const trends = report?.consumptionTrends || report?.dailyTrend || [];
  const departments = report?.departmentBreakdown || [];
  const reasons = report?.reasonDistribution || {};
  const tempRequests = report?.temporaryRequests || [];

  // Separate Beverage Overview Data
  const beverageOverview = report?.beverageOverview || {};
  const bevDay = beverageOverview?.daySummary || {};
  const bevMonth = beverageOverview?.monthSummary || {};
  const bevBeverages = bevDay?.beverages || [];
  const bevMonthBeverages = bevMonth?.beverages || [];
  const bevDailyTrend = beverageOverview?.dailyTrend || [];
  const bevEmployees = beverageOverview?.employeeConsumption || [];

  const diffVal = summary.requestActualDifference ?? summary.quantityDifference ?? report?.requestActualDifference ?? 0;
  const isDiffPositive = diffVal > 0;
  const isDiffNegative = diffVal < 0;

  const totalEmployeesVal = summary.totalEmployees ?? report?.totalEmployees ?? 0;
  const totalRequestsVal = summary.totalRequests ?? summary.totalBreakfastRequestsMonth ?? report?.totalRequests ?? 0;
  const regularTakersVal = summary.regularTakers ?? summary.totalBreakfastTakers ?? report?.regularTakers ?? 0;
  const permNonTakersVal = summary.permanentNonTakers ?? summary.totalNonTakers ?? report?.permanentNonTakers ?? 0;
  const todayReqQtyVal = summary.todayRequestedQty ?? summary.dailyRequestedQuantity ?? report?.todayRequestedQty ?? 0;
  const todayActServedQtyVal = summary.todayActualServedQty ?? summary.dailyActualQuantity ?? report?.todayActualServedQty ?? 0;
  const partRateVal = summary.participationRate ?? summary.overallParticipationRate ?? report?.participationRate ?? 0;

  return (
    <div className="page-body">
      {/* Executive Header */}
      <PageHeader
        title="Directors Executive Management Dashboard"
        subtitle={`Comprehensive management insights, request vs. actual consumption metrics, expenditure trends, and participation rates for ${report?.currentMonth || 'current month'}.`}
        icon={PieChart}
        actions={
          <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', flexWrap: 'wrap' }}>
            <StatusBadge variant="info">Executive Read-Only View</StatusBadge>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <DatePicker
                id="ceo-date-selector"
                value={selectedDate || report?.selectedDate || report?.todayDate || ''}
                onChange={(e) => handleDateChange(e.target.value)}
                style={{ width: 'auto' }}
              />
              {selectedDate && selectedDate !== report?.todayDate && (
                <Button
                  variant="secondary"
                  size="md"
                  onClick={handleResetToday}
                  title="Reset to today's date"
                >
                  Today
                </Button>
              )}
            </div>
            {loading && (
              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Updating...</span>
            )}
          </div>
        }
      />

      {/* 8 Core Management KPI Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '1rem',
          marginBottom: '1.75rem'
        }}
      >
        {/* 1. Total Headcount */}
        <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '4px solid #3b82f6' }}>
          <div>
            <div className="metric-label" style={{ fontSize: '0.7rem' }}>TOTAL EMPLOYEES</div>
            <div className="metric-val" style={{ fontSize: '1.6rem', color: '#60a5fa' }}>
              {totalEmployeesVal}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Active company workforce
            </span>
          </div>
          <Users size={32} color="#3b82f6" opacity={0.8} />
        </div>

        {/* 2. Total Breakfast Requests */}
        <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '4px solid #8b5cf6' }}>
          <div>
            <div className="metric-label" style={{ fontSize: '0.7rem' }}>TOTAL REQUESTS</div>
            <div className="metric-val" style={{ fontSize: '1.6rem', color: '#a78bfa' }}>
              {totalRequestsVal}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Portions requested for period
            </span>
          </div>
          <FileSpreadsheet size={32} color="#8b5cf6" opacity={0.8} />
        </div>

        {/* 3. Regular Breakfast Takers */}
        <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '4px solid #10b981' }}>
          <div>
            <div className="metric-label" style={{ fontSize: '0.7rem' }}>REGULAR TAKERS</div>
            <div className="metric-val" style={{ fontSize: '1.6rem', color: '#34d399' }}>
              {regularTakersVal}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Normal daily breakfast participants
            </span>
          </div>
          <CheckCircle2 size={32} color="#10b981" opacity={0.8} />
        </div>

        {/* 4. Permanent Non-Takers */}
        <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '4px solid #f59e0b' }}>
          <div>
            <div className="metric-label" style={{ fontSize: '0.7rem' }}>PERMANENT NON-TAKERS</div>
            <div className="metric-val" style={{ fontSize: '1.6rem', color: '#fbbf24' }}>
              {permNonTakersVal}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Permanent opt-outs (0 by default)
            </span>
          </div>
          <XCircle size={32} color="#f59e0b" opacity={0.8} />
        </div>

        {/* 5. Daily Requested Quantity */}
        <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '4px solid #06b6d4' }}>
          <div>
            <div className="metric-label" style={{ fontSize: '0.7rem' }}>TODAY'S REQUESTED QTY</div>
            <div className="metric-val" style={{ fontSize: '1.6rem', color: '#22d3ee' }}>
              {todayReqQtyVal}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Regular + 1-Day requests
            </span>
          </div>
          <Coffee size={32} color="#06b6d4" opacity={0.8} />
        </div>

        {/* 6. Daily Actual Served Quantity */}
        <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '4px solid #10b981' }}>
          <div>
            <div className="metric-label" style={{ fontSize: '0.7rem' }}>TODAY'S ACTUAL SERVED QTY</div>
            <div className="metric-val" style={{ fontSize: '1.6rem', color: '#10b981' }}>
              {todayActServedQtyVal}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Actual response quantity served
            </span>
          </div>
          <CheckCircle2 size={32} color="#10b981" opacity={0.8} />
        </div>

        {/* 7. Variance / Difference */}
        <div
          className="glass-panel metric-card"
          style={{
            padding: '1.25rem',
            borderLeft: `4px solid ${diffVal === 0 ? '#10b981' : isDiffPositive ? '#ef4444' : '#f59e0b'}`
          }}
        >
          <div>
            <div className="metric-label" style={{ fontSize: '0.7rem' }}>REQUEST VS ACTUAL DIFF</div>
            <div
              className="metric-val"
              style={{
                fontSize: '1.6rem',
                color: diffVal === 0 ? '#10b981' : isDiffPositive ? '#f87171' : '#fbbf24'
              }}
            >
              {isDiffPositive ? `+${diffVal}` : diffVal}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {diffVal === 0
                ? 'Exact match (0 variance)'
                : isDiffPositive
                ? 'Requested > Actual served'
                : 'Actual served > Requested'}
            </span>
          </div>
          {diffVal === 0 ? (
            <Minus size={32} color="#10b981" opacity={0.8} />
          ) : isDiffPositive ? (
            <ArrowUpRight size={32} color="#ef4444" opacity={0.8} />
          ) : (
            <ArrowDownRight size={32} color="#f59e0b" opacity={0.8} />
          )}
        </div>

        {/* 8. Take Rate / Participation */}
        <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '4px solid #ec4899' }}>
          <div>
            <div className="metric-label" style={{ fontSize: '0.7rem' }}>PARTICIPATION RATE</div>
            <div className="metric-val" style={{ fontSize: '1.6rem', color: '#f472b6' }}>
              {partRateVal}%
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Avg Month: {summary.avgMonthlyParticipationRate ?? partRateVal}%
            </span>
          </div>
          <TrendingUp size={32} color="#ec4899" opacity={0.8} />
        </div>
      </div>

      {/* Daily / Weekly / Monthly Summaries Comparison */}
      <div style={{ marginBottom: '1.75rem' }}>
        <h2 style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <Layers size={20} color="var(--accent-primary)" />
          Executive Period Summaries (Daily • Weekly • Monthly)
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
          {/* Daily Card */}
          <div className="panel-card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent-primary)', textTransform: 'uppercase' }}>
                DAILY SUMMARY
              </span>
              <span className="badge badge-secondary" style={{ fontSize: '0.75rem' }}>
                {dailySummary.date || report?.todayDate}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Requested Quantity:</span>
                <strong>{dailySummary.requestedQuantity ?? todayReqQtyVal ?? 0} portions</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Actual Served Quantity:</span>
                <strong style={{ color: '#10b981' }}>{dailySummary.actualServedQuantity ?? dailySummary.actualQuantity ?? todayActServedQtyVal ?? 0} portions</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Difference (Variance):</span>
                <strong style={{ color: ((dailySummary.difference ?? diffVal) === 0) ? '#10b981' : '#f59e0b' }}>
                  {dailySummary.difference ?? diffVal ?? 0}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Today's Expenditure:</span>
                <strong style={{ color: 'var(--accent-primary)' }}>₹{dailySummary.expenditure ?? dailySummary.cost ?? summary.todayCost ?? 0}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Participation Rate:</span>
                <strong>{dailySummary.participationRate ?? partRateVal ?? 0}%</strong>
              </div>
            </div>
          </div>

          {/* Weekly Card */}
          <div className="panel-card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#8b5cf6', textTransform: 'uppercase' }}>
                WEEKLY SUMMARY
              </span>
              <span className="badge badge-secondary" style={{ fontSize: '0.75rem' }}>
                {weeklySummary.startDate} → {weeklySummary.endDate}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Total Requested Quantity:</span>
                <strong>{weeklySummary.totalRequestedQuantity ?? 0} portions</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Total Actual Served Quantity:</span>
                <strong style={{ color: '#10b981' }}>{weeklySummary.totalActualServedQuantity ?? weeklySummary.totalActualQuantity ?? 0} portions</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Weekly Difference:</span>
                <strong style={{ color: ((weeklySummary.weeklyDifference ?? weeklySummary.difference ?? 0) === 0) ? '#10b981' : '#f59e0b' }}>
                  {weeklySummary.weeklyDifference ?? weeklySummary.difference ?? 0}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Total Weekly Spend:</span>
                <strong style={{ color: 'var(--accent-primary)' }}>₹{weeklySummary.totalWeeklySpend ?? weeklySummary.totalCost ?? 0}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Avg Daily Takers:</span>
                <strong>{weeklySummary.averageDailyTakers ?? weeklySummary.avgDailyTakers ?? 0} persons/day</strong>
              </div>
            </div>
          </div>

          {/* Monthly Card */}
          <div className="panel-card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#10b981', textTransform: 'uppercase' }}>
                MONTHLY SUMMARY
              </span>
              <span className="badge badge-secondary" style={{ fontSize: '0.75rem' }}>
                {monthlySummary.month || report?.currentMonth}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Total Month Requested:</span>
                <strong>{monthlySummary.totalMonthRequested ?? monthlySummary.totalRequestedQuantity ?? 0} portions</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Total Month Actual Served:</span>
                <strong style={{ color: '#10b981' }}>{monthlySummary.totalMonthActualServed ?? monthlySummary.totalActualQuantity ?? 0} portions</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Total Month Difference:</span>
                <strong style={{ color: ((monthlySummary.totalMonthDifference ?? monthlySummary.difference ?? 0) === 0) ? '#10b981' : '#f59e0b' }}>
                  {monthlySummary.totalMonthDifference ?? monthlySummary.difference ?? 0}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Total Monthly Spend:</span>
                <strong style={{ color: 'var(--accent-primary)' }}>₹{monthlySummary.totalMonthlySpend ?? monthlySummary.totalCost ?? summary.totalMonthlyCost ?? 0}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Average Cost Per Meal:</span>
                <strong>₹{monthlySummary.averageCostPerMeal ?? monthlySummary.avgCostPerMeal ?? summary.avgCostPerMeal ?? 0}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Request vs Actual Response Comparison Table */}
      <div className="panel-card" style={{ padding: '1.5rem', marginBottom: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h2 style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
              <TrendingUp size={20} color="var(--accent-primary)" />
              Daily Request vs. Actual Response Comparison
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', margin: '0.2rem 0 0 0' }}>
              Comparison of requested breakfast portions vs. meals actually served across recent operational dates
            </p>
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Showing {comparisons.length} active business dates
          </span>
        </div>

        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Requested Quantity</th>
                <th>Actual Response Quantity</th>
                <th>Difference (Variance)</th>
                <th>Take Rate</th>
                <th>Daily Expenditure</th>
                <th>Status / Variance Assessment</th>
              </tr>
            </thead>
            <tbody>
              {comparisons.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>
                    No daily records found for this period.
                  </td>
                </tr>
              ) : (
                comparisons.map(row => {
                  const diff = row.difference || 0;
                  const isExact = diff === 0;
                  const isOver = diff > 0;
                  return (
                    <tr key={row.date}>
                      <td>
                        <strong style={{ color: 'var(--text-primary)' }}>{row.date}</strong>
                      </td>
                      <td>
                        <span style={{ fontWeight: 600 }}>{row.requestedQuantity}</span>
                      </td>
                      <td>
                        <span style={{ fontWeight: 600, color: '#10b981' }}>{row.actualQuantity}</span>
                      </td>
                      <td>
                        <span
                          className="badge"
                          style={{
                            background: isExact ? 'rgba(16, 185, 129, 0.15)' : isOver ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                            color: isExact ? '#10b981' : isOver ? '#ef4444' : '#f59e0b',
                            fontWeight: 700
                          }}
                        >
                          {isOver ? `+${diff}` : diff}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{row.participationRate}%</span>
                        </div>
                      </td>
                      <td>
                        <strong style={{ color: 'var(--accent-primary)' }}>₹{row.dailyCost}</strong>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            row.status === 'EXACT_MATCH'
                              ? 'badge-success'
                              : row.status === 'UNDER_SERVED'
                              ? 'badge-danger'
                              : 'badge-warning'
                          }`}
                        >
                          {row.status === 'EXACT_MATCH'
                            ? '✓ Exact Match'
                            : row.status === 'UNDER_SERVED'
                            ? '⚠ Requested > Served'
                            : '⚡ Served > Requested'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Two Column Layout: Cost/Expense Information & Department Participation */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: '1.5rem', marginBottom: '1.75rem' }}>
        {/* Cost & Expense Overview */}
        <div className="panel-card" style={{ padding: '1.5rem' }}>
          <h2 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', margin: 0 }}>
            <Wallet size={18} color="var(--accent-primary)" />
            Cost & Fund Ledger Overview
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '1.25rem' }}>
            Authoritative financial metrics from the breakfast money ledger
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="glass-card" style={{ padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                  CURRENT BREAKFAST FUND BALANCE
                </span>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#10b981', marginTop: '0.2rem' }}>
                  ₹{summary.currentFundBalance || 0}
                </div>
              </div>
              <Wallet size={28} color="#10b981" opacity={0.7} />
            </div>

            <div className="glass-card" style={{ padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                  TOTAL MONTHLY EXPENDITURE
                </span>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--accent-primary)', marginTop: '0.2rem' }}>
                  ₹{summary.totalMonthlyCost || 0}
                </div>
              </div>
              <FileSpreadsheet size={28} color="var(--accent-primary)" opacity={0.7} />
            </div>

            <div className="glass-card" style={{ padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                  AVERAGE COST PER MEAL
                </span>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#8b5cf6', marginTop: '0.2rem' }}>
                  ₹{summary.avgCostPerMeal || 0}
                </div>
              </div>
              <Coffee size={28} color="#8b5cf6" opacity={0.7} />
            </div>
          </div>
        </div>

        {/* Department Participation Breakdown */}
        <div className="panel-card" style={{ padding: '1.5rem' }}>
          <h2 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', margin: 0 }}>
            <Building size={18} color="var(--accent-primary)" />
            Department Participation Breakdown
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '1.25rem' }}>
            Breakfast engagement rates across all company departments
          </p>

          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Department</th>
                  <th>Headcount</th>
                  <th>Takers</th>
                  <th>Participation Rate</th>
                </tr>
              </thead>
              <tbody>
                {departments.length === 0 ? (
                  <tr>
                    <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>
                      No department data available.
                    </td>
                  </tr>
                ) : (
                  departments.map(d => (
                    <tr key={d.department}>
                      <td>
                        <strong style={{ color: 'var(--text-primary)' }}>{d.department}</strong>
                      </td>
                      <td>{d.total}</td>
                      <td>
                        <span style={{ color: '#10b981', fontWeight: 600 }}>{d.takingToday}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}> / {d.normal}</span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <div
                            style={{
                              flex: 1,
                              height: '6px',
                              background: 'var(--border-color)',
                              borderRadius: '3px',
                              overflow: 'hidden',
                              minWidth: '50px'
                            }}
                          >
                            <div
                              style={{
                                width: `${Math.min(100, d.participationRate)}%`,
                                height: '100%',
                                background: d.participationRate > 70 ? '#10b981' : d.participationRate > 40 ? '#3b82f6' : '#f59e0b'
                              }}
                            />
                          </div>
                          <span style={{ fontSize: '0.8rem', fontWeight: 600, minWidth: '40px' }}>
                            {d.participationRate}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Bottom Row: Opt-Out Reasons & Temporary Requests */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 380px), 1fr))', gap: '1.5rem' }}>
        {/* Opt-Out Distribution */}
        <div className="panel-card" style={{ padding: '1.5rem' }}>
          <h2 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', margin: 0 }}>
            <HelpCircle size={18} color="var(--accent-primary)" />
            Opt-Out Reason Distribution
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '1.25rem' }}>
            Recorded reasons when regular takers opt out of daily breakfast
          </p>

          {Object.keys(reasons).length === 0 ? (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
              No opt-out reasons logged for this month.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              {Object.entries(reasons).map(([reason, count]) => (
                <div
                  key={reason}
                  className="glass-card"
                  style={{
                    padding: '0.75rem 1rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}
                >
                  <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{reason}</span>
                  <span className="badge badge-secondary" style={{ fontSize: '0.8rem', fontWeight: 700 }}>
                    {count} {count === 1 ? 'time' : 'times'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Temporary Specific-Date Requests Log */}
        <div className="panel-card" style={{ padding: '1.5rem' }}>
          <h2 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', margin: 0 }}>
            <Calendar size={18} color="var(--accent-primary)" />
            Permanent Non-Takers: Specific-Date Requests ({report?.currentMonth})
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '1.25rem' }}>
            One-day breakfast exceptions requested by permanent non-takers
          </p>

          {tempRequests.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
              No one-day breakfast exceptions logged for permanent non-takers this month.
            </p>
          ) : (
            <div className="table-container">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Employee</th>
                    <th>Quantity</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {tempRequests.map(tr => (
                    <tr key={tr.requestId || tr.id}>
                      <td><strong style={{ color: 'var(--text-primary)' }}>{tr.requestedDate}</strong></td>
                      <td>
                        <div>{tr.employeeName}</div>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{tr.employeeId}</span>
                      </td>
                      <td>
                        <span className="badge badge-secondary">{tr.quantity} portion(s)</span>
                      </td>
                      <td>
                        <span className={`badge ${tr.status === 'CONFIRMED' ? 'badge-success' : 'badge-danger'}`}>
                          {tr.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ================================================================= */}
      {/* SEPARATE BEVERAGE OVERVIEW SECTION (Section 5 Requirement)         */}
      {/* ================================================================= */}
      <div style={{ marginTop: '2.5rem', paddingTop: '2rem', borderTop: '2px dashed var(--border-color)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h2 style={{ fontSize: '1.3rem', display: 'flex', alignItems: 'center', gap: '0.65rem', margin: 0 }}>
              <Coffee size={24} color="#f59e0b" />
              Beverage Operations &amp; Consumption Overview
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '0.25rem 0 0 0' }}>
              Operational beverage consumption metrics for <strong>{selectedDate || report?.todayDate}</strong> ({report?.currentMonth}). All quantities measured in <strong>Cups</strong>. Maintained strictly distinct from breakfast meals.
            </p>
          </div>
          <span className="badge" style={{ background: 'rgba(245, 158, 11, 0.12)', color: '#f59e0b', fontWeight: 700, padding: '0.4rem 0.85rem' }}>
            🍵 Morning &amp; Evening Sessions
          </span>
        </div>

        {/* 4 Beverage KPI Cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '1rem',
            marginBottom: '1.75rem'
          }}
        >
          {/* 1. Today Total Cups */}
          <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '4px solid #f59e0b' }}>
            <div>
              <div className="metric-label" style={{ fontSize: '0.7rem' }}>TODAY'S BEVERAGE CUPS</div>
              <div className="metric-val" style={{ fontSize: '1.6rem', color: '#fbbf24' }}>
                {bevDay.totalCups || 0} <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Cups</span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Morning: {bevDay.morningCups || 0} • Evening: {bevDay.eveningCups || 0}
              </span>
            </div>
            <Coffee size={32} color="#f59e0b" opacity={0.8} />
          </div>

          {/* 2. Morning Session Cups */}
          <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '4px solid #eab308' }}>
            <div>
              <div className="metric-label" style={{ fontSize: '0.7rem' }}>MORNING SESSION</div>
              <div className="metric-val" style={{ fontSize: '1.6rem', color: '#fde047' }}>
                {bevDay.morningCups || 0} <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Cups</span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                AM Beverage consumption
              </span>
            </div>
            <Sun size={32} color="#eab308" opacity={0.8} />
          </div>

          {/* 3. Evening Session Cups */}
          <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '4px solid #8b5cf6' }}>
            <div>
              <div className="metric-label" style={{ fontSize: '0.7rem' }}>EVENING SESSION</div>
              <div className="metric-val" style={{ fontSize: '1.6rem', color: '#a78bfa' }}>
                {bevDay.eveningCups || 0} <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Cups</span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                PM Beverage consumption
              </span>
            </div>
            <Sunset size={32} color="#8b5cf6" opacity={0.8} />
          </div>

          {/* 4. Active Drinkers Participation */}
          <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '4px solid #10b981' }}>
            <div>
              <div className="metric-label" style={{ fontSize: '0.7rem' }}>EMPLOYEE PARTICIPATION</div>
              <div className="metric-val" style={{ fontSize: '1.6rem', color: '#34d399' }}>
                {bevDay.participationRate || 0}%
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {bevDay.uniqueDrinkers || 0} of {totalEmployeesVal} employees today
              </span>
            </div>
            <Users size={32} color="#10b981" opacity={0.8} />
          </div>
        </div>

        {/* Beverage Catalogue Breakdown: Today vs Month */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: '1.5rem', marginBottom: '1.75rem' }}>
          {/* Today's Beverage Distribution */}
          <div className="panel-card" style={{ padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: '0 0 0.5rem 0' }}>
              <Coffee size={18} color="var(--accent-primary)" />
              Daily Beverage Breakdown ({selectedDate || report?.todayDate})
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', margin: '0 0 1rem 0' }}>
              Morning and Evening distribution for all configured beverages
            </p>

            <div className="table-container">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Beverage</th>
                    <th>Morning</th>
                    <th>Evening</th>
                    <th>Total</th>
                    <th>Share</th>
                  </tr>
                </thead>
                <tbody>
                  {bevBeverages.length === 0 ? (
                    <tr>
                      <td colSpan="5" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>
                        No beverages logged for this date.
                      </td>
                    </tr>
                  ) : (
                    bevBeverages.map(b => {
                      const share = bevDay.totalCups > 0 ? Math.round((b.totalCups / bevDay.totalCups) * 100) : 0;
                      return (
                        <tr key={b.name}>
                          <td><strong style={{ color: 'var(--text-primary)' }}>{b.name}</strong></td>
                          <td>{b.morningCups} cups</td>
                          <td>{b.eveningCups} cups</td>
                          <td><strong style={{ color: 'var(--accent-primary)' }}>{b.totalCups} cups</strong></td>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                              <div style={{ flex: 1, height: '5px', background: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden', minWidth: '40px' }}>
                                <div style={{ width: `${share}%`, height: '100%', background: '#f59e0b' }} />
                              </div>
                              <span style={{ fontSize: '0.75rem', minWidth: '30px' }}>{share}%</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Monthly Beverage Totals */}
          <div className="panel-card" style={{ padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: '0 0 0.5rem 0' }}>
              <Layers size={18} color="#8b5cf6" />
              Monthly Beverage Volume ({report?.currentMonth})
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', margin: '0 0 1rem 0' }}>
              Aggregated monthly consumption across all configured beverages
            </p>

            <div className="table-container">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Beverage</th>
                    <th>Morning</th>
                    <th>Evening</th>
                    <th>Month Total</th>
                    <th>Share</th>
                  </tr>
                </thead>
                <tbody>
                  {bevMonthBeverages.length === 0 ? (
                    <tr>
                      <td colSpan="5" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>
                        No monthly beverage records found.
                      </td>
                    </tr>
                  ) : (
                    bevMonthBeverages.map(b => {
                      const share = bevMonth.totalCups > 0 ? Math.round((b.totalCups / bevMonth.totalCups) * 100) : 0;
                      return (
                        <tr key={b.name}>
                          <td><strong style={{ color: 'var(--text-primary)' }}>{b.name}</strong></td>
                          <td>{b.morningCups} cups</td>
                          <td>{b.eveningCups} cups</td>
                          <td><strong style={{ color: '#8b5cf6' }}>{b.totalCups} cups</strong></td>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                              <div style={{ flex: 1, height: '5px', background: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden', minWidth: '40px' }}>
                                <div style={{ width: `${share}%`, height: '100%', background: '#8b5cf6' }} />
                              </div>
                              <span style={{ fontSize: '0.75rem', minWidth: '30px' }}>{share}%</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Employee-Wise Beverage Consumption Table */}
        <div className="panel-card" style={{ padding: '1.5rem', marginBottom: '1.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                <Users size={18} color="var(--accent-primary)" />
                Employee Beverage Consumption Ranking ({report?.currentMonth})
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', margin: '0.2rem 0 0 0' }}>
                Cumulative employee consumption, session distribution, and preferred beverage for the month
              </p>
            </div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Showing {bevEmployees.length} active participating employees
            </span>
          </div>

          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Department</th>
                  <th>Morning Cups</th>
                  <th>Evening Cups</th>
                  <th>Total Cups</th>
                  <th>Preferred Beverage</th>
                  <th>Active Days</th>
                </tr>
              </thead>
              <tbody>
                {bevEmployees.length === 0 ? (
                  <tr>
                    <td colSpan="7" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>
                      No employee beverage consumption logged for this month.
                    </td>
                  </tr>
                ) : (
                  bevEmployees.map(emp => (
                    <tr key={emp.employeeId}>
                      <td>
                        <strong style={{ color: 'var(--text-primary)' }}>{emp.employeeName}</strong>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{emp.employeeId}</div>
                      </td>
                      <td>{emp.department}</td>
                      <td>{emp.morningCups} cups</td>
                      <td>{emp.eveningCups} cups</td>
                      <td>
                        <strong style={{ color: 'var(--accent-primary)' }}>{emp.totalCups} cups</strong>
                      </td>
                      <td>
                        <span className="badge badge-secondary">{emp.preferredBeverage}</span>
                      </td>
                      <td>{emp.daysActive} day(s)</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CEOViewPage;
