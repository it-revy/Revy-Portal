import React, { useState, useEffect } from 'react';
import API from '../services/api';
import {
  FileSpreadsheet,
  Download,
  Printer,
  Filter,
  Calendar,
  Wallet,
  TrendingUp,
  TrendingDown,
  ShoppingBag,
  Users,
  RefreshCw,
  FileText
} from 'lucide-react';

const ReportsPage = () => {
  const [availableYears, setAvailableYears] = useState([]);
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedMonth, setSelectedMonth] = useState('ALL');
  const [department, setDepartment] = useState('ALL');
  const [reportType, setReportType] = useState('MONTHLY_SUMMARY');

  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [activeTab, setActiveTab] = useState('monthly_summary');

  // Load available years on mount
  useEffect(() => {
    fetchYears();
  }, []);

  // Fetch report data when filters change
  useEffect(() => {
    if (selectedYear) {
      fetchMonthlyReport();
    }
  }, [selectedYear, selectedMonth, department]);

  const fetchYears = async () => {
    try {
      const res = await API.get('/reports/years');
      if (res.data.success) {
        setAvailableYears(res.data.years || []);
        setSelectedYear(res.data.defaultYear || new Date().getFullYear().toString());
      }
    } catch (err) {
      console.error('Failed to fetch available years:', err);
      setSelectedYear(new Date().getFullYear().toString());
    }
  };

  const fetchMonthlyReport = async () => {
    setLoading(true);
    try {
      const res = await API.get(`/reports/monthly?year=${selectedYear}&month=${selectedMonth}&department=${department}`);
      if (res.data.success) {
        setReportData(res.data);
      }
    } catch (err) {
      console.error('Failed to fetch monthly report:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExportExcel = async () => {
    setExporting(true);
    try {
      const res = await API.get(`/reports/export-excel?year=${selectedYear}&month=${selectedMonth}&department=${department}`, {
        responseType: 'blob'
      });
      const blob = new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const yearStr = selectedYear === 'all' ? 'All_Years' : selectedYear;
      link.setAttribute('download', `Breakfast_Money_Report_${yearStr}_${new Date().toISOString().substring(0, 10)}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export Excel workbook:', err);
      setError('Failed to export Excel report. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const monthlySummary = reportData?.monthlySummary || [];
  const yearlyTotal = reportData?.yearlyTotal || {};
  const employeeReport = reportData?.employeeReport || [];
  const orderSummary = reportData?.orderSummary || [];
  const moneyTransactions = reportData?.moneyTransactions || [];

  return (
    <div className="page-body">
      {/* Header Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.75rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', margin: 0 }}>
            <FileSpreadsheet color="var(--accent-primary)" size={28} /> Reports & Financial Ledger
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.35rem', fontSize: '0.9rem' }}>
            Comprehensive Monthly Financial Summary, Attendance Matrix, Orders & Ledger Transactions
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button className="btn btn-secondary" onClick={fetchMonthlyReport} disabled={loading} title="Refresh report preview">
            <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
          </button>
          <button className="btn btn-secondary" onClick={handlePrint} title="Print active report preview">
            <Printer size={16} /> Print Report
          </button>
          <button className="btn btn-primary" onClick={handleExportExcel} disabled={exporting} style={{ background: '#16a34a', borderColor: '#16a34a' }}>
            <Download size={16} /> {exporting ? 'Generating Excel...' : 'Export Excel (.xlsx)'}
          </button>
        </div>
      </div>

      {/* Filter Controls Panel */}
      <div className="glass-panel" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Year Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: '1 1 140px', minWidth: '130px' }}>
            <Calendar size={18} color="var(--accent-primary)" />
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Year:</span>
            <select
              className="form-select"
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              style={{ flex: 1, minWidth: '90px', padding: '0.45rem 0.8rem' }}
            >
              <option value="all">All Years</option>
              {availableYears.map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>

          {/* Report Type Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: '2 1 220px', minWidth: '180px' }}>
            <FileText size={18} color="var(--accent-primary)" />
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Type:</span>
            <select
              className="form-select"
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              style={{ flex: 1, minWidth: '160px', padding: '0.45rem 0.8rem' }}
            >
              <option value="MONTHLY_SUMMARY">Monthly Breakfast & Money Report</option>
            </select>
          </div>

          {/* Department Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: '2 1 200px', minWidth: '170px' }}>
            <Filter size={18} color="var(--accent-primary)" />
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Dept:</span>
            <select
              className="form-select"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              style={{ flex: 1, minWidth: '140px', padding: '0.45rem 0.8rem' }}
            >
              <option value="ALL">All Departments</option>
              <option value="IT Infrastructure">IT Infrastructure</option>
              <option value="Administration">Administration</option>
              <option value="Engineering">Engineering</option>
              <option value="Research & Development">Research & Development</option>
              <option value="Executive Office">Executive Office</option>
              <option value="Finance & Accounts">Finance & Accounts</option>
              <option value="Quality Assurance">Quality Assurance</option>
              <option value="Human Resources">Human Resources</option>
              <option value="Operations">Operations</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: '1 1 auto', justifyContent: 'flex-end' }}>
            <button className="btn btn-primary" onClick={fetchMonthlyReport} disabled={loading} style={{ whiteSpace: 'nowrap' }}>
              Generate Report
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards Overview */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem', marginBottom: '1.75rem' }}>
        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ background: 'rgba(37, 99, 235, 0.15)', padding: '0.85rem', borderRadius: '12px' }}>
            <Wallet size={24} color="#2563eb" />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Closing Balance</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.15rem' }}>
              ₹{(yearlyTotal.closingBalance || 0).toLocaleString('en-IN')}
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ background: 'rgba(22, 163, 74, 0.15)', padding: '0.85rem', borderRadius: '12px' }}>
            <TrendingUp size={24} color="#16a34a" />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Total Money Received</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#16a34a', marginTop: '0.15rem' }}>
              ₹{(yearlyTotal.totalMoneyReceived || 0).toLocaleString('en-IN')}
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ background: 'rgba(220, 38, 38, 0.15)', padding: '0.85rem', borderRadius: '12px' }}>
            <TrendingDown size={24} color="#dc2626" />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Total Spent</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#dc2626', marginTop: '0.15rem' }}>
              ₹{(yearlyTotal.totalSpent || 0).toLocaleString('en-IN')}
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ background: 'rgba(147, 51, 234, 0.15)', padding: '0.85rem', borderRadius: '12px' }}>
            <ShoppingBag size={24} color="#9333ea" />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Total Orders</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#9333ea', marginTop: '0.15rem' }}>
              {orderSummary.length}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Navigation Bar */}
      <div className="tabs-scroll" style={{ display: 'flex', borderBottom: '2px solid var(--border-color)', marginBottom: '1.5rem', gap: '0.5rem' }}>
        <button
          onClick={() => setActiveTab('monthly_summary')}
          style={{
            padding: '0.75rem 1.25rem',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'monthly_summary' ? '3px solid var(--accent-primary)' : '3px solid transparent',
            color: activeTab === 'monthly_summary' ? 'var(--accent-primary)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'monthly_summary' ? 700 : 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.9rem',
            whiteSpace: 'nowrap'
          }}
        >
          <FileText size={16} /> Sheet 1: Monthly Summary
        </button>

        <button
          onClick={() => setActiveTab('employee_report')}
          style={{
            padding: '0.75rem 1.25rem',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'employee_report' ? '3px solid var(--accent-primary)' : '3px solid transparent',
            color: activeTab === 'employee_report' ? 'var(--accent-primary)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'employee_report' ? 700 : 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.9rem',
            whiteSpace: 'nowrap'
          }}
        >
          <Users size={16} /> Sheet 2: Employee Monthly Report
        </button>

        <button
          onClick={() => setActiveTab('order_summary')}
          style={{
            padding: '0.75rem 1.25rem',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'order_summary' ? '3px solid var(--accent-primary)' : '3px solid transparent',
            color: activeTab === 'order_summary' ? 'var(--accent-primary)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'order_summary' ? 700 : 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.9rem',
            whiteSpace: 'nowrap'
          }}
        >
          <ShoppingBag size={16} /> Sheet 3: Order Summary
        </button>

        <button
          onClick={() => setActiveTab('money_transactions')}
          style={{
            padding: '0.75rem 1.25rem',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'money_transactions' ? '3px solid var(--accent-primary)' : '3px solid transparent',
            color: activeTab === 'money_transactions' ? 'var(--accent-primary)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'money_transactions' ? 700 : 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.9rem',
            whiteSpace: 'nowrap'
          }}
        >
          <Wallet size={16} /> Sheet 4: Money Transactions
        </button>
      </div>

      {/* Tab Content Display */}
      {loading ? (
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          Generating report preview from database...
        </div>
      ) : (
        <>
          {/* TAB 1: MONTHLY SUMMARY */}
          {activeTab === 'monthly_summary' && (
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                <h3 style={{ fontSize: '1.1rem', margin: 0, fontWeight: 700 }}>
                  MONTHLY BREAKFAST & FINANCIAL SUMMARY ({selectedYear === 'all' ? 'All Years' : selectedYear})
                </h3>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  Authoritative Transaction Ledger Source
                </span>
              </div>

              <div className="table-container">
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left' }}>Month</th>
                      <th style={{ textAlign: 'right' }}>Opening Balance</th>
                      <th style={{ textAlign: 'right' }}>Money Received</th>
                      <th style={{ textAlign: 'right' }}>Total Spent</th>
                      <th style={{ textAlign: 'right' }}>Closing Balance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthlySummary.length === 0 ? (
                      <tr>
                        <td colSpan="5" style={{ textAlign: 'center', padding: '2.5rem' }}>
                          No financial transaction records found for the selected period.
                        </td>
                      </tr>
                    ) : (
                      monthlySummary.map((row, idx) => (
                        <tr key={row.yearMonth || idx}>
                          <td><strong style={{ color: 'var(--text-primary)' }}>{row.monthName}</strong></td>
                          <td style={{ textAlign: 'right' }}>₹{row.openingBalance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                          <td style={{ textAlign: 'right', color: row.moneyReceived > 0 ? '#16a34a' : 'inherit', fontWeight: row.moneyReceived > 0 ? 600 : 400 }}>
                            ₹{row.moneyReceived.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </td>
                          <td style={{ textAlign: 'right', color: row.totalSpent > 0 ? '#dc2626' : 'inherit', fontWeight: row.totalSpent > 0 ? 600 : 400 }}>
                            ₹{row.totalSpent.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </td>
                          <td style={{ textAlign: 'right', fontWeight: 700 }}>
                            ₹{row.closingBalance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                  {monthlySummary.length > 0 && (
                    <tfoot>
                      <tr style={{ background: 'var(--bg-hover)', fontWeight: 700, borderTop: '2px solid var(--border-color)' }}>
                        <td style={{ textAlign: 'left', padding: '0.85rem' }}>TOTAL / PERIOD SUMMARY</td>
                        <td style={{ textAlign: 'right' }}>-</td>
                        <td style={{ textAlign: 'right', color: '#16a34a' }}>
                          ₹{yearlyTotal.totalMoneyReceived.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td style={{ textAlign: 'right', color: '#dc2626' }}>
                          ₹{yearlyTotal.totalSpent.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td style={{ textAlign: 'right', color: 'var(--accent-primary)', fontSize: '1.05rem' }}>
                          ₹{yearlyTotal.closingBalance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    </tfoot>
                  )}
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: EMPLOYEE MONTHLY REPORT */}
          {activeTab === 'employee_report' && (
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1.1rem', margin: 0, fontWeight: 700 }}>
                  EMPLOYEE MONTHLY ATTENDANCE REPORT ({employeeReport.length} Employees)
                </h3>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  Department: {department}
                </span>
              </div>

              <div style={{
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: 'var(--radius-sm)',
                padding: '0.65rem 1rem',
                marginBottom: '1rem',
                fontSize: '0.8rem',
                color: 'var(--text-secondary)'
              }}>
                ℹ️ Individual attendance counts strictly track employee-attributed breakfast entries. Historical records without employee tracking (<code>employee_id = null</code>) are excluded from employee attendance metrics and accounted for in financial expense summaries.
              </div>

              <div className="table-container">
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th>Employee ID</th>
                      <th>Name</th>
                      <th>Department</th>
                      <th>Designation</th>
                      <th>Type</th>
                      <th>Perm. Non-Taker</th>
                      <th style={{ textAlign: 'right' }}>Total Days</th>
                      <th style={{ textAlign: 'right' }}>Taken</th>
                      <th style={{ textAlign: 'right' }}>Not Taken</th>
                      <th style={{ textAlign: 'right' }}>No Response</th>
                      <th>Reason Breakdown</th>
                    </tr>
                  </thead>
                  <tbody>
                    {employeeReport.length === 0 ? (
                      <tr>
                        <td colSpan="11" style={{ textAlign: 'center', padding: '2.5rem' }}>
                          No employee records match the selected filter.
                        </td>
                      </tr>
                    ) : (
                      employeeReport.map(emp => (
                        <tr key={emp.employeeId}>
                          <td><strong style={{ color: 'var(--text-primary)' }}>{emp.employeeId}</strong></td>
                          <td>{emp.name}</td>
                          <td>{emp.department}</td>
                          <td>{emp.designation}</td>
                          <td>
                            <span className={`badge ${emp.participationType === 'NORMAL' ? 'badge-success' : 'badge-warning'}`}>
                              {emp.participationType}
                            </span>
                          </td>
                          <td>
                            <span className={`badge ${emp.isPermanentNotTaking ? 'badge-info' : 'badge-secondary'}`}>
                              {emp.isPermanentNotTaking ? 'YES' : 'NO'}
                            </span>
                          </td>
                          <td style={{ textAlign: 'right' }}>{emp.totalDays}</td>
                          <td style={{ textAlign: 'right' }}><strong style={{ color: '#16a34a' }}>{emp.takenCount}</strong></td>
                          <td style={{ textAlign: 'right' }}><strong style={{ color: '#dc2626' }}>{emp.notTakenCount}</strong></td>
                          <td style={{ textAlign: 'right' }}><span style={{ color: '#eab308' }}>{emp.noResponseCount}</span></td>
                          <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', maxWidth: '250px' }}>
                            {Object.entries(emp.reasonBreakdown || {}).map(([reason, count]) => (
                              <div key={reason} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', padding: '0.1rem 0' }}>
                                <span>{reason}:</span>
                                <strong style={{ color: 'var(--text-primary)' }}>{count}</strong>
                              </div>
                            ))}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: ORDER SUMMARY */}
          {activeTab === 'order_summary' && (
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                <h3 style={{ fontSize: '1.1rem', margin: 0, fontWeight: 700 }}>
                  BREAKFAST ORDER SUMMARY ({orderSummary.length} Orders)
                </h3>
              </div>

              <div className="table-container">
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th>Order ID</th>
                      <th>Business Date</th>
                      <th>Order Type</th>
                      <th>Order Title</th>
                      <th style={{ textAlign: 'right' }}>Emp Count</th>
                      <th>Breakfast Items</th>
                      <th>Common Items</th>
                      <th style={{ textAlign: 'right' }}>Total Cost</th>
                      <th>Created By</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orderSummary.length === 0 ? (
                      <tr>
                        <td colSpan="9" style={{ textAlign: 'center', padding: '2.5rem' }}>
                          No breakfast orders found for the selected period.
                        </td>
                      </tr>
                    ) : (
                      orderSummary.map((ord, idx) => (
                        <tr key={ord.orderId || idx}>
                          <td><strong style={{ color: 'var(--text-primary)' }}>{ord.orderId}</strong></td>
                          <td>{ord.businessDate}</td>
                          <td>
                            <span className={`badge ${
                              ord.orderType === 'HISTORICAL BREAKFAST' ? 'badge-historical' :
                              ord.orderType === 'DAILY BREAKFAST' ? 'badge-primary' : 'badge-info'
                            }`}>
                              {ord.orderType}
                            </span>
                          </td>
                          <td>{ord.orderTitle}</td>
                          <td style={{ textAlign: 'right' }}>
                            {ord.orderType === 'HISTORICAL BREAKFAST' ? (
                              <span style={{ fontSize: '0.75rem', color: '#7c3aed', fontWeight: 600 }}>Not Recorded</span>
                            ) : (
                              ord.applicableCount
                            )}
                          </td>
                          <td style={{ fontSize: '0.82rem', maxWidth: '240px' }}>{ord.breakfastItems || '-'}</td>
                          <td style={{ fontSize: '0.82rem', maxWidth: '200px' }}>{ord.commonItems || '-'}</td>
                          <td style={{ textAlign: 'right', fontWeight: 700, color: 'var(--accent-primary)' }}>
                            ₹{ord.totalCost.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </td>
                          <td>{ord.createdBy}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 4: MONEY TRANSACTIONS */}
          {activeTab === 'money_transactions' && (
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                <h3 style={{ fontSize: '1.1rem', margin: 0, fontWeight: 700 }}>
                  BREAKFAST MONEY TRANSACTIONS ({moneyTransactions.length} Transactions)
                </h3>
              </div>

              <div className="table-container">
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th>Txn ID</th>
                      <th>Date</th>
                      <th>Time</th>
                      <th>Type</th>
                      <th style={{ textAlign: 'right' }}>Amount</th>
                      <th style={{ textAlign: 'right' }}>Balance After</th>
                      <th>Reference Type</th>
                      <th>Description</th>
                      <th>Created By</th>
                    </tr>
                  </thead>
                  <tbody>
                    {moneyTransactions.length === 0 ? (
                      <tr>
                        <td colSpan="9" style={{ textAlign: 'center', padding: '2.5rem' }}>
                          No transaction ledger history found for the selected period.
                        </td>
                      </tr>
                    ) : (
                      moneyTransactions.map(t => (
                        <tr key={t.transactionId}>
                          <td><strong style={{ color: 'var(--text-primary)', fontFamily: 'monospace' }}>{t.transactionId}</strong></td>
                          <td>{t.transactionDate}</td>
                          <td>{t.transactionTime}</td>
                          <td>
                            <span className={`badge ${
                              t.type === 'MONEY_RECEIVED' ? 'badge-success' :
                              t.type === 'BREAKFAST_EXPENSE' ? 'badge-danger' :
                              'badge-warning'
                            }`}>
                              {t.type}
                            </span>
                          </td>
                          <td style={{ textAlign: 'right', fontWeight: 600, color: t.type === 'MONEY_RECEIVED' ? '#16a34a' : '#dc2626' }}>
                            ₹{t.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </td>
                          <td style={{ textAlign: 'right', fontWeight: 700 }}>
                            ₹{t.balanceAfterTransaction.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </td>
                          <td>{t.referenceType}</td>
                          <td style={{ fontSize: '0.82rem', maxWidth: '240px' }}>{t.description}</td>
                          <td>{t.createdBy}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ReportsPage;
