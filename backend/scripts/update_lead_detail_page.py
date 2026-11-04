import os

lead_detail_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend", "src", "pages", "CrmLeadDetailPage.jsx"
)

with open(lead_detail_path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace("\r\n", "\n")

# 1. Imports
import_target = """import OpportunityDetailModal from '../modules/crm/components/OpportunityDetailModal';"""
import_replacement = """import OpportunityDetailModal from '../modules/crm/components/OpportunityDetailModal';
import NextActivityPanel from '../modules/crm/components/NextActivityPanel';
import UnifiedTimeline from '../modules/crm/components/UnifiedTimeline';
import CustomerResponseModal from '../modules/crm/components/CustomerResponseModal';
import CompleteActivityModal from '../modules/crm/components/CompleteActivityModal';
import ActivityActionModal from '../modules/crm/components/ActivityActionModal';"""

assert import_target in c, "import_target not found!"
c = c.replace(import_target, import_replacement)

# 2. State & fetchLeadDetails
state_target = """  const [lead, setLead] = useState(null);
  const [communications, setCommunications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successNotification, setSuccessNotification] = useState(null);
  const [warningNotification, setWarningNotification] = useState(null);

  // Modals
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [isCommModalOpen, setIsCommModalOpen] = useState(false);
  const [isQualifyWizardOpen, setIsQualifyWizardOpen] = useState(false);
  const [viewContactModal, setViewContactModal] = useState(null);
  const [viewOpportunityModal, setViewOpportunityModal] = useState(null);
  const [selectedOppIdForDetail, setSelectedOppIdForDetail] = useState(null);

  // Add Opportunity Modal State
  const [isAddOppModalOpen, setIsAddOppModalOpen] = useState(false);
  const [newOppFormData, setNewOppFormData] = useState({
    name: '',
    estimatedValue: '',
    stage: 'Qualify',
    businessArea: 'Biogas',
    subStatus: '',
    description: '',
    expectedCloseDate: ''
  });
  const [submittingOpp, setSubmittingOpp] = useState(false);
  const [addOppError, setAddOppError] = useState(null);

  const canEdit = hasPermission('crm.lead.edit');
  const canUpdateStatus = hasPermission('crm.lead.status.update');
  const canLogComm = hasPermission('crm.communication.create') || hasPermission('crm.lead.edit');

  const fetchLeadDetails = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [leadRes, commsRes] = await Promise.all([
        crmService.getLeadById(id),
        crmService.getLeadCommunications(id)
      ]);

      if (leadRes.data.success) {
        setLead(leadRes.data.lead);
      }
      if (commsRes.data.success) {
        setCommunications(commsRes.data.communications || []);
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setError(`Lead with identifier "${id}" not found.`);
      } else {
        setError(err.response?.data?.message || 'Failed to load lead details. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }, [id]);"""

state_replacement = """  const [lead, setLead] = useState(null);
  const [communications, setCommunications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successNotification, setSuccessNotification] = useState(null);
  const [warningNotification, setWarningNotification] = useState(null);

  // Nurturing & Unified Timeline State
  const [nurturingState, setNurturingState] = useState(null);
  const [nextActivity, setNextActivity] = useState(null);
  const [timelineItems, setTimelineItems] = useState([]);
  const [timelineSort, setTimelineSort] = useState('desc');
  const [timelineFilter, setTimelineFilter] = useState('all');
  const [timelineLoading, setTimelineLoading] = useState(false);

  // Modals
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [isCommModalOpen, setIsCommModalOpen] = useState(false);
  const [isQualifyWizardOpen, setIsQualifyWizardOpen] = useState(false);
  const [viewContactModal, setViewContactModal] = useState(null);
  const [viewOpportunityModal, setViewOpportunityModal] = useState(null);
  const [selectedOppIdForDetail, setSelectedOppIdForDetail] = useState(null);

  // Nurturing Action Modals
  const [completeActivityModal, setCompleteActivityModal] = useState(null);
  const [actionActivityModal, setActionActivityModal] = useState(null);
  const [isCustomerResponseModalOpen, setIsCustomerResponseModalOpen] = useState(false);

  // Add Opportunity Modal State
  const [isAddOppModalOpen, setIsAddOppModalOpen] = useState(false);
  const [newOppFormData, setNewOppFormData] = useState({
    name: '',
    estimatedValue: '',
    stage: 'Qualify',
    businessArea: 'Biogas',
    subStatus: '',
    description: '',
    expectedCloseDate: ''
  });
  const [submittingOpp, setSubmittingOpp] = useState(false);
  const [addOppError, setAddOppError] = useState(null);

  const canEdit = hasPermission('crm.lead.edit');
  const canUpdateStatus = hasPermission('crm.lead.status.update');
  const canLogComm = hasPermission('crm.communication.create') || hasPermission('crm.lead.edit');

  const fetchLeadDetails = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [leadRes, nurturingRes, nextActRes, timelineRes] = await Promise.all([
        crmService.getLeadById(id),
        crmService.getLeadNurturing(id).catch(() => ({ data: { success: false } })),
        crmService.getLeadNextActivity(id).catch(() => ({ data: { success: false } })),
        crmService.getLeadTimeline(id, { sort: timelineSort, filter: timelineFilter }).catch(() => ({ data: { success: false, timeline: [] } }))
      ]);

      if (leadRes.data?.success) {
        setLead(leadRes.data.lead);
      }
      if (nurturingRes.data?.success) {
        setNurturingState(nurturingRes.data.nurturing);
      }
      if (nextActRes.data?.success) {
        setNextActivity(nextActRes.data.nextActivity);
      }
      if (timelineRes.data?.success) {
        setTimelineItems(timelineRes.data.timeline || []);
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setError(`Lead with identifier "${id}" not found.`);
      } else {
        setError(err.response?.data?.message || 'Failed to load lead details. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }, [id, timelineSort, timelineFilter]);

  const handleTimelineFilterChange = async (filterKey) => {
    setTimelineFilter(filterKey);
    setTimelineLoading(true);
    try {
      const res = await crmService.getLeadTimeline(id, { sort: timelineSort, filter: filterKey });
      if (res.data?.success) {
        setTimelineItems(res.data.timeline || []);
      }
    } catch (err) {
      console.error('Failed to filter timeline:', err);
    } finally {
      setTimelineLoading(false);
    }
  };

  const handleTimelineSortChange = async (newSort) => {
    setTimelineSort(newSort);
    setTimelineLoading(true);
    try {
      const res = await crmService.getLeadTimeline(id, { sort: newSort, filter: timelineFilter });
      if (res.data?.success) {
        setTimelineItems(res.data.timeline || []);
      }
    } catch (err) {
      console.error('Failed to sort timeline:', err);
    } finally {
      setTimelineLoading(false);
    }
  };

  const handlePauseNurturing = async () => {
    if (!window.confirm('Pause automatic lead nurturing cadence for this lead? Pending reminder emails and calls will be put on hold.')) return;
    try {
      const res = await crmService.pauseNurturing(id, { reason: 'User paused cadence from Lead Details panel.' });
      if (res.data.success) {
        fetchLeadDetails();
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to pause nurturing.');
    }
  };

  const handleResumeNurturing = async () => {
    try {
      const res = await crmService.resumeNurturing(id, {});
      if (res.data.success) {
        fetchLeadDetails();
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to resume nurturing.');
    }
  };"""

assert state_target in c, "state_target not found!"
c = c.replace(state_target, state_replacement)

# 3. Replace old communications list with NextActivityPanel and UnifiedTimeline
timeline_target = """          {/* Chronological Communication History Timeline */}
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <MessageSquare size={18} color="var(--accent-primary)" />
                <span>Communication History ({communications.length})</span>
              </h3>

              {canLogComm && (
                <button
                  onClick={() => setIsCommModalOpen(true)}
                  className="btn btn-secondary"
                  style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                >
                  <Plus size={13} />
                  <span>Log Interaction</span>
                </button>
              )}
            </div>

            {communications.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--text-muted)' }}>
                <MessageSquare size={32} color="#cbd5e1" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                <p style={{ margin: 0, fontSize: '0.875rem' }}>No communication events recorded yet.</p>
                <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.75rem' }}>
                  Log client calls, introductory emails, or internal discussions to build a complete customer interaction audit trail.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {communications.map(item => (
                  <div
                    key={item.id}
                    style={{
                      padding: '1rem',
                      background: '#ffffff',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.4rem',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          background: '#eff6ff',
                          color: '#1d4ed8'
                        }}>
                          {item.channel}
                        </span>
                        <strong style={{ fontSize: '0.9rem', color: '#0f172a' }}>
                          {item.eventType}
                        </strong>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {formatDateTime(item.communicationDate || item.createdAt)}
                      </span>
                    </div>

                    <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.875rem', color: '#334155', lineHeight: 1.5 }}>
                      {item.summary}
                    </p>

                    {(item.outcome || item.nextAction) && (
                      <div style={{
                        marginTop: '0.4rem',
                        padding: '0.5rem 0.75rem',
                        background: '#f8fafc',
                        borderRadius: '6px',
                        fontSize: '0.8rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.25rem'
                      }}>
                        {item.outcome && (
                          <div>
                            <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Outcome: </span>
                            <span>{item.outcome}</span>
                          </div>
                        )}
                        {item.nextAction && (
                          <div>
                            <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Next Action: </span>
                            <span>{item.nextAction}</span>
                            {item.followUpDate && (
                              <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                                (Follow-up: {formatDateTime(item.followUpDate)})
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                      Logged by <strong>{item.loggedBy?.name || item.loggedBy?.username || 'System User'}</strong> • ID: {item.communicationId}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>"""

timeline_replacement = """          {/* Next Activity Panel (Microsoft Dynamics 365 Sales Hub approach) */}
          <NextActivityPanel
            nextActivity={nextActivity}
            nurturingState={nurturingState}
            onCompleteActivity={(act) => setCompleteActivityModal(act)}
            onRescheduleActivity={(act) => setActionActivityModal({ activity: act, actionType: 'reschedule' })}
            onSkipActivity={(act) => setActionActivityModal({ activity: act, actionType: 'skip' })}
            onPauseNurturing={handlePauseNurturing}
            onResumeNurturing={handleResumeNurturing}
            canEdit={canEdit}
          />

          {/* Unified Activity Timeline (Dynamics 365 Sales Hub stacked layout) */}
          <UnifiedTimeline
            timelineItems={timelineItems}
            loading={timelineLoading}
            sortOrder={timelineSort}
            onSortChange={handleTimelineSortChange}
            activeFilter={timelineFilter}
            onFilterChange={handleTimelineFilterChange}
            onOpenLogInteraction={() => setIsCommModalOpen(true)}
            onOpenRecordResponse={() => setIsCustomerResponseModalOpen(true)}
            onCompleteActivity={(act) => setCompleteActivityModal(act)}
            onRescheduleActivity={(act) => setActionActivityModal({ activity: act, actionType: 'reschedule' })}
            onSkipActivity={(act) => setActionActivityModal({ activity: act, actionType: 'skip' })}
            onRefresh={() => fetchLeadDetails()}
            canEdit={canEdit}
          />"""

assert timeline_target in c, "timeline_target not found!"
c = c.replace(timeline_target, timeline_replacement)

# 4. Modals at bottom of page
modals_target = """      {/* Communication Modal */}
      {isCommModalOpen && (
        <CommunicationModal
          isOpen={isCommModalOpen}
          onClose={() => setIsCommModalOpen(false)}
          leadId={lead.id}
          leadName={lead.leadName}
          onCommunicationLogged={() => fetchLeadDetails()}
        />
      )}"""

modals_replacement = """      {/* Communication Modal */}
      {isCommModalOpen && (
        <CommunicationModal
          isOpen={isCommModalOpen}
          onClose={() => setIsCommModalOpen(false)}
          leadId={lead.id}
          leadName={lead.leadName}
          onCommunicationLogged={() => fetchLeadDetails()}
        />
      )}

      {/* Complete Nurturing Activity Modal */}
      {completeActivityModal && (
        <CompleteActivityModal
          isOpen={Boolean(completeActivityModal)}
          onClose={() => setCompleteActivityModal(null)}
          activity={completeActivityModal}
          lead={lead}
          onActivityCompleted={() => fetchLeadDetails()}
        />
      )}

      {/* Reschedule or Skip Activity Modal */}
      {actionActivityModal && (
        <ActivityActionModal
          isOpen={Boolean(actionActivityModal)}
          onClose={() => setActionActivityModal(null)}
          activity={actionActivityModal.activity}
          actionType={actionActivityModal.actionType}
          lead={lead}
          onActionSuccess={() => fetchLeadDetails()}
        />
      )}

      {/* Record Customer Response Modal */}
      {isCustomerResponseModalOpen && (
        <CustomerResponseModal
          isOpen={isCustomerResponseModalOpen}
          onClose={() => setIsCustomerResponseModalOpen(false)}
          lead={lead}
          onResponseRecorded={() => fetchLeadDetails()}
        />
      )}"""

assert modals_target in c, "modals_target not found!"
c = c.replace(modals_target, modals_replacement)

with open(lead_detail_path, "w", encoding="utf-8") as f:
    f.write(c)

print("Updated CrmLeadDetailPage.jsx successfully with NextActivityPanel, UnifiedTimeline, and modals!")

